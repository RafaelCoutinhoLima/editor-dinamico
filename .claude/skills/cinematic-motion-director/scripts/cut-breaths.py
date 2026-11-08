#!/usr/bin/env python3
"""
Remove breaths and dead air from talking-head footage (video + audio together), optionally
speed it up, and write a time map so every cue/scene time can be moved onto the new timeline.

Why energy-based and not Whisper word gaps: word timestamps are often wrong at phrase
boundaries (a real case gave "designers" a 0.02 s duration inside a "gap", and cutting by
word gaps deleted the word). Cutting only where the audio is actually quiet is safe; then
VERIFY by re-transcribing.

Usage (needs ffmpeg on PATH and numpy; --verify also needs `pip install faster-whisper`):
  python cut-breaths.py raw.mp4 --out cut.mov --speed 1.10 --verify --lang pt
  python cut-breaths.py raw.mp4 --out cut.mov --gap 0.25 --thr 22      # gentler

Outputs:
  cut.mov                 trimmed (and sped-up) video+audio, h264 + pcm
  cut.timemap.json        {"points": [[t_in, t_out], ...], "duration": s, "speed": x}
                          piecewise-linear map from ORIGINAL time to NEW time; times that
                          fall inside a removed pause snap to the cut point.

Tuning:
  --thr   dB below the speech level (70th percentile of the loudness curve) that still
          counts as speech. 24 removes breaths and room tone; lower it (20) if soft
          syllables get clipped, raise it (28) if breaths survive.
  --gap   quiet stretches shorter than this are kept (natural rhythm inside a phrase).
  --pad-start / --pad-end   audio kept before/after each speech run.
"""
import argparse, json, subprocess, sys
import numpy as np


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def decode_mono(path, sr):
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-af", "highpass=f=100", "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
              capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def speech_segments(x, sr, thr_db, gap, pad_start, pad_end, dur):
    hop = sr // 100  # 10 ms
    win = int(sr * 0.025)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode="same"))[::hop]
    db = 20 * np.log10(rms + 1e-9)
    speech = np.percentile(db, 70)
    loud = db > speech - thr_db
    t = np.arange(len(db)) * hop / sr
    segs, inside, s0, last = [], False, 0.0, 0.0
    for ti, on in zip(t, loud):
        if on:
            if not inside:
                if segs and ti - pad_start - segs[-1][1] < gap:
                    s0 = segs.pop()[0]          # short pause: keep it inside the phrase
                else:
                    s0 = max(0.0, ti - pad_start)
                inside = True
            last = ti
        elif inside and ti - last > 0.06:
            segs.append([s0, min(dur, last + pad_end)])
            inside = False
    if inside:
        segs.append([s0, min(dur, last + pad_end)])
    return [s for s in segs if s[1] - s[0] > 0.12], speech


def transcribe_words(path, lang):
    from faster_whisper import WhisperModel  # optional dependency
    x = decode_mono(path, 16000).astype(np.float32)
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(x, language=lang)
    return " ".join(s.text.strip() for s in segs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--out", default="cut.mov")
    ap.add_argument("--speed", type=float, default=1.0, help="applied after cutting (e.g. 1.10)")
    ap.add_argument("--thr", type=float, default=24.0)
    ap.add_argument("--gap", type=float, default=0.20)
    ap.add_argument("--pad-start", type=float, default=0.05)
    ap.add_argument("--pad-end", type=float, default=0.07)
    ap.add_argument("--verify", action="store_true", help="re-transcribe before/after and compare word counts")
    ap.add_argument("--lang", default="pt")
    a = ap.parse_args()

    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.input],
                    capture_output=True, text=True).stdout)
    x = decode_mono(a.input, 16000)
    segs, speech = speech_segments(x, 16000, a.thr, a.gap, a.pad_start, a.pad_end, dur)

    v, au = [], []
    for i, (s, e) in enumerate(segs):
        v.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{i}]")
        au.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,"
                  f"afade=t=out:st={max(0.0, e - s - 0.008):.3f}:d=0.008[a{i}]")
    n = len(segs)
    fc = ";".join(v + au) + ";" + "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]"
    if a.speed != 1.0:
        fc += f";[vc]setpts=PTS/{a.speed}[v];[ac]atempo={a.speed}[a]"
    else:
        fc += ";[vc]null[v];[ac]anull[a]"
    run(["ffmpeg", "-v", "error", "-y", "-i", a.input, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-c:a", "pcm_s16le", a.out])

    pts, cum = [], 0.0
    for s, e in segs:
        pts.append([round(s, 4), round(cum / a.speed, 4)])
        cum += e - s
        pts.append([round(e, 4), round(cum / a.speed, 4)])
    mp = a.out.rsplit(".", 1)[0] + ".timemap.json"
    json.dump({"points": pts, "duration": round(cum / a.speed, 4), "speed": a.speed}, open(mp, "w"))
    print(f"speech level {speech:.1f} dB | {n} kept runs | removed {dur - cum:.2f} s of breaths/pauses")
    print(f"new duration {cum / a.speed:.2f} s (was {dur:.2f} s) -> {a.out}, {mp}")

    if a.verify:
        # Whisper never transcribes the same speech identically twice, so compare word
        # sequences and only flag RUNS of missing words (a real cut), not single-word drift.
        import difflib, re, unicodedata
        norm = lambda w: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", w.lower()).encode("ascii", "ignore").decode())
        before = [w for w in map(norm, transcribe_words(a.input, a.lang).split()) if w]
        after = [w for w in map(norm, transcribe_words(a.out, a.lang).split()) if w]
        sm = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
        lost = [before[i1:i2] for op, i1, i2, j1, j2 in sm.get_opcodes() if op == "delete" or (op == "replace" and (i2 - i1) - (j2 - j1) >= 2)]
        print(f"words before {len(before)} | after {len(after)} | similarity {sm.ratio():.3f}")
        if lost:
            print("possibly missing:", " / ".join(" ".join(r) for r in lost))
        if any(len(r) >= 2 for r in lost) or sm.ratio() < 0.93:
            print("WARNING: speech may have been cut. Lower --thr or raise --pad-start/--pad-end and re-run.", file=sys.stderr)
            sys.exit(2)
        print("verify: OK (no run of missing words)")

if __name__ == "__main__":
    main()
