"""Transcrição local e gratuita com faster-whisper (timestamps por palavra)."""
from __future__ import annotations

from .utils import fmt_time, load_json, save_json


def _pick_device(device: str):
    if device != "auto":
        return device, ("float16" if device == "cuda" else "int8")
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def transcribe(src: str, out: str, model: str = "small", language: str | None = "pt", device: str = "auto") -> dict:
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise SystemExit("[edin] faster-whisper não instalado. Rode: pip install faster-whisper") from e

    dev, compute = _pick_device(device)
    print(f"[edin] Transcrevendo com whisper '{model}' em {dev} ({compute})... (1ª vez baixa o modelo)")
    wm = WhisperModel(model, device=dev, compute_type=compute)
    segments, info = wm.transcribe(
        src,
        language=language or None,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        condition_on_previous_text=False,
    )
    words = []
    for seg in segments:
        for w in seg.words or []:
            txt = w.word.strip()
            if not txt:
                continue
            words.append({"i": len(words), "w": txt, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
        if words:
            print(f"\r[edin] {fmt_time(words[-1]['e'])} transcrito", end="", flush=True)
    print()
    data = {"source": src, "language": info.language, "duration": info.duration, "words": words}
    save_json(data, out)
    print(f"[edin] {len(words)} palavras -> {out}")
    return data


def lines(words: list, max_pause: float = 0.6, max_words: int = 18):
    """Agrupa palavras em frases curtas (para leitura do Claude)."""
    out, cur = [], []
    for w in words:
        if cur and (w["s"] - cur[-1]["e"] > max_pause or len(cur) >= max_words):
            out.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1:] in ".?!":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def print_text(words_json: str, with_index: bool = True) -> None:
    data = load_json(words_json)
    for ln in lines(data["words"]):
        idx = f"#{ln[0]['i']}-{ln[-1]['i']} " if with_index else ""
        print(f"[{fmt_time(ln[0]['s'])}-{fmt_time(ln[-1]['e'])}] {idx}{' '.join(w['w'] for w in ln)}")
