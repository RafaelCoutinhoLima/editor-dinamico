"""Limpeza de voz, grátis e local (o que o Descript Studio Sound faz).

Etapas, nesta ordem:
1. Redução de ruído:
   - "dfn": DeepFilterNet 3 (MIT/Apache, binário de 36 MB sem Python). Melhor qualidade.
   - "rnn": RNNoise pelo filtro `arnndn` do ffmpeg (modelo de 300 KB). Mais leve.
   Os dois guardam um pouco do som original (`strength` em dB, como o "mix" dos profissionais), porque redução
   total deixa a voz robótica.
2. Cadeia "broadcast" (ffmpeg): corta grave de manuseio, tira o "embolado", de-esser, compressor suave e presença.

Binários e modelos são baixados uma vez, das fontes oficiais, para ~/.local/share/edin/.
"""
from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import urllib.request
from pathlib import Path

from .utils import run

HOME = Path(os.environ.get("EDIN_HOME", Path.home() / ".local" / "share" / "edin"))
DFN_VERSION = "0.5.6"
DFN_BASE = f"https://github.com/Rikorose/DeepFilterNet/releases/download/v{DFN_VERSION}"
DFN_FILES = {
    ("Linux", "x86_64"): f"deep-filter-{DFN_VERSION}-x86_64-unknown-linux-musl",
    ("Linux", "aarch64"): f"deep-filter-{DFN_VERSION}-aarch64-unknown-linux-gnu",
    ("Darwin", "x86_64"): f"deep-filter-{DFN_VERSION}-x86_64-apple-darwin",
    ("Darwin", "arm64"): f"deep-filter-{DFN_VERSION}-aarch64-apple-darwin",
    ("Windows", "AMD64"): f"deep-filter-{DFN_VERSION}-x86_64-pc-windows-msvc.exe",
}
RNN_URL = ("https://raw.githubusercontent.com/GregorR/rnnoise-models/master/"
           "somnolent-hogwash-2018-09-01/sh.rnnn")

# grave de manuseio fora, menos "embolado" (250 Hz), de-esser, compressor suave, presença (3 kHz) e ar (10 kHz)
BROADCAST = ("highpass=f=80,equalizer=f=250:t=q:w=1.2:g=-2.5,deesser=i=0.4,"
             "acompressor=threshold=-20dB:ratio=3:attack=8:release=160:makeup=2,"
             "equalizer=f=3000:t=q:w=1.0:g=2,equalizer=f=10000:t=q:w=1.0:g=1.5")

DEFAULT = {"clean": "dfn", "strength": 24, "chain": "broadcast"}


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"[edin] Baixando {url.rsplit('/', 1)[-1]} (uma vez só)...")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    tmp.rename(dest)
    return dest


def dfn_binary(download: bool = True) -> Path | None:
    """Caminho do deep-filter (baixa se preciso). None se não houver binário para esta plataforma."""
    found = shutil.which("deep-filter")
    if found:
        return Path(found)
    name = DFN_FILES.get((platform.system(), platform.machine()))
    if not name:
        return None
    dest = HOME / "bin" / ("deep-filter.exe" if name.endswith(".exe") else "deep-filter")
    if not dest.exists():
        if not download:
            return None
        _download(f"{DFN_BASE}/{name}", dest)
        dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dest


def rnn_model(download: bool = True) -> Path | None:
    dest = HOME / "models" / "sh.rnnn"
    if not dest.exists():
        if not download:
            return None
        _download(RNN_URL, dest)
    return dest


def _filter_path(p: Path) -> str:
    return str(p).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def clean(src: str, out_wav: str, cfg: dict | None = None, verbose: bool = False) -> str:
    """Limpa a voz de `src` (áudio ou vídeo) e grava `out_wav` (48 kHz, estéreo, mesma duração)."""
    cfg = {**DEFAULT, **(cfg or {})}
    mode, strength = cfg.get("clean"), float(cfg.get("strength", 24))
    out = Path(out_wav)
    out.parent.mkdir(parents=True, exist_ok=True)
    wd = out.parent / (out.stem + "_voz")
    wd.mkdir(exist_ok=True)
    base = wd / "entrada.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(base)],
        verbose=verbose)
    stage = base
    if mode == "dfn":
        exe = dfn_binary()
        if exe is None:
            print("[edin] DeepFilterNet indisponível nesta plataforma: usando RNNoise.")
            mode = "rnn"
        else:
            # -D compensa o atraso do modelo (sem isso a voz sai uns ms atrasada); -a limita a redução (mix)
            run([str(exe), "-D", "-a", f"{strength:g}", "-o", str(wd / "dfn"), str(base)], verbose=verbose)
            stage = wd / "dfn" / base.name
    chain = []
    if mode == "rnn":
        model = rnn_model()
        mix = max(0.0, min(1.0, 1 - 10 ** (-strength / 20)))  # mesma ideia do limite em dB
        chain.append(f"arnndn=m='{_filter_path(model)}':mix={mix:.3f}")
    if cfg.get("chain") == "broadcast":
        chain.append(BROADCAST)
    if chain:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(stage), "-af", ",".join(chain), "-ac", "2", "-ar", "48000",
             "-c:a", "pcm_s16le", str(out)], verbose=verbose)
    else:
        shutil.copyfile(stage, out)
    shutil.rmtree(wd, ignore_errors=True)
    return str(out)


def noise_report(path: str) -> dict:
    """Mede o piso de ruído (pausas) e o nível da fala, em dBFS, pela energia em janelas de 50 ms."""
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    win = 800
    if len(x) < win * 4:
        return {"ruido_db": None, "fala_db": None, "snr_db": None}
    rms = np.sqrt((x[: len(x) // win * win].reshape(-1, win) ** 2).mean(axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    ruido, fala = float(np.percentile(db, 10)), float(np.percentile(db, 90))
    return {"ruido_db": round(ruido, 1), "fala_db": round(fala, 1), "snr_db": round(fala - ruido, 1)}
