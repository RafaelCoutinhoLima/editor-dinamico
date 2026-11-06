"""Efeitos sonoros sintetizados com ffmpeg (nada para baixar, sem direitos autorais)."""
from __future__ import annotations

from pathlib import Path

from .utils import run

# expressões aevalsrc (t em segundos) ou cadeias de filtros sobre ruído
RECIPES = {
    "whoosh": ("anoisesrc=d=0.5:c=pink:a=0.9:r=48000",
               "highpass=f=400,lowpass=f=5000,afade=t=in:d=0.28:curve=exp,afade=t=out:st=0.28:d=0.22,volume=0.9"),
    "swoosh": ("anoisesrc=d=0.3:c=white:a=0.6:r=48000",
               "highpass=f=1500,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.18"),
    "pop": ("aevalsrc='0.9*sin(2*PI*(500+1800*exp(-45*t))*t)*exp(-28*t)':d=0.16:s=48000", ""),
    "click": ("aevalsrc='0.7*sin(2*PI*2400*t)*exp(-120*t)':d=0.05:s=48000", ""),
    "ding": ("aevalsrc='0.45*(sin(2*PI*1320*t)+0.6*sin(2*PI*1980*t)+0.3*sin(2*PI*2640*t))*exp(-5*t)':d=0.9:s=48000",
             ""),
    "boom": ("aevalsrc='0.95*sin(2*PI*(42+90*exp(-12*t))*t)*exp(-3.2*t)':d=1.2:s=48000", "lowpass=f=300"),
    "riser": ("aevalsrc='0.35*sin(2*PI*(180*t+380*t*t))*(t/1.5)':d=1.5:s=48000",
              "afade=t=out:st=1.4:d=0.1"),
    "glitch": ("anoisesrc=d=0.18:c=white:a=0.5:r=48000", "acrusher=bits=4:mode=log:aa=1,highpass=f=800"),
}


def sfx_file(kind: str, cache_dir: Path) -> Path:
    if kind not in RECIPES:
        raise SystemExit(f"[edin] SFX '{kind}' não existe. Opções: {', '.join(RECIPES)}")
    out = cache_dir / f"sfx_{kind}.wav"
    if out.exists():
        return out
    src, chain = RECIPES[kind]
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", src]
    if chain:
        cmd += ["-af", chain]
    cmd += ["-ac", "2", "-ar", "48000", str(out)]
    run(cmd)
    return out
