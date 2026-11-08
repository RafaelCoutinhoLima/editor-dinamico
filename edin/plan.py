"""Plano de edição (EDL em JSON): gerado automaticamente e refinado pelo Claude.

Formato do plano (ver docs/PLANO.md para a referência completa):
{
  "source": "video.mp4", "words": "video.words.json",
  "format": "9:16", "fps": 30, "preset": "reels",
  "audio": "source" | "music",
  "segments": [{"start": 1.2, "end": 4.0, "zoom": 1.0, "zoom_to": 1.04,
                "focus": "face", "speed": 1.0, "src": null, "broll": null}],
  "captions": {"style": "hormozi", "words_per_group": 3, "position": 0.68,
               "emphasis": [12, 40], "uppercase": true},
  "titles": [{"text": "...", "start": 0, "end": 2.5}],
  "sfx": [{"at": 3.2, "type": "whoosh", "volume": 0.5}],
  "auto_sfx": {"on_zoom": "whoosh", "on_emphasis": "pop"},
  "music": {"file": "musica.mp3", "volume": 0.12, "start": 0, "duck": true},
  "loudness": -14
}
"""
from __future__ import annotations

import random
import re

from .audio import snap_segments
from .voice import DEFAULT as VOICE_DEFAULT
from .utils import fmt_time, load_json, parse_range, probe, save_json

PRESETS = {
    # Reels/TikTok/Shorts: cortes secos, punch-ins frequentes, legenda grande palavra a palavra.
    # Som: clique suave na troca de zoom (whoosh em todo corte soa amador; use whoosh só em transições grandes)
    "reels": dict(format="9:16", max_gap=0.30, pad=0.06, zooms=[1.0, 1.18], zoom_every=3.2, drift=0.035,
                  captions="hormozi", words_per_group=3, position=0.68, auto_sfx={"on_zoom": "softclick"}),
    # YouTube horizontal: ritmo mais calmo, zoom sutil, legenda discreta
    "youtube": dict(format="16:9", max_gap=0.50, pad=0.12, zooms=[1.0, 1.10], zoom_every=7.0, drift=0.0,
                    captions="minimal", words_per_group=8, position=0.88, auto_sfx={}),
    # Cortes de podcast/entrevista para vertical
    "podcast": dict(format="9:16", max_gap=0.45, pad=0.10, zooms=[1.0, 1.12], zoom_every=4.5, drift=0.02,
                    captions="clean", words_per_group=4, position=0.70, auto_sfx={}),
    # Aula/tutorial: só tira silêncio, mantém enquadramento
    "aula": dict(format="original", max_gap=0.70, pad=0.15, zooms=[1.0], zoom_every=999, drift=0.0,
                 captions="minimal", words_per_group=8, position=0.88, auto_sfx={}),
}

# "um" sozinho é artigo em português ("tem um viés"): só conta como filler esticado ("umm")
FILLER_RE = re.compile(r"^(a+h+n*|h+m+|h+u+m+|e+h+|é{2,}|ã+|a{3,}|uh+|um{2,})[.,!?…]*$", re.IGNORECASE)


def _is_filler(word: str) -> bool:
    return bool(FILLER_RE.match(word.strip().lower()))


