"""Fotos realistas geradas na máquina (SDXL + SDXL-Lightning de 4 passos) e mapa de profundidade (Depth Anything
V2 Small) para animar como plano de filme no kit HTML (edin-foto3d.js). Ver docs/IMAGEM.md.

O PyTorch e os modelos ficam num venv separado (~/.local/share/edin/imagem, instalado pelo install_imagem.sh):
este módulo só monta os prompts, chama o worker (edin/imagem_worker.py) por subprocesso com `python -I` e faz o
pós (ampliação para 1080x1920, profundidade refinada, fundo preenchido e o pacote .foto3d.js) com OpenCV.
"""
from __future__ import annotations

import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .voice import HOME

IMG_HOME = Path(os.environ.get("EDIN_IMAGEM_HOME", HOME / "imagem"))
VENV_PY = IMG_HOME / "venv" / "bin" / "python"
MODELOS = IMG_HOME / "modelos"
AQUI = Path(__file__).resolve().parent
WORKER = AQUI / "imagem_worker.py"
MANIFESTO = AQUI / "modelos_imagem.json"

# resoluções nativas do SDXL (~1 megapixel, múltiplos de 64)
NATIVAS = [(1024, 1024), (896, 1152), (832, 1216), (768, 1344), (640, 1536),
           (1152, 896), (1216, 832), (1344, 768), (1536, 640)]

# curtos de propósito: o CLIP lê só 77 tokens e o estilo vai no fim do prompt (sujeito, personagem, lente, estilo)
ESTILOS = {
    "campanha": "campaign photo, natural backlight, 35mm film, Portra 400, film grain, shallow depth of field",
    "noite": "cinematic night photo, practical light, Vision3 500T film, film grain, shallow depth of field",
    "documental": "candid documentary photo, 35mm film, film grain, natural colors",
    "nenhum": "",
}
LENTES = {
    "24": "24mm wide lens",
    "35": "35mm lens",
    "50": "50mm lens",
    "85": "85mm f/1.8, bokeh",
    "macro": "100mm macro lens, close-up",
}
NEGATIVO = ("deformed hands, extra fingers, missing fingers, fused fingers, mutated hands, bad anatomy, "
            "distorted face, asymmetric eyes, extra limbs, text, watermark, logo, signature, letters, caption, "
            "cartoon, illustration, painting, 3d render, cgi, plastic skin, oversaturated, lowres, blurry, "
            "jpeg artifacts")


# ---------------------------------------------------------------------------------------------- ambiente
def estado() -> dict:
    """Para o `edin doctor`: venv, modelos baixados e GPU."""
    r = {"venv": VENV_PY.exists(), "modelos": {}, "pasta": str(IMG_HOME)}
    try:
        man = json.loads(MANIFESTO.read_text())["modelos"]
    except (OSError, ValueError):
        man = {}
    for nome, m in man.items():
        pasta = MODELOS / m["pasta"]
        ok = all((pasta / a).exists() and (pasta / a).stat().st_size == t for a, t in m["arquivos"].items())
        r["modelos"][nome] = {"ok": ok, "repo": m["repo"], "mb": round(sum(m["arquivos"].values()) / 1e6)}
    return r


def _checa(precisa: tuple[str, ...]):
    if not VENV_PY.exists():
        raise SystemExit(f"[edin] o gerador de imagem não está instalado ({VENV_PY} não existe). "
                         "Rode ./install_imagem.sh (ver docs/IMAGEM.md).")
    st = estado()["modelos"]
    falta = [n for n in precisa if not st.get(n, {}).get("ok")]
    if falta:
        raise SystemExit(f"[edin] modelo(s) faltando: {', '.join(falta)}. Rode ./install_imagem.sh --modelos.")


def _pasta(nome: str) -> Path:
    man = json.loads(MANIFESTO.read_text())["modelos"]
    return MODELOS / man[nome]["pasta"]


