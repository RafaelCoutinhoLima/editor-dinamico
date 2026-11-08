"""Emoji animado por cima do vídeo (estilo Submagic/Hormozi).

O libass não desenha emoji colorido de forma confiável, então cada emoji é um PNG do Twemoji
(https://github.com/jdecked/twemoji, gráficos CC BY 4.0 de Twitter/X e colaboradores), animado em quadros com
alfa (pop de entrada, leve flutuação, saída) e sobreposto com o `overlay` do ffmpeg acima da legenda, longe do rosto.

No plano: "captions": {"emoji": [{"word": 41, "emoji": "🔥"}, {"at": 3.2, "emoji": "💡", "duration": 1.2}]}
"""
from __future__ import annotations

import math
import shutil
import subprocess
import urllib.request
from pathlib import Path

import numpy as np

EMOJI_DIR = Path.home() / ".local" / "share" / "edin" / "emoji"
TWEMOJI_URLS = (
    "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/{kind}/{code}.{ext}",
    "https://raw.githubusercontent.com/jdecked/twemoji/main/assets/{kind}/{code}.{ext}",
)
MIN_GAP = 3.0        # no máximo 1 emoji a cada 3 s
DEFAULT_DUR = 1.2    # 0,8 a 2 s no padrão pro
SIZE = 150           # lado do emoji em px numa saída de 1080 de largura
UA = {"User-Agent": "edin/0.1 (+https://github.com/RafaelCoutinhoLima/editor-dinamico)"}


def twemoji_code(emoji: str) -> str:
    """'🔥' -> '1f525'. Como no Twemoji: sem o seletor FE0F, a não ser em sequências com ZWJ."""
    cps = [ord(c) for c in emoji]
    if 0x200D not in cps:
        cps = [c for c in cps if c != 0xFE0F]
    return "-".join(f"{c:x}" for c in cps)


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
    except Exception:
        return False
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return True


def emoji_png(emoji: str, px: int) -> Path:
    """PNG do emoji com pelo menos `px` de lado. Baixa só o que for usado para ~/.local/share/edin/emoji.
    Com rsvg-convert instalado usa o SVG (nítido em qualquer tamanho); senão o PNG 72x72 ampliado."""
    EMOJI_DIR.mkdir(parents=True, exist_ok=True)
    code = twemoji_code(emoji)
    candidates = [code] + ([code.replace("-fe0f", "")] if "-fe0f" in code else [])
    rsvg = shutil.which("rsvg-convert")
    for c in candidates:
        if rsvg:
            out = EMOJI_DIR / f"{c}_{px}.png"
            if out.exists():
                return out
            svg = EMOJI_DIR / f"{c}.svg"
            if svg.exists() or any(_download(u.format(kind="svg", code=c, ext="svg"), svg) for u in TWEMOJI_URLS):
                subprocess.run([rsvg, "-w", str(px), "-h", str(px), "-o", str(out), str(svg)], check=False)
                if out.exists():
                    return out
        png = EMOJI_DIR / f"{c}.png"
        if png.exists() or any(_download(u.format(kind="72x72", code=c, ext="png"), png) for u in TWEMOJI_URLS):
            return png
    raise SystemExit(f"[edin] Emoji {emoji!r} ({code}) não encontrado no Twemoji. Confira o caractere ou a internet.")


# ------------------------------------------------------------------ posição

def _face_boxes(faces: list, t0: float, t1: float, W: int, H: int) -> list:
    """Caixas do rosto (px, com folga) amostradas no intervalo. faces: [{t, x, y, size}] normalizados."""
    out = []
    for f in faces:
        if t0 - 0.5 <= f["t"] <= t1 + 0.5:
            # a caixa do YuNet vai do cabelo até um pouco abaixo do queixo: do topo até a boca/queixo
            s = f["size"] * H
            out.append((f["x"] * W - 0.38 * s, f["y"] * H - 0.5 * s, f["x"] * W + 0.38 * s, f["y"] * H + 0.40 * s))
    return out


def _hits(box, faces) -> bool:
    x0, y0, x1, y1 = box
    return any(x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1] for b in faces)


