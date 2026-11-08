"""Detecção de trocas de plano (cortes) com PySceneDetect (AdaptiveDetector).

Usos no edin:
- `edin scenes video.mp4` -> `video.scenes.json` (cortes e cenas, com cache);
- o rastreio de rosto e o `pan` recomeçam a cada plano (nunca atravessam um corte);
- `edin montage` encaixa cada pedaço dentro de um plano só (sem quadro do plano vizinho no começo ou no fim);
- `scene_segments()` gera um segmento por cena para o agente reenquadrador-vertical.

Cada corte leva uma nota: `hard` = troca de câmera/plano de verdade; `false` = o enquadramento continua e só o
conteúdo mudou (banner que entra numa tela de app, rolagem, texto trocando no motion). A câmera virtual e o `pan`
recomeçam só nos cortes `hard`; a lista completa serve para separar cenas.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import numpy as np

from .utils import is_image, load_json, probe, save_json

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "edin" / "scenes"
VERSION = 2
THRESHOLD = 3.0  # adaptive_threshold do AdaptiveDetector (padrão do PySceneDetect)
MIN_SCENE = 0.4  # segundos: cortes mais próximos que isso viram um só


def _key(video: str, extra: str = "") -> str:
    st = Path(video).stat()
    raw = f"{Path(video).resolve()}|{st.st_size}|{int(st.st_mtime)}|{VERSION}|{THRESHOLD}|{MIN_SCENE}|{extra}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _frame(video: str, t: float):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
                          "-vf", "scale=160:90", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(90, 160, 3) if len(raw) == 160 * 90 * 3 else None


def cut_score(video: str, t: float) -> dict:
    """Compara o quadro antes e depois do corte: correlação de histograma de cor (HS) e fração de bordas que
    continuam no lugar. Mesma paleta E mesmas bordas = o plano continua (corte `hard: false`).
    Medido: trocas de câmera de palestra dão hist <= 0,78 ou bordas <= 0,64; banner/rolagem em tela de app,
    hist >= 0,98 e bordas >= 0,66."""
    import cv2

    a, b = _frame(video, t - 0.12), _frame(video, t + 0.08)
    if a is None or b is None:
        return {"t": t, "hist": 0.0, "edges": 0.0, "hard": True}
    hs = [cv2.calcHist([cv2.cvtColor(x, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 16], [0, 180, 0, 256])
          for x in (a, b)]
    hist = float(cv2.compareHist(hs[0], hs[1], cv2.HISTCMP_CORREL))
    ea, eb = cv2.Canny(a, 60, 160) > 0, cv2.Canny(b, 60, 160) > 0
    k = np.ones((3, 3), np.uint8)
    da, db = cv2.dilate(ea.astype(np.uint8), k) > 0, cv2.dilate(eb.astype(np.uint8), k) > 0
    edges = float(((ea & db).sum() + (eb & da).sum()) / max(1, ea.sum() + eb.sum()))
    return {"t": t, "hist": round(hist, 3), "edges": round(edges, 3), "hard": not (hist >= 0.9 and edges >= 0.6)}


def _detect(video: str, start: float | None = None, end: float | None = None) -> list[dict]:
    """Cortes detectados entre start e end: [{t, hist, edges, hard}]."""
    try:
        from scenedetect import AdaptiveDetector, detect
    except ImportError as e:
        raise SystemExit("[edin] PySceneDetect não instalado. Rode: pip install 'scenedetect[opencv-headless]'") from e
    fps = probe(video)["fps"] or 30.0
    det = AdaptiveDetector(adaptive_threshold=THRESHOLD, min_scene_len=max(2, int(round(MIN_SCENE * fps))))
    scenes = detect(video, det, start_time=start, end_time=end, show_progress=False)
    return [cut_score(video, round(s[0].seconds, 3)) for s in scenes[1:]]


def detect_scenes(video: str, out: str | None = None, force: bool = False) -> dict:
    """Detecta os cortes do vídeo inteiro. Grava `out` (se pedido) e um cache em ~/.cache/edin/scenes."""
    cache = CACHE_DIR / f"{_key(video)}.json"
    if cache.exists() and not force:
        data = load_json(str(cache))
    else:
        info = probe(video)
        print(f"[edin] Detectando cenas em {Path(video).name} (PySceneDetect AdaptiveDetector)...")
        detail = _detect(video)
        cuts = [c["t"] for c in detail]
        bounds = [0.0, *cuts, round(info["duration"], 3)]
        data = {"video": str(Path(video).resolve()), "duration": round(info["duration"], 3), "fps": info["fps"],
                "detector": "adaptive", "threshold": THRESHOLD, "min_scene": MIN_SCENE, "cuts": cuts,
                "hard_cuts": [c["t"] for c in detail if c["hard"]], "detail": detail,
                "scenes": [{"start": a, "end": b} for a, b in zip(bounds, bounds[1:]) if b - a > 1e-3]}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        save_json(data, str(cache))
    if out:
        save_json(data, out)
    return data


def _sidecar(video: str) -> Path:
    return Path(video).with_name(Path(video).stem + ".scenes.json")


def cuts_between(video: str, t0: float, t1: float, hard_only: bool = True) -> list[float]:
    """Cortes dentro de (t0, t1), em tempo da fonte. Usa o `video.scenes.json` ao lado, o cache do vídeo inteiro
    ou, se não houver, detecta só a janela do segmento (rápido em vídeos longos) e guarda em cache."""
    if is_image(video) or not Path(video).exists():
        return []
    detail = None
    for f in (_sidecar(video), CACHE_DIR / f"{_key(video)}.json"):
        if f.exists():
            d = load_json(str(f))
            detail = d.get("detail") or [{"t": t, "hard": True} for t in d.get("cuts", [])]
            break
    if detail is None:
        a, b = max(0.0, t0 - 0.5), t1 + 0.5
        win = CACHE_DIR / f"{_key(video, f'{a:.3f}-{b:.3f}')}.json"
        if win.exists():
            detail = load_json(str(win))
        else:
            detail = _detect(video, a, b)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            save_json(detail, str(win))
    return [c["t"] for c in detail if t0 < c["t"] < t1 and (c.get("hard", True) or not hard_only)]


def shots(video: str, t0: float, t1: float, min_len: float = 0.3) -> list[tuple[float, float]]:
    """Divide [t0, t1] em planos pelos cortes `hard`. Pedaços menores que `min_len` nas pontas são absorvidos
    (o corte cai quase na borda do segmento: não vale recomeçar a câmera por poucos quadros)."""
    cuts = [c for c in cuts_between(video, t0, t1) if c - t0 >= min_len and t1 - c >= min_len]
    bounds = [t0, *cuts, t1]
    return [(a, b) for a, b in zip(bounds, bounds[1:])]


def fit_in_shot(cuts: list[float], start: float, dur: float, total: float) -> float:
    """Desloca `start` o mínimo possível para o trecho [start, start+dur] caber num plano só.
    Se nenhum plano comporta o trecho, devolve `start` sem mudar."""
    end = start + dur
    if not [c for c in cuts if start + 0.02 < c < end - 0.02]:
        return start
    bounds = [0.0, *cuts, total]
    best = None
    for a, b in zip(bounds, bounds[1:]):
        if b - a < dur:
            continue
        cand = min(max(start, a), b - dur)  # posição mais próxima dentro deste plano
        if best is None or abs(cand - start) < abs(best - start):
            best = cand
    return start if best is None else round(best, 3)


def scene_segments(video: str, min_len: float = 0.4, hard_only: bool = False, **extra) -> list[dict]:
    """Um segmento por cena (`{"start", "end", **extra}`), juntando cenas curtas (flash, transição) com a
    anterior. Base pronta para o agente reenquadrador-vertical classificar e preencher fit/pan/zoom.
    `hard_only=True` separa só nas trocas de plano de verdade (ignora banner/rolagem dentro da mesma tela)."""
    data = detect_scenes(video)
    cuts = data.get("hard_cuts", data["cuts"]) if hard_only else data["cuts"]
    bounds = [0.0, *cuts, data["duration"]]
    segs = []
    for a, b in zip(bounds, bounds[1:]):
        if segs and (b - a < min_len or segs[-1]["end"] - segs[-1]["start"] < min_len):
            segs[-1]["end"] = b
        else:
            segs.append({"start": a, "end": b, **extra})
    return segs