def _espera_gpu_livre(limite_mb: int = 600, timeout: float = 30.0):
    """Espera a VRAM ocupada cair (o processo anterior acabou de sair e o driver ainda devolve a memória).

    Sem isso o cuDNN do processo seguinte falhava ao carregar kernels (SUBLIBRARY_LOADING_FAILED).
    """
    fim = time.time() + timeout
    while time.time() < fim:
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=10).stdout.split()
            if out and int(out[0]) < limite_mb:
                return
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return
        time.sleep(0.5)


def _roda_worker(cmd: str, job: dict, on_evento=None, worker: Path | None = None) -> list[dict]:
    """Roda uma etapa no venv de imagem. Se o cuDNN falhar ao carregar kernels (a GPU acabou de ser liberada
    pelo processo anterior e a falha fica presa no processo), repete a etapa num processo novo."""
    for tentativa in range(3):
        try:
            return _roda_worker_1(cmd, job, on_evento, worker)
        except _ErroCudnn:
            print(f"[edin] {cmd}: cuDNN não carregou (GPU recém-liberada); repetindo num processo novo", flush=True)
            time.sleep(5 + 5 * tentativa)
    return _roda_worker_1(cmd, job, on_evento, worker)


class _ErroCudnn(Exception):
    pass


def _roda_worker_1(cmd: str, job: dict, on_evento=None, worker: Path | None = None) -> list[dict]:
    """Roda `worker` (padrão: imagem_worker.py) no venv de imagem; eventos JSON do stdout vão para on_evento."""
    worker = worker or WORKER
    rotulo = "imagem" if worker == WORKER else worker.stem.replace("_worker", "")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(job, f)
        jp = f.name
    env = dict(os.environ, HF_HUB_OFFLINE="1",
               TRANSFORMERS_VERBOSITY="error", DIFFUSERS_VERBOSITY="error")
    env.pop("PYTHONPATH", None)
    # o atalho `edin` põe no LD_LIBRARY_PATH o cuDNN/cuBLAS do venv principal (faster-whisper, outra versão);
    # herdado aqui, o PyTorch do venv de imagem carregava as sub-bibliotecas erradas do cuDNN
    # (CUDNN_STATUS_SUBLIBRARY_LOADING_FAILED em toda convolução). O venv de imagem traz as próprias.
    env.pop("LD_LIBRARY_PATH", None)
    eventos = []
    from .utils import TravaPesada

    trava = TravaPesada(f"edin {rotulo} ({cmd})").__enter__()
    _espera_gpu_livre()
    time.sleep(3)  # o driver ainda termina de soltar o contexto do processo anterior
    try:
        p = subprocess.Popen([str(VENV_PY), "-I", str(worker), cmd, jp], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, env=env)
        err: list[str] = []
        import threading

        th = threading.Thread(target=lambda: err.extend(p.stderr), daemon=True)
        th.start()
        for line in p.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            ev = json.loads(line)
            eventos.append(ev)
            if on_evento:
                on_evento(ev)
        p.wait()
        th.join(timeout=2)
        if p.returncode != 0:
            log_erro = Path.home() / ".cache" / "edin" / f"{rotulo}_erro.log"
            log_erro.parent.mkdir(parents=True, exist_ok=True)
            log_erro.write_text(f"etapa: {cmd}\n" + "".join(err))
            shutil.copy(jp, log_erro.with_name(f"{rotulo}_erro_job_{cmd}.json"))
            if "CUDNN_STATUS_SUBLIBRARY_LOADING_FAILED" in "".join(err):
                raise _ErroCudnn()
            tail = "".join(err[-25:]) + f"\n[edin] log completo da etapa '{cmd}': {log_erro}"
            if "OutOfMemoryError" in tail or "out of memory" in tail:
                tail += "\n[edin] faltou VRAM: feche outros programas que usam a GPU (nvidia-smi) e tente de novo."
            raise SystemExit(f"[edin] o worker de {rotulo} falhou ({p.returncode}):\n{tail}")
    finally:
        trava.__exit__(None, None, None)
        os.unlink(jp)
    return eventos


# ---------------------------------------------------------------------------------------------- prompt
def nativa(w: int, h: int) -> tuple[int, int]:
    alvo = w / h
    return min(NATIVAS, key=lambda r: abs(r[0] / r[1] - alvo))


