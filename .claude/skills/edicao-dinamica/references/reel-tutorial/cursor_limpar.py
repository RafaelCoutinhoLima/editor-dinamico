# Apaga o cursor gravado (seta/mão) dos quadros ampliados e grava a trajetória suavizada.
# Entrada: rascunhos/cursor_track.json, src_raw, src_x2.  Saída: rascunhos/src_x2c/*.png e rascunhos/cursor_suave.json
import cv2, numpy as np, os, json
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda *p: os.path.join(W, "rascunhos", *p)
LIM = 1500  # acima disso não há seta/mão no quadro (cursor de texto, escondido ou fora)
mods = np.load(R("cursor_modelos.npy"), allow_pickle=True).item()
size = {k: (m["img"].shape[1], m["img"].shape[0]) for k, m in mods.items()}
tr = json.load(open(R("cursor_track.json")))
idx = sorted(int(k[:5]) for k in tr)
det = {i: tr[f"{i:05d}.png"] for i in idx}
ok = {i: det[i]["score"] < LIM for i in idx}
os.makedirs(R("src_x2c"), exist_ok=True)
raw = lambda i: cv2.imread(R("src_raw", f"{i:05d}.png"))
def box(i, pad=3):
    d = det[i]; w, h = size[d["tipo"]]; return d["x"] - pad, d["y"] - pad, d["x"] + w + pad, d["y"] + h + pad
def inter(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

# trechos contínuos (quadros consecutivos)
runs, cur = [], [idx[0]]
for i in idx[1:]:
    if i == cur[-1] + 1: cur.append(i)
    else: runs.append(cur); cur = [i]
runs.append(cur)

suave = {}
for run in runs:
    # trajetória: só quadros com cursor; buracos curtos (<=6) interpolados; suavização gaussiana sigma 2,5 quadros
    pts = [(i, det[i]["x"], det[i]["y"]) for i in run if ok[i]]
    if len(pts) < 2: continue
    seg, segs = [pts[0]], []
    for p in pts[1:]:
        if p[0] - seg[-1][0] <= 7: seg.append(p)
        else: segs.append(seg); seg = [p]
    segs.append(seg)
    for seg in segs:
        fi = np.arange(seg[0][0], seg[-1][0] + 1)
        xs = np.interp(fi, [p[0] for p in seg], [p[1] for p in seg]); ys = np.interp(fi, [p[0] for p in seg], [p[2] for p in seg])
        k = np.exp(-0.5 * (np.arange(-8, 9) / 2.5) ** 2); k /= k.sum()
        pad = lambda v: np.concatenate([np.full(8, v[0]), v, np.full(8, v[-1])])
        xs2, ys2 = np.convolve(pad(xs), k, "valid"), np.convolve(pad(ys), k, "valid")
        tipo = None
        for j, f in enumerate(fi):
            if f in ok and ok[f]: tipo = det[f]["tipo"]
            suave[int(f)] = dict(x=round(float(xs2[j]), 2), y=round(float(ys2[j]), 2), tipo=tipo or seg[0] and det[seg[0][0]]["tipo"])

# limpeza: tapa o cursor com o mesmo lugar de um quadro vizinho em que o cursor está longe e o fundo é igual
n_viz = n_inp = 0
for run in runs:
    for i in run:
        out = R("src_x2c", f"{i:05d}.png")
        if os.path.exists(out): continue
        big = cv2.imread(R("src_x2", f"{i:05d}.png"))
        if ok[i]:
            b = box(i); x0, y0, x1, y1 = max(b[0], 0), max(b[1], 0), min(b[2], 1362), min(b[3], 596)
            ri = raw(i).astype(np.int16); feito = False
            ring = np.zeros(ri.shape[:2], bool); ring[max(y0 - 6, 0):y1 + 6, max(x0 - 6, 0):x1 + 6] = True; ring[y0:y1, x0:x1] = False
            for d in sorted(range(-45, 46), key=abs):
                j = i + d
                if d == 0 or j not in det or j < run[0] or j > run[-1]: continue
                if ok[j] and inter(box(j, 6), (x0, y0, x1, y1)): continue
                rj = raw(j).astype(np.int16)
                if np.abs(ri[ring] - rj[ring]).mean() > 3: continue
                donor = cv2.imread(R("src_x2", f"{j:05d}.png"))
                big[2 * y0:2 * y1, 2 * x0:2 * x1] = donor[2 * y0:2 * y1, 2 * x0:2 * x1]; feito = True; n_viz += 1; break
            if not feito:
                m = np.zeros(big.shape[:2], np.uint8); m[2 * y0:2 * y1, 2 * x0:2 * x1] = 255
                big = cv2.inpaint(big, m, 5, cv2.INPAINT_TELEA); n_inp += 1
        cv2.imwrite(out, big)
json.dump(dict(suave=suave, size=size), open(R("cursor_suave.json"), "w"))
print("trajetória em", len(suave), "quadros; tapados com vizinho", n_viz, "; inpaint", n_inp)
