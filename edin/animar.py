"""`edin animar`: foto -> clipe de vídeo com movimento de verdade (imagem para vídeo), local, na GPU.

Modelo: Wan2.2-TI2V-5B (Wan-AI, Apache 2.0), 24 fps nativo, 704x1280 (vertical) ou 1280x704. Dois "motores"
com os mesmos codificadores de texto e VAE:
  fastwan  (padrão) FastWan2.2-TI2V-5B (FastVideo, Apache 2.0), destilado por DMD para 3 passos sem CFG:
           ~4,5 min por clipe de 3 s
  wan      (--qualidade) Wan2.2-TI2V-5B oficial, 50 passos com CFG 5: ~27 min por clipe de 3 s, sem o pulo do
           1º quadro e sem troca de identidade; para 1 ou 2 planos-chave quando houver tempo
Ver docs/VIDEO_IA.md (escolha do modelo, tempos medidos, VRAM/RAM, boas práticas de prompt).

O PyTorch roda no venv do gerador de imagem (~/.local/share/edin/imagem/venv, instalado pelo install_imagem.sh;
o install_video.sh só acrescenta o que falta) e os pesos ficam em ~/.local/share/edin/video/modelos. Este módulo
monta o job, chama o worker (edin/video_worker.py) em três processos (texto, gerar, decodificar; cada um começa
com a VRAM livre) e amplia o clipe nativo para 1080 no lado menor.
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .imagem import VENV_PY, _roda_worker
from .voice import HOME

VIDEO_HOME = Path(os.environ.get("EDIN_VIDEO_HOME", HOME / "video"))
MODELOS = VIDEO_HOME / "modelos"
AQUI = Path(__file__).resolve().parent
WORKER = AQUI / "video_worker.py"
MANIFESTO = AQUI / "modelos_video.json"
FPS = 24
MAX_QUADROS = 121  # 5 s a 24 fps: o comprimento de treino do Wan2.2-TI2V-5B

MOTORES = {
    # transformer: pasta do transformer usado (o oficial é convertido de fp32 para bf16 pelo install_video.sh)
    "wan": {"modelo": "wan22_ti2v_5b", "transformer": "transformer_bf16", "passos": 50, "cfg": 5.0},
    "fastwan": {"modelo": "fastwan", "transformer": "transformer", "amostrador": "dmd",
                "passos_dmd": [1000, 757, 522], "cfg": 1.0},
}
RESOLUCOES = {"vertical": (704, 1280), "horizontal": (1280, 704), "quadrado": (960, 960)}

# o Wan entende prompt longo (UMT5, 512 tokens): descrever o movimento, o ritmo e a câmera ajuda mais que estilo
SUFIXO = "natural realistic motion, steady camera, cinematic film look, consistent face and identity"


# ---------------------------------------------------------------------------------------------- ambiente
def _man() -> dict:
    try:
        return json.loads(MANIFESTO.read_text())["modelos"]
    except (OSError, ValueError):
        return {}


def _pasta(nome: str) -> Path:
    return MODELOS / _man()[nome]["pasta"]


def _bf16_ok() -> bool:
    d = _pasta("wan22_ti2v_5b") / "transformer_bf16"
    f = d / "diffusion_pytorch_model.safetensors.index.json"
    if not f.exists():
        return False
    arqs = set(json.loads(f.read_text())["weight_map"].values())
    return all((d / a).exists() for a in arqs)


COMUNS = ("text_encoder/", "tokenizer/", "vae/", "scheduler/", "model_index.json", "transformer/config.json")


def estado() -> dict:
    """Para o `edin doctor`: venv, arquivos de cada motor e a conversão bf16."""
    r = {"venv": VENV_PY.exists(), "pasta": str(VIDEO_HOME)}
    try:
        comuns = _arquivos_ok("wan22_ti2v_5b", COMUNS)
        r["fastwan"] = comuns and _arquivos_ok("fastwan")
        r["qualidade"] = comuns and _arquivos_ok("wan22_ti2v_5b") and _bf16_ok()
    except (KeyError, OSError):
        r["fastwan"] = r["qualidade"] = False
    return r


def _arquivos_ok(nome: str, prefixos: tuple[str, ...] = ("",)) -> bool:
    m = _man()[nome]
    pasta = MODELOS / m["pasta"]
    return all((pasta / a).exists() and (pasta / a).stat().st_size == t
               for a, t in m["arquivos"].items() if a.startswith(prefixos))


def _checa(motor: str):
    if not VENV_PY.exists():
        raise SystemExit(f"[edin] o venv de IA não está instalado ({VENV_PY}). Rode ./install_video.sh "
                         "(ver docs/VIDEO_IA.md).")
    # texto (UMT5), tokenizer e VAE vêm sempre do repositório oficial; o transformer, do motor escolhido
    if not _arquivos_ok("wan22_ti2v_5b", COMUNS):
        raise SystemExit("[edin] faltam arquivos do Wan2.2-TI2V-5B. Rode ./install_video.sh --modelos.")
    if motor == "wan":
        if not _arquivos_ok("wan22_ti2v_5b"):
            raise SystemExit("[edin] --qualidade precisa do transformer do Wan2.2-TI2V-5B (20 GB). Rode "
                             "./install_video.sh --modelos (sem --sem-qualidade).")
        if not _bf16_ok():
            raise SystemExit("[edin] falta converter o transformer para bf16. Rode ./install_video.sh --modelos.")
    elif not _arquivos_ok(MOTORES[motor]["modelo"]):
        raise SystemExit(f"[edin] falta o modelo do motor {motor}. Rode ./install_video.sh --modelos.")


def preparar(verbose: bool = True):
    """Converte o transformer oficial (fp32, 20 GB) em bf16 (10 GB) uma vez: metade da leitura por passo."""
    base = _pasta("wan22_ti2v_5b")
    if _bf16_ok():
        return
    t0 = time.time()
    ev = (lambda e: print(f"[edin] bf16: {e['arquivo']} ({e['segundos']} s)", flush=True)) if verbose else None
    _roda_worker("preparar", {"origem": str(base / "transformer"), "destino": str(base / "transformer_bf16")}, ev,
                 worker=WORKER)
    if verbose:
        print(f"[edin] transformer convertido para bf16 em {time.time() - t0:.0f} s")


# ---------------------------------------------------------------------------------------------- clipes
def quadros(duracao: float) -> int:
    """Duração em s -> número de quadros a 24 fps no formato 4k+1 que o VAE do Wan pede (3 s -> 73)."""
    n = int(round(duracao * FPS / 4)) * 4 + 1
    if n > MAX_QUADROS:
        print(f"[edin] aviso: {duracao:g} s passa do treino do modelo (5 s); usando 5 s. Para mais, encadeie clipes.")
        n = MAX_QUADROS
    return max(n, 17)


def resolucao(foto: str, forcar: str | None = None) -> tuple[int, int]:
    if forcar:
        if forcar in RESOLUCOES:
            return RESOLUCOES[forcar]
        w, h = (int(x) for x in forcar.lower().split("x"))
        return w // 32 * 32, h // 32 * 32
    from PIL import Image

    with Image.open(foto) as im:
        r = im.width / im.height
    if r < 0.8:
        return RESOLUCOES["vertical"]
    if r > 1.25:
        return RESOLUCOES["horizontal"]
    return RESOLUCOES["quadrado"]


def monta_prompt(prompt: str, sufixo: str | None = None) -> str:
    s = SUFIXO if sufixo is None else sufixo
    p = prompt.strip().rstrip(".,")
    return f"{p}. {s}" if s else p


def amplia(src: Path, dst: Path, tamanho: str = "auto", modo: str = "lanczos"):
    """Clipe nativo (704x1280) -> 1080 no lado menor (lanczos + nitidez leve, ou Real-ESRGAN) e recorte central
    para o quadro final (1080x1920, 1920x1080 ou 1080x1080 no automático)."""
    from .utils import probe

    info = probe(str(src))
    w, h = info["w"], info["h"]
    if tamanho == "auto":
        tw, th = (1080, 1920) if h > w * 1.2 else (1920, 1080) if w > h * 1.2 else (1080, 1080)
    else:
        tw, th = (int(x) for x in tamanho.lower().split("x"))
    base = src
    if modo == "esrgan":
        from .enhance import enhance

        base = Path(enhance(str(src), None, mode="esrgan", scale=2))
    vf = (f"scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,crop={tw}:{th}"
          + (",unsharp=5:5:0.45:5:5:0" if modo == "lanczos" else "") + ",setsar=1")
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(base), "-vf", vf, "-c:v", "libx264", "-preset", "slow",
                        "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(dst)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"[edin] ffmpeg falhou ao ampliar {src}: {p.stderr[-400:]}")


def animar(itens: list[dict], motor: str = "fastwan", upscale: str = "lanczos", tamanho: str = "auto",
           manter_nativo: bool = True, verbose: bool = True) -> list[dict]:
    """itens: [{foto, prompt (já montado), saida, quadros, seed, w, h, negativo?, passos?, cfg?}]."""
    _checa(motor)
    m = MOTORES[motor]
    base = _pasta("wan22_ti2v_5b")
    tdir = (base if m["modelo"] == "wan22_ti2v_5b" else _pasta(m["modelo"])) / m["transformer"]
    tmp = Path(tempfile.mkdtemp(prefix="edin_animar_"))
    t0 = time.time()
    job_itens = []
    for i, it in enumerate(itens):
        j = {"foto": str(Path(it["foto"]).resolve()), "prompt": it["prompt"], "seed": int(it["seed"]),
             "frames": int(it["quadros"]), "w": int(it["w"]), "h": int(it["h"]),
             "negativo": it.get("negativo") or "", "latente": str(tmp / f"{i:03d}.pt"),
             "saida": str(tmp / f"{i:03d}.mp4"), "fps": FPS}
        for k in ("amostrador", "passos_dmd", "passos", "cfg", "shift"):
            if k in m:
                j[k] = m[k]
            if it.get(k) is not None:
                j[k] = it[k]
        job_itens.append(j)
    usa_cfg = any(float(j.get("cfg", 1)) > 1 for j in job_itens)
    if usa_cfg:
        from .video_worker import NEGATIVO_WAN

        for j in job_itens:
            j["negativo"] = j["negativo"] or NEGATIVO_WAN
    prompts = sorted({j["prompt"] for j in job_itens} | ({j["negativo"] for j in job_itens} if usa_cfg else set()))
    medidas: dict = {"motor": motor}

    # 1) texto
    ts = time.time()
    evs = _roda_worker("texto", {"modelo": str(base), "prompts": prompts, "saida": str(tmp / "emb.pt")},
                       worker=WORKER)
    fim = next((e for e in evs if e["evento"] == "fim"), {})
    # "s": tempo do próprio worker; "parede_s" inclui a espera pela trava (outro trabalho pesado na frente)
    medidas["texto"] = {"s": fim.get("segundos"), "parede_s": round(time.time() - ts, 1), "vram_mb": fim.get("vram_mb"), "ram_mb": fim.get("ram_mb")}
    if verbose:
        print(f"[edin] texto: {len(prompts)} prompt(s) em {medidas['texto']['s']} s "
              f"(VRAM {fim.get('vram_mb')} MB, RAM {fim.get('ram_mb')} MB)", flush=True)

    # 2) difusão
    def ev(e):
        if not verbose:
            return
        if e["evento"] == "passo":
            print(f"\r[edin] clipe {e['i'] + 1}/{len(itens)}: passo {e['passo']}/{e['de']} ({e['segundos']} s)   ",
                  end="", flush=True)
        elif e["evento"] == "latente":
            print(f"\n[edin] clipe {e['i'] + 1}: {e['segundos']} s de difusão, VRAM pico {e['vram_mb']} MB", flush=True)
        elif e["evento"] == "carga":
            print(f"[edin] carga: VAE {e['vae_s']} s, transformer {e['transformer_s']} s, "
                  f"{e['fixos']}/{e['blocos']} blocos fixos na GPU", flush=True)

    ts = time.time()
    evs = _roda_worker("gerar", {"modelo": str(base), "transformer": str(tdir), "embeddings": str(tmp / "emb.pt"),
                                 "itens": job_itens}, ev, worker=WORKER)
    fim = next((e for e in evs if e["evento"] == "fim"), {})
    lats = {e["i"]: e for e in evs if e["evento"] == "latente"}
    medidas["gerar"] = {"s": fim.get("segundos"), "parede_s": round(time.time() - ts, 1), "ram_mb": fim.get("ram_mb"), "fixos": fim.get("fixos"),
                        "gpu": fim.get("gpu")}

    # 3) VAE
    ts = time.time()
    evs = _roda_worker("decodificar", {"modelo": str(base), "itens": job_itens}, worker=WORKER)
    fim = next((e for e in evs if e["evento"] == "fim"), {})
    vids = {e["saida"]: e for e in evs if e["evento"] == "video"}
    medidas["vae"] = {"s": fim.get("segundos"), "parede_s": round(time.time() - ts, 1), "vram_mb": fim.get("vram_mb"), "ram_mb": fim.get("ram_mb"),
                      "tiling": fim.get("tiling")}
    if verbose:
        print(f"[edin] VAE: {medidas['vae']['s']} s (VRAM {fim.get('vram_mb')} MB, tiling {fim.get('tiling')})")

    # 4) ampliar
    res = []
    for i, (it, j) in enumerate(zip(itens, job_itens)):
        dst = Path(it["saida"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        ta = time.time()
        if manter_nativo:
            nat = dst.with_name(dst.stem + ".nativo.mp4")
            shutil.copy(j["saida"], nat)
        if upscale == "nenhum":
            shutil.copy(j["saida"], dst)
        else:
            amplia(Path(j["saida"]), dst, tamanho, upscale)
        r = {k: v for k, v in it.items() if k not in ("negativo",)}
        r.update(motor=motor, nativa=f"{j['w']}x{j['h']}", fps=FPS, segundos_clipe=round(j["frames"] / FPS, 2),
                 difusao_s=lats.get(i, {}).get("segundos"), vram_mb=lats.get(i, {}).get("vram_mb"),
                 vae_s=vids.get(j["saida"], {}).get("segundos"),
                 passos=j.get("passos_dmd", j.get("passos")), cfg=j.get("cfg"), upscale=upscale,
                 ampliar_s=round(time.time() - ta, 1))
        res.append(r)
        if verbose:
            print(f"[edin] OK {dst}")
    shutil.rmtree(tmp, ignore_errors=True)
    total = time.time() - t0
    medidas["total_s"] = round(total, 1)
    if verbose:
        print(f"[edin] {len(itens)} clipe(s) em {total:.0f} s ({motor}): {json.dumps(medidas, ensure_ascii=False)}")
    _registra(res, medidas)
    return res


def _registra(res: list[dict], medidas: dict):
    """edin_animar.json na pasta de cada clipe: foto, prompt, seed e parâmetros (para refazer igual) e tempos."""
    por_pasta: dict[Path, list] = {}
    for r in res:
        por_pasta.setdefault(Path(r["saida"]).parent, []).append(r)
    for pasta, rs in por_pasta.items():
        f = pasta / "edin_animar.json"
        try:
            dados = json.loads(f.read_text())
        except (OSError, ValueError):
            dados = {"clipes": {}}
        for r in rs:
            dados["clipes"][Path(r["saida"]).name] = {k: v for k, v in r.items() if k != "saida"}
        dados["ultima_execucao"] = medidas
        f.write_text(json.dumps(dados, ensure_ascii=False, indent=2))


def _seed() -> int:
    return secrets.randbelow(2**31 - 1)


def itens_do_lote(path: str, so: list[str] | None = None) -> tuple[list[dict], dict]:
    """Lote de clipes de um roteiro (caminhos relativos ao JSON):
    {
      "pasta": "clipes", "motor": "fastwan", "duracao": 3, "upscale": "lanczos",
      "clipes": [{"id": "p13_escada", "foto": "fotos/p13_escada_s4243.png",
                  "prompt": "she walks up the stairs toward the sun", "duracao": 4, "seed": 7, "n": 2}]
    }
    Saída: <pasta>/<id>.mp4 (com n > 1: <id>_s<seed>.mp4)."""
    base = Path(path).resolve().parent
    cfg = json.loads(Path(path).read_text())
    pasta = base / cfg.get("pasta", "clipes")
    itens = []
    for c in cfg["clipes"]:
        if so and c["id"] not in so:
            continue
        foto = str((base / c["foto"]).resolve())
        seed = int(c.get("seed", cfg.get("seed", _seed())))
        n = int(c.get("n", cfg.get("n", 1)))
        w, h = resolucao(foto, c.get("resolucao", cfg.get("resolucao")))
        for k in range(n):
            nome = f"{c['id']}.mp4" if n == 1 else f"{c['id']}_s{seed + k}.mp4"
            it = {"foto": foto, "prompt": monta_prompt(c["prompt"], c.get("sufixo", cfg.get("sufixo"))),
                  "seed": seed + k, "saida": str(pasta / nome), "clipe": c["id"],
                  "quadros": quadros(float(c.get("duracao", cfg.get("duracao", 3)))), "w": w, "h": h}
            for key in ("passos", "cfg", "negativo", "shift"):
                if key in c or key in cfg:
                    it[key] = c.get(key, cfg.get(key))
            itens.append(it)
    return itens, cfg


# ---------------------------------------------------------------------------------------------- CLI
def cmd_animar(a):
    if a.lote:
        itens, cfg = itens_do_lote(a.lote, a.so.split(",") if a.so else None)
        motor = "wan" if a.qualidade else (a.motor or cfg.get("motor", "fastwan"))
        up = a.upscale or cfg.get("upscale", "lanczos")
        tam = a.size or cfg.get("size", "auto")
    else:
        if not a.foto or not a.prompt:
            sys.exit("[edin] uso: edin animar foto.png \"descrição do movimento\" -o clipe.mp4 (ou --lote x.json)")
        if not Path(a.foto).exists():
            sys.exit(f"[edin] {a.foto} não existe")
        motor = "wan" if a.qualidade else (a.motor or "fastwan")
        up, tam = a.upscale or "lanczos", a.size or "auto"
        seed = a.seed if a.seed is not None else _seed()
        w, h = resolucao(a.foto, a.resolucao)
        out = Path(a.out or Path(a.foto).with_suffix(".mp4").name)
        itens = []
        for k in range(a.n):
            saida = out if a.n == 1 else out.with_name(f"{out.stem}_s{seed + k}{out.suffix or '.mp4'}")
            it = {"foto": a.foto, "prompt": monta_prompt(a.prompt, a.sufixo), "seed": seed + k, "saida": str(saida),
                  "quadros": quadros(a.duracao), "w": w, "h": h}
            if a.passos:
                it["passos"] = a.passos
            if a.cfg is not None:
                it["cfg"] = a.cfg
            if a.negativo:
                it["negativo"] = a.negativo
            itens.append(it)
    if not itens:
        sys.exit("[edin] nada para animar")
    if motor not in MOTORES:
        sys.exit(f"[edin] motor desconhecido: {motor} (use {' ou '.join(MOTORES)})")
    for it in itens:
        print(f"[edin] {Path(it['saida']).name}  seed {it['seed']}  {it['quadros']} quadros  {it['w']}x{it['h']}  "
              f"motor {motor}")
        if a.mostrar_prompt:
            print(f"   {it['prompt']}")
    animar(itens, motor, up, tam, manter_nativo=not a.sem_nativo)


def add_parsers(sp):
    s = sp.add_parser("animar", help="foto -> clipe de vídeo com movimento real (Wan2.2-TI2V-5B local), "
                                     "ver docs/VIDEO_IA.md")
    s.add_argument("foto", nargs="?", help="foto de entrada (primeiro quadro do clipe; o rosto é preservado)")
    s.add_argument("prompt", nargs="?", help="o que acontece, em inglês (ação, ritmo, câmera)")
    s.add_argument("-o", "--out", help="saída .mp4 (padrão: nome da foto .mp4)")
    s.add_argument("--duracao", type=float, default=3, help="segundos (1 a 5, padrão 3; 24 fps)")
    s.add_argument("--seed", type=int, help="semente (padrão: sorteada e impressa)")
    s.add_argument("--n", type=int, default=1, help="quantas variações (seeds seguidas)")
    s.add_argument("--motor", choices=list(MOTORES), help="fastwan (padrão, 3 passos, ~4,5 min por clipe de 3 s) "
                                                          "ou wan (50 passos, ~27 min)")
    s.add_argument("--qualidade", action="store_true", help="o mesmo que --motor wan: Wan2.2 completo, 50 passos com "
                                                            "CFG; sem pulo no 1º quadro; para 1 ou 2 planos-chave")
    s.add_argument("--passos", type=int, help="passos do wan (padrão 50)")
    s.add_argument("--cfg", type=float, help="guidance do wan (padrão 5)")
    s.add_argument("--negativo", help="prompt negativo (padrão: o do Wan2.2)")
    s.add_argument("--sufixo", help="texto acrescentado ao prompt (padrão: movimento natural, câmera estável...; "
                                    "\"\" para nenhum)")
    s.add_argument("--resolucao", help="vertical (704x1280), horizontal (1280x704), quadrado (960x960) ou WxH; "
                                       "padrão: pela foto")
    s.add_argument("--size", help="quadro final (padrão auto: 1080x1920, 1920x1080 ou 1080x1080)")
    s.add_argument("--upscale", choices=["lanczos", "esrgan", "nenhum"], help="ampliação até 1080 (padrão lanczos)")
    s.add_argument("--sem-nativo", action="store_true", help="não guarda o clipe nativo (<saida>.nativo.mp4)")
    s.add_argument("--lote", help="JSON com vários clipes (ver docs/VIDEO_IA.md)")
    s.add_argument("--so", help="com --lote: só estes ids (separados por vírgula)")
    s.add_argument("--mostrar-prompt", action="store_true", help="imprime o prompt final")
    s.set_defaults(fn=cmd_animar)