def monta_prompt(prompt: str, personagem: str = "", lente: str | None = None, estilo: str = "campanha") -> str:
    partes = [prompt.strip().rstrip(",")]
    if personagem:
        partes.append(personagem.strip().rstrip(","))
    if lente:
        partes.append(LENTES.get(str(lente), str(lente)))
    if ESTILOS.get(estilo, estilo):
        partes.append(ESTILOS.get(estilo, estilo))
    return ", ".join(p for p in partes if p)


# ---------------------------------------------------------------------------------------------- ampliação
def amplia(src: Path, dst: Path, w: int, h: int, modo: str = "lanczos"):
    """Da resolução nativa do SDXL para o quadro (cover + recorte central). lanczos + nitidez leve (padrão) ou
    Real-ESRGAN x4plus e redução por área."""
    import cv2
    import numpy as np

    im = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if modo == "esrgan":
        from .enhance import _pick_gpu, esrgan_binary

        exe = esrgan_binary()
        gpu = None if exe is None else _pick_gpu(exe, "realesrgan-x4plus", 4, 0)
        if gpu is not None:
            tmp = dst.with_suffix(".x4.png")
            p = subprocess.run([str(exe), "-i", str(src), "-o", str(tmp), "-n", "realesrgan-x4plus", "-s", "4",
                                "-m", str(exe.parent / "models"), "-g", str(gpu)], capture_output=True, text=True)
            if p.returncode == 0 and tmp.exists():
                im = cv2.imread(str(tmp), cv2.IMREAD_COLOR)
                tmp.unlink()
            else:
                print("[edin] Real-ESRGAN falhou; usando lanczos")
                modo = "lanczos"
        else:
            modo = "lanczos"
    ih, iw = im.shape[:2]
    s = max(w / iw, h / ih)
    nw, nh = max(w, round(iw * s)), max(h, round(ih * s))
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
    im = cv2.resize(im, (nw, nh), interpolation=interp)
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    im = im[y0:y0 + h, x0:x0 + w]
    if modo == "lanczos" and s > 1:
        bl = cv2.GaussianBlur(im, (0, 0), 1.1)
        im = np.clip(im.astype(np.float32) * 1.35 - bl.astype(np.float32) * 0.35, 0, 255).astype(np.uint8)
    cv2.imwrite(str(dst), im)


