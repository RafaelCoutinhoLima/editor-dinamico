"""Análise de áudio por energia: ajusta os cortes para nunca comer o começo ou o fim de uma palavra.

Lição de edições reais (skill cinematic-motion-director, MIT): os timestamps do Whisper erram nas
bordas das frases. Cortar só pela pausa entre palavras já apagou palavra inteira. Aqui o plano usa os
tempos do Whisper para decidir O QUE manter e a energia do áudio para decidir ONDE cortar.
"""
from __future__ import annotations

import subprocess

import numpy as np

SR = 16000
HOP = 0.01  # 10 ms por quadro de energia


class Energy:
    """Curva de energia (dB) do áudio, amostrada a cada 10 ms."""

    def __init__(self, src: str, thr_db: float = 24.0):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-af", "highpass=f=100", "-f", "f32le",
                              "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
        x = np.frombuffer(raw, np.float32).astype(np.float64)
        hop, win = int(SR * HOP), int(SR * 0.025)
        if len(x) < win:
            self.db = np.full(1, -120.0)
        else:
            rms = np.sqrt(np.convolve(x ** 2, np.ones(win) / win, mode="same"))[::hop]
            self.db = 20 * np.log10(rms + 1e-9)
        self.speech = float(np.percentile(self.db, 70))
        self.loud = self.db > self.speech - thr_db

    def _i(self, t: float) -> int:
        return int(min(max(round(t / HOP), 0), len(self.db) - 1))

    def is_loud(self, t: float) -> bool:
        return bool(self.loud[self._i(t)])

    def extend_end(self, t: float, limit: float, max_ext: float = 0.30, pad: float = 0.07) -> float:
        """Empurra o fim do corte para depois do último som da palavra (até max_ext e sem passar de limit)."""
        i, stop = self._i(t), self._i(min(limit, t + max_ext))
        last = None
        quiet = 0
        while i <= stop:
            if self.loud[i]:
                last, quiet = i, 0
            else:
                quiet += 1
                if quiet >= 6:  # 60 ms de silêncio: a palavra acabou
                    break
            i += 1
        if last is None:
            return t
        return min(limit, max(t, last * HOP + pad))

    def extend_start(self, t: float, limit: float, max_ext: float = 0.25, pad: float = 0.05) -> float:
        """Puxa o início do corte para antes do primeiro som da palavra (até max_ext e sem passar de limit)."""
        i, stop = self._i(t), self._i(max(limit, t - max_ext))
        first = None
        quiet = 0
        while i >= stop:
            if self.loud[i]:
                first, quiet = i, 0
            else:
                quiet += 1
                if quiet >= 6:
                    break
            i -= 1
        if first is None:
            return t
        return max(limit, min(t, first * HOP - pad))


def snap_segments(segs: list, src: str, duration: float, thr_db: float = 24.0) -> int:
    """Ajusta in-place as bordas de corte dos segmentos (só onde há corte de verdade). Devolve quantas mexeu."""
    try:
        en = Energy(src, thr_db)
    except Exception as e:  # sem áudio, ffmpeg falhou etc.: mantém os tempos do Whisper
        print(f"[edin] Aviso: ajuste por energia desligado ({e})")
        return 0
    moved = 0
    for k, s in enumerate(segs):
        prev_end = segs[k - 1]["end"] if k else 0.0
        nxt_start = segs[k + 1]["start"] if k + 1 < len(segs) else duration
        contiguous_prev = k and abs(s["start"] - prev_end) < 0.02
        contiguous_next = k + 1 < len(segs) and abs(nxt_start - s["end"]) < 0.02
        # limites: a palavra vizinha (inclusive fillers removidos) que não pode entrar no corte
        hi = min(nxt_start, s.get("_hi", duration))
        lo = max(prev_end, s.get("_lo", 0.0))
        if not contiguous_next:
            ne = en.extend_end(s["end"], hi)
            moved += ne != s["end"]
            s["end"] = ne
        if not contiguous_prev:
            ns = en.extend_start(s["start"], lo)
            moved += ns != s["start"]
            s["start"] = ns
    return moved


def loudness(path: str) -> dict:
    """Mede LUFS integrado e true peak de um arquivo final."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null",
                        "-"], capture_output=True, text=True)
    out = {"lufs": None, "true_peak": None}
    summary = p.stderr.rsplit("Summary:", 1)[-1]
    for line in summary.splitlines():
        line = line.strip()
        if line.startswith("I:"):
            out["lufs"] = float(line.split()[1])
        elif line.startswith("Peak:"):
            out["true_peak"] = float(line.split()[1])
    return out
