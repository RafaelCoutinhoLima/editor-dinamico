# Extrai os quadros usados (com remendo do "abc") para rascunhos/src_raw/NNNNN.png
import cv2, os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
from cenas import SCENES, PATCH
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(W, "rascunhos", "src_raw"); os.makedirs(out, exist_ok=True)
cap = cv2.VideoCapture(os.path.join(W, "fonte", "gravacao.mp4"))
def read(i):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read(); return f
clean = read(round(PATCH["clean_t"]*30))
x0,y0,x1,y1 = PATCH["rect"]
need = set()
for s in SCENES:
    for p in s["pieces"]:
        if p[0]=="src": need.update(range(math.floor(p[1]*30), math.ceil(p[2]*30)+1))
        else: need.add(round(p[1]*30))
for t in (112.0, 342.0, 462.0): need.add(round(t*30))
need = sorted(need); print(len(need), "quadros")
cur = None
for i in need:
    if os.path.exists(f"{out}/{i:05d}.png"): continue
    if cur is None or i != cur+1: cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, f = cap.read(); cur = i
    if PATCH["t0"]*30 <= i <= PATCH["t1"]*30: f[y0:y1, x0:x1] = clean[y0:y1, x0:x1]
    cv2.imwrite(f"{out}/{i:05d}.png", f)
