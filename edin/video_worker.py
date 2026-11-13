"""Worker do `edin animar` (foto -> clipe de vídeo com Wan2.2-TI2V-5B): roda no venv do gerador de imagem
(~/.local/share/edin/imagem/venv, PyTorch CUDA + diffusers), chamado pelo edin por subprocesso com `python -I`.
Autocontido: não importa nada do pacote edin.

    python -I video_worker.py preparar <job.json>     (pesos fp32 do transformer -> bf16, uma vez só)
    python -I video_worker.py texto <job.json>        (UMT5-XXL: prompts -> embeddings)
    python -I video_worker.py gerar <job.json>        (VAE codifica a foto; transformer gera os latentes)
    python -I video_worker.py decodificar <job.json>  (VAE: latentes -> quadros -> .mp4 nativo)
    python -I video_worker.py info

Memória (RTX 4050 de 6 GB, 14 GB de RAM): o modelo tem 5 B de parâmetros (10 GB em bf16) e o codificador de texto
UMT5-XXL tem 5,7 B (11,4 GB). Nenhum dos dois cabe inteiro nem na VRAM nem na RAM livre. Cada um é montado
"vazio" (device meta) e cada bloco é lido do safetensors (mmap) e posto na GPU só na hora de rodar, e solto logo
depois ("streaming" por bloco). Os blocos que cabem ficam fixos na GPU (sem leitura nos passos seguintes).
A RAM fica em ~2 GB por processo (o resto é cache de disco, que o kernel recupera). Cada etapa é um processo,
então cada uma começa com a VRAM inteira livre.

Progresso e resultados saem no stdout como linhas JSON ({"evento": ...}); avisos das bibliotecas vão para o stderr.
"""
from __future__ import annotations

import gc
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

# negativo padrão do Wan2.2 (o modelo foi treinado com ele, em chinês): cores estouradas, estático, borrado,
# legendas, pior qualidade, JPEG, feio, mutilado, dedos a mais, mãos e rostos mal desenhados, deformado,
# membros malformados, dedos fundidos, imagem parada, fundo bagunçado, três pernas, muita gente ao fundo,
# andando de costas
NEGATIVO_WAN = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
                "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，"
                "手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")

# módulos que o Wan mantém em fp32 (iguais ao _keep_in_fp32_modules do diffusers)
FP32 = ("rope", "time_embedder", "scale_shift_table", "norm1", "norm2", "norm3")