def build_talking_plan(src: str, words_json: str, preset: str = "reels", rng: str | None = None,
                       remove_fillers: bool = True, fmt: str | None = None, speed: float = 1.0,
                       snap: bool = True, clean_voice: bool = True) -> dict:
    cfg = PRESETS[preset]
    info = probe(src)
    all_words = load_json(words_json)["words"]
    if any(w["s"] >= info["duration"] for w in all_words):  # transcrição de outro vídeo (ou de outra versão)
        raise SystemExit(f"[edin] {words_json} tem palavras depois do fim de {src} ({info['duration']:.1f}s). "
                         "A transcrição não é deste vídeo: rode edin transcribe de novo.")
    words = all_words
    by_i = {w["i"]: w for w in all_words}
    r = parse_range(rng)
    if r:
        words = [w for w in words if w["s"] >= r[0] - 0.05 and w["e"] <= r[1] + 0.05]
    kept = [w for w in words if not (remove_fillers and _is_filler(w["w"]))]
    if not kept:
        raise SystemExit("[edin] Nenhuma palavra no intervalo escolhido.")

    # 1) blocos de fala: quebra quando a pausa é maior que max_gap (ou quando houve filler removido)
    blocks, cur = [], [kept[0]]
    for prev, w in zip(kept, kept[1:]):
        filler_between = w["i"] - prev["i"] > 1
        if w["s"] - prev["e"] > cfg["max_gap"] or filler_between:
            blocks.append(cur)
            cur = []
        cur.append(w)
    blocks.append(cur)

    pad = cfg["pad"]
    segs = []
    for b in blocks:
        # vizinhos no original (inclusive fillers removidos): o ajuste por energia não pode engoli-los
        prv, nxt = by_i.get(b[0]["i"] - 1), by_i.get(b[-1]["i"] + 1)
        lo = prv["e"] if prv else 0.0
        hi = nxt["s"] if nxt else info["duration"]
        # filler removido costuma vir grudado na palavra (sem silêncio) e o Whisper marca o fim dele cedo:
        # o limite fica no meio do caminho, senão o ajuste por energia traz o "ahn" de volta
        if prv and remove_fillers and _is_filler(prv["w"]):
            lo = (prv["e"] + b[0]["s"]) / 2
        if nxt and remove_fillers and _is_filler(nxt["w"]):
            hi = (b[-1]["e"] + nxt["s"]) / 2
        segs.append({"start": max(0.0, b[0]["s"] - pad), "end": min(info["duration"], b[-1]["e"] + pad),
                     "_words": b, "_lo": lo, "_hi": hi})
    if r:  # nunca sair do trecho pedido
        for s in segs:
            s["_lo"], s["_hi"] = max(s["_lo"], r[0] - 0.05), min(s["_hi"], r[1] + 0.05)
    # evita sobreposição entre blocos vizinhos
    for a, b in zip(segs, segs[1:]):
        if b["start"] < a["end"]:
            mid = (a["_words"][-1]["e"] + b["_words"][0]["s"]) / 2
            a["end"], b["start"] = mid, mid
    # 1b) corta pela energia do áudio, não só pelos tempos do Whisper (não come o fim das palavras)
    if snap and info["has_audio"]:
        n = snap_segments(segs, src, info["duration"])
        if n:
            print(f"[edin] {n} bordas de corte ajustadas pela energia do áudio")

    # 2) divide blocos longos para criar punch-ins (sem remover tempo)
    out = []
    every = cfg["zoom_every"]
    for s in segs:
        ws = s["_words"]
        start = s["start"]
        while s["end"] - start > every * 1.6:
            # procura a maior pausa entre palavras perto de start+every
            cands = [(ws[k + 1]["s"] - ws[k]["e"], k) for k in range(len(ws) - 1)
                     if start + every * 0.7 <= ws[k]["e"] <= start + every * 1.3]
            if not cands:
                break
            _, k = max(cands)
            cut = (ws[k]["e"] + ws[k + 1]["s"]) / 2
            out.append({"start": start, "end": cut})
            start = cut
        out.append({"start": start, "end": s["end"]})

    zooms = cfg["zooms"]
    for i, s in enumerate(out):
        z = zooms[i % len(zooms)]
        s["start"], s["end"] = round(s["start"], 3), round(s["end"], 3)
        s["zoom"] = z
        if speed and abs(speed - 1.0) > 1e-3:
            s["speed"] = round(speed, 3)
        if cfg["drift"]:
            s["zoom_to"] = round(z + cfg["drift"], 3)
        s["focus"] = "face"
    plan = {
        "source": src,
        "words": words_json,
        "format": fmt or cfg["format"],
        "fps": 30 if info["fps"] > 31 or info["fps"] < 23 else round(info["fps"], 3),
        "preset": preset,
        "audio": "source",
        "segments": out,
        "captions": {"style": cfg["captions"], "words_per_group": cfg["words_per_group"],
                     "position": cfg["position"], "emphasis": [], "uppercase": cfg["captions"] == "hormozi"},
        "titles": [],
        "sfx": [],
        "auto_sfx": dict(cfg["auto_sfx"]),
        "music": None,
        "loudness": -14,
        # limpeza de voz (DeepFilterNet + cadeia broadcast); null desliga
        "voice": dict(VOICE_DEFAULT) if clean_voice else None,
    }
    return plan


# ---------------------------------------------------------------- montagem no beat

