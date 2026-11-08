#!/usr/bin/env python3
"""
Lip-sync an AI avatar clip (HeyGen etc.) to the REAL narration: drop the clip's own audio and
re-time its frames so the mouth follows the voice you will actually use.

  python avatar-sync.py avatar.mp4 voice.wav --end 4.48 --out avatar_synced.mp4
  python avatar-sync.py avatar.mp4 voice.wav --end 3.7 --anchors anchors.json --size 1080x1920

How: MFCC + DTW between the clip's audio and the narration gives a monotone time map
narration_t -> clip_t; each output frame samples the matching clip frame. Uniform stretching
is NOT enough — avatar TTS paces words differently (a measured case was 0.2 s off mid-phrase).
When the clip has pauses the narration doesn't (e.g. a long gap after the first word), DTW can
drift: pass word anchors from Whisper on both tracks, [[voice_t, clip_t], ...], and they
replace the DTW map. Start the clip at the end of a pause instead of jumping inside it — a
jump reads as a cut in frame 4.
Needs ffmpeg, numpy, scipy.
"""
import argparse, json, os, shutil, subprocess, tempfile
import numpy as np
from scipy.fft import dct

SR, HOP, WIN = 16000, 160, 400


def pcm(path, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-t", str(dur)] if dur else []) + ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).astype(np.float64)


def mfcc(x):
    x = np.append(x[0], x[1:] - 0.97 * x[:-1])
    n = 1 + (len(x) - WIN) // HOP
    fr = np.stack([x[i * HOP:i * HOP + WIN] for i in range(n)]) * np.hamming(WIN)
    spec = np.abs(np.fft.rfft(fr, 512)) ** 2
    mel = lambda f: 2595 * np.log10(1 + f / 700); imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(60), mel(7600), 42)); b = np.floor(513 * pts / SR).astype(int)
    fb = np.zeros((40, 257))
    for m in range(1, 41):
        fb[m - 1, b[m - 1]:b[m]] = (np.arange(b[m - 1], b[m]) - b[m - 1]) / max(1, b[m] - b[m - 1])
        fb[m - 1, b[m]:b[m + 1]] = (b[m + 1] - np.arange(b[m], b[m + 1])) / max(1, b[m + 1] - b[m])
    c = dct(np.log(spec @ fb.T + 1e-10), type=2, axis=1, norm="ortho")[:, 1:13]
    return (c - c.mean(0)) / (c.std(0) + 1e-8)


def dtw(A, B):
    D = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)); n, m = D.shape
    C = np.full((n + 1, m + 1), np.inf); C[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            C[i, j] = D[i - 1, j - 1] + min(C[i - 1, j - 1], C[i - 1, j], C[i, j - 1])
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = np.argmin([C[i - 1, j - 1], C[i - 1, j], C[i, j - 1]])
        i, j = (i - 1, j - 1) if k == 0 else (i - 1, j) if k == 1 else (i, j - 1)
    return path[::-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip"); ap.add_argument("voice")
    ap.add_argument("--end", type=float, required=True, help="narration time where the avatar is cut away")
    ap.add_argument("--out", default="avatar_synced.mp4")
    ap.add_argument("--anchors", help="JSON [[voice_t, clip_t], ...] (overrides DTW)")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    if a.anchors:
        anc = json.load(open(a.anchors)); ut = np.array([x[0] for x in anc]); hm = np.array([x[1] for x in anc])
    else:
        path = dtw(mfcc(pcm(a.voice, a.end + 1.0)), mfcc(pcm(a.clip)))
        vi = np.array([p[0] for p in path]) * HOP / SR; hi = np.array([p[1] for p in path]) * HOP / SR
        ut = np.unique(vi); hm = np.array([hi[vi == u].mean() for u in ut])
        hm = np.maximum.accumulate(np.convolve(np.pad(hm, 4, mode="edge"), np.ones(9) / 9, mode="valid"))
    tmp = tempfile.mkdtemp()
    src_fps = eval(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", a.clip], capture_output=True, text=True).stdout.strip())
    subprocess.run(["ffmpeg", "-v", "error", "-i", a.clip, "-an", f"{tmp}/h%05d.png"], check=True)
    n_src = len(os.listdir(tmp)); os.makedirs(f"{tmp}/o")
    for f in range(int(round((a.end + 0.15) * a.fps))):
        idx = min(n_src, max(1, int(round(float(np.interp(f / a.fps, ut, hm)) * src_fps)) + 1))
        shutil.copy(f"{tmp}/h{idx:05d}.png", f"{tmp}/o/o{f:05d}.png")
    w, h = a.size.split("x")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", f"{tmp}/o/o%05d.png", "-vf",
                    f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},unsharp=5:5:0.4", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", a.out], check=True)
    shutil.rmtree(tmp)
    print(f"ok {a.out}")


if __name__ == "__main__":
    main()
