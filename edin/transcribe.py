"""Transcrição local e gratuita com faster-whisper (timestamps por palavra)."""
from __future__ import annotations

import subprocess

import numpy as np

from .utils import fmt_time, load_json, save_json


def _load_audio(src: str, sr: int = 16000) -> np.ndarray:
    """Decodifica o áudio com o ffmpeg (16 kHz mono). Evita o PyAV do faster-whisper, que quebra entre versões
    (o av 19 removeu o argumento metadata_errors que o faster-whisper 1.2 usa) e não lê tudo que o ffmpeg lê."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    x = np.frombuffer(p.stdout, np.float32)
    if not len(x):
        raise SystemExit(f"[edin] {src} não tem áudio para transcrever.")
    return x


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


def _whisper(src: str, model: str, language: str | None, device: str, **kw):
    """Roda o faster-whisper e devolve (segmentos, info). Com device=auto, se a GPU falhar (ex.: libcublas/cuDNN
    ausentes, o que só aparece no 1º trecho decodificado), refaz em CPU em vez de quebrar."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise SystemExit("[edin] faster-whisper não instalado. Rode: pip install faster-whisper") from e

    audio = _load_audio(src)
    dev, compute = _pick_device(device)
    print(f"[edin] Transcrevendo com whisper '{model}' em {dev} ({compute})... (1ª vez baixa o modelo)")
    try:
        wm = WhisperModel(model, device=dev, compute_type=compute)
        segments, info = wm.transcribe(audio, language=language or None, word_timestamps=True, vad_filter=True,
                                       condition_on_previous_text=False, **kw)
        out = []
        for seg in segments:
            out.append(seg)
            print(f"\r[edin] {fmt_time(seg.end)} transcrito", end="", flush=True)
        print()
        return out, info
    except RuntimeError as e:
        if device != "auto" or dev != "cuda":
            raise
        print(f"\n[edin] Aviso: GPU indisponível ({str(e).splitlines()[0]}). Usando CPU.")
        return _whisper(src, model, language, "cpu", **kw)


def transcribe(src: str, out: str, model: str = "small", language: str | None = "pt", device: str = "auto") -> dict:
    segments, info = _whisper(src, model, language, device, vad_parameters={"min_silence_duration_ms": 300})
    words = []
    for seg in segments:
        for w in seg.words or []:
            txt = w.word.strip()
            if not txt:
                continue
            words.append({"i": len(words), "w": txt, "s": round(w.start, 3), "e": round(w.end, 3), "p": round(w.probability, 3)})
    data = {"source": src, "language": info.language, "duration": info.duration, "words": words}
    save_json(data, out)
    print(f"[edin] {len(words)} palavras -> {out}")
    return data


def transcribe_words(src: str, model: str = "small", language: str | None = "pt", device: str = "auto") -> list:
    """Transcreve sem salvar (usado pelo `edin verify`)."""
    segments, _ = _whisper(src, model, language, device, vad_parameters={"min_silence_duration_ms": 300})
    return [{"w": w.word.strip(), "s": w.start, "e": w.end} for seg in segments for w in (seg.words or [])
            if w.word.strip()]


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
