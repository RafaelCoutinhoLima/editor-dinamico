"""Crítico automático: audita o plano (ritmo, gancho, legendas, som) e o vídeo final (palavras perdidas, loudness).

Regras tiradas de edições reais (ver docs/REGRAS.md). Cada aviso diz o problema e como corrigir.
`edin check` não decide sozinho: ele aponta; o Claude (ou o agente critico-de-edicao) decide.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

from .plan import load_plan, remap_words, seg_out_dur
from .utils import fmt_time, probe

# limites por formato de saída (segundos)
MAX_SHOT = {"9:16": 3.2, "1:1": 3.5, "4:5": 3.5, "16:9": 8.0, "original": 12.0}
MAX_DUR = {"9:16": 90.0, "1:1": 90.0, "4:5": 90.0}


def _shots(plan: dict) -> list:
    """Planos visuais: um plano muda quando há corte de verdade, troca de zoom, b-roll ou outra fonte."""
    shots, t, prev = [], 0.0, None
    for seg in plan["segments"]:
        d = seg_out_dur(seg)
        key = (seg.get("src"), (seg.get("broll") or {}).get("src"), seg.get("zoom", 1.0))
        moving = (abs(float(seg.get("zoom_to", seg.get("zoom", 1.0))) - float(seg.get("zoom", 1.0))) > 0.02
                  or bool(seg.get("pan")))
        # zoom lento recomeçando no segmento seguinte também é uma mudança visível
        cont = (prev is not None and abs(seg["start"] - prev["end"]) < 0.02 and key == prev["_key"]
                and not moving and not prev["_moving"])
        if cont:
            shots[-1]["end"] += d
            shots[-1]["moving"] = shots[-1]["moving"] and moving
        else:
            shots.append({"start": t, "end": t + d, "moving": moving})
        prev = {**seg, "_key": key, "_moving": moving}
        t += d
    return shots


def audit_plan(plan_path: str) -> list:
    plan = load_plan(plan_path)
    fmt = plan.get("format", "9:16")
    vertical = fmt in ("9:16", "4:5", "1:1")
    segs = plan["segments"]
    total = sum(seg_out_dur(s) for s in segs)
    words = remap_words(plan)
    warn = []

    def w(level, msg):
        warn.append((level, msg))

    # ------------------------------------------------ duração e gancho
    if fmt in MAX_DUR and total > MAX_DUR[fmt]:
        w("aviso", f"Vídeo com {total:.0f}s. Para Reels/Shorts, acima de {MAX_DUR[fmt]:.0f}s perde retenção: corte "
                   "enrolação ou divida em partes.")
    if words and words[0]["s"] > 0.5:
        w("erro", f"Primeira palavra só em {words[0]['s']:.2f}s. O gancho tem que estar na tela em 0,5s: corte o "
                  "começo do 1º segmento.")
    titles = plan.get("titles") or []
    if vertical and plan.get("words") and not titles:
        w("dica", "Sem título no gancho. Em shorts, um `titles` de até 6 palavras de 0 a ~2,5s segura o scroll.")
    for t in titles:
        n = len(t["text"].split())
        if n > 6:
            w("aviso", f"Título '{t['text']}' tem {n} palavras. Máximo 6 para ler em 2s.")
        dur = float(t.get("end", 2.5)) - float(t.get("start", 0))
        if dur < 0.4 + 0.3 * n:
            w("aviso", f"Título '{t['text']}' fica {dur:.1f}s na tela; precisa de pelo menos {0.4 + 0.3 * n:.1f}s "
                       "para ser lido.")

    # ------------------------------------------------ ritmo
    limit = MAX_SHOT.get(fmt, 8.0)
    for sh in _shots(plan):
        d = sh["end"] - sh["start"]
        if d > limit * (1.6 if sh["moving"] else 1.0):
            w("aviso", f"Plano parado de {d:.1f}s em {fmt_time(sh['start'])}-{fmt_time(sh['end'])}. Em {fmt} algo "
                       f"deve mudar a cada {limit:.1f}s: punch-in, b-roll ou corte.")
    tiny = [n for n, s in enumerate(segs) if seg_out_dur(s) < 0.25 and not s.get("src")]
    if tiny:
        w("aviso", f"Segmentos muito curtos (< 0,25s) piscam na tela: {', '.join(f'seg {n:02d}' for n in tiny[:8])}. "
                   "Junte com o vizinho.")
    # zoom alto só preocupa onde há rosto (em texto/logo ampliado é intencional)
    zooms = [float(s.get("zoom", 1.0)) for s in segs if s.get("focus", "face") == "face" or isinstance(s.get("focus"), list)]
    if max(zooms + [1.0]) > 1.45:
        w("aviso", "Zoom acima de 1.45 perde nitidez e pode cortar a cabeça. Use até 1.3 nos momentos de impacto.")
    broll = sum(seg_out_dur(s) for s in segs if s.get("broll"))
    if total and broll / total > 0.30 and plan.get("words"):
        w("aviso", f"B-roll em {broll / total:.0%} do vídeo. Em vídeo de pessoa falando, o rosto deve aparecer em "
                   "pelo menos 60-70% do tempo.")

    # ------------------------------------------------ vertical sem letterbox
    if fmt in ("9:16", "4:5"):
        info_cache = {}
        boxed = 0.0
        for seg in segs:
            src = seg.get("src") or plan["source"]
            if not Path(src).exists() or seg.get("fit") not in ("blur", "pad") or seg.get("pan"):
                continue
            if src not in info_cache:
                info_cache[src] = probe(src)
            inf = info_cache[src]
            if inf["w"] / inf["h"] > 1.3 and float(seg.get("zoom", 1.0)) < 1.15:
                boxed += seg_out_dur(seg)
        if total and boxed / total > 0.15:
            w("aviso", f"{boxed / total:.0%} do vídeo é quadro horizontal encaixado na vertical quase sem ampliar "
                       "(fica pequeno com faixas). Use `pan` em telas largas e `fit: extend` com zoom em texto/logo.")

    # ------------------------------------------------ legendas
    cap = plan.get("captions")
    if cap and words:
        pos = float(cap.get("position", 0.7))
        if vertical and not 0.15 <= pos <= 0.80:
            w("erro", f"Legenda em position={pos}: fora da zona segura do 9:16 (o app cobre o topo ~11% e a base "
                      "~17%). Use entre 0.55 e 0.78.")
        emph = set(cap.get("emphasis") or [])
        if emph and total and len(emph) / total > 0.5:
            w("aviso", f"{len(emph)} palavras de ênfase em {total:.0f}s. Ênfase demais vira ruído: no máximo uma a "
                       "cada 2 ou 3 segundos.")
        ghost = [x for x in words if x.get("p", 1) < 0.15]
        if ghost:
            show = ", ".join(f"{fmt_time(x['s'])} '{x['w']}'" for x in ghost[:8])
            lvl = "erro" if ghost[0]["s"] < 2.0 else "aviso"
            w(lvl, f"{len(ghost)} palavras com confiança < 15% (provável alucinação do Whisper sobre música, vinheta "
                   f"ou ruído): {show}. Ouça o trecho e apague o segmento se não for fala.")
        lowp = [x for x in words if 0.15 <= x.get("p", 1) < 0.5]
        if lowp:
            show = ", ".join(f"#{x['i']} '{x['w']}'" for x in lowp[:10])
            w("dica", f"{len(lowp)} palavras com transcrição incerta (confira nomes, marcas e números): {show}")
    elif plan.get("words") and not cap:
        w("dica", "Legendas desligadas. 85% assistem sem som: considere ligar.")

    # ------------------------------------------------ som
    n_sfx = len(plan.get("sfx") or [])
    auto = plan.get("auto_sfx") or {}
    if auto.get("on_cut") and auto.get("on_zoom"):
        w("aviso", "on_cut e on_zoom ligados juntos: som em todo corte e em toda troca de zoom fica cansativo.")
    if auto.get("on_zoom") in ("whoosh", "swoosh") or auto.get("on_cut") in ("whoosh", "swoosh"):
        w("dica", "Whoosh automático em todo corte soa genérico. Prefira `softclick` e guarde o whoosh para "
                  "transições grandes.")
    if total and n_sfx / total > 1.2:
        w("aviso", f"{n_sfx} efeitos manuais em {total:.0f}s. Menos é mais: acentos só no gancho, números e viradas.")
    booms = sum(1 for e in plan.get("sfx") or [] if e.get("type") in ("boom", "riser"))
    if booms > 2:
        w("aviso", f"{booms} boom/riser. Use no máximo 2 por vídeo (gancho e revelação).")
    mus = plan.get("music")
    if mus and mus.get("file") and plan.get("audio", "source") == "source":
        if plan.get("words") and float(mus.get("volume", 0.12)) > 0.2:
            w("aviso", "Música alta para vídeo falado: volume entre 0.08 e 0.15 (≈17 dB abaixo da voz).")
        if not Path(mus["file"]).exists():
            w("erro", f"Música não encontrada: {mus['file']}")

    # ------------------------------------------------ arquivos
    for n, seg in enumerate(segs):
        for p in (seg.get("src"), (seg.get("broll") or {}).get("src")):
            if p and not Path(p).exists():
                w("erro", f"seg {n:02d}: arquivo não encontrado {p}")
        if seg["end"] <= seg["start"]:
            w("erro", f"seg {n:02d}: end ({seg['end']}) <= start ({seg['start']})")
    return warn


def _norm(word: str) -> str:
    s = unicodedata.normalize("NFKD", word.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s)


def verify_render(plan_path: str, video: str, model: str = "small", lang: str = "pt") -> list:
    """Retranscreve o vídeo final e compara com as palavras que o plano manteve. Acha palavras comidas no corte."""
    from .transcribe import transcribe_words

    plan = load_plan(plan_path)
    expected = [x for x in map(_norm, (w["w"] for w in remap_words(plan))) if x]
    if not expected:
        return []
    got_words = transcribe_words(video, model, lang)
    got = [x for x in map(_norm, (w["w"] for w in got_words)) if x]
    sm = difflib.SequenceMatcher(a=expected, b=got, autojunk=False)
    warn = []
    exp_words = [w for w in remap_words(plan) if _norm(w["w"])]
    # cortes de verdade no vídeo final (troca só de zoom com áudio contínuo não é corte)
    cuts, t, prev = [], 0.0, None
    for seg in plan["segments"]:
        if prev is not None and (seg.get("src") != prev.get("src") or abs(seg["start"] - prev["end"]) > 0.02):
            cuts.append(t)
        t += seg_out_dur(seg)
        prev = seg
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        lost = (i2 - i1) - (j2 - j1) if op == "replace" else (i2 - i1 if op == "delete" else 0)
        if lost < 1:
            continue
        ws = exp_words[i1:i2]
        txt = " ".join(w["w"] for w in ws)
        near = any(ws[0]["s"] - 0.35 <= c <= ws[-1]["e"] + 0.35 for c in cuts)
        if near:
            warn.append(("erro", f"Possível palavra comida em {fmt_time(ws[0]['s'])}: '{txt}'. Aumente o `end` do "
                                 "segmento anterior ou o `start` do seguinte em 0,05-0,15s."))
        elif lost >= 2:  # longe de corte o áudio é contínuo: é o Whisper ouvindo diferente
            warn.append(("dica", f"Whisper ouviu diferente em {fmt_time(ws[0]['s'])}: '{txt}' (sem corte perto; "
                                 "confira se a transcrição original está certa)."))
    ratio = sm.ratio()
    level = "ok" if ratio >= 0.93 and not warn else "aviso"
    warn.append((level, f"Fala preservada: {ratio:.1%} das palavras batem ({len(expected)} esperadas, {len(got)} "
                        "ouvidas). Palavras soltas diferentes são ruído do Whisper; 2+ seguidas é corte real."))
    return warn


def audit_video(plan_path: str, video: str) -> list:
    from .audio import loudness

    plan = load_plan(plan_path)
    warn = []
    info = probe(video)
    total = sum(seg_out_dur(s) for s in plan["segments"])
    if abs(info["duration"] - total) > 0.25:
        warn.append(("aviso", f"Duração do arquivo {info['duration']:.2f}s difere do plano {total:.2f}s."))
    if not info["has_audio"]:
        warn.append(("erro", "Vídeo final sem áudio."))
        return warn
    lu = loudness(video)
    target = float(plan.get("loudness", -14))
    if lu["lufs"] is not None:
        lvl = "ok" if abs(lu["lufs"] - target) <= 1.5 else "aviso"
        warn.append((lvl, f"Loudness {lu['lufs']:.1f} LUFS (alvo {target:g})."))
    if lu["true_peak"] is not None and lu["true_peak"] > -0.5:
        warn.append(("aviso", f"Pico {lu['true_peak']:.1f} dBTP: pode distorcer no celular (alvo ≤ -1)."))
    return warn


def print_report(warn: list) -> int:
    icon = {"erro": "ERRO ", "aviso": "AVISO", "dica": "DICA ", "ok": "OK   "}
    order = {"erro": 0, "aviso": 1, "dica": 2, "ok": 3}
    for level, msg in sorted(warn, key=lambda x: order[x[0]]):
        print(f"{icon[level]} {msg}")
    errs = sum(1 for lv, _ in warn if lv == "erro")
    avisos = sum(1 for lv, _ in warn if lv == "aviso")
    if not errs and not avisos:
        print("Veredito: pode renderizar/publicar.")
    else:
        print(f"Veredito: mais uma passada ({errs} erro(s), {avisos} aviso(s)).")
    return 1 if errs else 0
