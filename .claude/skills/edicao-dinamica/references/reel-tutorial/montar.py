# Monta o Reel tutorial do LoopEdu quadro a quadro (OpenCV + PIL) e envia ao ffmpeg por rawvideo.
# Uso: python montar.py [saida.mp4] [--rascunho] [--so T0 T1]
import os, sys, json, math, subprocess, re
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from cenas import SCENES, HIDE

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda *p: os.path.join(W, *p)
OW, OH, FPS = 1080, 1920, 30
CARD_W, CARD_CY, CARD_R, CARD_HMAX = 1000, 960, 32, 1180
F600, F700 = A("assets", "Sora-600.ttf"), A("assets", "Sora-700.ttf")
GRAD = [(0x81, 0x8c, 0xf8), (0xa8, 0x55, 0xf7), (0xff, 0x6b, 0x4a)]
UMAP = json.load(open(A("rascunhos", "uniq_map.json")))
SC = 2  # fonte ampliada 2x (Real-ESRGAN)
SRC_W, SRC_H = 1362, 596

def font(path, size): return ImageFont.truetype(path, size)
def ease_out(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)

# ---------------- áudio: falas ----------------
NARR = A("fonte", "narracao.mp3")
def falas():
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", NARR, "-af", "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", NARR],
                               capture_output=True, text=True).stdout)
    segs, on = [], 0.0
    for a, b in zip(ss, se): segs.append((on, a)); on = b
    segs.append((on, dur))
    assert len(segs) == 16, len(segs)
    # conferido com transcrição: [0] intro, [1] matéria, [2,3] assuntos+ementa, ..., [14,15] fechamento
    groups = [[0], [1], [2, 3]] + [[i] for i in range(4, 14)] + [[14, 15]]
    return [(segs[g[0]][0], segs[g[-1]][1]) for g in groups], dur

LINES, NARR_DUR = falas()
LEAD, TAIL = 0.15, 0.60
INTRO_D = 4.5
CLOSE_D = max(3.7, (LINES[13][1] - LINES[13][0]) + LEAD + 0.45)

# ---------------- layout das cenas ----------------
def layout(sc):
    L = LINES[sc["line"]][1] - LINES[sc["line"]][0]
    D = round((L + LEAD + TAIL) * FPS) / FPS
    ps = sc["pieces"]
    fixed = sum((p[2] - p[1]) for p in ps if p[0] == "src" and p[3]) + sum(p[2] for p in ps if p[0] == "freeze" and p[2])
    flex = sum((p[2] - p[1]) for p in ps if p[0] == "src" and not p[3])
    rem_freeze = any(p[0] == "freeze" and p[2] is None for p in ps)
    if rem_freeze:
        speed = max(1.0, flex / max(D - fixed - 0.8, 0.1)) if flex else 1.0
        rest = D - fixed - flex / speed
    else:
        speed = flex / (D - fixed) if flex else 1.0
        speed = min(max(speed, 1.0), sc.get("maxspeed", 1.15))
        D = max(D, round((fixed + flex / speed) * FPS) / FPS)
        rest = D - fixed - flex / speed
    segs, t = [], 0.0
    for p in ps:
        if p[0] == "src":
            sp = 1.0 if p[3] else speed
            d = (p[2] - p[1]) / sp
            segs.append(dict(kind="src", t0=t, t1=t + d, a=p[1], b=p[2], sp=sp)); t += d
        else:
            d = p[2] if p[2] else rest
            segs.append(dict(kind="freeze", t0=t, t1=t + d, a=p[1], b=p[1], sp=0)); t += d
    if t < D - 1e-6:  # completa segurando o último quadro
        last = segs[-1]
        segs.append(dict(kind="freeze", t0=t, t1=D, a=last["b"], b=last["b"], sp=0, cam0=last["b"] + (last["t1"] - last["t0"] if last["kind"] == "freeze" else 0)))
    return dict(D=D, segs=segs, speed=speed, L=L)

