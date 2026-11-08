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
        try:  # o OpenCV 5 avisa "setPreferableTarget" a cada detector criado: só ruído
            cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
        except AttributeError:
            pass
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


def activity_pan(src: str, t0: float, t1: float, view: float, cache_dir: Path) -> list:
    """Câmera lateral automática para telas de app, site e planilha (estilo Auto Reframe para UI).
    Devolve [x_inicio, x_fim] normalizados (centro do recorte).

    Interfaces são lidas da esquerda para a direita: a câmera mantém no quadro o INÍCIO do texto (rótulos, campos,
    o que está sendo digitado). O início é achado pelas bordas de letras (Canny) abaixo do topo da tela, quadro a
    quadro, e suavizado pela mediana de cada terço do segmento (a transição de entrada não engana).
    Zona morta: se o alvo anda menos de 6% da largura, a câmera fica parada.
    É uma proposta, como o Auto Reframe: telas com texto CENTRALIZADO (loader, card central) podem sair cortadas;
    confira cada segmento e troque por `pan` manual onde errar.
    `view` = largura do recorte / largura da fonte."""
    import cv2

    key = cache_dir / f"{Path(src).name}.pan7_{t0:.2f}_{t1:.2f}_{view:.3f}.json"
    if key.exists():
        return load_json(str(key))
    w = 480
    info = probe(src)
    h = int(round(w * info["h"] / info["w"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{max(0.2, t1 - t0):.3f}", "-i", src,
                          "-vf", f"fps=4,scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h)
    half = view / 2

    def clamp(x):
        return float(min(max(x, half), 1 - half))

    alvos = []
    for f in np.frombuffer(raw[:n * w * h], np.uint8).reshape(n, h, w):
        e = cv2.Canny(f, 60, 160)[int(h * 0.22):]
        bordas = (e > 0).sum(axis=0).astype(float)
        bordas[bordas > e.shape[0] * 0.35] = 0  # linhas verticais longas são borda de card/janela, não texto
        if bordas.sum() < 1:
            continue
        acum = np.cumsum(bordas) / bordas.sum()
        inicio = (np.searchsorted(acum, 0.08) + 0.5) / w  # onde começa o texto (8% das bordas à esquerda)
        fim = (np.searchsorted(acum, 0.92) + 0.5) / w
        if fim - inicio <= view * 0.9:
            alvos.append((inicio + fim) / 2)  # conteúdo estreito: centraliza nele
        else:
            alvos.append(inicio - 0.03 + half)  # conteúdo largo: mantém o início da leitura com margem
    if not alvos:
        res = [0.5, 0.5]
    else:
        k = max(1, len(alvos) // 3)
        x0, x1 = float(np.median(alvos[:k])), float(np.median(alvos[-k:]))
        if abs(x1 - x0) < 0.06:
            x0 = x1 = float(np.median(alvos))
        res = [clamp(x0), clamp(x1)]
    save_json(res, str(key))
    return res


# ---------------------------------------------------------------- câmera virtual (estilo Premiere Auto Reframe)
#
# Por plano (nunca atravessa corte): alvo amostrado a CAM_FPS (rosto, ou atividade/saliência sem rosto), filtro
# One Euro de ida e volta (fase zero: tira o tremor da detecção sem atrasar), antecipação de LEAD s, zona morta
# com histerese (a câmera só sai do lugar quando o alvo deixa a zona morta e volta a parar quando o alcança), mola
# criticamente amortecida com velocidade máxima. Se o alvo varia pouco no plano inteiro, a câmera fica PARADA
# (o Premiere faz isso; o Resolve treme).

CAM_FPS = 6.0
CAM_STEP = 1 / 30
LEAD = 0.25
REFRAME_DEFAULT = {"mode": "auto", "deadzone": 0.15, "smooth": 1.0, "max_speed": 1.0}


def reframe_cfg(cfg) -> dict:
    """Normaliza o campo `reframe` do segmento: "static"/"track"/"auto" ou {"mode", "deadzone", "smooth", ...}."""
    if isinstance(cfg, str):
        cfg = {"mode": cfg}
    out = dict(REFRAME_DEFAULT)
    out.update({k: v for k, v in (cfg or {}).items() if v is not None})
    if out["mode"] not in ("static", "track", "auto"):
        raise SystemExit(f"[edin] reframe.mode inválido: {out['mode']} (use static, track ou auto)")
    return out


def _gray_window(src: str, t0: float, t1: float, fps: float, w: int):
    """Quadros em cinza (w de largura) entre t0 e t1 a `fps`; devolve (tempos, array n x h x w)."""
    info = probe(src)
    h = int(round(w * info["h"] / info["w"] / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{max(0.1, t1 - t0):.3f}", "-i", src,
                          "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h)
    frames = np.frombuffer(raw[:n * w * h], np.uint8).reshape(n, h, w)
    return [t0 + (k + 0.5) / fps for k in range(n)], frames


def face_window(src: str, t0: float, t1: float, cache_dir: Path, fps: float = CAM_FPS) -> list:
    """Rosto a `fps` dentro de [t0, t1]: [{t, x, y, size}] normalizados. Com mais de um rosto, fica com o mesmo
    do quadro anterior (o mais perto entre os grandes), em vez de pular para quem ficou maior por um instante."""
    key = cache_dir / f"{Path(src).name}.facecam4_{t0:.2f}_{t1:.2f}_{fps:g}.json"
    if key.exists():
        return load_json(str(key))
    ts, frames = _gray_window(src, t0, t1, fps, SAMPLE_W)
    res = []
    if len(frames):
        sh = frames.shape[1]
        det = _detector(SAMPLE_W, sh)
        dets = [[tuple(float(v) for v in f) for f in det(img)] for img in frames]
        # semente: persistência x área (quadros com detecção compatível x tamanho²). Quem fala costuma ser o rosto
        # grande, mas de perfil ou no escuro aparece em poucos quadros; a plateia de frente aparece em todos, pequena.
        # A partir da semente segue a MESMA pessoa para a frente e para trás.
        def support(f):
            cx = f[0] + f[2] / 2
            return sum(any(0.6 <= g[3] / f[3] <= 1.6 and abs(g[0] + g[2] / 2 - cx) <= 0.25 * SAMPLE_W for g in fs)
                       for fs in dets) * f[3] ** 2

        seeds = [(support(f), k, f) for k, fs in enumerate(dets) for f in fs]
        if seeds:
            _, k0, seed = max(seeds, key=lambda s: s[0])
            seed_prev = (seed[0] + seed[2] / 2, seed[1] + seed[3] / 2, seed[3])
            picked = {}

            def walk(order):
                prev, miss = seed_prev, 0
                for k in order:
                    faces = dets[k]
                    if prev is not None and miss < fps:  # mesma pessoa: tamanho parecido e perto de onde estava
                        faces = [f for f in faces if 0.6 <= f[3] / prev[2] <= 1.6
                                 and abs(f[0] + f[2] / 2 - prev[0]) <= 0.25 * SAMPLE_W]
                    if not faces:
                        miss += 1  # perdido (de perfil, coberto): não troca pela plateia; recomeça após 1 s
                        continue
                    miss = 0
                    big = max(f[3] for f in faces)
                    cand = [f for f in faces if f[3] >= 0.5 * big]
                    if prev is not None:
                        f = min(cand, key=lambda f: (f[0] + f[2] / 2 - prev[0]) ** 2 + (f[1] + f[3] / 2 - prev[1]) ** 2)
                    else:
                        f = max(cand, key=lambda f: f[3])
                    prev = (f[0] + f[2] / 2, f[1] + f[3] / 2, f[3])
                    picked[k] = f

            walk(range(k0, len(dets)))
            walk(range(k0, -1, -1))
            for k in sorted(picked):
                x, y, w, h = picked[k]
                res.append({"t": round(ts[k], 3), "x": round((x + w / 2) / SAMPLE_W, 4),
                            "y": round((y + h / 2) / sh, 4), "size": round(h / sh, 4)})
    save_json(res, str(key))
    return res


def _saliency(gray) -> tuple:
    """Saliência por resíduo espectral (Hou & Zhang 2007): centro (x, y) normalizado do que mais chama atenção."""
    import cv2

    h, w = gray.shape
    sw, sh = 64, max(8, int(64 * h / w))
    small = cv2.resize(gray, (sw, sh)).astype(np.float32)
    f = np.fft.fft2(small)
    log_a = np.log(np.abs(f) + 1e-6).astype(np.float32)
    resid = log_a - cv2.blur(log_a, (3, 3))
    sal = (np.abs(np.fft.ifft2(np.exp(resid + 1j * np.angle(f)))) ** 2).astype(np.float32)
    sal = cv2.GaussianBlur(sal, (9, 9), 2.5)
    m = np.clip(sal - sal.mean(), 0, None)
    tot = float(m.sum())
    if tot <= 0:
        return 0.5, 0.5
    ys, xs = np.mgrid[0:sh, 0:sw]
    return float((m * xs).sum() / tot + 0.5) / sw, float((m * ys).sum() / tot + 0.5) / sh


def activity_window(src: str, t0: float, t1: float, cache_dir: Path, fps: float = CAM_FPS) -> list:
    """Mapa de atividade com compensação do movimento GLOBAL da câmera (ORB + RANSAC, estimateAffinePartial2D):
    o quadro anterior é alinhado ao atual antes da diferença, então pan/tilt/zoom da câmera original não contam
    como atividade; sobra o que se mexe de verdade (pessoa, objeto, cursor). Sem atividade, usa a saliência.
    Devolve [{t, x, y, w, kind}] normalizados (w = fração de pixels ativos)."""
    import cv2

    key = cache_dir / f"{Path(src).name}.activity_{t0:.2f}_{t1:.2f}_{fps:g}.json"
    if key.exists():
        return load_json(str(key))
    ts, frames = _gray_window(src, t0, t1, fps, 320)
    res = []
    orb = cv2.ORB_create(600)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    prev, prev_kd = None, None
    for t, cur in zip(ts, frames):
        cur_b = cv2.GaussianBlur(cur, (3, 3), 0)
        kd = orb.detectAndCompute(cur_b, None)
        item = None
        if prev is not None:
            h, w = cur.shape
            m = None
            if prev_kd[1] is not None and kd[1] is not None and len(prev_kd[0]) >= 8 and len(kd[0]) >= 8:
                matches = bf.match(prev_kd[1], kd[1])
                if len(matches) >= 8:
                    p1 = np.float32([prev_kd[0][mm.queryIdx].pt for mm in matches])
                    p2 = np.float32([kd[0][mm.trainIdx].pt for mm in matches])
                    m, _ = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3.0)
            if m is None:
                m = np.float32([[1, 0, 0], [0, 1, 0]])
            warped = cv2.warpAffine(prev, m, (w, h))
            valid = cv2.erode(cv2.warpAffine(np.full_like(prev, 255), m, (w, h)), np.ones((5, 5), np.uint8))
            diff = cv2.absdiff(cur_b, warped)
            diff[valid == 0] = 0
            act = cv2.morphologyEx((diff > 22).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            frac = float(act.mean())
            if frac > 0.002:
                ys, xs = np.nonzero(act)
                item = {"x": float(xs.mean() + 0.5) / w, "y": float(ys.mean() + 0.5) / h, "w": frac, "kind": "motion"}
        if item is None:
            sx, sy = _saliency(cur_b)
            item = {"x": sx, "y": sy, "w": 0.0, "kind": "saliency"}
        res.append({"t": round(t, 3), **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in item.items()}})
        prev, prev_kd = cur_b, kd
    save_json(res, str(key))
    return res


def _one_euro(x: np.ndarray, dt: float, min_cutoff: float = 0.4, beta: float = 2.0, d_cutoff: float = 1.0):
    """Filtro One Euro (Casiez 2012): suaviza muito quando o alvo está quase parado e pouco quando anda rápido."""
    def alpha(cut):
        r = 2 * np.pi * cut * dt
        return r / (r + 1)

    out = np.empty_like(x)
    out[0], dx_prev = x[0], 0.0
    for i in range(1, len(x)):
        dx = (x[i] - out[i - 1]) / dt
        dx_prev = dx_prev + alpha(d_cutoff) * (dx - dx_prev)
        a = alpha(min_cutoff + beta * abs(dx_prev))
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def _follow(target: np.ndarray, dz: float, settle: float, vmax: float, dt: float) -> np.ndarray:
    """Câmera com zona morta + histerese e mola criticamente amortecida com velocidade máxima."""
    omega = 5.8 / max(0.2, settle)  # criticamente amortecida: assenta (2%) em ~`settle` segundos
    k0 = max(1, int(round(0.5 / dt)))
    goal = cam = float(np.median(target[:k0]))
    v, moving = 0.0, False
    out = np.empty_like(target)
    for i, x in enumerate(target):
        if not moving and abs(x - goal) > dz:
            moving = True
        if moving:
            goal = float(x)
            if abs(x - cam) < dz * 0.25 and abs(v) < vmax * 0.15:
                moving = False  # alcançou: trava no lugar até o alvo sair da zona morta de novo
        acc = omega * omega * (goal - cam) - 2 * omega * v
        v = float(np.clip(v + acc * dt, -vmax, vmax))
        cam += v * dt
        out[i] = cam
    return out


def camera_path(samples: list, t0: float, t1: float, view: float, cfg: dict, axis: str = "x"):
    """Trajetória do foco num plano, num eixo. `samples` = [{t, x, y}] do alvo (normalizado na fonte);
    `view` = tamanho do recorte relativo à fonte nesse eixo. Devolve (True, valor_parado) ou
    (False, (tempos, valores)). Sem amostras: (True, None)."""
    if not samples:
        return True, None
    ts = np.array([s["t"] for s in samples])
    xs = np.array([s[axis] for s in samples], dtype=float)
    dz = float(cfg["deadzone"]) * view
    lo, hi = np.percentile(xs, [5, 95])
    if cfg["mode"] == "static" or len(samples) < 2 or (cfg["mode"] == "auto" and hi - lo <= 2 * dz):
        return True, float(np.median(xs))
    grid = np.arange(t0, t1 + CAM_STEP / 2, CAM_STEP)
    raw = np.interp(grid, ts, xs)
    smooth = (_one_euro(raw, CAM_STEP) + _one_euro(raw[::-1], CAM_STEP)[::-1]) / 2
    lead = np.interp(grid + LEAD, grid, smooth)
    path = _follow(lead, dz, float(cfg["smooth"]), float(cfg["max_speed"]) * view, CAM_STEP)
    if cfg["mode"] == "auto" and np.ptp(path) < dz * 0.2:
        return True, float(np.median(path))
    return False, (grid, path)


def simplify_keys(ts, xs, tol: float = 0.4) -> list:
    """Reduz (t, x em px) a poucos pontos para interpolação linear com erro < tol px (Ramer-Douglas-Peucker)."""
    pts = list(zip((float(t) for t in ts), (float(x) for x in xs)))
    keep = {0, len(pts) - 1}
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        (ta, xa), (tb, xb) = pts[a], pts[b]
        best, worst = -1, tol
        for i in range(a + 1, b):
            ti, xi = pts[i]
            d = abs(xi - (xa + (xb - xa) * (ti - ta) / ((tb - ta) or 1e-9)))
            if d > worst:
                best, worst = i, d
        if best >= 0:
            keep.add(best)
            stack += [(a, best), (best, b)]
    return [pts[i] for i in sorted(keep)]


def piecewise_expr(keys: list) -> str:
    """Expressão do ffmpeg (variável t) que interpola linearmente os pontos (t, valor), sem if aninhado:
    v0 + soma(inclinação_i * clip(t - t_i, 0, dt_i)). Antes do 1º ponto e depois do último fica parado."""
    terms = [f"{keys[0][1]:.2f}"]
    for (ta, va), (tb, vb) in zip(keys, keys[1:]):
        if abs(vb - va) < 1e-3 or tb - ta <= 1e-6:
            continue
        terms.append(f"{(vb - va) / (tb - ta):+.4f}*clip(t-{ta:.4f},0,{tb - ta:.4f})")
    return "".join(terms)