# ---------------------------------------------------------------------------------------------- gerar
def gerar(itens: list[dict], tamanho=(1080, 1920), upscale="lanczos", lightning=True, verbose=True) -> list[dict]:
    """itens: [{prompt (já montado), negativo, seed, saida, passos, cfg}]. Gera na nativa do SDXL e amplia."""
    _checa(("sdxl", "lightning") if lightning else ("sdxl",))
    w, h = tamanho
    nw, nh = nativa(w, h)
    tmpdir = Path(tempfile.mkdtemp(prefix="edin_imagem_"))
    job_itens = []
    for i, it in enumerate(itens):
        job_itens.append({"prompt": it["prompt"], "negativo": it.get("negativo", NEGATIVO), "seed": it["seed"],
                          "w": nw, "h": nh, "passos": it.get("passos", 4 if lightning else 28),
                          "cfg": it.get("cfg", 0 if lightning else 5.5), "saida": str(tmpdir / f"{i:03d}.png")})
    job = {"itens": job_itens, "sdxl": str(_pasta("sdxl")), "memoria": "auto",
           "lora": str(_pasta("lightning") / "sdxl_lightning_4step_lora.safetensors") if lightning else None}
    t0 = time.time()
    tempos = {}

    def ev(e):
        if e["evento"] == "latente":
            tempos.setdefault(e["i"], {})["unet_s"] = e["segundos"]
            if e.get("tokens", 0) > 77:
                print(f"[edin] aviso: prompt {e['i'] + 1} tem {e['tokens']} tokens; o CLIP só lê os 77 primeiros "
                      "(o estilo no fim é cortado). Encurte a descrição.")
            if verbose:
                print(f"[edin] imagem {e['i'] + 1}/{len(itens)}: {e['segundos']:.1f} s na UNet")
        elif e["evento"] == "imagem":
            tempos.setdefault(e["i"], {})["vae_s"] = e["segundos"]

    # UNet e VAE em processos separados: cada etapa começa com a VRAM de 6 GB inteira livre
    job["latentes_em"] = str(tmpdir / "latentes.pt")
    evs = _roda_worker("gerar", job, ev)
    fim = next((e for e in evs if e["evento"] == "fim"), {})
    evs2 = _roda_worker("decodificar", {"itens": job_itens, "sdxl": job["sdxl"], "latentes": job["latentes_em"]}, ev)
    fim2 = next((e for e in evs2 if e["evento"] == "fim"), {})
    fim = dict(fim, vae_s=fim2.get("vae_s"), vae_tiling=fim2.get("vae_tiling"),
               vram_mb=dict(fim.get("vram_mb", {}), vae=fim2.get("vram_vae")))
    res = []
    for i, it in enumerate(itens):
        dst = Path(it["saida"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        ta = time.time()
        amplia(Path(job_itens[i]["saida"]), dst, w, h, upscale)
        r = dict(it, nativa=f"{nw}x{nh}", tamanho=f"{w}x{h}", upscale=upscale, lightning=lightning,
                 passos=job_itens[i]["passos"], cfg=job_itens[i]["cfg"], **tempos.get(i, {}),
                 ampliar_s=round(time.time() - ta, 2))
        res.append(r)
    shutil.rmtree(tmpdir, ignore_errors=True)
    total = time.time() - t0
    if verbose and fim:
        print(f"[edin] {len(itens)} imagem(ns) em {total:.1f} s (carga {fim.get('carga_s')} s, prompts "
              f"{fim.get('texto_s')} s, UNet+LoRA {fim.get('unet_carga_s')} s, VAE {fim.get('vae_s')} s); "
              f"VRAM pico: {fim.get('vram_mb')} MB; {fim.get('gpu')}")
    _registra(res, fim, total)
    return res


def _registra(res: list[dict], fim: dict, total: float):
    """edin_imagem.json na pasta de cada imagem: prompt, seed e parâmetros (para refazer igual)."""
    por_pasta: dict[Path, list] = {}
    for r in res:
        por_pasta.setdefault(Path(r["saida"]).parent, []).append(r)
    for pasta, rs in por_pasta.items():
        f = pasta / "edin_imagem.json"
        try:
            dados = json.loads(f.read_text())
        except (OSError, ValueError):
            dados = {"imagens": {}}
        for r in rs:
            dados["imagens"][Path(r["saida"]).name] = {k: v for k, v in r.items() if k != "saida"}
        dados["ultima_execucao"] = {"total_s": round(total, 1), **{k: v for k, v in fim.items() if k != "evento"}}
        f.write_text(json.dumps(dados, ensure_ascii=False, indent=2))


def _seed() -> int:
    return secrets.randbelow(2**31 - 1)


def itens_do_comando(a) -> tuple[list[dict], tuple[int, int]]:
    w, h = (int(x) for x in a.size.lower().split("x"))
    out = Path(a.out or "foto.png")
    seed = a.seed if a.seed is not None else _seed()
    prompt = monta_prompt(a.prompt, a.personagem or "", a.lente, a.estilo)
    itens = []
    for k in range(a.n):
        saida = out if a.n == 1 else out.with_name(f"{out.stem}_{k + 1}{out.suffix or '.png'}")
        it = {"prompt": prompt, "seed": seed + k, "saida": str(saida), "negativo": a.negativo or NEGATIVO}
        if a.passos:
            it["passos"] = a.passos
        if a.cfg is not None:
            it["cfg"] = a.cfg
        itens.append(it)
    return itens, (w, h)


def itens_do_lote(path: str, so: list[str] | None = None) -> tuple[list[dict], tuple[int, int], dict]:
    """Lote de planos de um roteiro:
    {
      "pasta": "fotos", "size": "1080x1920", "estilo": "campanha", "upscale": "lanczos",
      "personagens": {"ana": {"descricao": "young Brazilian woman, 19, curly dark hair, ...", "seed": 4242}},
      "planos": [{"id": "01_janela", "prompt": "...", "personagem": "ana", "lente": "35", "n": 2, "seed": 7,
                  "estilo": "noite"}]
    }
    Personagem: a mesma descrição física entra em todos os planos dela e a seed padrão é a dela (seed do plano
    sobrescreve). Saída: <pasta>/<id>.png (com n > 1: <id>_s<seed>.png)."""
    base = Path(path).resolve().parent
    cfg = json.loads(Path(path).read_text())
    w, h = (int(x) for x in cfg.get("size", "1080x1920").lower().split("x"))
    pasta = base / cfg.get("pasta", "fotos")
    pers = cfg.get("personagens", {})
    itens = []
    for pl in cfg["planos"]:
        if so and pl["id"] not in so:
            continue
        p = pers.get(pl.get("personagem", ""), {})
        if pl.get("personagem") and not p:
            raise SystemExit(f"[edin] plano {pl['id']}: personagem {pl['personagem']} não está em \"personagens\"")
        seed = pl.get("seed", p.get("seed", _seed()))
        n = int(pl.get("n", cfg.get("n", 1)))
        prompt = monta_prompt(pl["prompt"], p.get("descricao", ""), pl.get("lente"), pl.get("estilo", cfg.get("estilo", "campanha")))
        for k in range(n):
            nome = f"{pl['id']}.png" if n == 1 else f"{pl['id']}_s{seed + k}.png"
            it = {"prompt": prompt, "seed": seed + k, "saida": str(pasta / nome), "plano": pl["id"],
                  "negativo": pl.get("negativo", cfg.get("negativo", NEGATIVO))}
            for key in ("passos", "cfg"):
                if key in pl or key in cfg:
                    it[key] = pl.get(key, cfg.get(key))
            itens.append(it)
    return itens, (w, h), cfg


# ---------------------------------------------------------------------------------------------- profundidade
def _guiado(I, p, r: int, eps: float):
    import cv2

    m = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mI, mp = m(I), m(p)
    a = (m(I * p) - mI * mp) / (m(I * I) - mI * mI + eps)
    b = mp - a * mI
    return m(a) * I + m(b)


def _borra(x, sig: float):
    """Gaussiano grande barato: reduz, borra com sigma ~4 e volta (o resultado é liso de qualquer jeito)."""
    import cv2

    if sig <= 6:
        return cv2.GaussianBlur(x, (0, 0), sig)
    f = sig / 4
    h, w = x.shape[:2]
    p = cv2.resize(x, (max(2, round(w / f)), max(2, round(h / f))), interpolation=cv2.INTER_AREA)
    p = cv2.GaussianBlur(p, (0, 0), 4)
    return cv2.resize(p, (w, h), interpolation=cv2.INTER_LINEAR)


def _fundo(img, d, folga: float):
    """Camada de fundo para as bordas de oclusão: profundidade sem os degraus (o longe avança `folga` do quadro
    para dentro do que está perto) e cor preenchida só com pixels de profundidade parecida (o fundo de verdade,
    nunca a cor do sujeito)."""
    import cv2
    import numpy as np

    H, W = d.shape
    s = 0.5
    hs, ws = round(H * s), round(W * s)
    dh = cv2.resize(d, (ws, hs), interpolation=cv2.INTER_AREA)
    R = max(3, int(folga * min(W, H) * s))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * R + 1, 2 * R + 1))
    R2 = int(R * 1.5)
    # só perto de degrau de verdade (salto > 0,06 em ~3 px); rampa suave (chão, parede em perspectiva) fica igual
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    degrau = (cv2.dilate(dh, k3) - cv2.erode(dh, k3)) > 0.06
    perto = cv2.dilate(degrau.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * R2 + 1, 2 * R2 + 1))) > 0
    # profundidade de trás: cada pixel do lado de perto de um degrau (até 1,5x a folga) pega a profundidade do
    # pixel mais próximo que está mesmo atrás dele (pelo menos 0,06 mais longe): degrau atrás da perna, céu
    # atrás da cabeça. (A erosão pegava o mínimo do disco, que atrás de uma silhueta costuma ser o céu.)
    salto, passo = 0.06, 0.04
    niv = np.arange(0, 1 + passo, passo)
    kp = np.floor((dh - salto) / passo).astype(np.int32)
    db = dh.copy()
    fy, fx = np.mgrid[0:hs, 0:ws].astype(np.int32)  # de onde vem a cor de trás de cada pixel (ele mesmo)
    for kk in range(len(niv)):
        sel = (kp == kk) & perto
        if not sel.any():
            continue
        longe = dh < niv[kk]
        if not longe.any():
            continue
        dist, lab = cv2.distanceTransformWithLabels((~longe).astype(np.uint8), cv2.DIST_L2, 5,
                                                    labelType=cv2.DIST_LABEL_PIXEL)
        zy, zx = np.nonzero(longe)
        lz = lab[zy, zx]
        ly, lx = np.zeros(lab.max() + 1, np.int32), np.zeros(lab.max() + 1, np.int32)
        ly[lz], lx[lz] = zy, zx
        py, px = np.nonzero(sel)
        ok = dist[py, px] <= R2
        q = lab[py[ok], px[ok]]
        db[py[ok], px[ok]] = dh[ly[q], lx[q]]
        fy[py[ok], px[ok]], fx[py[ok], px[ok]] = ly[q], lx[q]
    # alisa a profundidade de trás dentro da faixa (o vizinho mais próximo dá degraus) e nunca passa da frente
    faixa = (dh - db) > 0.03
    fw = faixa.astype(np.float32)
    lis = _borra(db * fw, R / 5) / np.maximum(_borra(fw, R / 5), 1e-4)
    db = np.where(faixa, np.minimum(lis, dh), dh).astype(np.float32)
    db_full = np.minimum(cv2.resize(db, (W, H), interpolation=cv2.INTER_LINEAR), d)
    buraco = (d - db_full) > 0.03
    buraco = cv2.dilate(buraco.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
    # cor de trás: a do pixel de trás mais próximo (por construção mais longe que o sujeito: nunca a cor dele),
    # alisada só dentro da faixa (o vizinho mais próximo dá raios) sem puxar nada de fora dela
    imh = cv2.resize(img, (ws, hs), interpolation=cv2.INTER_AREA).astype(np.float32)
    fill = imh[fy, fx]
    fw = faixa.astype(np.float32)
    fill = _borra(fill * fw[..., None], R / 6) / np.maximum(_borra(fw, R / 6), 1e-4)[..., None]
    fill = np.where(faixa[..., None], fill, imh)
    fill = cv2.resize(fill, (W, H), interpolation=cv2.INTER_CUBIC)
    # grão parecido com o da foto no preenchimento (sem ele a mancha lisa denuncia)
    rng = np.random.default_rng(7)
    ruido = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7)
    lap = img.astype(np.float32) - cv2.GaussianBlur(img.astype(np.float32), (0, 0), 1.5)
    amp = float(np.std(lap[~buraco])) if (~buraco).any() else 2.0
    fill += (ruido * amp * 0.8)[..., None]
    m = cv2.GaussianBlur(buraco.astype(np.float32), (0, 0), 1.5)[..., None]
    fundo = np.clip(img.astype(np.float32) * (1 - m) + fill * m, 0, 255).astype(np.uint8)
    return fundo, db_full, buraco