def clock(lay, t):
    """tempo local -> (tempo do quadro na fonte, relógio da câmera)"""
    for s in lay["segs"]:
        if t < s["t1"] or s is lay["segs"][-1]:
            if s["kind"] == "src":
                st = min(s["a"] + (t - s["t0"]) * s["sp"], s["b"]); return st, st
            c0 = s.get("cam0", s["a"])
            return s["a"], c0 + (t - s["t0"])
    raise ValueError

def cam_at(kf, c):
    if c <= kf[0][0]: return kf[0][1:]
    for k0, k1 in zip(kf, kf[1:]):
        if c <= k1[0]:
            u = smooth((c - k0[0]) / (k1[0] - k0[0]))
            return tuple(a + (b - a) * u for a, b in zip(k0[1:], k1[1:]))
    return kf[-1][1:]

# ---------------- fundo, ícone, textos ----------------
def make_bg():
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    ang = math.radians(160); dx, dy = math.sin(ang), -math.cos(ang)
    Lg = abs(OW * dx) + abs(OH * dy)
    t = ((xx - OW / 2) * dx + (yy - OH / 2) * dy) / Lg + 0.5
    stops = [(0, (0x1e, 0x1b, 0x4b)), (0.45, (0x19, 0x1a, 0x3f)), (1.0, (0x0f, 0x17, 0x2a))]
    img = np.zeros((OH, OW, 3), np.float32)
    for c in range(3):
        img[..., c] = np.interp(t, [s[0] for s in stops], [s[1][c] for s in stops])
    for (cx, cy, r, a) in [(540, 470, 820, 0.42), (540, 1650, 700, 0.16)]:
        d = np.sqrt((xx - cx) ** 2 + ((yy - cy) * 1.05) ** 2) / r
        m = (np.clip(1 - d, 0, 1) ** 2 * a)[..., None]
        img = img * (1 - m) + np.array([79, 70, 229], np.float32) * m
    return img

def rounded_mask(w, h, r, ss=1):
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS) if ss > 1 else m

LOGO = Image.open(A("assets", "logo.jpeg")).convert("RGB")
def icon(size):
    im = LOGO.resize((size, size), Image.LANCZOS).convert("RGBA")
    im.putalpha(rounded_mask(size, size, int(size * 0.23), 4)); return im

def glow(size, color=(99, 102, 241), alpha=0.75):
    pad = size; im = Image.new("RGBA", (size + 2 * pad, size + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([pad, pad, pad + size, pad + size], fill=color + (int(255 * alpha),))
    return im.filter(ImageFilter.GaussianBlur(size * 0.32))

def text_img(txt, path, size, fill=(255, 255, 255), gradient=False):
    f = font(path, size); bb = f.getbbox(txt)
    w, h = bb[2] - bb[0] + 8, bb[3] - bb[1] + 8
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).text((4 - bb[0], 4 - bb[1]), txt, font=f, fill=255)
    if gradient:
        x = np.linspace(0, 1, w)
        cols = np.stack([np.interp(x, [0, 0.5, 1], [g[c] for g in GRAD]) for c in range(3)], -1)
        rgb = np.repeat(cols[None], h, 0).astype(np.uint8); im = Image.fromarray(rgb).convert("RGBA")
    else:
        im = Image.new("RGBA", (w, h), fill + (255,))
    im.putalpha(m); return im

def pill(txt, size=46, path=F600, padx=38, pady=22, color=(255, 255, 255), bg=0.13, border=0.24, track=0):
    t = text_img(txt, path, size, color)
    w, h = t.width + 2 * padx, t.height + 2 * pady
    ss = 3; im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], h * ss // 2, fill=(255, 255, 255, int(255 * bg)),
                        outline=(255, 255, 255, int(255 * border)), width=2 * ss)
    im = im.resize((w, h), Image.LANCZOS); im.alpha_composite(t, (padx, pady)); return im

