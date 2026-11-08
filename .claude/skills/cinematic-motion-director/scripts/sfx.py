#!/usr/bin/env python3
"""
Synthesized SFX track (no samples): soft mouse clicks on cuts, ticks on checkmarks, sub booms.
Creators often find stock whooshes too loud and generic — a real-sounding mouse click (press
+ quieter release, 3 timbre variants) reads as "editing" without shouting.

Usage:
  python sfx.py --duration 84 --out fx.wav --clicks 3.54,5.85,7.3 --ticks 12.4,15.1 --booms 17.2
  python sfx.py --duration 30 --out fx.wav --clicks-file cuts.json      # JSON list of seconds

Clicks land 10 ms before the given time so the transient sits on the cut. Output is mono,
peak 0.5 — mix it ~20 dB under the voice (volume ≈ 0.5 in Remotion).
"""
import argparse, json, wave
import numpy as np

SR = 48000


def bandpass_noise(n, lo, hi, rng):
    X = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n)


def click_part(gain, tone, dec, rng):
    n = int(0.045 * SR); t = np.arange(n) / SR
    s = bandpass_noise(n, 1800, 9000, rng) * np.exp(-t / 0.0018)
    s += np.sin(2 * np.pi * tone * t) * np.exp(-t / dec) * 0.5 + np.sin(2 * np.pi * tone * 2.7 * t) * np.exp(-t / (dec * 0.5)) * 0.25
    return s / np.abs(s).max() * gain


def mouse_click(variant, rng):
    down = click_part(1.0, 1150 + variant * 40, 0.006, rng)
    up = click_part(0.45, 1500 + variant * 40, 0.004, rng)
    gap = int((0.075 + 0.01 * variant) * SR)
    out = np.zeros(gap + len(up)); out[:len(down)] += down; out[gap:] += up
    return out


def tick():
    n = int(0.03 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 3200 * t) * np.exp(-t / 0.004)


def boom():
    n = int(1.6 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (40 + 80 * np.exp(-t / 0.08)) * t) * np.exp(-t / 0.5)


def times(arg):
    return [float(x) for x in arg.split(",") if x.strip()] if arg else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", default="fx.wav")
    ap.add_argument("--clicks", default="")
    ap.add_argument("--clicks-file")
    ap.add_argument("--ticks", default="")
    ap.add_argument("--booms", default="")
    ap.add_argument("--click-gain", type=float, default=0.55)
    a = ap.parse_args()
    rng = np.random.default_rng(5)
    N = int(SR * a.duration); buf = np.zeros(N)

    def put(sig, t, g):
        i = int(t * SR)
        if 0 <= i < N:
            s = sig[: N - i]; buf[i:i + len(s)] += s * g

    clicks = times(a.clicks) + (json.load(open(a.clicks_file)) if a.clicks_file else [])
    for k, t in enumerate(clicks):
        put(mouse_click(k % 3, rng), t - 0.01, a.click_gain)
    for t in times(a.ticks):
        put(tick(), t, 0.3)
    for t in times(a.booms):
        put(boom(), t, 0.6)
    if np.abs(buf).max() > 0:
        buf *= 0.5 / np.abs(buf).max()
    with wave.open(a.out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    print(f"ok {a.out}: {len(clicks)} clicks")


if __name__ == "__main__":
    main()
