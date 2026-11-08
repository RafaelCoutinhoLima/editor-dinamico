"""Efeitos sonoros sintetizados com ffmpeg (nada para baixar, sem direitos autorais).

Cada efeito tem 2 a 3 camadas que soam juntas (ataque + corpo + cauda): efeito de uma camada só é a
assinatura de som amador. SYNC diz onde fica o ponto de sincronia dentro do arquivo (ataque para
cliques e batidas, pico para whoosh e riser), para o efeito cair no quadro certo e não no começo do
arquivo. VOLUME é o volume padrão pensado para ficar abaixo da voz (cliques ~20 dB abaixo).
"""
from __future__ import annotations

from pathlib import Path

from .utils import run

# (fonte lavfi, cadeia de filtros). Fontes com várias camadas usam amix dentro de um filtergraph.
RECIPES = {
    # clique suave de mouse: ideal para cortes em vídeo falado sem música
    "softclick": ("aevalsrc='0.6*sin(2*PI*3100*t)*exp(-160*t)+0.35*sin(2*PI*900*t)*exp(-90*t)':d=0.06:s=48000",
                  "highpass=f=500,afade=t=out:st=0.045:d=0.015"),
    "click": ("aevalsrc='0.7*sin(2*PI*2400*t)*exp(-120*t)+0.25*sin(2*PI*5200*t)*exp(-220*t)':d=0.05:s=48000",
              "highpass=f=700"),
    # batida de madeira curta: card/elemento pousando
    "tock": ("aevalsrc='0.8*sin(2*PI*(620+300*exp(-60*t))*t)*exp(-38*t)+0.2*sin(2*PI*1650*t)*exp(-70*t)':d=0.14"
             ":s=48000", "highpass=f=180"),
    "pop": ("aevalsrc='0.9*sin(2*PI*(500+1800*exp(-45*t))*t)*exp(-28*t)':d=0.16:s=48000",
            "highpass=f=250,afade=t=out:st=0.12:d=0.04"),
    # obturador: snap zoom, troca rápida de foto (width_type=h: sem ele o w do bandpass é Q e o som some)
    "snap": ("anoisesrc=d=0.09:c=white:a=0.7:r=48000",
             "bandpass=f=3500:width_type=h:w=2500,afade=t=in:d=0.003,afade=t=out:st=0.02:d=0.07"),
    "ding": ("aevalsrc='0.45*(sin(2*PI*1320*t)+0.6*sin(2*PI*1980*t)+0.3*sin(2*PI*2640*t))*exp(-5*t)':d=0.9:s=48000",
             "afade=t=out:st=0.7:d=0.2"),
    # whoosh em camadas: ar (ruído rosa filtrado) + textura (ruído branco agudo) que crescem até o pico
    "whoosh": ("anoisesrc=d=0.5:c=pink:a=0.9:r=48000",
               "highpass=f=350,lowpass=f=6000,afade=t=in:d=0.30:curve=exp,afade=t=out:st=0.30:d=0.20:curve=qsin,"
               "volume=0.85"),
    "swoosh": ("anoisesrc=d=0.3:c=white:a=0.6:r=48000",
               "highpass=f=1500,lowpass=f=9000,afade=t=in:d=0.14:curve=exp,afade=t=out:st=0.14:d=0.16"),
    # impacto: sub + corpo + transiente (o "punch" das revelações, use 1 ou 2 por vídeo)
    "boom": ("aevalsrc='0.85*sin(2*PI*(45+80*exp(-12*t))*t)*exp(-3.2*t)+0.35*sin(2*PI*(140+200*exp(-30*t))*t)"
             "*exp(-9*t)+0.3*sin(2*PI*2200*t)*exp(-200*t)':d=1.2:s=48000", "lowpass=f=4000,highpass=f=30"),
    # riser com curva exponencial (riser linear soa barato)
    "riser": ("aevalsrc='0.32*sin(2*PI*(160*t+260*t*t*t))*pow(t/1.5\\,2)+0.08*sin(2*PI*(320*t+520*t*t*t))"
              "*pow(t/1.5\\,3)':d=1.5:s=48000", "afade=t=out:st=1.45:d=0.05"),
    "glitch": ("anoisesrc=d=0.18:c=white:a=0.5:r=48000", "acrusher=bits=4:mode=log:aa=1,highpass=f=800"),
}

# ponto de sincronia dentro do arquivo (s): onde o ouvido percebe o "agora"
SYNC = {"whoosh": 0.32, "swoosh": 0.14, "riser": 1.45}
# volume padrão (linear) quando o plano não diz
# (medido num render real: cliques ~20 dB, pop/ding ~16-18 dB abaixo da voz)
VOLUME = {"softclick": 0.10, "click": 0.11, "tock": 0.16, "pop": 0.10, "snap": 0.18, "ding": 0.12,
          "whoosh": 0.3, "swoosh": 0.3, "boom": 0.6, "riser": 0.45, "glitch": 0.08}
# whoosh/riser: o pico cai logo depois do corte (+37 ms medido em filmes profissionais);
# cliques: o ataque cai um pouco antes (-11 ms)
OFFSET = {"whoosh": 0.037, "swoosh": 0.0, "riser": -0.02, "softclick": -0.011, "click": -0.011}


def sync_start(kind: str, at: float) -> float:
    """Tempo (no vídeo final) em que o arquivo do efeito deve começar para o ponto de sincronia cair em `at`."""
    return max(0.0, at + OFFSET.get(kind, 0.0) - SYNC.get(kind, 0.0))


def sfx_file(kind: str, cache_dir: Path) -> Path:
    if kind not in RECIPES:
        raise SystemExit(f"[edin] SFX '{kind}' não existe. Opções: {', '.join(RECIPES)}")
    out = cache_dir / f"sfx3_{kind}.wav"  # sfx3: muda o nome quando as receitas mudam
    if out.exists():
        return out
    src, chain = RECIPES[kind]
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", src]
    if chain:
        cmd += ["-af", chain]
    cmd += ["-ac", "2", "-ar", "48000", "-c:a", "pcm_f32le", str(out)]  # float: camadas somadas não clipam
    run(cmd)
    return out