def to_np(im):  # RGBA PIL -> (rgb float, alpha float)
    a = np.asarray(im, np.float32); return a[..., :3], a[..., 3:] / 255.0

def blit(canvas, im, cx, cy, op=1.0, scale=1.0):
    if op <= 0.003: return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    rgb, a = to_np(im); a = a * op
    x0, y0 = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + im.width, OW), min(y0 + im.height, OH)
    if xa >= xb or ya >= yb: return
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    c = canvas[ya:yb, xa:xb]; c[:] = c * (1 - a[sub]) + rgb[sub] * a[sub]

BG = make_bg()
FOOT_ICON = icon(60); FOOT_TXT = text_img("LoopEdu", F700, 40)
def footer(canvas, op=1.0):
    gap = 18; tw = FOOT_ICON.width + gap + FOOT_TXT.width; x0 = 540 - tw / 2
    blit(canvas, FOOT_ICON, x0 + 30, 1610, op); blit(canvas, FOOT_TXT, x0 + 60 + gap + FOOT_TXT.width / 2, 1610, op)

# ---------------- quadros da fonte ----------------
_cache = {}
def src_frame(t):
    i = int(round(t * FPS)); name = None
    for k in (i, i - 1, i + 1, i - 2, i + 2):
        if f"{k:05d}.png" in UMAP: name = UMAP[f"{k:05d}.png"]; break
    if name is None: raise KeyError(t)
    if name not in _cache:
        if len(_cache) > 40: _cache.clear()
        pc = A("rascunhos", "src_x2c", name)  # quadro com o cursor gravado apagado
        _cache[name] = cv2.cvtColor(cv2.imread(pc if os.path.exists(pc) else A("rascunhos", "src_x2", name)), cv2.COLOR_BGR2RGB)
    f = _cache[name]
    hs = [r for (a, b, r) in HIDE if a <= t <= b]
    if hs:
        f = f.copy()
        for (x0, y0, x1, y1) in hs:
            x0, y0, x1, y1 = x0 * SC, y0 * SC, x1 * SC, y1 * SC
            L = f[y0:y1, x0 - 1:x0].astype(np.float32); R = f[y0:y1, x1:x1 + 1].astype(np.float32)
            u = np.linspace(0, 1, x1 - x0, dtype=np.float32)[None, :, None]
            f[y0:y1, x0:x1] = (L * (1 - u) + R * u).astype(np.uint8)
    return f