def profundidade(fotos: list[str], folga: float = 0.06, lado: int = 770, nome: str | None = None,
                 verbose: bool = True) -> list[dict]:
    """foto.png -> foto.depth.png (16 bits, 0 = longe, 65535 = perto), foto.fundo.png (bordas de oclusão
    preenchidas) e foto.foto3d.js (cor, fundo e profundidades embutidas para o edin-foto3d.js)."""
    import cv2
    import numpy as np

    _checa(("profundidade",))
    tmp = Path(tempfile.mkdtemp(prefix="edin_prof_"))
    itens = [{"entrada": str(Path(f).resolve()), "saida": str(tmp / f"{i}.npy"), "lado": lado} for i, f in enumerate(fotos)]
    t0 = time.time()
    evs = _roda_worker("profundidade", {"modelo": str(_pasta("profundidade")), "itens": itens})
    t_rede = {e["entrada"]: e["segundos"] for e in evs if e["evento"] == "profundidade"}
    vram = next((e.get("vram_mb") for e in evs if e["evento"] == "fim"), None)
    res = []
    for it in itens:
        r = pos_profundidade(Path(it["entrada"]), np.load(it["saida"]), folga, nome if len(fotos) == 1 else None)
        r["rede_s"] = t_rede.get(it["entrada"])
        res.append(r)
        if verbose:
            m = r["meta"]
            print(f"[edin] {Path(r['foto']).name}: {Path(r['depth']).name}, {Path(r['fundo']).name}, "
                  f"{Path(r['js']).name} (nome \"{r['nome']}\", foco {m['foco']}, buraco {m['buraco'] * 100:.1f}%; "
                  f"rede {r['rede_s']} s, pós {r['pos_s']} s)")
    shutil.rmtree(tmp, ignore_errors=True)
    if verbose:
        print(f"[edin] profundidade de {len(fotos)} foto(s) em {time.time() - t0:.1f} s; VRAM pico {vram} MB")
    return res


