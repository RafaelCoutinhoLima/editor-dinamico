# Detecta o cursor (seta ou mão) em cada quadro de rascunhos/src_raw -> rascunhos/cursor_track.json
import cv2, numpy as np, os, json
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mods = np.load(os.path.join(W, "rascunhos", "cursor_modelos.npy"), allow_pickle=True).item()
tm = {}
for k, m in mods.items():
    core = cv2.erode(m["mask"], np.ones((2, 2), np.uint8))  # miolo, sem a borda serrilhada
    tm[k] = (m["img"].astype(np.float32), np.repeat(core[..., None], 3, 2).astype(np.float32), core.sum())
src = os.path.join(W, "rascunhos", "src_raw"); res = {}
for f in sorted(os.listdir(src)):
    im = cv2.imread(os.path.join(src, f)).astype(np.float32); best = None
    for k, (t, m, n) in tm.items():
        r = cv2.matchTemplate(im, t, cv2.TM_SQDIFF, mask=m)
        mn, _, loc, _ = cv2.minMaxLoc(r); sc = mn / (n * 3)
        if best is None or sc < best[1]: best = (k, sc, loc)
    res[f] = dict(tipo=best[0], score=round(float(best[1]), 1), x=int(best[2][0]), y=int(best[2][1]))
json.dump(res, open(os.path.join(W, "rascunhos", "cursor_track.json"), "w"))
sc = np.array([v["score"] for v in res.values()])
print("quadros", len(sc), "percentis score", np.percentile(sc, [10, 50, 75, 90, 95, 99]).round(1))