def crop_card(frame, cx, cy, w, h):
    w = min(w, SRC_W); h = min(h, SRC_H)
    cx = min(max(cx, w / 2), SRC_W - w / 2); cy = min(max(cy, h / 2), SRC_H - h / 2)
    ch = int(round(CARD_W * h / w))
    if ch > CARD_HMAX: ch = CARD_HMAX
    x0, y0 = (cx - w / 2) * SC, (cy - h / 2) * SC
    # recorte subpixel por transformação afim (evita tremida em movimentos lentos)
    sx = CARD_W / (w * SC); sy = ch / (h * SC)
    M = np.float32([[sx, 0, -x0 * sx], [0, sy, -y0 * sy]])
    if sx < 0.75:  # reduz antes para não serrilhar
        k = sx / 0.9
        small = cv2.resize(frame, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        M = np.float32([[sx / k, 0, -x0 * sx], [0, sy / k, -y0 * sy]])
        card = cv2.warpAffine(small, M, (CARD_W, ch), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    else:
        card = cv2.warpAffine(frame, M, (CARD_W, ch), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return card.astype(np.float32), (cx, cy, w, h)

_mask_cache = {}
def card_mask(ch):
    if ch not in _mask_cache:
        m = np.asarray(rounded_mask(CARD_W, ch, CARD_R, 3), np.float32) / 255.0
        sh = np.zeros((ch + 240, CARD_W + 240), np.float32)
        sh[120 + 22:120 + 22 + ch, 120:120 + CARD_W] = m
        sh = cv2.GaussianBlur(cv2.resize(sh, None, fx=0.25, fy=0.25), (0, 0), 9)
        sh = cv2.resize(sh, (CARD_W + 240, ch + 240)) * 0.55
        if len(_mask_cache) > 200: _mask_cache.clear()
        _mask_cache[ch] = (m[..., None], sh[..., None])
    return _mask_cache[ch]

def put_card(canvas, card):
    ch = card.shape[0]; m, sh = card_mask(ch)
    x0, y0 = (OW - CARD_W) // 2, int(round(CARD_CY - ch / 2))
    sy0, sx0 = y0 - 120, x0 - 120
    ya, yb = max(sy0, 0), min(sy0 + ch + 240, OH); xa, xb = max(sx0, 0), min(sx0 + CARD_W + 240, OW)
    c = canvas[ya:yb, xa:xb]; s = sh[ya - sy0:yb - sy0, xa - sx0:xb - sx0]
    c[:] = c * (1 - s) + np.array([5, 6, 20], np.float32) * s
    c = canvas[y0:y0 + ch, x0:x0 + CARD_W]; c[:] = c * (1 - m) + card * m
    return y0

_cap_cache = {}
def caption(txt):
    if txt not in _cap_cache: _cap_cache[txt] = pill(txt)
    return _cap_cache[txt]

# ---------------- cursor redesenhado com trajetória suave ----------------
_CS = A("rascunhos", "cursor_suave.json")
CUR = json.load(open(_CS)) if os.path.exists(_CS) else None
SPR = {}
if CUR:
    _mods = np.load(A("rascunhos", "cursor_modelos.npy"), allow_pickle=True).item()
    for k, m in _mods.items():
        img = cv2.cvtColor(m["img"], cv2.COLOR_BGR2RGB)
        big = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC).astype(np.float32)
        al = cv2.resize(m["mask"].astype(np.float32), None, fx=4, fy=4, interpolation=cv2.INTER_LINEAR)
        al = cv2.GaussianBlur(np.clip((al - 0.35) / 0.3, 0, 1), (0, 0), 1.0)
        SPR[k] = (big, al)

def cursor_pos(st):
    if not CUR: return None
    f = st * FPS; a, b = int(math.floor(f)), int(math.ceil(f)); S = CUR["suave"]
    pa, pb = S.get(str(a)), S.get(str(b))
    if pa and pb:
        u = f - a; return pa["x"] + (pb["x"] - pa["x"]) * u, pa["y"] + (pb["y"] - pa["y"]) * u, (pa if u < 0.5 else pb)["tipo"]
    p = pa or pb
    return (p["x"], p["y"], p["tipo"]) if p else None

def draw_cursor(card, pos, cx, cy, w, h):
    x, y, tipo = pos; k = CARD_W / w
    big, al = SPR[tipo]; sw, sh = big.shape[1] / 4 * k, big.shape[0] / 4 * k
    spr = cv2.resize(big, (max(1, round(sw)), max(1, round(sh))), interpolation=cv2.INTER_AREA)
    a = cv2.resize(al, (spr.shape[1], spr.shape[0]), interpolation=cv2.INTER_AREA)[..., None]
    px, py = (x - (cx - w / 2)) * k, (y - (cy - h / 2)) * k
    x0, y0 = int(round(px)), int(round(py))
    H, Wd = card.shape[:2]
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + spr.shape[1], Wd), min(y0 + spr.shape[0], H)
    if xa >= xb or ya >= yb: return
    sub = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    c = card[ya:yb, xa:xb]; c[:] = c * (1 - a[sub]) + spr[sub] * a[sub]

# ---------------- cenas ----------------
LAYOUTS = [layout(s) for s in SCENES]

def render_scene(si, t):
    sc, lay = SCENES[si], LAYOUTS[si]
    st, c = clock(lay, t)
    cx, cy, w, h = cam_at(sc["cam"], c)
    push = 1 - 0.035 * (t / lay["D"])
    frame = src_frame(st)
    card, (cx, cy, w, h) = crop_card(frame, cx, cy, w * push, h * push)
    pos = cursor_pos(st)
    if pos: draw_cursor(card, pos, cx, cy, w, h)
    if "spot" in sc and c >= sc["spot"][0]:  # destaque só na insígnia conquistada
        a = smooth((c - sc["spot"][0]) / 0.5); x0, y0, x1, y1 = sc["spot"][1]
        k = CARD_W / w
        rx0, ry0 = int((x0 - (cx - w / 2)) * k), int((y0 - (cy - h / 2)) * k)
        rx1, ry1 = int((x1 - (cx - w / 2)) * k), int((y1 - (cy - h / 2)) * k)
        m = np.zeros(card.shape[:2], np.float32)
        cv2.rectangle(m, (rx0, ry0), (rx1, ry1), 1.0, -1); m = cv2.GaussianBlur(m, (0, 0), 14)[..., None]
        dim = 1 - 0.68 * a
        card = card * (m + (1 - m) * dim)
    canvas = BG.copy()
    top = put_card(canvas, card)
    # legendas: troca pelo relógio da câmera, com fade de 0,3 s
    caps = sc["caps"]; idx = 0
    for j, (cc, _) in enumerate(caps):
        if c >= cc: idx = j
    # tempo local de cada troca
    starts = [0.0] + [local_of(lay, cc) for cc, _ in caps[1:]]
    for j, (_, txt) in enumerate(caps):
        t0 = starts[j]; t1 = starts[j + 1] if j + 1 < len(caps) else lay["D"] + 1
        op = min(1, max(0, (t - t0) / 0.3 + (1 if j == 0 else 0))) * min(1, max(0, (t1 - t) / 0.3))
        if op > 0:
            im = caption(txt); blit(canvas, im, 540, top - 40 - im.height / 2, op)
    footer(canvas)
    return canvas

def local_of(lay, cc):
    for s in lay["segs"]:
        if s["kind"] == "src" and s["a"] - 0.6 <= cc <= s["b"]:
            return s["t0"] + max(0, cc - s["a"]) / s["sp"]
        if s["kind"] == "src" and cc < s["a"]:
            return s["t0"]
    return lay["D"]

# ---------------- introdução e fechamento ----------------
def thumb(t, rect, size=(270, 350)):
    f = src_frame(t); x0, y0, x1, y1 = [v * SC for v in rect]
    tw, th = size; asp = tw / th; w, h = x1 - x0, y1 - y0
    if w / h > asp: nw = h * asp; x0 += (w - nw) / 2; w = nw
    else: nh = w / asp; h = nh
    crop = f[int(y0):int(y0 + h), int(x0):int(x0 + w)]
    im = Image.fromarray(cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA)).convert("RGBA")
    im.putalpha(rounded_mask(tw, th, 24, 3))
    pad = 40; out = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 14, pad + tw, pad + th + 14], 24, fill=(3, 4, 18, 150))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14))); out.alpha_composite(im, (pad, pad))
    ImageDraw.Draw(out).rounded_rectangle([pad, pad, pad + tw - 1, pad + th - 1], 24, outline=(255, 255, 255, 70), width=2)
    return out

