# Recorta da gravação os modelos do cursor (seta e mão) com máscara, por diferença entre dois quadros
import cv2, numpy as np, os
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cap = cv2.VideoCapture(os.path.join(W, "fonte", "gravacao.mp4"))
def fr(t): cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * 30)); return cap.read()[1]
mods = {}
for nome, ta, tb, (x0, y0, x1, y1) in [("seta", 478.80, 478.70, (1046, 233, 1063, 258)),
                                       ("mao", 196.20, 196.80, (436, 306, 460, 336))]:
    a, b = fr(ta), fr(tb)
    ca, cb = a[y0:y1, x0:x1], b[y0:y1, x0:x1]
    m = (np.abs(ca.astype(int) - cb.astype(int)).max(2) > 6).astype(np.uint8)
    # preenche o miolo branco do cursor: tudo que não é alcançável a partir da borda
    pad = np.pad(m, 1); ff = pad.copy() * 1; h, w = pad.shape
    flood = np.zeros((h + 2, w + 2), np.uint8); out = pad.copy()
    cv2.floodFill(out, flood, (0, 0), 2)
    m = ((out != 2)[1:-1, 1:-1]).astype(np.uint8)
    ys, xs = np.nonzero(m); bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    mods[nome] = dict(img=ca[by0:by1, bx0:bx1].copy(), mask=m[by0:by1, bx0:bx1].copy())
    print(nome, mods[nome]["img"].shape, int(m.sum()))
np.save(os.path.join(W, "rascunhos", "cursor_modelos.npy"), mods, allow_pickle=True)
big = np.hstack([cv2.resize(mods[k]["img"] * mods[k]["mask"][..., None], (180, 240), interpolation=cv2.INTER_NEAREST) for k in mods])
cv2.imwrite(os.path.join(W, "rascunhos", "cursor_modelos.png"), big)
