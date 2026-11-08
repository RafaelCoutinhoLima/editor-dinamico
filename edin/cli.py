"""edin: editor de vídeo dinâmico com IA, grátis e local.

Fluxo típico (vídeo falado):
  edin transcribe video.mp4                 -> video.words.json
  edin text video.words.json                -> transcrição com tempos e índices (para o Claude ler)
  edin plan video.mp4 --preset reels        -> video.plan.json (o Claude refina)
  edin hunt video.words.json                -> video.candidates.json (melhores trechos para shorts)
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
    from .voice import dfn_binary, rnn_model

    dfn, rnn = dfn_binary(download=False), rnn_model(download=False)
    print(f"{'OK ' if dfn else '-- '} limpeza de voz DeepFilterNet {dfn or '(baixa no 1º uso)'}")
    print(f"{'OK ' if rnn else '-- '} limpeza de voz RNNoise {rnn or '(baixa no 1º uso)'}")
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
    plan = build_talking_plan(a.video, words, a.preset, a.range, not a.keep_fillers, a.format, a.speed,
                              not a.no_snap, not a.no_clean_voice)
    if a.cold_open:
        from .hunt import apply_cold_open

        apply_cold_open(plan, a.cold_open, a.range)
    out = a.out or _stem(a.video) + (f".{a.name}" if a.name else "") + ".plan.json"
    save_plan(plan, out)


def cmd_hunt(a):
    from .hunt import hunt

    hunt(a.words, a.video, a.top, a.min, a.max, a.out)


def cmd_montage(a):
    from .plan import build_montage_plan, save_plan

    plan = build_montage_plan(a.clips, a.music, a.duration, a.music_start, a.format, a.beats_per_cut, a.seed)
    save_plan(plan, a.out)


def cmd_timeline(a):
    from .plan import print_timeline

    print_timeline(a.plan)


def cmd_render(a):
    from .render import render

    out = a.out or default_output(a.plan, a.draft)
    render(a.plan, out, a.draft, a.keep, a.verbose)


FORMAT_NAMES = {"9:16": "vertical", "16:9": "horizontal", "1:1": "quadrado", "4:5": "retrato", "original": "original"}


def _video_date(src: str) -> str:
    """Data do vídeo original: AAAA-MM-DD no nome do arquivo, senão creation_time dos metadados, senão modificação."""
    import re
    import subprocess
    from datetime import date

    m = re.search(r"(20\d\d)[-_.]?(\d\d)[-_.]?(\d\d)", Path(src).name)
    if m:
        return "-".join(m.groups())
    try:
        tag = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=creation_time", "-of",
                              "csv=p=0", src], capture_output=True, text=True).stdout.strip()
        if re.match(r"\d{4}-\d\d-\d\d", tag) and not tag.startswith("1970"):
            return tag[:10]
        return date.fromtimestamp(Path(src).stat().st_mtime).isoformat()
    except OSError:
        return date.today().isoformat()


def default_output(plan_path: str, draft: bool) -> str:
    """Padrão de saída: <pasta do plano>/videos/AAAA-MM-DD_<formato>.mp4 (rascunhos em rascunhos/).
    Não sobrescreve: se o nome existir, acrescenta _2, _3..."""
    from .plan import load_plan

    plan = load_plan(plan_path)
    base = Path(plan_path).resolve().parent / ("rascunhos" if draft else "videos")
    name = f"{_video_date(plan['source'])}_{FORMAT_NAMES.get(plan.get('format', '9:16'), 'video')}"
    if draft:
        name += "_rascunho"
    base.mkdir(parents=True, exist_ok=True)
    out, k = base / f"{name}.mp4", 2
    while out.exists() and not draft:  # rascunho pode ser sobrescrito; final nunca
        out, k = base / f"{name}_{k}.mp4", k + 1
    return str(out)


def cmd_auto(a):
    """Atalho: transcreve (se preciso), planeja e renderiza com o preset."""
    from .plan import build_talking_plan, save_plan
    from .render import render
    from .transcribe import transcribe

    words = _stem(a.video) + ".words.json"
    if not Path(words).exists():
        transcribe(a.video, words, a.model, None if a.lang == "auto" else a.lang, "auto")
    plan = build_talking_plan(a.video, words, a.preset, a.range, speed=a.speed)
    pp = _stem(a.video) + ".plan.json"
    save_plan(plan, pp)
    render(pp, a.out or default_output(pp, a.draft), a.draft)


def cmd_check(a):
    from .check import audit_plan, audit_video, print_report, report_json

    warn, metrics = audit_plan(a.plan), {}
    if a.video:
        warn += audit_video(a.plan, a.video, metrics)
    if a.json:
        sys.exit(report_json(warn, metrics, plano=a.plan, video=a.video))
    sys.exit(print_report(warn))


def cmd_verify(a):
    from .check import print_report, verify_render

    sys.exit(print_report(verify_render(a.plan, a.video, a.model, None if a.lang == "auto" else a.lang)))


def cmd_voice(a):
    from .utils import run
    from .voice import clean, noise_report

    out = a.out or _stem(a.input) + "_voz_limpa" + (".mp4" if not a.input.lower().endswith((".wav", ".mp3", ".m4a"))
                                                     else ".wav")
    cfg = {"clean": None if a.mode == "none" else a.mode, "strength": a.strength,
           "chain": None if a.no_chain else "broadcast"}
    wav = clean(a.input, str(Path(out).with_suffix(".wav")) if out.endswith(".mp4") else out, cfg, a.verbose)
    if out.endswith(".mp4"):  # devolve o vídeo com a voz limpa (vídeo copiado, sem reencode)
        run(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-i", wav, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out])
        Path(wav).unlink()
    antes, depois = noise_report(a.input), noise_report(out)
    print(f"[edin] Voz limpa: {out}")
    print(f"       ruído de fundo {antes['ruido_db']} -> {depois['ruido_db']} dBFS | "
          f"fala/ruído {antes['snr_db']} -> {depois['snr_db']} dB")


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


# ---- motion (Remotion) -------------------------------------------------------------- ver docs/MOTION.md
def cmd_motion(a):
    from .remotion_bridge import motion

    out = a.out or _stem(a.video) + "_motion.mp4"
    motion(a.plan, a.video, out, a.matte, a.props_only, a.guides, a.concurrency, a.verbose)


def _add_motion_parser(sp):
    s = sp.add_parser("motion", help="motion design com Remotion por cima do vídeo editado (chave \"motion\" do plano)")
    s.add_argument("plan")
    s.add_argument("video", help="vídeo já renderizado pelo edin (edin render)")
    s.add_argument("-o", "--out")
    s.add_argument("--matte", choices=["auto", "on", "off"], default="auto",
                   help="recorte da pessoa para a palavra atrás da cabeça (auto: só se houver behind-head-word)")
    s.add_argument("--props-only", action="store_true", help="só gera as props e a mídia (para o Remotion Studio)")
    s.add_argument("--guides", action="store_true", help="desenha zonas seguras, rosto e caixas (conferência)")
    s.add_argument("--concurrency", type=int)
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=cmd_motion)
# ---- fim motion


# ---- b-roll (Pexels) e conferência de legenda/emoji ------------------------------------- ver docs/PLANO.md
def cmd_broll(a):
    from .broll import fetch, resolve_plan

    if a.plan:
        from .plan import load_plan
        from .utils import save_json

        raw = load_json(a.plan)
        plan = load_plan(a.plan)
        n = resolve_plan(plan, Path(a.plan).resolve().parent)
        base = Path(a.plan).resolve().parent
        for seg_raw, seg in zip(raw["segments"], plan["segments"]):
            if (seg_raw.get("broll") or {}).get("query") and not seg_raw["broll"].get("src"):
                seg_raw["broll"]["src"] = str(Path(seg["broll"]["src"]).relative_to(base))
        save_json(raw, a.plan)
        print(f"[edin] {n} b-roll(s) resolvido(s) em {a.plan} (créditos em broll/CREDITOS.txt)")
        return
    if not a.query:
        raise SystemExit("[edin] Passe a consulta (edin broll \"estudante cansado\") ou --plan plano.json")
    dest = Path(a.dir) if a.dir else Path.cwd() / "broll"
    for path, it in fetch(a.query, a.orientation, a.n, dest):
        print(f"{path}  {it['w']}x{it['h']} {it['duration']:.0f}s  {it['author']}  {it['url']}")
    print(f"[edin] Créditos em {dest / 'CREDITOS.txt'}")


def cmd_captions(a):
    from .captions import caption_warnings, layout_captions, word_categories
    from .emoji import plan_warnings
    from .plan import load_plan, remap_words
    from .render import FORMATS

    plan = load_plan(a.plan)
    cap = plan.get("captions")
    if not cap:
        print("Plano sem legenda (captions: null).")
        return
    W, H = FORMATS.get(plan.get("format", "9:16"), (1080, 1920))
    words = remap_words(plan)
    lay = layout_captions(words, cap, W, H)
    p = lay["params"]
    print(f"Legenda {cap.get('style', 'hormozi')}: letra {p['letter']:.0f} px (fonte {p['size']:.0f}), "
          f"centro em y={p['pos_y']} de {H}, {len(lay['groups'])} grupos, até {p['per']} palavras")
    cats = word_categories(words, cap)
    if cats:
        print("Categorias: " + " ".join(f"#{w['i']}:{w['w']}" for w in words if w["i"] in cats))
    for wmsg in caption_warnings(cap, W, H) + plan_warnings(cap, words):
        print(f"aviso: {wmsg}")


def _add_broll_parser(sp):
    s = sp.add_parser("broll", help="baixa b-roll grátis do Pexels (PEXELS_API_KEY) com créditos em broll/")
    s.add_argument("query", nargs="?", help="o que buscar, ex.: \"estudante cansado\"")
    s.add_argument("--orientation", choices=["portrait", "landscape", "square"], default="portrait")
    s.add_argument("--n", type=int, default=3, help="quantos clipes baixar")
    s.add_argument("--dir", help="pasta de destino (padrão: ./broll)")
    s.add_argument("--plan", help="resolve os \"broll\": {\"query\"} do plano e grava o src nele")
    s.set_defaults(fn=cmd_broll)

    s = sp.add_parser("captions", help="confere a legenda do plano: tamanho, posição, categorias e emojis")
    s.add_argument("plan")
    s.set_defaults(fn=cmd_captions)
# ---- fim b-roll


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
    s.add_argument("--speed", type=float, default=1.0, help="acelera a fala depois do corte (1.05-1.10 soa natural)")
    s.add_argument("--no-snap", action="store_true", help="não ajustar cortes pela energia do áudio")
    s.add_argument("--no-clean-voice", action="store_true", help="não limpar a voz (ruído + cadeia broadcast)")
    s.add_argument("--cold-open", nargs="?", const="auto", metavar="A-B",
                   help="repete a frase mais forte do trecho (1 a 3 s) no início; ou índices de palavra A-B")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_plan)

    s = sp.add_parser("hunt", help="acha os melhores trechos de um vídeo longo para shorts (-> .candidates.json)")
    s.add_argument("words", help="video.words.json")
    s.add_argument("--video", help="vídeo/áudio para energia e tom (padrão: o da transcrição)")
    s.add_argument("--top", type=int, default=5)
    s.add_argument("--min", type=float, default=20, help="duração mínima em s (padrão 20)")
    s.add_argument("--max", type=float, default=60, help="duração máxima em s (padrão 60)")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_hunt)

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
    s.add_argument("--speed", type=float, default=1.0)
    s.add_argument("--draft", action="store_true")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_auto)

    s = sp.add_parser("check", help="crítico automático: ritmo, gancho, legendas, som (e o vídeo final, se passar)")
    s.add_argument("plan")
    s.add_argument("video", nargs="?", help="vídeo renderizado (preto, congelado, silêncio, loudness, ffprobe, ritmo, "
                                            "faixas, contraste)")
    s.add_argument("--json", action="store_true", help="relatório em JSON (para agentes)")
    s.set_defaults(fn=cmd_check)

    s = sp.add_parser("verify", help="retranscreve o vídeo final e acha palavras comidas nos cortes")
    s.add_argument("plan")
    s.add_argument("video")
    s.add_argument("--model", default="small")
    s.add_argument("--lang", default="pt")
    s.set_defaults(fn=cmd_verify)

    s = sp.add_parser("sheet", help="folha de quadros (contact sheet) para revisar o vídeo")
    s.add_argument("video")
    s.add_argument("-n", type=int, default=12)
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_sheet)

    s = sp.add_parser("voice", help="limpa a voz de um áudio/vídeo (DeepFilterNet ou RNNoise + cadeia broadcast)")
    s.add_argument("input")
    s.add_argument("-o", "--out", help="saída .wav ou .mp4 (padrão: <nome>_voz_limpa)")
    s.add_argument("--mode", default="dfn", choices=["dfn", "rnn", "none"], help="redutor de ruído (padrão dfn)")
    s.add_argument("--strength", type=float, default=24, help="redução máxima em dB (padrão 24; 100 = total)")
    s.add_argument("--no-chain", action="store_true", help="sem a cadeia broadcast (EQ, de-esser, compressor)")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=cmd_voice)

    s = sp.add_parser("sfx", help="lista efeitos sonoros embutidos")
    s.set_defaults(fn=cmd_sfx)

    s = sp.add_parser("clean", help="apaga a pasta temporária de um render")
    s.add_argument("out")
    s.set_defaults(fn=cmd_clean)

    _add_motion_parser(sp)
    _add_broll_parser(sp)

    a = p.parse_args(argv)
    if a.cmd not in ("doctor", "sfx", "text"):
        check_tools()
    a.fn(a)


if __name__ == "__main__":
    main()