INTRO = None
def intro_assets():
    global INTRO
    if INTRO: return INTRO
    INTRO = dict(
        icon=icon(230), glow=glow(230), tag=pill("TUTORIAL", 34, F700, 30, 16, (226, 232, 240), 0.13, 0.30),
        l1=text_img("Como usar o", F700, 80), l2=text_img("LoopEdu", F700, 128, gradient=True),
        l3=text_img("em menos de 2 minutos", F600, 52, (0xcb, 0xd5, 0xe1)),
        th=[thumb(112.0, (185, 100, 770, 596)).rotate(-7, Image.BICUBIC, expand=True),
            thumb(342.0, (282, 120, 745, 545)).rotate(6, Image.BICUBIC, expand=True),
            thumb(462.0, (300, 60, 1060, 430)).rotate(-3, Image.BICUBIC, expand=True)],
        pills=[pill(x, 32, F600, 26, 14) for x in ("Matéria", "Rotina", "Estudo", "Revisão")])
    return INTRO

def appear(t, t0, d=0.4): return ease_out((t - t0) / d)

def render_intro(t):
    I = intro_assets(); cv = BG.copy()
    out = 1 - smooth((t - (INTRO_D - 0.4)) / 0.4)
    a = appear(t, 0.0, 0.55); fl = math.sin(t * 2.2) * 5
    blit(cv, I["glow"], 540, 440 + fl, a * out * 0.9, 0.9 + 0.1 * a)
    blit(cv, I["icon"], 540, 440 + fl, a * out, 0.75 + 0.25 * a)
    for (k, t0, y) in [("tag", 0.35, 655), ("l1", 0.6, 760), ("l2", 0.8, 880), ("l3", 1.05, 995)]:
        a = appear(t, t0); blit(cv, I[k], 540, y + 30 * (1 - a), a * out)
    xs, rots_y = [300, 540, 780], [1255, 1225, 1255]
    for j, im in enumerate(I["th"]):
        a = appear(t, 1.3 + 0.15 * j, 0.5)
        blit(cv, im, xs[j] + (j - 1) * -40 * (1 - a), rots_y[j] + 90 * (1 - a) + fl * 0.6, a * out)
    ws = [p.width for p in I["pills"]]; gap = 16; x = 540 - (sum(ws) + gap * 3) / 2
    for j, p in enumerate(I["pills"]):
        a = appear(t, 1.9 + 0.08 * j); blit(cv, p, x + p.width / 2, 1500 + 20 * (1 - a), a * out); x += p.width + gap
    footer(cv)
    return cv

