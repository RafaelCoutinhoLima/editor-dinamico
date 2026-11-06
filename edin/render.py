"""Renderização do plano: corta, reenquadra, dá zoom, aplica b-roll, legenda, SFX, música e normaliza o áudio."""
from __future__ import annotations

import shutil
from pathlib import Path

from .captions import build_ass
from .plan import load_plan, remap_words, seg_out_dur, seg_src
from .reframe import crop_box, face_track, focus_for
from .sfx import sfx_file
from .utils import FONTS_DIR, ffmpeg_filter_path, is_image, load_json, probe, run, workdir_for

FORMATS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def _even(x: float) -> int:
    return int(round(x / 2) * 2)


def out_size(plan: dict, main: dict, draft: bool):
    fmt = plan.get("format", "9:16")
    if fmt in FORMATS:
        w, h = FORMATS[fmt]
    else:  # original
        s = min(1.0, 1920 / max(main["w"], main["h"]))
        w, h = _even(main["w"] * s), _even(main["h"] * s)
    if draft:
        w, h = _even(w / 2), _even(h / 2)
    return w, h


def _atempo(speed: float) -> str:
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


class Renderer:
    def __init__(self, plan: dict, output: str, draft: bool = False, verbose: bool = False):
        self.plan, self.output, self.draft, self.verbose = plan, output, draft, verbose
        self.wd = workdir_for(output)
        self.cache = self.wd / "cache"
        self.cache.mkdir(exist_ok=True)
        self._probe, self._tracks = {}, {}
        main = self.info(plan["source"])
        self.W, self.H = out_size(plan, main, draft)
        self.fps = float(plan.get("fps", 30))
        self.crf = 28 if draft else 18
        self.preset = "ultrafast" if draft else "veryfast"

    def info(self, src):
        if src not in self._probe:
            self._probe[src] = probe(src)
        return self._probe[src]

    def track(self, src):
        if src not in self._tracks:
            print(f"[edin] Detectando rosto em {Path(src).name}...")
            self._tracks[src] = face_track(src, self.cache)
        return self._tracks[src]

    # ------------------------------------------------------------ vídeo de um segmento
    def _vchain(self, src: str, t0: float, t1: float, zoom: float, zoom_to: float, focus, d_out: float) -> str:
        info = self.info(src)
        if focus == "center" or focus is None:
            (fx, fy), has_face = (0.5, 0.5), False
        elif isinstance(focus, (list, tuple)):
            (fx, fy), has_face = (float(focus[0]), float(focus[1])), True
        else:
            (fx, fy), has_face = focus_for(self.track(src), t0, t1)
        zoom, zoom_to = max(1.0, zoom), max(1.0, zoom_to)  # zoom < 1 cortaria fora do quadro
        zmin = min(zoom, zoom_to)
        cx, cy, cw, ch = crop_box(info["w"], info["h"], self.W, self.H, zmin, fx, fy, has_face)
        chain = [f"crop={cw}:{ch}:{cx}:{cy}"]
        if abs(zoom_to - zoom) > 1e-3:
            a, b = zoom / zmin, zoom_to / zmin
            n = max(1, int(round(d_out * self.fps)) - 1)
            up = 1.5 if not self.draft else 1.0
            chain += [f"scale={_even(self.W * up)}:{_even(self.H * up)}:flags=bicubic",
                      f"zoompan=z='{a:.4f}+({b - a:.4f})*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                      f":d=1:s={self.W}x{self.H}:fps={self.fps}"]
        else:
            chain.append(f"scale={self.W}:{self.H}:flags=lanczos")
        chain += [f"fps={self.fps}", "setsar=1", "format=yuv420p"]
        return ",".join(chain)

    def render_segment(self, i: int, seg: dict) -> Path:
        out = self.wd / f"seg_{i:04d}.mp4"
        src = seg_src(self.plan, seg)
        speed = float(seg.get("speed", 1.0) or 1.0)
        d_src = seg["end"] - seg["start"]
        d_out = d_src / speed
        zoom = float(seg.get("zoom", 1.0))
        zoom_to = float(seg.get("zoom_to", zoom))
        cmd = ["ffmpeg", "-y", "-v", "error"]
        broll = seg.get("broll")
        if broll:
            bsrc = broll["src"]
            if is_image(bsrc):
                cmd += ["-loop", "1", "-framerate", str(self.fps), "-t", f"{d_out:.3f}", "-i", bsrc]
                bz = float(broll.get("zoom", 1.0))
                bz2 = float(broll.get("zoom_to", bz + 0.08))
                b0, b1 = 0.0, 0.0
            else:
                b0 = float(broll.get("start", 0.0))
                b1 = b0 + d_out
                cmd += ["-stream_loop", "-1", "-ss", f"{b0:.3f}", "-t", f"{d_out:.3f}", "-i", bsrc]
                bz = float(broll.get("zoom", 1.0))
                bz2 = float(broll.get("zoom_to", bz + 0.04))
            vchain = "setpts=PTS-STARTPTS," + self._vchain(bsrc, b0, b1, bz, bz2, broll.get("focus", "face"), d_out)
            a_idx = 1
            cmd += ["-ss", f"{seg['start']:.3f}", "-t", f"{d_src:.3f}", "-i", src]
        else:
            if is_image(src):
                cmd += ["-loop", "1", "-framerate", str(self.fps), "-t", f"{d_out:.3f}", "-i", src]
            else:
                cmd += ["-ss", f"{seg['start']:.3f}", "-t", f"{d_src:.3f}", "-i", src]
            pts = f"setpts=(PTS-STARTPTS)/{speed}" if speed != 1.0 else "setpts=PTS-STARTPTS"
            vchain = pts + "," + self._vchain(src, seg["start"], seg["end"], zoom, zoom_to, seg.get("focus", "face"),
                                              d_out)
            a_idx = 0
        use_src_audio = self.plan.get("audio", "source") == "source" and not is_image(src) \
            and self.info(src)["has_audio"]
        if use_src_audio:
            achain = "asetpts=PTS-STARTPTS"
            if speed != 1.0:
                achain += "," + _atempo(speed)
            fo = max(0.0, d_out - 0.015)
            achain += f",aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.012," \
                      f"afade=t=out:st={fo:.3f}:d=0.015,apad"
            fc = f"[0:v]{vchain}[v];[{a_idx}:a]{achain}[a]"
        else:
            cmd += ["-f", "lavfi", "-t", f"{d_out:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            n_in = 2 if broll else 1
            fc = f"[0:v]{vchain}[v];[{n_in}:a]anull[a]"
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{d_out:.3f}",
                "-c:v", "libx264", "-preset", self.preset, "-crf", str(self.crf), "-r", str(self.fps),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(out)]
        run(cmd, verbose=self.verbose)
        return out

    # ------------------------------------------------------------ efeitos sonoros
    def sfx_events(self, words_out: list) -> list:
        ev = [dict(e) for e in self.plan.get("sfx") or []]
        auto = self.plan.get("auto_sfx") or {}
        if auto.get("on_zoom"):
            t, prev = 0.0, None
            for n, seg in enumerate(self.plan["segments"]):
                z = seg.get("zoom", 1.0)
                if prev is not None and z != prev:
                    ev.append({"at": max(0.0, t - 0.12), "type": auto["on_zoom"], "volume": 0.35})
                prev = z
                t += seg_out_dur(seg)
        if auto.get("on_emphasis"):
            emph = set((self.plan.get("captions") or {}).get("emphasis") or [])
            for w in words_out:
                if w["i"] in emph:
                    ev.append({"at": w["s"], "type": auto["on_emphasis"], "volume": 0.5})
        if auto.get("on_cut"):
            t = 0.0
            for seg in self.plan["segments"][:-1]:
                t += seg_out_dur(seg)
                ev.append({"at": max(0.0, t - 0.05), "type": auto["on_cut"], "volume": 0.3})
        return ev

    # ------------------------------------------------------------ pipeline
    def run(self) -> str:
        segs = self.plan["segments"]
        print(f"[edin] Renderizando {len(segs)} segmentos em {self.W}x{self.H} @ {self.fps:g}fps"
              f"{' (rascunho)' if self.draft else ''}")
        files = []
        for i, seg in enumerate(segs):
            files.append(self.render_segment(i, seg))
            print(f"\r[edin] segmento {i + 1}/{len(segs)}", end="", flush=True)
        print()
        lst = self.wd / "concat.txt"
        lst.write_text("".join(f"file '{f.name}'\n" for f in files))
        joined = self.wd / "joined.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst.name, "-c", "copy", joined.name],
            cwd=str(self.wd))
        total = sum(seg_out_dur(s) for s in segs)

        words_out = remap_words(self.plan)
        cap = self.plan.get("captions")
        titles = self.plan.get("titles") or []
        has_subs = bool((cap and words_out) or titles)
        if has_subs:
            ass = build_ass(words_out if cap else [], cap or {}, self.W, self.H, titles, total)
            (self.wd / "captions.ass").write_text(ass, encoding="utf-8")

        inputs = ["-i", joined.name]
        fc = []
        if has_subs:
            fc.append(f"[0:v]subtitles=captions.ass:fontsdir='{ffmpeg_filter_path(str(FONTS_DIR))}'[v]")
        else:
            fc.append("[0:v]null[v]")
        fc.append("[0:a]asplit=2[voice][sc]")
        mix = ["[voice]"]
        n = 1
        for k, e in enumerate(self.sfx_events(words_out)):
            f = sfx_file(e["type"], self.cache)
            inputs += ["-i", str(f)]
            ms = int(float(e["at"]) * 1000)
            fc.append(f"[{n}:a]adelay={ms}|{ms},volume={float(e.get('volume', 0.5))}[s{k}]")
            mix.append(f"[s{k}]")
            n += 1
        music = self.plan.get("music")
        if music and music.get("file"):
            inputs += ["-stream_loop", "-1", "-ss", str(float(music.get("start", 0))), "-i", music["file"]]
            vol = float(music.get("volume", 0.12))
            fade = max(0.0, total - 1.5)
            fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},"
                      f"volume={vol},afade=t=in:d=0.4,afade=t=out:st={fade:.3f}:d=1.5[mus]")
            if music.get("duck", True) and self.plan.get("audio", "source") == "source":
                fc.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[musd]")
                mix.append("[musd]")
            else:
                fc.append("[sc]anullsink")
                mix.append("[mus]")
            n += 1
        else:
            fc.append("[sc]anullsink")
        lufs = float(self.plan.get("loudness", -14))
        fc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,"
                  f"loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[a]")
        out_abs = str(Path(self.output).resolve())
        cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
               "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", self.preset, "-crf", str(self.crf + 2),
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_abs]
        run(cmd, cwd=str(self.wd), verbose=self.verbose)
        print(f"[edin] Pronto: {out_abs} ({total:.1f}s)")
        return out_abs


def render(plan_path: str, output: str, draft: bool = False, keep: bool = False, verbose: bool = False) -> str:
    plan = load_plan(plan_path)
    r = Renderer(plan, output, draft, verbose)
    try:
        return r.run()
    finally:
        if not keep:
            for f in r.wd.glob("seg_*.mp4"):
                f.unlink()
            for name in ("joined.mp4",):
                p = r.wd / name
                if p.exists():
                    p.unlink()


def contact_sheet(video: str, out: str, n: int = 12, cols: int = 4) -> str:
    info = probe(video)
    rows = (n + cols - 1) // cols
    fps = n / max(info["duration"], 0.1)
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf",
         f"fps={fps:.5f},scale=360:-2,drawtext=text='%{{pts\\:hms}}':x=8:y=8:fontsize=22:fontcolor=white:"
         f"box=1:boxcolor=black@0.6,tile={cols}x{rows}:padding=6:color=0x222222", "-frames:v", "1", out])
    return out


def clean(output: str) -> None:
    wd = workdir_for(output)
    shutil.rmtree(wd, ignore_errors=True)
