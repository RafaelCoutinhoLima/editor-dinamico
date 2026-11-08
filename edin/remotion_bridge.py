"""Ponte edin -> Remotion: "o edin corta, o Remotion embeleza".

Lê o plano (chave nova "motion": [...]) e o vídeo já renderizado pelo edin, monta as props da
composição EdinOverlay (remotion/src) e chama `npx remotion render`.

  props = palavras remapeadas para o tempo de saída (plan.remap_words)
        + trilha de rosto do vídeo editado (reframe.face_track, já em tempo e enquadramento de saída)
        + overlays do plano com tempos resolvidos (segundos ou índice de palavra #n)
        + recorte da pessoa (opcional, para a palavra atrás da cabeça)

Recorte da pessoa: modelo PP-HumanSeg (opencv_zoo, Apache-2.0, 6 MB) rodando no cv2.dnn, que o
edin já usa. Sem dependência nova; o modelo é baixado uma vez para ~/.cache/edin/models.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .plan import load_plan, remap_words
from .reframe import face_track
from .utils import FONTS_DIR, ROOT_DIR, probe, save_json, workdir_for

REMOTION_DIR = ROOT_DIR / "remotion"
PUBLIC_JOB = REMOTION_DIR / "public" / "edin"  # recriada a cada render (só a mídia deste vídeo entra no bundle)
COMPOSITION = "EdinOverlay"

TYPES = {"behind-head-word", "kinetic-title", "card", "checklist", "lower-third", "caption-pill"}
DEFAULT_DUR = {"behind-head-word": 2.5, "kinetic-title": 2.5, "card": 3.0, "checklist": 4.0, "lower-third": 3.5}
DEFAULT_ACCENT = "#FFE500"  # mesmo amarelo da legenda hormozi do edin

SEG_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/human_segmentation_pphumanseg/"
           "human_segmentation_pphumanseg_2023mar.onnx")
MODELS_DIR = Path(os.environ.get("EDIN_MODELS", Path.home() / ".cache" / "edin" / "models"))


# ---------------------------------------------------------------- props

def _motion_cfg(plan: dict) -> tuple[list, dict]:
    m = plan.get("motion") or []
    if isinstance(m, dict):  # forma longa: {"accent": "#...", "overlays": [...]}
        return list(m.get("overlays") or []), m
    return list(m), {}


def _resolve_time(item: dict, key: str, word_key: str, by_i: dict, edge: str):
    if item.get(key) is not None:
        return float(item[key])
    if item.get(word_key) is not None:
        w = by_i.get(int(item[word_key]))
        if w is None:
            raise SystemExit(f"[edin] motion: palavra #{item[word_key]} não está no vídeo final (foi cortada?)")
        return float(w[edge])
    return None


def resolve_overlays(items: list, words: list, duration: float, plan_caps: dict | None) -> tuple[list, list]:
    """Converte a lista "motion" do plano em overlays com start/end em segundos de saída."""
    by_i = {w["i"]: w for w in words}
    out, warns = [], []
    for n, raw in enumerate(items):
        o = dict(raw)
        t = o.get("type")
        if t not in TYPES:
            warns.append(f"motion[{n}]: tipo '{t}' desconhecido (use {', '.join(sorted(TYPES))}); ignorado")
            continue
        start = _resolve_time(o, "start", "word", by_i, "s")
        end = _resolve_time(o, "end", "word_end", by_i, "e")
        if t == "caption-pill":
            start = 0.0 if start is None else start
            end = duration if end is None else end
            emph = o.get("emphasis")
            if emph is None and plan_caps:
                emph = plan_caps.get("emphasis") or []
            o["emphasis"] = [int(i) for i in (emph or [])]
            if "words_per_page" in o:
                o["wordsPerPage"] = int(o.pop("words_per_page"))
        else:
            if start is None:
                raise SystemExit(f"[edin] motion[{n}] ({t}): falta 'start' (segundos) ou 'word' (índice #n)")
            if end is None:
                end = start + float(o.get("duration", DEFAULT_DUR[t]))
        start, end = max(0.0, start), min(duration, end)
        if end - start < 0.3:
            warns.append(f"motion[{n}] ({t}): janela {start:.2f}-{end:.2f}s curta demais; ignorado")
            continue
        o["start"], o["end"] = round(start, 3), round(end, 3)
        for k in ("word", "word_end", "duration"):
            o.pop(k, None)
        if t == "checklist":
            its = o.get("items") or []
            if not its:
                raise SystemExit(f"[edin] motion[{n}] (checklist): 'items' vazio")
            norm = []
            for k, it in enumerate(its):
                it = {"text": it} if isinstance(it, str) else dict(it)
                at = _resolve_time(it, "at", "word", by_i, "s")
                if at is None:  # distribui os itens ao longo da janela, deixando o primeiro respirar
                    at = start + 0.6 + (end - start - 1.2) * k / max(1, len(its))
                norm.append({"text": str(it["text"]), "at": round(at, 3)})
            o["items"] = norm
        if t in ("behind-head-word",) and len(str(o.get("text", ""))) > 12:
            warns.append(f"motion[{n}]: palavra atrás da cabeça funciona melhor com 1 palavra curta")
        out.append(o)
    return out, warns


def build_props(plan_path: str, video: str, cache_dir: Path) -> tuple[dict, list]:
    plan = load_plan(plan_path)
    info = probe(video)
    items, cfg = _motion_cfg(plan)
    words = [{"i": w["i"], "w": w["w"], "s": w["s"], "e": w["e"], "blk": w.get("blk", 0)} for w in remap_words(plan)]
    overlays, warns = resolve_overlays(items, words, info["duration"], plan.get("captions"))
    if plan.get("captions") and any(o["type"] == "caption-pill" for o in overlays):
        warns.append("o plano tem 'captions' (legenda queimada pelo edin) e 'caption-pill' no motion: "
                     "vão aparecer duas legendas. Renderize com \"captions\": null ou tire o caption-pill.")
    # trilha de rosto do PRÓPRIO vídeo editado: já está no tempo e no enquadramento de saída
    st = Path(video).stat()
    fdir = cache_dir / f"faces_{int(st.st_mtime)}_{st.st_size}"
    fdir.mkdir(parents=True, exist_ok=True)
    face = face_track(video, fdir)
    if not face:
        warns.append("nenhum rosto detectado no vídeo editado: overlays usam um rosto central presumido")
    props = {
        "video": "edin/video" + Path(video).suffix.lower(),
        "person": None,
        "width": info["w"],
        "height": info["h"],
        "fps": round(info["fps"], 3),
        "duration": round(info["duration"], 3),
        "words": words,
        "face": face,
        "overlays": overlays,
        "accent": cfg.get("accent") or plan.get("motion_accent") or DEFAULT_ACCENT,
        "showGuides": False,
    }
    return props, warns


# ---------------------------------------------------------------- recorte da pessoa (opcional)

def _seg_model() -> Path:
    p = MODELS_DIR / "human_segmentation_pphumanseg_2023mar.onnx"
    if not p.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[edin] baixando modelo de recorte (6 MB) -> {p}")
        urllib.request.urlretrieve(SEG_URL, p)
    return p


def person_matte(video: str, out_webm: Path, windows: list | None = None) -> Path:
    """Pessoa sobre fundo transparente (VP9 com alfa), mesmo tamanho e tempo do vídeo.

    `windows`: lista de (start, end) em segundos; fora delas o quadro sai vazio (mais rápido).
    """
    import cv2
    import numpy as np

    info = probe(video)
    W, H, fps = info["w"], info["h"], info["fps"]
    net = cv2.dnn.readNetFromONNX(str(_seg_model()))
    src = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", f"{fps}", "-i", "-", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
                            "-crf", "32", "-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1",
                            "-auto-alt-ref", "0", str(out_webm)], stdin=subprocess.PIPE)
    size = W * H * 3
    prev, n = None, 0
    empty = np.zeros((H, W, 4), np.uint8).tobytes()
    k = max(3, int(W / 270) | 1)
    side = min(W, H)
    n_tiles = -(-max(W, H) // side)
    offs = [round(i * (max(W, H) - side) / max(1, n_tiles - 1)) for i in range(n_tiles)]
    while True:
        buf = src.stdout.read(size)
        if len(buf) < size:
            break
        t = n / fps
        n += 1
        if windows and not any(s - 0.5 <= t <= e + 0.5 for s, e in windows):
            enc.stdin.write(empty)
            prev = None
            continue
        rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        # o modelo espera quadrado (192x192): roda em ladrilhos quadrados ao longo do lado maior
        # (esmagar 9:16 num quadrado corta cabelo e ombros) e junta pelo máximo
        m = np.zeros((H, W), np.float32)
        for o in offs:
            tile = rgb[o:o + side] if H >= W else rgb[:, o:o + side]
            blob = (cv2.dnn.blobFromImage(tile, 1 / 255.0, (192, 192)) - 0.5) / 0.5
            net.setInput(blob)
            pm = cv2.resize(net.forward()[0, 1], (side, side), interpolation=cv2.INTER_CUBIC)  # prob. de pessoa
            if H >= W:
                m[o:o + side] = np.maximum(m[o:o + side], pm)
            else:
                m[:, o:o + side] = np.maximum(m[:, o:o + side], pm)
        m = np.clip((m - 0.4) / 0.25, 0, 1)  # limiar suave
        m = m if prev is None else 0.65 * m + 0.35 * prev  # menos tremida nas bordas
        prev = m
        m = cv2.GaussianBlur(m, (k, k), 0)
        enc.stdin.write(np.dstack([rgb, (m * 255).astype(np.uint8)]).tobytes())
    enc.stdin.close()
    enc.wait()
    src.wait()
    if enc.returncode != 0:
        raise RuntimeError("[edin] falha ao gerar o recorte da pessoa (ffmpeg sem libvpx-vp9?)")
    return out_webm


# ---------------------------------------------------------------- mídia e render

def _link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.link(src, dst)  # hardlink: sem cópia e o bundler do Remotion enxerga como arquivo normal
    except OSError:
        shutil.copy2(src, dst)


def prepare_public(video: str, person: Path | None) -> None:
    if PUBLIC_JOB.exists():
        shutil.rmtree(PUBLIC_JOB)
    PUBLIC_JOB.mkdir(parents=True)
    _link(Path(video).resolve(), PUBLIC_JOB / ("video" + Path(video).suffix.lower()))
    for f in ("Anton-Regular.ttf", "Montserrat-ExtraBold.ttf"):
        _link(FONTS_DIR / f, PUBLIC_JOB / "fonts" / f)
    if person:
        _link(person, PUBLIC_JOB / "person.webm")


def _npx() -> str:
    npx = shutil.which("npx")
    if not npx:
        raise SystemExit("[edin] npx não encontrado. Instale o Node.js 18+ (https://nodejs.org) para usar 'edin motion'.")
    if not (REMOTION_DIR / "node_modules" / "remotion").exists():
        npm = shutil.which("npm")
        print("[edin] instalando dependências do Remotion (uma vez só)...")
        subprocess.run([npm or "npm", "install", "--no-fund", "--no-audit"], cwd=REMOTION_DIR, check=True)
    return npx


def motion(plan_path: str, video: str, output: str, matte: str = "auto", props_only: bool = False,
           guides: bool = False, concurrency: int | None = None, verbose: bool = False) -> str:
    wd = workdir_for(output)
    props, warns = build_props(plan_path, video, wd / "cache")
    props["showGuides"] = guides
    behind = [(o["start"], o["end"]) for o in props["overlays"] if o["type"] == "behind-head-word"]
    person = None
    if behind and matte != "off":
        try:
            person = person_matte(video, wd / "person.webm", behind)
            props["person"] = "edin/person.webm"
            print(f"[edin] recorte da pessoa: {person}", flush=True)
        except Exception as e:  # sem modelo/rede/libvpx: cai para a máscara elíptica pelo rosto
            if matte == "on":
                raise
            warns.append(f"recorte da pessoa indisponível ({e}); usando máscara pelo rosto")
    for w in warns:
        print(f"[edin] aviso: {w}", flush=True)
    prepare_public(video, person)
    props_path = wd / "props.json"
    save_json(props, str(props_path))
    n = {}
    for o in props["overlays"]:
        n[o["type"]] = n.get(o["type"], 0) + 1
    print(f"[edin] props: {len(props['words'])} palavras, {len(props['face'])} amostras de rosto, overlays "
          + (", ".join(f"{v}x {k}" for k, v in n.items()) or "nenhum") + f" -> {props_path}", flush=True)
    if props_only:
        print(f"[edin] prévia: cd remotion && npx remotion studio --props={props_path}")
        return str(props_path)
    npx = _npx()
    out = Path(output).resolve()
    cmd = [npx, "remotion", "render", "src/index.ts", COMPOSITION, str(out), f"--props={props_path}",
           "--codec=h264", "--crf=18", "--log=" + ("verbose" if verbose else "info")]
    if concurrency:
        cmd.append(f"--concurrency={concurrency}")
    if os.environ.get("EDIN_BROWSER"):  # ex.: /usr/bin/google-chrome se o chrome-headless-shell não abrir
        cmd.append(f"--browser-executable={os.environ['EDIN_BROWSER']}")
    if verbose:
        print("[edin] $", " ".join(cmd))
    r = subprocess.run(cmd, cwd=REMOTION_DIR)
    if r.returncode != 0:
        raise SystemExit("[edin] o render do Remotion falhou (veja o log acima). Se o Chrome não abriu por falta de "
                         "bibliotecas, veja docs/MOTION.md (seção Problemas).")
    print(f"[edin] pronto: {out}")
    return str(out)
