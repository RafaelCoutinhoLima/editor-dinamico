#!/usr/bin/env python3
"""
Per-shot spacing pass (zero-overlap rule) and "worst stretch" review sheets from a rendered MP4.

  python shot-pass.py out/video.mp4 shots.json --out out/review/pass      # 3 frames per shot
  python shot-pass.py out/video.mp4 --every 2 --out out/review/sheet       # 1 frame every 2 s

shots.json: [[from, to], ...] or {"name": [from, to], ...} in seconds.
For each shot it extracts start+0.3 s, middle and end-0.05 s (plus any "peaks": [t,...] given
as a third element), labels each tile with its time and shot name, and tiles 6 x 2 per page
(pass_0.jpg, pass_1.jpg …) at 360 px wide — big enough to see text touching text.
Needs ffmpeg and Pillow.
"""
import argparse, json, os, subprocess
from PIL import Image, ImageDraw


def grab(video, t, path, w):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", f"scale={w}:-2", path], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("shots", nargs="?")
    ap.add_argument("--every", type=float, help="instead of shots: one frame every N seconds")
    ap.add_argument("--out", default="out/review/pass")
    ap.add_argument("--width", type=int, default=360)
    a = ap.parse_args()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout)
    items = []
    if a.every:
        t = 0.0
        while t < dur - 0.05:
            items.append((t, "")); t += a.every
    else:
        spec = json.load(open(a.shots, encoding="utf8"))
        shots = spec.items() if isinstance(spec, dict) else [(str(i), s) for i, s in enumerate(spec)]
        for name, s in shots:
            f, to = float(s[0]), float(s[1])
            ts = [min(f + 0.3, (f + to) / 2), (f + to) / 2, max(f, to - 0.05)] + [float(p) for p in (s[2] if len(s) > 2 else [])]
            items += [(t, name) for t in ts]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    tiles = []
    for i, (t, name) in enumerate(items):
        p = f"{a.out}_tile{i:03d}.png"
        grab(a.video, t, p, a.width)
        im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, a.width, 18], fill=(0, 0, 0)); d.text((4, 3), f"{t:.2f}s {name}", fill=(255, 80, 80))
        tiles.append(im); os.remove(p)
    per = 12
    h = tiles[0].size[1]
    for page in range((len(tiles) + per - 1) // per):
        W = Image.new("RGB", (a.width * 6, h * 2), "white")
        for j, im in enumerate(tiles[page * per:(page + 1) * per]):
            W.paste(im, ((j % 6) * a.width, (j // 6) * h))
        W.save(f"{a.out}_{page}.jpg", quality=85)
    print(f"{len(tiles)} frames -> {a.out}_0..{(len(tiles) - 1) // per}.jpg")


if __name__ == "__main__":
    main()
