"""Detecção de rosto (OpenCV, sem download de modelo) para reenquadrar e dar zoom no lugar certo."""
from __future__ import annotations

import statistics
import subprocess
from pathlib import Path

import numpy as np

from .utils import ROOT_DIR, is_image, load_json, probe, save_json

SAMPLE_FPS = 2.0
SAMPLE_W = 480


YUNET = ROOT_DIR / "assets" / "models" / "face_detection_yunet_2023mar.onnx"


def _detector(w: int, h: int):
    """Devolve uma função img_gray -> lista de (x, y, w, h). YuNet (preciso) ou Haar (reserva)."""
    import cv2

    if hasattr(cv2, "FaceDetectorYN") and YUNET.exists():
        det = cv2.FaceDetectorYN.create(str(YUNET), "", (w, h), 0.7, 0.3, 50)

        def yunet(gray):
            bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            _, faces = det.detect(bgr)
            return [] if faces is None else [tuple(f[:4]) for f in faces]

        return yunet
    xml = Path(getattr(getattr(cv2, "data", None), "haarcascades", "") or "") / "haarcascade_frontalface_default.xml"
    if xml.exists():
        casc = cv2.CascadeClassifier(str(xml))
        return lambda gray: list(casc.detectMultiScale(gray, 1.1, 6, minSize=(int(h * 0.08),) * 2))
    print("[edin] Aviso: nenhum detector de rosto disponível, usando enquadramento central.")
    return lambda gray: []


def face_track(src: str, cache_dir: Path) -> list:
    """Amostra o vídeo a 2 fps e devolve [{t, x, y, size}] normalizados (0..1) do maior rosto."""
    cache = cache_dir / (Path(src).name + ".faces.json")
    if cache.exists():
        return load_json(str(cache))
    import cv2

    info = probe(src)
    sh = int(round(SAMPLE_W * info["h"] / info["w"] / 2) * 2)
    det = _detector(SAMPLE_W, sh)
    if is_image(src):
        cmd = ["ffmpeg", "-v", "error", "-i", src, "-vf", f"scale={SAMPLE_W}:{sh}", "-f", "rawvideo",
               "-pix_fmt", "gray", "-frames:v", "1", "-"]
        fps = 1.0
    else:
        cmd = ["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={SAMPLE_FPS},scale={SAMPLE_W}:{sh}", "-f",
               "rawvideo", "-pix_fmt", "gray", "-"]
        fps = SAMPLE_FPS
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = SAMPLE_W * sh
    res, n = [], 0
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        img = np.frombuffer(buf, np.uint8).reshape(sh, SAMPLE_W)
        faces = det(img)
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = (float(v) for v in (x, y, w, h))
            res.append({"t": round(n / fps, 2), "x": round((x + w / 2) / SAMPLE_W, 4),
                        "y": round((y + h / 2) / sh, 4), "size": round(h / sh, 4)})
        n += 1
    proc.wait()
    save_json(res, str(cache))
    return res


def focus_for(track: list, start: float, end: float):
    """Centro do rosto (mediana) dentro do segmento; cai para vizinhança, global ou centro."""
    def med(items):
        return statistics.median(i["x"] for i in items), statistics.median(i["y"] for i in items)

    inside = [f for f in track if start <= f["t"] <= end]
    if inside:
        return med(inside), True
    near = [f for f in track if start - 2 <= f["t"] <= end + 2]
    if near:
        return med(near), True
    if track:
        return med(track), True
    return (0.5, 0.42), False


def crop_box(sw: int, sh: int, out_w: int, out_h: int, zoom: float, fx: float, fy: float, has_face: bool):
    """Caixa de recorte (x, y, w, h) na fonte com a proporção de saída, zoom e foco."""
    aspect = out_w / out_h
    if sw / sh > aspect:
        bh, bw = sh, sh * aspect
    else:
        bw, bh = sw, sw / aspect
    cw, ch = bw / zoom, bh / zoom
    cw, ch = int(min(cw, sw) // 2 * 2), int(min(ch, sh) // 2 * 2)
    # rosto fica a ~40% do topo do quadro (regra dos terços)
    cx = fx * sw - cw / 2
    cy = (fy * sh - 0.40 * ch) if has_face else (fy * sh - ch / 2)
    cx = int(min(max(cx, 0), sw - cw))
    cy = int(min(max(cy, 0), sh - ch))
    return cx, cy, cw, ch