def place(items: list, layout: dict, words_out: list, W: int, H: int, faces: list | None = None):
    """Resolve tempo e posição de cada emoji. Devolve (lista, avisos)."""
    p = layout["params"]
    unit = W / 1080
    by_i = {w["i"]: w for w in words_out}
    word_pos = {w["i"]: (w, g) for g in layout["groups"] for w in g["words"]}
    res, warns = [], []
    top_safe, bot_safe = 220 * H / 1920, H - 450 * H / 1920
    for it in items:
        em = it.get("emoji")
        if not em:
            continue
        size = int(float(it.get("size", SIZE)) * unit)
        dur = float(it.get("duration", DEFAULT_DUR))
        if "word" in it:
            w = by_i.get(int(it["word"]))
            if not w:
                warns.append(f"emoji {em}: palavra #{it['word']} não está no vídeo final (cortada?); ignorado")
                continue
            t0 = max(0.0, w["s"] - 0.06)
            anchor = word_pos.get(w["i"])
        else:
            t0 = float(it.get("at", 0.0))
            anchor = None
            for g in layout["groups"]:
                if g["start"] <= t0 + 0.05 < g["end"]:
                    anchor = (None, g)
                    break
        t1 = t0 + dur
        gap = 0.12 * size
        if anchor:
            w, g = anchor
            x = w["x"] if w else (p["ml"] + W - p["mr"]) / 2
            line_y = w["y"] if w else (g["top"] + g["bottom"]) / 2
            top, bottom = g["top"], g["bottom"]
            xs = [ww["x"] - ww["width"] / 2 for ww in g["words"]] + [ww["x"] + ww["width"] / 2 for ww in g["words"]]
            left, right = min(xs), max(xs)
        else:
            x = (p["ml"] + W - p["mr"]) / 2
            top = bottom = line_y = p["pos_y"]
            left = right = x
        fb = _face_boxes(faces or [], t0, t1, W, H)
        # obstáculos: o rosto (olhos e boca) e as palavras da legenda na tela durante o emoji
        lh = p["letter"] * W / 1080 * 0.75
        txt = [(ww["x"] - ww["width"] / 2 - 6, ww["y"] - lh, ww["x"] + ww["width"] / 2 + 6, ww["y"] + lh)
               for g in layout["groups"] if g["start"] < t1 and g["end"] > t0 for ww in g["words"]]
        if "x" in it or "y" in it:  # posição manual (normalizada)
            cands = [(float(it.get("x", x / W)) * W, float(it.get("y", (top - gap - size / 2) / H)) * H, 1.0)]
        else:
            cands = []
            for sc in (1.0, 0.8):
                h2, g2 = size * sc / 2, gap * sc
                cands += [(x, top - g2 - h2, sc),                     # acima da palavra (padrão)
                          ((left + right) / 2, top - g2 - h2, sc)]    # acima do centro da legenda
            cands += [(right + gap + size / 2, line_y, 1.0),          # à direita da legenda
                      (left - gap - size / 2, line_y, 1.0)]           # à esquerda da legenda
            if fb:  # ao lado da cabeça, na altura da boca, do lado com mais espaço
                fx0 = sorted(b[0] for b in fb)[len(fb) // 2]
                fx1 = sorted(b[2] for b in fb)[len(fb) // 2]
                fy = sorted((b[1] + b[3]) / 2 for b in fb)[len(fb) // 2]
                sides = [(fx0 - gap - size / 2, fy, 1.0), (fx1 + gap + size / 2, fy, 1.0)]
                cands += sorted(sides, key=lambda c: -min(c[0] - p["ml"], W - p["mr"] - c[0]))
            cands += [(x, bottom + gap + size / 2, 1.0)]              # abaixo da legenda
        chosen = None
        for cx, cy, sc in cands:
            half = size * sc / 2
            if not p["ml"] + half <= cx <= W - p["mr"] - half:
                continue
            box = (cx - half, cy - half, cx + half, cy + half)
            if cy - half < top_safe or cy + half > bot_safe:
                continue
            if not _hits(box, fb) and not _hits(box, txt):
                chosen = (cx, cy, sc)
                break
        if chosen is None:
            cx, cy, sc = cands[0]
            half = size * sc / 2
            chosen = (min(max(cx, p["ml"] + half), W - p["mr"] - half), cy, sc)
            warns.append(f"emoji {em} em {t0:.1f}s: não achei lugar livre (rosto/legenda); ficou acima da palavra. "
                         "Ajuste com \"x\"/\"y\" ou mude a palavra")
        res.append({"emoji": em, "t0": round(t0, 3), "t1": round(t1, 3), "size": int(size * chosen[2]),
                    "x": int(chosen[0]), "y": int(chosen[1])})
    res.sort(key=lambda e: e["t0"])
    warns += frequency_warnings(res)
    return res, warns


def frequency_warnings(res: list) -> list:
    out = []
    for a, b in zip(res, res[1:]):
        if b["t0"] - a["t0"] < MIN_GAP:
            out.append(f"emoji {b['emoji']} em {b['t0']:.1f}s fica a {b['t0'] - a['t0']:.1f}s do anterior "
                       f"(padrão pro: no máximo 1 a cada {MIN_GAP:g} s)")
    return out


def plan_warnings(cap: dict, words_out: list) -> list:
    """Avisos que dá para saber só pelo plano (antes do render)."""
    items = (cap or {}).get("emoji") or []
    by_i = {w["i"]: w for w in words_out}
    res = []
    for it in items:
        if "word" in it and int(it["word"]) in by_i:
            res.append({"emoji": it.get("emoji"), "t0": by_i[int(it["word"])]["s"]})
        elif "at" in it:
            res.append({"emoji": it.get("emoji"), "t0": float(it["at"])})
    res.sort(key=lambda e: e["t0"])
    return frequency_warnings(res)


# ------------------------------------------------------------------ animação

def _ease_out_back(x: float, k: float = 2.2) -> float:
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def render_frames(png: Path, size: int, dur: float, fps: float, out_dir: Path) -> int:
    """Quadros RGBA do emoji animado: pop com overshoot (0,22 s) subindo, flutuação leve, saída encolhendo."""
    import cv2

    src = cv2.imread(str(png), cv2.IMREAD_UNCHANGED)
    if src is None:
        raise RuntimeError(f"PNG inválido: {png}")
    if src.shape[2] == 3:
        src = np.dstack([src, np.full(src.shape[:2], 255, np.uint8)])
    master_px = int(size * 1.2)
    interp = cv2.INTER_CUBIC if master_px > src.shape[0] else cv2.INTER_AREA
    m = cv2.resize(src, (master_px, master_px), interpolation=interp).astype(np.float32)
    m[..., :3] *= m[..., 3:4] / 255.0  # pré-multiplica: sem halo escuro ao reamostrar
    canvas = int(size * 1.6) // 2 * 2
    out_dir.mkdir(parents=True, exist_ok=True)
    n = max(1, int(round(dur * fps)))
    t_in, t_out = 0.22, 0.18
    for f in range(n):
        t = f / fps
        if t < t_in:
            u = t / t_in
            sc, alpha, dy = 0.3 + 0.7 * _ease_out_back(u), min(1.0, u * 2.5), (1 - u) ** 3 * 0.22 * size
        elif t > dur - t_out:
            u = (t - (dur - t_out)) / t_out
            sc, alpha, dy = 1 - 0.45 * u * u, 1 - u, -0.10 * size * u
        else:
            sc, alpha, dy = 1.0, 1.0, 0.0
        sway = math.sin(2 * math.pi * (t - t_in) / 1.4) if t > t_in else 0.0
        sc *= 1 + 0.025 * sway
        ang = 5.0 * sway
        k = sc * size / master_px
        M = cv2.getRotationMatrix2D((master_px / 2, master_px / 2), ang, k)
        M[0, 2] += canvas / 2 - master_px / 2
        M[1, 2] += canvas / 2 - master_px / 2 + dy
        fr = cv2.warpAffine(m, M, (canvas, canvas), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0, 0))
        a = np.clip(fr[..., 3:4], 0, 255)
        rgb = np.where(a > 0, fr[..., :3] * 255.0 / np.maximum(a, 1e-3), 0)
        img = np.dstack([np.clip(rgb, 0, 255), a * alpha]).astype(np.uint8)
        cv2.imwrite(str(out_dir / f"{f:04d}.png"), img)
    return canvas