CLOSE = None
def render_close(t):
    global CLOSE
    if CLOSE is None:
        CLOSE = dict(icon=icon(250), glow=glow(250), l1=text_img("LoopEdu", F700, 104),
                     l2=text_img("Estude melhor.", F700, 76), l3=text_img("Viva por inteiro.", F700, 76, gradient=True),
                     bio=pill("Link na bio", 40, F600, 34, 18))
    C = CLOSE; cv = BG.copy(); fl = math.sin(t * 2.2) * 5
    a = appear(t, 0.0, 0.55)
    blit(cv, C["glow"], 540, 620 + fl, a * 0.9, 0.9 + 0.1 * a); blit(cv, C["icon"], 540, 620 + fl, a, 0.75 + 0.25 * a)
    for (k, t0, y) in [("l1", 0.3, 845), ("l2", 0.6, 975), ("l3", 0.85, 1070), ("bio", 1.15, 1215)]:
        a = appear(t, t0); blit(cv, C[k], 540, y + 30 * (1 - a), a)
    footer(cv)
    return cv

# ---------------- linha do tempo ----------------
def timeline():
    items = [("intro", 0.0, INTRO_D, None)]; t = INTRO_D
    for i, lay in enumerate(LAYOUTS): items.append(("cena", t, t + lay["D"], i)); t += lay["D"]
    items.append(("fecho", t, t + CLOSE_D, None)); return items, t + CLOSE_D

def voice_starts(items):
    st = {0: 0.3}
    for kind, t0, t1, i in items:
        if kind == "cena": st[SCENES[i]["line"]] = t0 + LEAD
        if kind == "fecho": st[13] = t0 + LEAD
    return st

