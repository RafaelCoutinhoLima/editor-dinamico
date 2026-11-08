#!/usr/bin/env python3
"""
Original music bed synthesized in code (no samples, no rights issues), driven by a small JSON
spec of sections, and auto-ducked under the narration.

Usage:
  python synth-score.py spec.json --out bed.wav [--voice voice.wav]

spec.json (all times in seconds on the FINAL timeline):
{
  "duration": 50,
  "bpm": 104,
  "progression": [[57,"m"],[53,"M"],[55,"M"],[52,"m"]],      # root MIDI + quality, 1 chord per bar
  "progression_after": {"at": 30.4, "chords": [[48,"M"],[55,"M"],[57,"m"],[53,"M"]]},  # optional lift
  "sections": [                                              # intensity 0..1 per layer, interpolated
    {"at": 0,    "pad": 0.5, "pluck": 0.3, "bass": 0.25, "drums": 0.0, "bright": 0.3},
    {"at": 17.2, "pad": 0.7, "pluck": 0.45,"bass": 0.55, "drums": 0.45,"bright": 0.8},
    {"at": 48.8, "pad": 0.8, "pluck": 0.3, "bass": 0.3,  "drums": 0.0, "bright": 0.3},
    {"at": 50,   "pad": 0.0, "pluck": 0.0, "bass": 0.0,  "drums": 0.0, "bright": 0.2}
  ],
  "risers": [[15.4, 1.8]],          # [start, length] noise risers into a hit
  "booms":  [17.2],                 # sub hits
  "ticks":  {"from": 0, "to": 25}   # optional clock tick on every beat (tension)
}

Layers: triangle pad, plucked arpeggio (8ths, 16ths when bright > 0.6), sine sub bass,
kick + hat. Ducking: music -45 % while the voice is above speech level. Output: 48 kHz
stereo 16-bit, peak-normalised to 0.9 — set the final level in the editor (≈ 9–12 LU under
the voice).
"""
import argparse, json, subprocess, wave
import numpy as np

SR = 48000


def load(path, n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).astype(np.float64)
    return np.pad(x, (0, max(0, n - len(x))))[:n]


def lp(x, cutoff):
    """One-pole low-pass, cutoff per sample (vectorised in blocks for speed)."""
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s)
        y[i] = s
    return y


def note(m):
    return 440 * 2 ** ((m - 69) / 12)


def tri(f, t):
    return 2 * np.abs(2 * ((f * t) % 1) - 1) - 1


def saw(f, t):
    return 2 * ((f * t) % 1) - 1


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def place(buf, sig, at, g=1.0):
    i = int(at * SR)
    if i >= len(buf) or i < 0:
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default="bed.wav")
    ap.add_argument("--voice", help="narration to duck under")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf8"))
    rng = np.random.default_rng(a.seed)
    DUR = float(spec["duration"]); N = int(SR * DUR); T = np.arange(N) / SR
    BEAT = 60 / float(spec.get("bpm", 104)); BAR = BEAT * 4
    prog = spec.get("progression", [[48, "M"], [55, "M"], [57, "m"], [53, "M"]])
    after = spec.get("progression_after")
    secs = sorted(spec["sections"], key=lambda s: s["at"])

    def curve(key):
        return np.interp(T, [s["at"] for s in secs], [s.get(key, 0) for s in secs])

    def chord_at(t):
        p = after["chords"] if after and t >= after["at"] else prog
        root, q = p[int(t / BAR) % len(p)]
        return root, [root, root + (3 if q == "m" else 4), root + 7]

    bright = curve("bright")
    music = np.zeros(N)

    pad = np.zeros(N)
    for i in range(int(DUR / BAR) + 1):
        t0 = i * BAR
        _, tones = chord_at(t0 + 0.01)
        n = int(BAR * SR); tt = np.arange(n) / SR
        s = sum(tri(note(m - 12), tt) + 0.5 * tri(note(m - 12) * 1.004, tt) for m in tones)
        place(pad, s * np.minimum(1, tt / 0.8) * np.minimum(1, (BAR - tt) / 0.3) * 0.08, t0)
    music += lp(pad, 1600) * curve("pad")

    pl = np.zeros(N); t = 0.0; k = 0
    while t < DUR - 0.5:
        root, tones = chord_at(t)
        seq = tones + [root + 12]
        bi = min(N - 1, int(t * SR))
        m = seq[k % 4] + (12 if bright[bi] > 0.6 and k % 8 >= 4 else 0)
        n = int(0.35 * SR); tt = np.arange(n) / SR
        place(pl, (tri(note(m), tt) + 0.3 * saw(note(m) * 2, tt)) * env(n, 0.003, 0.12), t)
        t += BEAT / 4 if bright[bi] > 0.6 else BEAT / 2
        k += 1
    music += lp(pl, 1200 + 3800 * bright) * curve("pluck")

    bass = np.zeros(N)
    for i in range(int(DUR / (BEAT * 2)) + 1):
        t0 = i * BEAT * 2
        root, _ = chord_at(t0)
        n = int(BEAT * 2 * SR); tt = np.arange(n) / SR
        place(bass, np.sin(2 * np.pi * note(root - 24) * tt) * env(n, 0.01, 0.6), t0)
    music += bass * curve("bass")

    drums = np.zeros(N)
    nk = int(0.4 * SR); tk = np.arange(nk) / SR
    kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-tk / 0.03)) * tk) * np.exp(-tk / 0.16)
    nh = int(0.06 * SR); hn = rng.standard_normal(nh); hn = hn - lp(hn, 6000)
    hat = hn * np.exp(-np.arange(nh) / SR / 0.015)
    t = 0.0
    while t < DUR:
        place(drums, kick, t, 0.9); place(drums, hat, t + BEAT / 2, 0.25); t += BEAT
    music += drums * curve("drums")

    tick_cfg = spec.get("ticks")
    if tick_cfg:
        n = int(0.03 * SR); tt = np.arange(n) / SR
        click = np.sin(2 * np.pi * 3200 * tt) * np.exp(-tt / 0.004)
        t = float(tick_cfg.get("from", 0))
        while t < float(tick_cfg.get("to", DUR)):
            place(music, click, t, 0.18); t += BEAT
    for at, length in spec.get("risers", []):
        n = int(length * SR); tr = np.arange(n) / SR
        place(music, lp(rng.standard_normal(n), 400 + 5000 * (tr / tr[-1]) ** 2) * (tr / tr[-1]) ** 2, at, 0.35)
    nb = int(2.0 * SR); tb = np.arange(nb) / SR
    boom = np.sin(2 * np.pi * (40 + 80 * np.exp(-tb / 0.08)) * tb) * np.exp(-tb / 0.6)
    for at in spec.get("booms", []):
        place(music, boom, at, 0.8)

    if a.voice:
        v = load(a.voice, N); hop = 480
        rms = np.sqrt(np.convolve(v ** 2, np.ones(hop) / hop, mode="same"))
        thr = max(0.01, np.percentile(rms[rms > 1e-4], 70) * 0.35) if np.any(rms > 1e-4) else 0.02
        sp = np.convolve((rms > thr).astype(float), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
        music *= 1 - 0.45 * np.clip(sp * 1.5, 0, 1)
    music *= 0.9 / max(1e-9, np.abs(music).max())
    music *= np.clip((DUR - T) / 1.2, 0, 1)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.stack([music, music], 1) * 32767).astype(np.int16).tobytes())
    print(f"ok {a.out} {DUR:.1f}s")


if __name__ == "__main__":
    main()