def pos_profundidade(src: Path, raw, folga: float = 0.06, nome: str | None = None) -> dict:
    """Profundidade crua da rede (disparidade, maior = perto) -> arquivos .depth.png, .fundo.png e .foto3d.js."""
    import cv2
    import numpy as np

    if True:
        tp = time.time()
        img = cv2.imread(str(src), cv2.IMREAD_COLOR)
        raw = raw.astype(np.float32)
        lo, hi = np.percentile(raw, 0.5), np.percentile(raw, 99.5)
        d = np.clip((raw - lo) / max(hi - lo, 1e-6), 0, 1)
        # borda da profundidade presa à borda da cor (filtro guiado): sem halo de fundo grudado no sujeito
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        d = np.clip(_guiado(g, d, 4, 2e-3) * 0.7 + d * 0.3, 0, 1).astype(np.float32)
        base = src.with_suffix("")
        cv2.imwrite(f"{base}.depth.png", (d * 65535).round().astype(np.uint16))
        fundo, db, buraco = _fundo(img, d, folga)
        cv2.imwrite(f"{base}.fundo.png", fundo)
        # sujeito: o que está perto (acima do percentil 80); foco = mediana dele, centro = centroide
        lim = np.percentile(d, 80)
        sel = d >= lim
        foco = float(np.median(d[sel]))
        ys, xs = np.nonzero(sel)
        centro = [round(float(xs.mean()) / d.shape[1], 4), round(float(ys.mean()) / d.shape[0], 4)]
        meta = {"foco": round(foco, 4), "centro": centro, "folga": folga, "w": d.shape[1], "h": d.shape[0],
                "buraco": round(float(buraco.mean()), 4)}
        prof = np.dstack([np.zeros_like(d), db, d])  # BGR: R = frente, G = fundo
        ok1, jc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 93])
        ok2, jf = cv2.imencode(".jpg", fundo, [cv2.IMWRITE_JPEG_QUALITY, 90])
        ok3, pp = cv2.imencode(".png", (prof * 255).round().astype(np.uint8))
        b64 = lambda b: base64.b64encode(b.tobytes()).decode()
        n = nome if nome else re.sub(r"[^A-Za-z0-9_-]", "_", src.stem)
        js = (f"// gerado por edin profundidade a partir de {src.name}: foto, fundo preenchido e profundidade "
              f"(R = frente, G = fundo)\n(window.EDIN_FOTOS = window.EDIN_FOTOS || {{}})[{json.dumps(n)}] = {{\n"
              f"  meta: {json.dumps(meta)},\n  cor: 'data:image/jpeg;base64,{b64(jc)}',\n"
              f"  fundo: 'data:image/jpeg;base64,{b64(jf)}',\n  prof: 'data:image/png;base64,{b64(pp)}',\n}};\n")
        Path(f"{base}.foto3d.js").write_text(js)
        return {"foto": str(src), "depth": f"{base}.depth.png", "fundo": f"{base}.fundo.png",
                "js": f"{base}.foto3d.js", "nome": n, "meta": meta, "pos_s": round(time.time() - tp, 2)}


