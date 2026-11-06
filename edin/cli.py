"""edin: editor de vídeo dinâmico com IA, grátis e local.

Fluxo típico (vídeo falado):
  edin transcribe video.mp4                 -> video.words.json
  edin text video.words.json                -> transcrição com tempos e índices (para o Claude ler)
  edin plan video.mp4 --preset reels        -> video.plan.json (o Claude refina)
  edin timeline video.plan.json             -> como vai ficar o vídeo final
  edin render video.plan.json -o final.mp4  -> vídeo editado
  edin sheet final.mp4                      -> folha de quadros para conferir

Montagem no beat (sem fala):
  edin montage clip1.mp4 clip2.mp4 --music musica.mp3 --duration 30 -o montagem.plan.json
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .utils import check_tools, load_json


def _stem(p: str) -> str:
    return str(Path(p).with_suffix(""))


def cmd_doctor(_):
    ok = True
    for tool in ("ffmpeg", "ffprobe"):
        found = shutil.which(tool)
        print(f"{'OK ' if found else 'FALTA'} {tool} {found or ''}")
        ok &= bool(found)
    for mod, why in (("faster_whisper", "transcrição"), ("cv2", "detecção de rosto"), ("numpy", "base"),
                     ("librosa", "montagem no beat")):
        try:
            __import__(mod)
            print(f"OK  {mod} ({why})")
        except ImportError:
            print(f"FALTA {mod} ({why})  -> pip install -r requirements.txt")
            ok = False
    try:
        import ctranslate2

        print(f"GPU CUDA: {ctranslate2.get_cuda_device_count()} dispositivo(s)")
    except Exception:
        pass
    sys.exit(0 if ok else 1)


def cmd_transcribe(a):
    from .transcribe import transcribe

    out = a.out or _stem(a.video) + ".words.json"
    transcribe(a.video, out, a.model, None if a.lang == "auto" else a.lang, a.device)


def cmd_text(a):
    from .transcribe import print_text

    print_text(a.words)


def cmd_plan(a):
    from .plan import PRESETS, build_talking_plan, save_plan

    if a.preset not in PRESETS:
        sys.exit(f"Preset inválido. Opções: {', '.join(PRESETS)}")
    words = a.words or _stem(a.video) + ".words.json"
    if not Path(words).exists():
        sys.exit(f"[edin] {words} não existe. Rode antes: edin transcribe {a.video}")
    plan = build_talking_plan(a.video, words, a.preset, a.range, not a.keep_fillers, a.format)
    out = a.out or _stem(a.video) + (f".{a.name}" if a.name else "") + ".plan.json"
    save_plan(plan, out)


def cmd_montage(a):
    from .plan import build_montage_plan, save_plan

    plan = build_montage_plan(a.clips, a.music, a.duration, a.music_start, a.format, a.beats_per_cut, a.seed)
    save_plan(plan, a.out)


def cmd_timeline(a):
    from .plan import print_timeline

    print_timeline(a.plan)


def cmd_render(a):
    from .render import render

    out = a.out or str(Path(a.plan).with_suffix("")).replace(".plan", "") + ("_rascunho" if a.draft else "_editado") \
        + ".mp4"
    render(a.plan, out, a.draft, a.keep, a.verbose)


def cmd_auto(a):
    """Atalho: transcreve (se preciso), planeja e renderiza com o preset."""
    from .plan import build_talking_plan, save_plan
    from .render import render
    from .transcribe import transcribe

    words = _stem(a.video) + ".words.json"
    if not Path(words).exists():
        transcribe(a.video, words, a.model, a.lang, "auto")
    plan = build_talking_plan(a.video, words, a.preset, a.range)
    pp = _stem(a.video) + ".plan.json"
    save_plan(plan, pp)
    render(pp, a.out or _stem(a.video) + "_editado.mp4", a.draft)


def cmd_sheet(a):
    from .render import contact_sheet

    out = a.out or _stem(a.video) + "_quadros.jpg"
    contact_sheet(a.video, out, a.n)
    print(out)


def cmd_sfx(_):
    from .sfx import RECIPES

    print("Efeitos disponíveis:", ", ".join(RECIPES))


def cmd_clean(a):
    from .render import clean

    clean(a.out)


def main(argv=None):
    p = argparse.ArgumentParser(prog="edin", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("doctor", help="verifica dependências")
    s.set_defaults(fn=cmd_doctor)

    s = sp.add_parser("transcribe", help="transcreve com faster-whisper (palavra por palavra)")
    s.add_argument("video")
    s.add_argument("--model", default="small", help="tiny|base|small|medium|large-v3|turbo (padrão small)")
    s.add_argument("--lang", default="pt", help="idioma (pt, en, ... ou auto)")
    s.add_argument("--device", default="auto", help="auto|cpu|cuda")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_transcribe)

    s = sp.add_parser("text", help="mostra a transcrição com tempos e índices das palavras")
    s.add_argument("words")
    s.set_defaults(fn=cmd_text)

    s = sp.add_parser("plan", help="gera plano automático de edição para vídeo falado")
    s.add_argument("video")
    s.add_argument("--words")
    s.add_argument("--preset", default="reels", help="reels|youtube|podcast|aula")
    s.add_argument("--format", help="9:16|16:9|1:1|4:5|original (sobrescreve o preset)")
    s.add_argument("--range", help="trecho do original, ex: 90-150 ou 1:30-2:30 (para cortes/shorts)")
    s.add_argument("--name", help="sufixo do arquivo, ex: short1")
    s.add_argument("--keep-fillers", action="store_true", help="não remover ahn/hum/éé")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_plan)

    s = sp.add_parser("montage", help="plano de montagem cortada no ritmo da música")
    s.add_argument("clips", nargs="+")
    s.add_argument("--music", required=True)
    s.add_argument("--duration", type=float, default=30)
    s.add_argument("--music-start", type=float, default=0)
    s.add_argument("--format", default="9:16")
    s.add_argument("--beats-per-cut", type=int, default=2)
    s.add_argument("--seed", type=int, default=7)
    s.add_argument("-o", "--out", default="montagem.plan.json")
    s.set_defaults(fn=cmd_montage)

    s = sp.add_parser("timeline", help="mostra a linha do tempo final de um plano")
    s.add_argument("plan")
    s.set_defaults(fn=cmd_timeline)

    s = sp.add_parser("render", help="renderiza um plano")
    s.add_argument("plan")
    s.add_argument("-o", "--out")
    s.add_argument("--draft", action="store_true", help="meia resolução, rápido, para conferir")
    s.add_argument("--keep", action="store_true", help="mantém arquivos temporários")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=cmd_render)

    s = sp.add_parser("auto", help="transcreve + planeja + renderiza num comando só")
    s.add_argument("video")
    s.add_argument("--preset", default="reels")
    s.add_argument("--range")
    s.add_argument("--model", default="small")
    s.add_argument("--lang", default="pt")
    s.add_argument("--draft", action="store_true")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_auto)

    s = sp.add_parser("sheet", help="folha de quadros (contact sheet) para revisar o vídeo")
    s.add_argument("video")
    s.add_argument("-n", type=int, default=12)
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_sheet)

    s = sp.add_parser("sfx", help="lista efeitos sonoros embutidos")
    s.set_defaults(fn=cmd_sfx)

    s = sp.add_parser("clean", help="apaga a pasta temporária de um render")
    s.add_argument("out")
    s.set_defaults(fn=cmd_clean)

    a = p.parse_args(argv)
    if a.cmd not in ("doctor", "sfx", "text", "timeline"):
        check_tools()
    a.fn(a)


if __name__ == "__main__":
    main()