def detect_beats(music: str, start: float = 0.0, duration: float | None = None):
    try:
        import librosa
        import numpy as np
    except ImportError as e:
        raise SystemExit("[edin] librosa não instalado. Rode: pip install librosa") from e
    y, sr = librosa.load(music, sr=22050, mono=True, offset=start, duration=duration)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    times = librosa.times_like(onset, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    # energia local normalizada em cada beat (para acelerar cortes nas partes fortes)
    energy = np.interp(beats, times, onset) if len(beats) else np.array([])
    if len(energy):
        energy = (energy - energy.min()) / (np.ptp(energy) + 1e-9)
    return tempo, [float(b) for b in beats], [float(e) for e in energy]


def build_montage_plan(clips: list, music: str, duration: float = 30.0, music_start: float = 0.0,
                       fmt: str = "9:16", beats_per_cut: int = 2, seed: int = 7) -> dict:
    rnd = random.Random(seed)
    tempo, beats, energy = detect_beats(music, music_start, duration + 2)
    print(f"[edin] {tempo:.0f} BPM, {len(beats)} batidas detectadas")
    if len(beats) < 2:
        raise SystemExit("[edin] Não achei batidas suficientes na música.")
    # pontos de corte: a cada N batidas; nas partes de maior energia, a cada batida
    cuts, k = [0.0], 0
    while k < len(beats) - 1:
        step = 1 if (energy and energy[k] > 0.75 and beats_per_cut > 1) else beats_per_cut
        k += step
        if k < len(beats):
            cuts.append(beats[k])
    cuts = [c for c in cuts if c <= duration]
    if duration - cuts[-1] >= 0.15:  # fecha na duração pedida (as batidas vão até duration+2)
        cuts.append(duration)
    infos = {c: probe(c) for c in clips}
    pos = {c: rnd.uniform(0, max(0.0, infos[c]["duration"] * 0.3)) if not infos[c]["duration"] == 0 else 0
           for c in clips}
    segs = []
    order = list(clips)
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        d = b - a
        if d < 0.15:
            continue
        c = order[i % len(order)]
        if i % len(order) == len(order) - 1:
            rnd.shuffle(order)
        cd = infos[c]["duration"]
        st = pos[c]
        if st + d > cd:
            st = max(0.0, rnd.uniform(0, max(0.0, cd - d)))
        pos[c] = st + d + rnd.uniform(0.2, 1.5)
        z = rnd.choice([1.0, 1.05, 1.12])
        segs.append({"src": c, "start": round(st, 3), "end": round(st + d, 3), "zoom": z,
                     "zoom_to": round(z + rnd.choice([0.04, 0.06, -0.03]), 3), "focus": "face"})
    return {
        "source": clips[0], "words": None, "format": fmt, "fps": 30, "preset": "montagem",
        "audio": "music", "segments": segs,
        "captions": None, "titles": [], "sfx": [], "auto_sfx": {},
        "music": {"file": music, "volume": 1.0, "start": music_start, "duck": False},
        "loudness": -14,
    }


# ---------------------------------------------------------------- linha do tempo de saída

def load_plan(path: str) -> dict:
    """Carrega o plano e converte caminhos relativos (relativos à pasta do plano) em absolutos."""
    from pathlib import Path

    plan = load_json(path)
    base = Path(path).resolve().parent

    def ab(p):
        if not p:
            return p
        q = Path(p).expanduser()
        return str(q if q.is_absolute() else (base / q).resolve())

    plan["source"] = ab(plan["source"])
    plan["words"] = ab(plan.get("words"))
    for seg in plan["segments"]:
        if seg.get("src"):
            seg["src"] = ab(seg["src"])
        if seg.get("broll") and seg["broll"].get("src"):  # {"query": ...} sem src: resolvido no render
            seg["broll"]["src"] = ab(seg["broll"]["src"])
    if plan.get("music") and plan["music"].get("file"):
        plan["music"]["file"] = ab(plan["music"]["file"])
    return plan


def seg_src(plan: dict, seg: dict) -> str:
    return seg.get("src") or plan["source"]


def seg_out_dur(seg: dict) -> float:
    return (seg["end"] - seg["start"]) / float(seg.get("speed", 1.0) or 1.0)


def remap_words(plan: dict) -> list:
    """Converte timestamps das palavras (vídeo original) para a linha do tempo do vídeo editado."""
    if not plan.get("words"):
        return []
    words = load_json(plan["words"])["words"]
    out, t0, blk, prev_end = [], 0.0, 0, None
    for seg in plan["segments"]:
        sp = float(seg.get("speed", 1.0) or 1.0)
        d = seg_out_dur(seg)
        # bloco novo quando o segmento não continua exatamente o anterior (legenda não mistura frases)
        if prev_end is None or abs(seg["start"] - prev_end) > 0.02 or seg.get("src"):
            blk += 1
        prev_end = seg["end"]
        if seg_src(plan, seg) == plan["source"]:
            for w in words:
                mid = (w["s"] + w["e"]) / 2
                if seg["start"] <= mid < seg["end"]:
                    s = t0 + max(0.0, (w["s"] - seg["start"]) / sp)
                    e = t0 + min(d, (w["e"] - seg["start"]) / sp)
                    out.append({**w, "s": round(s, 3), "e": round(max(e, s + 0.05), 3), "blk": blk})
        t0 += d
    return out


def print_timeline(plan_path: str) -> None:
    plan = load_plan(plan_path)
    words = remap_words(plan)
    t0 = 0.0
    total = sum(seg_out_dur(s) for s in plan["segments"])
    print(f"Duração final: {fmt_time(total)} ({total:.1f}s) em {len(plan['segments'])} segmentos")
    for n, seg in enumerate(plan["segments"]):
        d = seg_out_dur(seg)
        ws = [w for w in words if t0 <= w["s"] < t0 + d]
        txt = " ".join(f"{w['w']}" for w in ws)
        idx = f"#{ws[0]['i']}-{ws[-1]['i']}" if ws else ""
        b = seg.get("broll") or {}
        extra = f" broll={b.get('src') or 'pexels:' + str(b.get('query'))}" if b else ""
        src = f" src={seg['src']}" if seg.get("src") else ""
        print(f"seg {n:02d} out[{fmt_time(t0)}-{fmt_time(t0 + d)}] src[{fmt_time(seg['start'])}-{fmt_time(seg['end'])}]"
              f" zoom {seg.get('zoom', 1.0)}{src}{extra} {idx} | {txt}")
        t0 += d


def save_plan(plan: dict, path: str) -> None:
    save_json(plan, path)
    total = sum(seg_out_dur(s) for s in plan["segments"])
    print(f"[edin] Plano salvo em {path}: {len(plan['segments'])} segmentos, {total:.1f}s de vídeo final")