def emit(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def log(msg):
    print(msg, file=sys.stderr, flush=True)


_PICO_ANON = [0]


def _amostra_ram():
    """Thread que guarda o pico de RssAnon (memória própria do processo). O VmHWM conta também as páginas dos
    safetensors mapeados (mmap), que são cache de disco e o kernel recupera quando precisa."""
    import threading

    def run():
        while True:
            try:
                for ln in Path("/proc/self/status").read_text().splitlines():
                    if ln.startswith("RssAnon:"):
                        _PICO_ANON[0] = max(_PICO_ANON[0], int(ln.split()[1]) // 1024)
            except OSError:
                pass
            time.sleep(0.2)

    threading.Thread(target=run, daemon=True).start()


def _rss_mb() -> int:
    """Pico de memória anônima (RAM de verdade) deste processo, em MB."""
    return _PICO_ANON[0]


def _vram():
    import torch

    return round(torch.cuda.max_memory_allocated() / 2**20)


# ---------------------------------------------------------------------------------------------- pesos por bloco
class Fonte:
    """Lê tensores de um safetensors (arquivo único ou com index.json) por prefixo, sem carregar o resto (mmap)."""

    def __init__(self, pasta: Path, nome: str):
        from safetensors import safe_open

        idx = pasta / f"{nome}.safetensors.index.json"
        if idx.exists():
            mapa = json.loads(idx.read_text())["weight_map"]
        else:
            with safe_open(str(pasta / f"{nome}.safetensors"), framework="pt") as f:
                mapa = {k: f"{nome}.safetensors" for k in f.keys()}
        self.mapa = mapa
        self.abertos = {arq: safe_open(str(pasta / arq), framework="pt") for arq in set(mapa.values())}

    def chaves(self, prefixo: str = "") -> list[str]:
        return [k for k in self.mapa if k.startswith(prefixo)]

    def tensor(self, k: str):
        return self.abertos[self.mapa[k]].get_tensor(k)


def _dtype_de(nome: str, padrao):
    import torch

    return torch.float32 if any(p in nome.split(".") for p in FP32) else padrao


def _poe(mod, nome: str, t):
    """Põe o tensor t no lugar do parâmetro/buffer `nome` do módulo (troca o tensor meta pelo de verdade)."""
    import torch

    *cam, folha = nome.split(".")
    m = mod
    for c in cam:
        m = getattr(m, c)
    if folha in m._parameters:
        m._parameters[folha] = torch.nn.Parameter(t, requires_grad=False)
    else:
        m._buffers[folha] = t


def _esvazia(mod):
    """Devolve os parâmetros do módulo para o device meta (solta a VRAM)."""
    import torch

    for sub in mod.modules():
        for k, p in list(sub._parameters.items()):
            if p is not None and p.device.type != "meta":
                sub._parameters[k] = torch.nn.Parameter(torch.empty_like(p, device="meta"), requires_grad=False)


class Streamer:
    """Liga ganchos nos blocos de `blocos` (ModuleList): antes de cada bloco rodar, lê os pesos dele da Fonte e põe
    na GPU; depois, solta. Os `fixos` primeiros blocos ficam na GPU de vez. Um thread lê o próximo bloco do disco
    para um de dois buffers de memória fixada (pinned, reaproveitados) enquanto a GPU calcula o atual; a cópia
    para a GPU é assíncrona, num stream próprio. Leitura de disco, cópia e cálculo andam juntos."""

    def __init__(self, blocos, prefixo: str, fonte: Fonte, dev, dtype, fixos: int = 0, converte=None,
                 circular: bool = True):
        import threading
        import torch

        self.blocos, self.prefixo, self.fonte, self.dev, self.dtype = blocos, prefixo, fonte, dev, dtype
        self.n = len(blocos)
        self.fixos = fixos
        self.circular = circular  # várias passadas (difusão): ao fim do último bloco, já lê o primeiro de novo
        self.converte = converte or (lambda nome, t: t.to(_dtype_de(nome, dtype)))
        self.lido_s = 0.0
        self.copia_s = 0.0
        self.bytes = 0
        self._pref: dict[int, dict] = {}
        self._th = None
        self._lock = threading.Lock()
        self.stream = torch.cuda.Stream()
        # dois buffers fixados do tamanho de um bloco (alinhado a 256 bytes por tensor)
        tam = 0
        for k in fonte.chaves(f"{prefixo}{fixos if fixos < self.n else 0}."):
            t = self.converte(k, fonte.tensor(k))
            tam += -(-t.numel() * t.element_size() // 256) * 256
        self._buf = [torch.empty(tam, dtype=torch.uint8).pin_memory() for _ in range(2)] if fixos < self.n else []
        self._ev = [None, None]
        self._slot_de: dict[int, int] = {}
        self._prox_slot = 0
        for i, b in enumerate(blocos):
            if i < fixos:
                self._carrega(i)
            else:
                b.register_forward_pre_hook(self._antes(i))
                b.register_forward_hook(self._depois(i))

    def _le_cpu(self, i: int) -> dict:
        """Lê o bloco i do disco (mmap) para um buffer fixado: devolve {nome: vista do buffer}."""
        t0 = time.time()
        p = f"{self.prefixo}{i}."
        d = {}
        if not self._buf:  # bloco fixo (lido uma vez): memória comum
            for k in self.fonte.chaves(p):
                d[k[len(p):]] = self.converte(k, self.fonte.tensor(k)).contiguous()
            self.lido_s += time.time() - t0
            return d
        s = self._prox_slot
        self._prox_slot = 1 - s
        if self._ev[s] is not None:
            self._ev[s].synchronize()  # a cópia anterior que saiu deste buffer já terminou
        buf, off = self._buf[s], 0
        for k in self.fonte.chaves(p):
            t = self.converte(k, self.fonte.tensor(k))
            nb = t.numel() * t.element_size()
            v = buf[off:off + nb].view(t.dtype).view(t.shape)
            v.copy_(t)
            d[k[len(p):]] = v
            off += -(-nb // 256) * 256
        self._slot_de[i] = s
        self.lido_s += time.time() - t0
        return d

    def _prefetch(self, i: int):
        import threading

        if i >= self.n or i < self.fixos or i in self._pref:
            return

        def run():
            d = self._le_cpu(i)
            with self._lock:
                self._pref[i] = d

        self._th = threading.Thread(target=run, daemon=True)
        self._th.start()

    def _carrega(self, i: int):
        import torch

        if self._th is not None:
            self._th.join()
            self._th = None
        with self._lock:
            d = self._pref.pop(i, None)
        if d is None:
            d = self._le_cpu(i)
        t0 = time.time()
        with torch.cuda.stream(self.stream):
            g = {k: v.to(self.dev, non_blocking=True) for k, v in d.items()}
            if i in self._slot_de:
                ev = torch.cuda.Event()
                ev.record(self.stream)
                self._ev[self._slot_de.pop(i)] = ev
        atual = torch.cuda.current_stream()
        atual.wait_stream(self.stream)
        for k, v in g.items():
            # o tensor nasceu no stream de cópia e é usado no stream de cálculo: sem isto o alocador reaproveitava
            # a memória dele para a cópia do bloco seguinte enquanto o cálculo ainda lia (vídeo virava ruído)
            v.record_stream(atual)
            _poe(self.blocos[i], k, v)
            self.bytes += v.numel() * v.element_size()
        self.copia_s += time.time() - t0

    def fecha(self):
        if self._th is not None:
            self._th.join()
            self._th = None
        self._pref.clear()

    def _antes(self, i):
        def f(mod, args):
            self._carrega(i)
            prox = i + 1 if i + 1 < self.n else (self.fixos if self.circular else None)
            if prox is not None:
                self._prefetch(prox)
        return f

    def _depois(self, i):
        def f(mod, args, out):
            _esvazia(mod)
            return out
        return f


def _fixos_que_cabem(bloco_mb: float, reserva_mb: float, maximo: int) -> int:
    import torch

    livre = torch.cuda.mem_get_info()[0] / 2**20
    n = int((livre - reserva_mb) // bloco_mb)
    return max(0, min(maximo, n))


# ---------------------------------------------------------------------------------------------- preparar
def preparar(job_path: str):
    """Transformer fp32 do repositório oficial (20 GB) -> bf16 (10 GB), mantendo em fp32 os módulos que o Wan
    mantém em fp32. Um shard por vez (RAM ~3 GB)."""
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    job = json.loads(Path(job_path).read_text())
    src, dst = Path(job["origem"]), Path(job["destino"])
    dst.mkdir(parents=True, exist_ok=True)
    idx = json.loads((src / "diffusion_pytorch_model.safetensors.index.json").read_text())
    mapa_novo = {}
    for arq in sorted(set(idx["weight_map"].values())):
        alvo = dst / arq
        mapa_novo.update({k: arq for k, v in idx["weight_map"].items() if v == arq})
        if alvo.exists() and alvo.stat().st_size > 0:
            continue
        t0 = time.time()
        d = {}
        with safe_open(str(src / arq), framework="pt") as f:
            for k in f.keys():
                d[k] = f.get_tensor(k).to(_dtype_de(k, torch.bfloat16)).contiguous()
        tmp = alvo.with_suffix(".tmp")
        save_file(d, str(tmp), metadata={"format": "pt"})
        tmp.rename(alvo)
        del d
        gc.collect()
        emit(evento="shard", arquivo=arq, segundos=round(time.time() - t0, 1))
    (dst / "diffusion_pytorch_model.safetensors.index.json").write_text(json.dumps({"weight_map": mapa_novo}))
    import shutil

    shutil.copy(src / "config.json", dst / "config.json")
    emit(evento="fim", ram_mb=_rss_mb())


# ---------------------------------------------------------------------------------------------- texto
def _limpa(t: str) -> str:
    import html

    try:
        import ftfy

        t = ftfy.fix_text(t)
    except ImportError:
        pass
    t = html.unescape(html.unescape(t)).strip()
    return re.sub(r"\s+", " ", t).strip()


def texto(job_path: str):
    """UMT5-XXL em bf16, um bloco por vez na GPU. Todos os prompts do lote passam juntos por cada bloco, então os
    11 GB de pesos são lidos uma vez só por lote."""
    import torch
    from accelerate import init_empty_weights
    from transformers import AutoConfig, AutoTokenizer, UMT5EncoderModel

    job = json.loads(Path(job_path).read_text())
    base = Path(job["modelo"])
    cuda = torch.device("cuda")
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(str(base / "tokenizer"), local_files_only=True)
    cfg = AutoConfig.from_pretrained(str(base / "text_encoder"), local_files_only=True)
    with init_empty_weights(include_buffers=False):
        te = UMT5EncoderModel(cfg)
    te = te.eval()
    fonte = Fonte(base / "text_encoder", "model")
    # tudo que não é bloco (embedding de 256 mil tokens x 4096 = 2,1 GB, norma final) vai para a GPU
    for k in fonte.chaves():
        if ".block." not in k:
            _poe(te, k, fonte.tensor(k).to(cuda, torch.bfloat16))
    if te.encoder.embed_tokens is not te.shared:
        te.encoder.embed_tokens = te.shared
    st = Streamer(te.encoder.block, "encoder.block.", fonte, cuda, torch.bfloat16,
                  converte=lambda n, t: t.to(torch.bfloat16), circular=False)
    textos = [_limpa(p) for p in job["prompts"]]
    L = int(job.get("max_tokens", 512))
    torch.cuda.reset_peak_memory_stats()
    out = {}
    with torch.inference_mode():
        ti = tok(textos, padding="max_length", max_length=L, truncation=True, add_special_tokens=True,
                 return_attention_mask=True, return_tensors="pt")
        lens = ti.attention_mask.gt(0).sum(dim=1)
        h = te(ti.input_ids.to(cuda), ti.attention_mask.to(cuda)).last_hidden_state
        for p, e, n in zip(job["prompts"], h, lens):
            out[p] = e[: int(n)].to("cpu", torch.bfloat16).clone()
            if int(n) >= L:
                log(f"[edin animar] aviso: prompt cortado em {L} tokens: {p[:60]}...")
    st.fecha()
    torch.save(out, job["saida"])
    emit(evento="fim", segundos=round(time.time() - t0, 1), prompts=len(textos), vram_mb=_vram(),
         ram_mb=_rss_mb(), leitura_s=round(st.lido_s, 1), tokens=[int(x) for x in lens])


# ---------------------------------------------------------------------------------------------- VAE
def _vae(base: Path, dev, dtype):
    from diffusers import AutoencoderKLWan

    return AutoencoderKLWan.from_pretrained(str(base / "vae"), torch_dtype=dtype, local_files_only=True).to(dev).eval()


def _foto(caminho: str, w: int, h: int):
    """Foto -> tensor [-1, 1] (1, 3, h, w), cobrindo o quadro (recorte central, sem esticar)."""
    import numpy as np
    import torch
    from PIL import Image

    im = Image.open(caminho).convert("RGB")
    s = max(w / im.width, h / im.height)
    nw, nh = max(w, round(im.width * s)), max(h, round(im.height * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    im = im.crop((x0, y0, x0 + w, y0 + h))
    a = torch.from_numpy(np.asarray(im).copy()).permute(2, 0, 1).float() / 127.5 - 1
    return a[None]


# ---------------------------------------------------------------------------------------------- forward compacto
# O TI2V-5B condiciona pela primeira imagem dando timestep 0 aos tokens do 1º quadro latente e t aos outros.
# O pipeline do diffusers faz isso com um timestep POR TOKEN: a modulação (6 x 3072 em fp32 por token) chega a
# 1,2 GB com 17 mil tokens (3 s) e é recriada em cada bloco: não cabe em 6 GB. Como só há um valor por quadro
# latente, aqui a modulação é calculada por quadro e aplicada por broadcast (B, F, T, D): mesma conta, ~1/900 da
# memória. O FFN também roda em fatias de tokens (mesma conta, pico menor).
FFN_FATIAS = 4


def _bloco_forward(self, h, ctx, temb, rot):
    B, N, D = h.shape
    Fq = temb.shape[1]
    T = N // Fq
    mod = self.scale_shift_table.unsqueeze(0) + temb.float()  # (B, F, 6, D)
    sh, sc, g, csh, csc, cg = (m.squeeze(2)[:, :, None, :] for m in mod.chunk(6, dim=2))  # (B, F, 1, D)

    def q(x):
        return x.view(B, Fq, T, D)

    n = (q(self.norm1(h.float())) * (1 + sc) + sh).view(B, N, D).type_as(h)
    a = self.attn1(n, None, None, rot)
    h = (q(h.float()) + q(a) * g).view(B, N, D).type_as(h)
    del n, a
    n = self.norm2(h.float()).type_as(h)
    h = h + self.attn2(n, ctx, None, None)
    del n
    n = (q(self.norm3(h.float())) * (1 + csc) + csh).view(B, N, D).type_as(h)
    passo = -(-N // FFN_FATIAS)
    ff = torch_cat([self.ffn(n[:, i:i + passo]) for i in range(0, N, passo)], dim=1)
    del n
    return (q(h.float()) + q(ff.float()) * cg).view(B, N, D).type_as(h)


def torch_cat(xs, dim):
    import torch

    return torch.cat(xs, dim=dim)


def _wan_forward(tr, x, tq, ctx):
    """Forward do WanTransformer3DModel com timestep por quadro latente: x (B, C, F, H, W), tq (B, F)."""
    B, C, F, H, W = x.shape
    p_t, p_h, p_w = tr.config.patch_size
    rot = tr.rope(x)
    h = tr.patch_embedding(x).flatten(2).transpose(1, 2).contiguous()
    temb, tproj, ctx, _ = tr.condition_embedder(tq.flatten(), ctx, None, timestep_seq_len=F // p_t)
    tproj = tproj.unflatten(2, (6, -1))  # (B, F, 6, D)
    for b in tr.blocks:
        h = b(h, ctx, tproj, rot)
    N, D = h.shape[1], h.shape[2]
    Fq = tproj.shape[1]
    shift, scale = (tr.scale_shift_table.unsqueeze(0) + temb.unsqueeze(2)).chunk(2, dim=2)  # (B, F, 1, D)
    h = (tr.norm_out(h.float()).view(B, Fq, N // Fq, D) * (1 + scale) + shift).view(B, N, D).type_as(h)
    h = tr.proj_out(h)
    h = h.reshape(B, F // p_t, H // p_h, W // p_w, p_t, p_h, p_w, -1).permute(0, 7, 1, 4, 2, 5, 3, 6)
    return h.flatten(6, 7).flatten(4, 5).flatten(2, 3)


# ---------------------------------------------------------------------------------------------- gerar
def gerar(job_path: str):
    import torch
    from accelerate import init_empty_weights
    from diffusers import UniPCMultistepScheduler, WanTransformer3DModel

    job = json.loads(Path(job_path).read_text())
    base = Path(job["modelo"])
    cuda = torch.device("cuda")
    if not torch.cuda.is_available():
        raise SystemExit("PyTorch sem CUDA: o edin animar precisa de GPU NVIDIA")
    embs = torch.load(job["embeddings"], weights_only=True)
    t0 = time.time()

    # ---- 1) VAE codifica a primeira imagem de cada clipe (fp32, a VRAM está livre)
    vae = _vae(base, cuda, torch.float32)
    zm = torch.tensor(vae.config.latents_mean).view(1, -1, 1, 1, 1)
    zs = torch.tensor(vae.config.latents_std).view(1, -1, 1, 1, 1)
    conds = []
    with torch.inference_mode():
        for it in job["itens"]:
            img = _foto(it["foto"], it["w"], it["h"]).to(cuda)
            lat = vae.encode(img.unsqueeze(2)).latent_dist.mode().float().cpu()
            conds.append((lat - zm) / zs)
    del vae
    gc.collect()
    torch.cuda.empty_cache()
    t_vae = time.time() - t0

    # ---- 2) transformer montado vazio; o que não é bloco vai para a GPU, os blocos vêm do disco por streaming
    t1 = time.time()
    tdir = Path(job["transformer"])
    cfg = WanTransformer3DModel.load_config(str(tdir))
    with init_empty_weights(include_buffers=False):
        tr = WanTransformer3DModel.from_config(cfg)
    tr = tr.eval()  # sem .to(bf16): os buffers do RoPE ficam em fp32 e os pesos vêm com o dtype do arquivo
    from diffusers.models.transformers.transformer_wan import WanTransformerBlock

    WanTransformerBlock.forward = _bloco_forward
    for nome, b in list(tr.named_buffers()):
        _poe(tr, nome, b.to(cuda))
    fonte = Fonte(tdir, "diffusion_pytorch_model")
    for k in fonte.chaves():
        if not k.startswith("blocks."):
            _poe(tr, k, fonte.tensor(k).to(cuda, _dtype_de(k, torch.bfloat16)))
    n_blocos = len(tr.blocks)
    bloco_mb = sum(fonte.tensor(k).numel() for k in fonte.chaves("blocks.0.")) * 2 / 2**20
    # reserva de VRAM para as ativações: cresce com o número de tokens do vídeo (medida na RTX 4050)
    tokens_max = max(((it["frames"] - 1) // 4 + 1) * (it["h"] // 32) * (it["w"] // 32) for it in job["itens"])
    reserva = float(job.get("reserva_mb") or (800 + tokens_max * 0.05))
    fixos = job.get("fixos")
    if fixos is None:
        fixos = _fixos_que_cabem(bloco_mb, reserva, n_blocos)
    st = Streamer(tr.blocks, "blocks.", fonte, cuda, torch.bfloat16, fixos=int(fixos))
    t_carga = time.time() - t1
    log(f"[edin animar] transformer: {fixos}/{n_blocos} blocos fixos na GPU ({bloco_mb:.0f} MB cada), "
        f"reserva {reserva:.0f} MB, {tokens_max} tokens")
    emit(evento="carga", vae_s=round(t_vae, 1), transformer_s=round(t_carga, 1), fixos=int(fixos),
         blocos=n_blocos, tokens=tokens_max)

    # ---- 3) difusão
    res = []
    for i, it in enumerate(job["itens"]):
        torch.cuda.reset_peak_memory_stats()
        ts = time.time()
        F = (it["frames"] - 1) // 4 + 1
        H, W = it["h"] // 16, it["w"] // 16
        g = torch.Generator("cpu").manual_seed(int(it["seed"]))
        lat = torch.randn((1, 48, F, H, W), generator=g, dtype=torch.float32).to(cuda)
        cond = conds[i].to(cuda)
        mask = torch.ones((1, 1, F, H, W), device=cuda)
        mask[:, :, 0] = 0
        pe = embs[it["prompt"]]
        pe = torch.cat([pe, pe.new_zeros(512 - pe.shape[0], pe.shape[1])])[None].to(cuda)
        cfg_s = float(it.get("cfg", 5.0))
        ne = None
        if cfg_s > 1:
            ne = embs[it["negativo"]]
            ne = torch.cat([ne, ne.new_zeros(512 - ne.shape[0], ne.shape[1])])[None].to(cuda)

        def modelo(x, t):
            inp = ((1 - mask) * cond + mask * x).to(torch.bfloat16)
            tq = torch.full((1, F), float(t), device=cuda)
            tq[:, 0] = 0  # 1º quadro latente = a foto (já limpa)
            v = _wan_forward(tr, inp, tq, pe)
            if ne is not None:
                vu = _wan_forward(tr, inp, tq, ne)
                v = vu + cfg_s * (v - vu)
            return v.float()

        with torch.inference_mode():
            if it.get("amostrador") == "dmd":
                # DMD (FastWan): prevê o vídeo limpo em cada passo e re-sorteia ruído no nível do passo seguinte
                passos = [int(x) for x in it.get("passos_dmd", [1000, 757, 522])]
                for j, t in enumerate(passos):
                    tj = time.time()
                    sig = t / 1000.0
                    v = modelo(lat, torch.tensor(float(t), device=cuda))
                    x0 = lat - sig * v
                    if j + 1 < len(passos):
                        s2 = passos[j + 1] / 1000.0
                        ruido = torch.randn(lat.shape, generator=g, dtype=torch.float32).to(cuda)
                        lat = (1 - s2) * x0 + s2 * ruido
                    else:
                        lat = x0
                    emit(evento="passo", i=i, passo=j + 1, de=len(passos), segundos=round(time.time() - tj, 1))
            else:
                sch = UniPCMultistepScheduler.from_pretrained(str(base / "scheduler"), local_files_only=True)
                if it.get("shift"):
                    sch = UniPCMultistepScheduler.from_config(sch.config, flow_shift=float(it["shift"]))
                sch.set_timesteps(int(it.get("passos", 50)), device=cuda)
                n = len(sch.timesteps)
                for j, t in enumerate(sch.timesteps):
                    tj = time.time()
                    v = modelo(lat, t)
                    lat = sch.step(v, t, lat, return_dict=False)[0]
                    emit(evento="passo", i=i, passo=j + 1, de=n, segundos=round(time.time() - tj, 1))
        lat = ((1 - mask) * cond + mask * lat).float().cpu()
        torch.save(lat, it["latente"])
        r = dict(i=i, segundos=round(time.time() - ts, 1), vram_mb=_vram(), ram_mb=_rss_mb(),
                 leitura_s=round(st.lido_s, 1), copia_s=round(st.copia_s, 1), lido_gb=round(st.bytes / 1e9, 1))
        res.append(r)
        emit(evento="latente", **r)
        del cond, mask, lat
        torch.cuda.empty_cache()
    st.fecha()
    emit(evento="fim", itens=res, gpu=torch.cuda.get_device_name(0), torch=torch.__version__, fixos=int(fixos),
         ram_mb=_rss_mb(), segundos=round(time.time() - t0, 1))


# ---------------------------------------------------------------------------------------------- decodificar
def _cortes(n: int, N: int, ov: int) -> list[tuple[int, int]]:
    """Divide N (em latentes) em n faixas com `ov` de sobreposição."""
    if n <= 1:
        return [(0, N)]
    passo = (N + ov * (n - 1)) / n
    r = []
    for k in range(n):
        a = round(k * (passo - ov))
        r.append((a, N if k == n - 1 else min(N, round(a + passo))))
    return r


def _decodifica(vae, z, grade: tuple[int, int], ov: int = 4):
    """Decodificador do VAE do Wan2.2 em blocos espaciais (grade linhas x colunas, sobreposição de `ov` latentes =
    64 px, emenda em rampa linear) e, dentro de cada bloco, um latente por vez (4 quadros) com o cache causal do
    próprio VAE. Cada pedaço sai da GPU assim que fica pronto: o vídeo inteiro nunca fica na VRAM.
    O decode inteiro de 704x1280 não cabe em 6 GB nem em bf16 (o decodificador trabalha com 256 canais a 352x640
    por 4 quadros); o tiling do diffusers guarda o vídeo inteiro na GPU e usa blocos de 256 px (3x mais lento)."""
    import torch
    from diffusers.models.autoencoders.autoencoder_kl_wan import unpatchify

    _, _, F, H, W = z.shape
    s = 16
    acc = torch.zeros(3, 4 * (F - 1) + 1, H * s, W * s)
    pes = torch.zeros(1, 1, H * s, W * s)
    for y0, y1 in _cortes(grade[0], H, ov):
        for x0, x1 in _cortes(grade[1], W, ov):
            vae.clear_cache()
            x = vae.post_quant_conv(z[:, :, :, y0:y1, x0:x1])
            partes = []
            for i in range(F):
                vae._conv_idx = [0]
                o = vae.decoder(x[:, :, i:i + 1], feat_cache=vae._feat_map, feat_idx=vae._conv_idx,
                                first_chunk=(i == 0))
                partes.append(unpatchify(o, patch_size=vae.config.patch_size).clamp(-1, 1)[0].float().cpu())
            vae.clear_cache()
            o = torch.cat(partes, 1)
            h, w = o.shape[2], o.shape[3]
            wy, wx, r = torch.ones(h), torch.ones(w), ov * s
            if y0 > 0:
                wy[:r] = torch.linspace(0, 1, r)
            if y1 < H:
                wy[-r:] = torch.linspace(1, 0, r)
            if x0 > 0:
                wx[:r] = torch.linspace(0, 1, r)
            if x1 < W:
                wx[-r:] = torch.linspace(1, 0, r)
            m = (wy[:, None] * wx[None, :]).clamp_min(1e-4)
            acc[:, :, y0 * s:y1 * s, x0 * s:x1 * s] += o * m
            pes[:, :, y0 * s:y1 * s, x0 * s:x1 * s] += m
            del partes, o, x
            torch.cuda.empty_cache()
    return acc / pes


def decodificar(job_path: str):
    """Latentes -> quadros (VAE do Wan2.2 em fp32, em blocos) -> .mp4 nativo (x264 CRF 12, sem perda visível).
    fp32 e não bf16: em bf16 o decodificador cabe em blocos maiores (2x2, 88 s para 73 quadros contra 190 s), mas
    a textura sai visivelmente mais lisa (pele, tecido, degraus); medido em 2026-11-13."""
    import numpy as np
    import torch

    job = json.loads(Path(job_path).read_text())
    base = Path(job["modelo"])
    cuda = torch.device("cuda")
    t0 = time.time()
    dtype = torch.bfloat16 if job.get("vae_bf16") else torch.float32
    vae = _vae(base, cuda, torch.float32)
    vae.encoder = None  # só o decodificador
    vae = vae.to(dtype)
    gc.collect()
    torch.cuda.empty_cache()
    zm = torch.tensor(vae.config.latents_mean).view(1, -1, 1, 1, 1)
    zs = torch.tensor(vae.config.latents_std).view(1, -1, 1, 1, 1)
    torch.cuda.reset_peak_memory_stats()
    # fp32 em 704x1280: 4x3 cabe (4,3 GB de VRAM); 3x2 não. bf16: 2x2 cabe (4,0 GB).
    grades = [(2, 2), (3, 2), (4, 3), (5, 4), (6, 5)] if dtype == torch.bfloat16 else [(4, 3), (5, 4), (6, 5)]
    g0 = 0
    for it in job["itens"]:
        ts = time.time()
        lat = torch.load(it["latente"], weights_only=True)
        z = (lat * zs + zm).to(cuda, dtype)
        vid = None
        # se faltar VRAM, blocos menores (mesma imagem, mais lento)
        g = g0
        while vid is None:
            grade = grades[g] if it["h"] >= it["w"] else grades[g][::-1]
            try:
                with torch.inference_mode():
                    vid = _decodifica(vae, z, grade)
            except torch.cuda.OutOfMemoryError:
                vae.clear_cache()
                gc.collect()
                torch.cuda.empty_cache()
                if g + 1 >= len(grades):
                    raise
                g += 1
                g0 = g
                log(f"[edin animar] VAE: faltou VRAM, decodificando em blocos {grades[g]}")
        # (3, F, H, W) em [-1, 1] -> uint8 para o ffmpeg
        vid = ((vid + 1) * 127.5).round().clamp(0, 255).to(torch.uint8).permute(1, 2, 3, 0).numpy()
        F_, H_, W_ = vid.shape[:3]
        Path(it["saida"]).parent.mkdir(parents=True, exist_ok=True)
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{W_}x{H_}", "-r", str(it.get("fps", 24)), "-i", "-", "-c:v", "libx264",
                              "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                              it["saida"]], stdin=subprocess.PIPE)
        p.stdin.write(np.ascontiguousarray(vid).tobytes())
        p.stdin.close()
        if p.wait() != 0:
            raise SystemExit(f"ffmpeg falhou ao gravar {it['saida']}")
        emit(evento="video", saida=it["saida"], quadros=F_, w=W_, h=H_, segundos=round(time.time() - ts, 1),
             grade=list(grades[g0]))
        del vid, z
        torch.cuda.empty_cache()
    emit(evento="fim", segundos=round(time.time() - t0, 1), vram_mb=_vram(), ram_mb=_rss_mb(),
         tiling=list(grades[g0]), dtype=str(dtype).replace("torch.", ""))


def info():
    import torch

    r = {"torch": torch.__version__, "cuda": torch.version.cuda, "gpu": torch.cuda.is_available()}
    if r["gpu"]:
        p = torch.cuda.get_device_properties(0)
        r.update(nome=p.name, vram_mb=round(p.total_memory / 2**20))
    for mod in ("diffusers", "transformers", "accelerate", "safetensors", "ftfy"):
        try:
            r[mod] = __import__(mod).__version__
        except Exception as e:  # noqa: BLE001
            r[mod] = f"FALTA ({e.__class__.__name__})"
    emit(evento="info", **r)


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    _amostra_ram()
    if cmd == "preparar":
        preparar(sys.argv[2])
    elif cmd == "texto":
        texto(sys.argv[2])
    elif cmd == "gerar":
        gerar(sys.argv[2])
    elif cmd == "decodificar":
        decodificar(sys.argv[2])
    else:
        info()