# ---------------------------------------------------------------------------------------------- CLI
def cmd_imagem(a):
    if a.lote:
        itens, tam, cfg = itens_do_lote(a.lote, a.so.split(",") if a.so else None)
        up = a.upscale or cfg.get("upscale", "lanczos")
    else:
        if not a.prompt:
            sys.exit("[edin] passe o prompt ou --lote arquivo.json")
        itens, tam = itens_do_comando(a)
        up = a.upscale or "lanczos"
    if not itens:
        sys.exit("[edin] nada para gerar")
    for it in itens:
        print(f"[edin] {Path(it['saida']).name}  seed {it['seed']}")
    if a.mostrar_prompt:
        for it in itens:
            print(f"   {it['prompt']}")
    res = gerar(itens, tam, up, lightning=not a.sem_lightning)
    for r in res:
        print(f"[edin] OK {r['saida']}")
    if a.profundidade:
        profundidade([r["saida"] for r in res])


def cmd_profundidade(a):
    for f in a.fotos:
        if not Path(f).exists():
            sys.exit(f"[edin] {f} não existe")
    profundidade(a.fotos, a.folga, a.lado, a.nome)


def add_parsers(sp):
    s = sp.add_parser("imagem", help="foto realista gerada na máquina (SDXL + Lightning 4 passos), ver docs/IMAGEM.md")
    s.add_argument("prompt", nargs="?", help="descrição em inglês (o estilo de foto de campanha é acrescentado)")
    s.add_argument("-o", "--out", help="saída .png (padrão foto.png; com --n 4: foto_1.png ... foto_4.png)")
    s.add_argument("--size", default="1080x1920", help="tamanho final (gera na nativa do SDXL mais próxima e amplia)")
    s.add_argument("--seed", type=int, help="semente (padrão: sorteada e impressa); com --n, seed, seed+1...")
    s.add_argument("--n", type=int, default=1, help="quantas variações (seeds seguidas)")
    s.add_argument("--negativo", help="prompt negativo (só vale com --cfg > 1 ou --sem-lightning)")
    s.add_argument("--passos", type=int, help="passos (padrão 4 com Lightning, 28 sem)")
    s.add_argument("--cfg", type=float, help="guidance (padrão 0 com Lightning, 5.5 sem)")
    s.add_argument("--estilo", default="campanha", help="campanha|noite|documental|nenhum ou texto livre")
    s.add_argument("--lente", help="24|35|50|85|macro ou texto")
    s.add_argument("--personagem", help="descrição física fixa do personagem (igual em todos os planos dele)")
    s.add_argument("--upscale", choices=["lanczos", "esrgan"], help="ampliação até o tamanho final (padrão lanczos)")
    s.add_argument("--lote", help="JSON com personagens e planos de um roteiro (ver docs/IMAGEM.md)")
    s.add_argument("--so", help="com --lote: só estes ids de plano (separados por vírgula)")
    s.add_argument("--sem-lightning", action="store_true", help="SDXL puro, 28 passos com CFG e negativo (~6x mais lento)")
    s.add_argument("--profundidade", action="store_true", help="também roda o edin profundidade nas fotos geradas")
    s.add_argument("--mostrar-prompt", action="store_true", help="imprime o prompt final")
    s.set_defaults(fn=cmd_imagem)

    s = sp.add_parser("profundidade", help="mapa de profundidade (Depth Anything V2) + fundo + pacote .foto3d.js")
    s.add_argument("fotos", nargs="+")
    s.add_argument("--folga", type=float, default=0.06,
                   help="largura do fundo preenchido atrás das bordas, em fração do lado menor (padrão 0,06)")
    s.add_argument("--lado", type=int, default=770, help="lado menor na rede (múltiplo de 14; padrão 770)")
    s.add_argument("--nome", help="nome no EDIN_FOTOS (padrão: nome do arquivo)")
    s.set_defaults(fn=cmd_profundidade)