def build_audio(items, total, path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", NARR, "-f", "f32le", "-ac", "1", "-ar", "48000", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32); sr = 48000
    out = np.zeros(int((total + 0.5) * sr), np.float32)
    for k, s0 in voice_starts(items).items():
        on, off = LINES[k]; a, b = int((on - 0.04) * sr), int((off + 0.06) * sr)
        seg = x[max(a, 0):b].copy(); n = int(0.02 * sr)
        seg[:n] *= np.linspace(0, 1, n); seg[-n:] *= np.linspace(1, 0, n)
        p = int((s0 - 0.04) * sr); out[p:p + len(seg)] += seg
    out = out[:int(total * sr)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "1", "-ar", "48000", "-i", "-", path], input=out.tobytes(), check=True)

def table(items):
    st = voice_starts(items); print("\nfala | cena               | início cena | voz          | fim cena | silêncio no fim")
    bad = 0
    for kind, t0, t1, i in items:
        k = 0 if kind == "intro" else (13 if kind == "fecho" else SCENES[i]["line"])
        on, off = LINES[k]; v0 = st[k]; v1 = v0 + off - on; sil = t1 - v1
        nxt = [st[j] for j in st if st[j] > v0]; gap = (min(nxt) - v1) if nxt else sil
        name = kind if i is None else SCENES[i]["name"]
        print(f"{k:4d} | {name:18s} | {t0:11.2f} | {v0:5.2f}-{v1:5.2f} | {t1:8.2f} | {sil:5.2f} s (até a próxima fala {gap:4.2f} s)")
        bad += gap > 1.0
    return bad

def main():
    args = sys.argv[1:]
    outp = args[0] if args and not args[0].startswith("--") else A("videos", "2026-11-09_vertical.mp4")
    rasc = "--rascunho" in args
    rng = None
    if "--so" in args: i = args.index("--so"); rng = (float(args[i + 1]), float(args[i + 2]))
    items, total = timeline()
    for i, lay in enumerate(LAYOUTS):
        print(f"{SCENES[i]['name']:12s} D={lay['D']:.2f}s velocidade={lay['speed']:.2f} " +
              " ".join(f"[{s['kind']} {s['a']:.2f}-{s['b']:.2f} -> {s['t1']-s['t0']:.2f}s]" for s in lay["segs"]))
    bad = table(items); print(f"\nduração total {total:.2f} s; silêncios > 1 s: {bad}")
    wav = A("rascunhos", "voz_montada.wav"); build_audio(items, total, wav)
    t0, t1 = rng if rng else (0, total)
    n0, n1 = int(round(t0 * FPS)), int(round(t1 * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
           "-ss", f"{n0 / FPS:.3f}", "-t", f"{(n1 - n0) / FPS:.3f}", "-i", wav,
           "-map", "0:v", "-map", "1:a", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,volume=2.7dB", "-ac", "2", "-c:v", "libx264", "-preset", "veryfast" if rasc else "slow", "-crf", "23" if rasc else "17",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", outp]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    prev_last = {}
    DIS = 0.3
    for n in range(n0, n1):
        t = n / FPS
        for kind, a, b, i in items:
            if a <= t < b or (kind == "fecho" and t >= a): break
        lt = t - a
        f = render_intro(lt) if kind == "intro" else render_close(lt) if kind == "fecho" else render_scene(i, lt)
        idx = items.index((kind, a, b, i))
        if idx > 0 and lt < DIS:  # dissolve na cena anterior (0,3 s)
            pk, pa, pb, pi = items[idx - 1]; pt = pb - pa - 1 / FPS
            key = idx - 1
            if key not in prev_last:
                prev_last[key] = render_intro(pt) if pk == "intro" else render_scene(pi, pt)
            u = smooth(lt / DIS); f = prev_last[key] * (1 - u) + f * u
        ff.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
        if n % 150 == 0: print(f"  {t:6.1f}/{total:.1f} s", flush=True)
    ff.stdin.close(); ff.wait(); print("ok", outp)

if __name__ == "__main__":
    main()
