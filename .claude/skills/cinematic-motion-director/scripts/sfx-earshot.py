#!/usr/bin/env python3
"""
SFX track from the earshot sound bank (github.com/Leonxlnx/earshot, MIT): 252 designed effects
stored as code — clicks, keys, pops, knocks, whooshes, shutters, dings, hits, risers — rendered by
id, each audited for clicks / cut tails / clipping. No samples, no models, no network, CPU only.

  python sfx-earshot.py cues.json --voice voice.wav --duration 108 --out fx.wav
  python sfx-earshot.py cues.json --duration 30 --out fx.wav --earshot C:/tools/earshot

cues.json: [{"t": 2.40, "role": "click"}, {"t": 5.1, "role": "whoosh", "dur": 0.5},
            {"t": 7.0, "role": "ding", "pitch": "E6"}, {"t": 9.2, "role": "key", "id": "typing_key/laptop"}, ...]
  t     = the picture event (cut, cursor press, typed char, photo landing), in seconds
  role  = a row of ROLES below (sound, sync point, offset, run gap, level)
  id / pitch / dur / apex / under = optional per-cue overrides

Placement follows earshot's measurements on professional films: each take is aligned on its
measured sync point (onset for hits, loudest moment for whooshes / risers), moved by the role's
offset (taps lead the cut, whoosh peaks land just after it), runs keep a minimum gap, and every
event gets a new seed (round robin: never the same take twice in a row).
Level: with --voice, each take's loudest 50 ms sits `under` dB below the voice's loud level
(p90 of its 50 ms frames) — UI foley must read as detail, never compete with the words.
Without --voice the voice level is assumed at -16 dBFS RMS.

Setup once (no torch needed for the bank):
  git clone https://github.com/Leonxlnx/earshot && pip install numpy scipy soundfile soxr
then pass --earshot <that folder> or set EARSHOT_DIR.
"""
import argparse, json, os, subprocess, sys, wave
import numpy as np

SR = 48000
# role: (bank id, align 'onset'|'peak', offset_ms, min_gap_ms, dB under the voice)
# offsets / gaps = earshot launch-preset medians; levels tuned for voice-led Reels (no music bed).
ROLES = {
    "click":  ("pro_click/mouse",     "onset", -11,  85, 20),   # cut / cursor press
    "key":    ("typing_key/laptop",   "onset",   8,  60, 25),   # one per typed character
    "tick":   ("pro_hover_tick/ping", "onset",   0,  66, 22),   # checkmark, counter step
    "tock":   ("knock/wood",          "onset", -40, 100, 18),   # card / chip landing
    "pop":    ("ui_pop/soft",         "onset",   4, 114, 18),   # bubble, row arriving
    "land":   ("pro_pop_in/round",    "onset",  30, 159, 18),   # element popping in
    "snap":   ("shutter/dslr",        "onset",   9,  66, 18),   # photo whip / snap zoom
    "ding":   ("notify/mid_tine",     "onset",   0, 110, 16),   # notification, confirm
    "whoosh": ("whoosh_fast/crisp",   "peak",   37,   0, 16),   # fast move into a cut
    "swoosh": ("whoosh_big/thump",    "peak",    3,   0, 14),   # big transition (rare)
    "hit":    ("cut_hit/punch",       "onset",   0,   0, 12),   # the reveal (1-2 per film)
    "drop":   ("cut_hit/kick",        "onset",   0,   0, 12),   # sub hit under a key word gap
    "riser":  ("riser/dark",          "peak",  -23,   0, 14),   # build into the reveal (once)
}


def load_bank(path):
    for p in [path, os.environ.get("EARSHOT_DIR")]:
        if p and os.path.isdir(os.path.join(p, "earshot", "forge")):
            sys.path.insert(0, p)
    try:
        from earshot.forge import bank
        return bank
    except ImportError as e:
        sys.exit(f"earshot not found ({e}); clone github.com/Leonxlnx/earshot and pass --earshot DIR")


def pcm(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def frames_db(x, win=int(0.05 * SR)):
    n = len(x) // win
    if n == 0:
        return np.array([20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)])
    r = np.sqrt(np.mean(x[:n * win].reshape(n, win) ** 2, axis=1))
    return 20 * np.log10(r + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cues"); ap.add_argument("--out", default="fx.wav")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--voice", help="narration file: sets each effect's level against the voice")
    ap.add_argument("--earshot", help="path to the earshot repo clone")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    bank = load_bank(a.earshot)
    cues = sorted(json.load(open(a.cues, encoding="utf8")), key=lambda c: c["t"])

    if a.voice:
        f = frames_db(pcm(a.voice)); f = f[f > f.max() - 40]
        voice_db = float(np.percentile(f, 90))
    else:
        voice_db = -16.0

    out = np.zeros((int(a.duration * SR) + SR, 2), np.float32)
    last_t, count, report = {}, {}, []
    for i, c in enumerate(cues):
        role = c["role"]
        if role not in ROLES:
            sys.exit(f"unknown role '{role}' (roles: {', '.join(ROLES)})")
        sid, align, off, gap, under = ROLES[role]
        sid = c.get("id", sid); under = c.get("under", under)
        t = c["t"]
        if gap and role in last_t and (t - last_t[role]) * 1000 < gap:
            t = last_t[role] + gap / 1000          # space the run, keep order
        last_t[role] = t
        count[role] = count.get(role, 0) + 1
        for k in range(5):                         # a take that fails the audit is re-rolled on a new seed
            y, m = bank.render(sid, seed=a.seed * 1000 + i + 7919 * k, dur=c.get("dur"), apex=c.get("apex"), pitch=c.get("pitch"))
            if (m.get("checks") or {}).get("ok", True):
                break
        y = np.asarray(y, np.float32)
        if y.ndim == 1:
            y = np.stack([y, y], 1)
        sync = float(m["peak_s"] if align == "peak" else m["onset_s"])
        loud = float(frames_db(y.mean(1), int(0.05 * SR)).max())
        g = 10 ** ((voice_db - under - loud) / 20)
        start = int(round((t + off / 1000 - sync) * SR))
        s0, y0 = max(0, start), max(0, -start)
        seg = y[y0:y0 + len(out) - s0] * g
        out[s0:s0 + len(seg)] += seg
        ok = (m.get("checks") or {}).get("ok", True)
        report.append(f"{t:7.2f}s {role:7s} {sid:22s} {voice_db - under:6.1f} dB{'' if ok else '  (audit warning)'}")

    out = out[:int(a.duration * SR)]
    pk = float(np.abs(out).max())
    if pk > 0.89:
        out *= 0.89 / pk
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(out, -1, 1) * 32767).astype("<i2").tobytes())
    print("\n".join(report))
    print(f"ok {a.out}: {len(cues)} effects, voice loud level {voice_db:.1f} dB, "
          + ", ".join(f"{k} x{v}" for k, v in count.items()))


if __name__ == "__main__":
    main()
