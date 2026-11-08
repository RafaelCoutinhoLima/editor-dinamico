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
MAX_DUR_HARD = 180.0     # Reels aceita até 3 min; acima disso não sobe como Reel
MIN_TEXT_PX = 55         # corpo mínimo do texto (px) num quadro de 1080 de largura
MIN_CONTRAST = 3.0       # contraste WCAG mínimo para texto grande
SCD_CHANGE, SCD_CUT = 5.0, 10.0  # score do scdet: mudança visual (punch-in conta) e corte de verdade
MAX_STILL_916 = 4.0      # 9:16 com fala: segundos máximos sem mudança visual medida no vídeo


def _platform_limit(fmt: str, dur: float, vertical: bool) -> tuple | None:
    """Limite de duração para Reels/Shorts/TikTok: aviso acima de 90 s, erro acima de 180 s."""
    if not vertical:
        return None
    if dur > MAX_DUR_HARD:
        return ("erro", f"Vídeo com {dur:.0f}s: acima de {MAX_DUR_HARD:.0f}s não entra como Reel. Divida em partes.")
    lim = MAX_DUR.get(fmt, 90.0)
    if dur > lim:
        return ("aviso", f"Vídeo com {dur:.0f}s. Para Reels/Shorts, acima de {lim:.0f}s perde retenção: corte "
                         "enrolação ou divida em partes.")
    return None


def _out_size(plan: dict) -> tuple | None:
    """Tamanho do vídeo final que o render gera para este plano (None se a fonte não existir)."""
    from .render import FORMATS, out_size

    fmt = plan.get("format", "9:16")
    if fmt in FORMATS:
        return FORMATS[fmt]
    if not Path(plan["source"]).exists():
        return None
    return out_size(plan, probe(plan["source"]), False)


def _rgb(c: str | None) -> tuple:
    """Cor ASS '&HAABBGGRR&' ou '#RRGGBB' -> (r, g, b)."""
    from .captions import ass_color

    h = re.sub(r"[^0-9A-Fa-f]", "", ass_color(c)[2:])[-6:].rjust(6, "0")
    return int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)


def _lum(rgb) -> float:
    """Luminância relativa (WCAG) de uma cor RGB 0-255 ou de um cinza (número)."""
    if isinstance(rgb, (int, float)):
        rgb = (rgb, rgb, rgb)
    lin = [(v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _text_items(plan: dict, W: int, H: int) -> list:
    """Textos que o render desenha (legenda e títulos), com corpo da fonte em px, borda, caixa e cores.
    Segue as mesmas contas de captions.build_ass."""
    from .captions import BLACK, STYLES, WHITE

    base = min(W, H)
    items = []
    cap = plan.get("captions")
    if cap and plan.get("words"):
        st = STYLES.get(cap.get("style", "hormozi"), STYLES["hormozi"])
        colors = [WHITE] + [c for c in (cap.get("active_color", st["active"]), cap.get("emphasis_color", st["emph"]))
                            if c]
        items.append({"kind": "legenda", "name": f"legenda ({cap.get('style', 'hormozi')})",
                      "size": int(base * st["size"] * float(cap.get("scale", 1.0))),
                      "border": max(1, int(base * st["outline"])), "edge": BLACK, "box": None,
                      "colors": colors, "y": float(cap.get("position", 0.7)), "times": None})
    for t in plan.get("titles") or []:
        custom = any(k in t for k in ("font", "size", "y", "color"))
        fs = int(base * float(t.get("size", 0.10))) if custom else int(base * 0.10)
        boxed = (not custom) or bool(t.get("box", False))
        items.append({"kind": "titulo", "name": f"título '{t['text']}'", "size": fs,
                      "border": max(2, fs // 14) if custom else int(base * 0.028), "edge": "&H00101010&",
                      "box": "&H00101010&" if boxed else None,
                      "colors": [t.get("color"), t.get("accent") or "&H0000E5FF&"] if "*" in t["text"]
                      else [t.get("color")],
                      "y": float(t.get("y", 0.15)) if custom else 0.12 + fs / (2 * H),
                      "times": (float(t.get("start", 0)), float(t.get("end", 2.5)))})
    return items


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
    lim = _platform_limit(fmt, total, fmt in MAX_DUR)
    if lim:
        w(*lim)
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

    # ------------------------------------------------ legibilidade (corpo da fonte no vídeo final)
    size = _out_size(plan)
    if size:
        W, H = size
        for it in _text_items(plan, W, H):
            # vertical: o vídeo ocupa a largura do celular, conta o px num quadro de 1080 de largura;
            # horizontal (tela deitada/TV): conta o px num quadro de 1080 de altura, com limite menor
            vert = H >= W
            px = it["size"] * 1080 / (W if vert else H)
            lim = MIN_TEXT_PX if vert else round(MIN_TEXT_PX * 0.75)
            if px < lim:
                ref = "largura" if vert else "altura"
                w("aviso", f"{it['name'][0].upper() + it['name'][1:]} com corpo de {px:.0f} px (em 1080 de {ref}): "
                           f"pequeno demais para ler no celular. Use pelo menos {lim} px (`scale` da legenda ou "
                           "`size` do título).")

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

    # ------------------------------------------------ voz
    if plan.get("words") and plan.get("audio", "source") == "source" and Path(plan["source"]).exists():
        v = plan.get("voice") or {}
        if not v.get("clean"):
            from .voice import noise_report

            nr = noise_report(plan["source"])
            if nr["snr_db"] is not None and nr["snr_db"] < 30:
                w("aviso", f"Fonte com ruído de fundo (fala só {nr['snr_db']} dB acima do ruído) e limpeza de voz "
                           "desligada. Ligue `\"voice\": {\"clean\": \"dfn\"}` (padrão do `edin plan`).")

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


BAND_W, BAND_H, BAND_STEP = 108, 192, 0.25


def _scan(video: str, has_audio: bool, bands: bool) -> dict:
    """Uma passada só do ffmpeg no vídeo final (reduzido para 320 px): blackdetect, freezedetect, scdet (score de
    mudança por quadro), ebur128 com pico real e LRA, silencedetect e, se pedir, os quadros a 4/s para find_bands."""
    import subprocess

    import numpy as np

    small = "scale=320:320:force_original_aspect_ratio=decrease:force_divisible_by=2"
    vchain = (f"{small},blackdetect=d=0.2:pix_th=0.05:pic_th=0.998,freezedetect=n=0.002:d=1.0,"
              "scdet=t=100,metadata=mode=print:key=lavfi.scd.score[vo]")
    if bands:
        fc = (f"[0:v]split=2[va][vb];[va]{vchain};"
              f"[vb]fps={1 / BAND_STEP},scale={BAND_W}:{BAND_H},format=gray[bands]")
    else:
        fc = f"[0:v]{vchain}"
    if has_audio:
        fc += ";[0:a]asplit=2[a1][a2];[a1]ebur128=peak=true:framelog=quiet[ao];[a2]silencedetect=n=-45dB:d=0.5[as]"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-filter_complex", fc]
    if bands:
        cmd += ["-map", "[bands]", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    cmd += ["-map", "[vo]"] + (["-map", "[ao]", "-map", "[as]"] if has_audio else []) + ["-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True)
    err = p.stderr.decode("utf-8", "replace")
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou na varredura do vídeo:\n{err[-1500:]}")

    out = {"black": [], "freeze": [], "silence": [], "scores": [], "lufs": None, "lra": None, "true_peak": None,
           "frames": None}
    t_frame, open_freeze, open_sil = 0.0, None, None
    for line in err.splitlines():
        if "pts_time:" in line and "frame:" in line:
            t_frame = float(line.rsplit("pts_time:", 1)[1].split()[0])
        elif "lavfi.scd.score=" in line:
            out["scores"].append((t_frame, float(line.rsplit("=", 1)[1])))
        elif "black_start:" in line:
            m = re.search(r"black_start:([\d.]+) black_end:([\d.]+)", line)
            if m:
                out["black"].append((float(m[1]), float(m[2])))
        elif "freeze_start:" in line:
            open_freeze = float(line.rsplit(":", 1)[1])
        elif "freeze_end:" in line and open_freeze is not None:
            out["freeze"].append((open_freeze, float(line.rsplit(":", 1)[1])))
            open_freeze = None
        elif "silence_start:" in line:
            open_sil = max(0.0, float(line.rsplit(":", 1)[1]))
        elif "silence_end:" in line and open_sil is not None:
            out["silence"].append((open_sil, float(line.split("silence_end:")[1].split("|")[0])))
            open_sil = None
    out["open_freeze"], out["open_silence"] = open_freeze, open_sil  # foram até o fim do arquivo
    summary = err.rsplit("Summary:", 1)[-1] if "Summary:" in err else ""
    for line in summary.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("I:", "LRA:", "Peak:"):
            key = {"I:": "lufs", "LRA:": "lra", "Peak:": "true_peak"}[parts[0]]
            try:
                out[key] = float(parts[1])
            except ValueError:
                pass
    if bands:
        raw, sz = p.stdout, BAND_W * BAND_H
        n = len(raw) // sz
        out["frames"] = np.frombuffer(raw[:n * sz], np.uint8).reshape(n, BAND_H, BAND_W).astype(float)
    return out


def _mp4_atoms(path: str, limit: int = 32) -> list:
    """Átomos de topo do MP4 na ordem do arquivo (para saber se o moov vem antes do mdat)."""
    import os

    size, pos, atoms = os.path.getsize(path), 0, []
    with open(path, "rb") as fh:
        while pos + 8 <= size and len(atoms) < limit:
            fh.seek(pos)
            h = fh.read(16)
            n, typ = int.from_bytes(h[:4], "big"), h[4:8].decode("latin1")
            if n == 1:
                n = int.from_bytes(h[8:16], "big")
            elif n == 0:
                n = size - pos
            if n < 8:
                break
            atoms.append(typ)
            pos += n
    return atoms


def _tech_checks(plan: dict, video: str, info: dict, metrics: dict) -> list:
    """ffprobe técnico: resolução do formato, yuv420p, fps constante, AAC 48 kHz, +faststart, áudio x vídeo e
    duração para a plataforma."""
    import json
    import subprocess

    import numpy as np

    warn = []
    d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", video],
                                  capture_output=True, text=True).stdout or "{}")
    streams = d.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = plan.get("format", "9:16")
    W, H = info["w"], info["h"]
    tech = {"resolucao": f"{W}x{H}", "pix_fmt": v.get("pix_fmt"), "codec_video": v.get("codec_name"),
            "fps": round(info["fps"], 3)}

    exp = _out_size(plan)
    if exp and (W, H) != tuple(exp):
        ew, eh = exp
        if abs(W * 2 - ew) <= 2 and abs(H * 2 - eh) <= 2:
            warn.append(("erro", f"Resolução {W}x{H} é a do rascunho; o formato {fmt} pede {ew}x{eh}. Renderize sem "
                                  "--draft antes de publicar."))
        elif abs(W / H - ew / eh) > 0.01:
            warn.append(("erro", f"Proporção errada: {W}x{H}, o formato {fmt} pede {ew}x{eh}."))
        else:
            warn.append(("aviso", f"Resolução {W}x{H}; o formato {fmt} pede {ew}x{eh}."))
    if v.get("pix_fmt") and v["pix_fmt"] != "yuv420p":
        warn.append(("aviso", f"Pixel {v['pix_fmt']}: use yuv420p (8 bits, 4:2:0). Outros formatos ficam pretos ou "
                              "lavados em parte dos celulares e são reconvertidos com perda pelas redes."))

    # fps constante: intervalo entre quadros pelos tempos dos pacotes (só lê o contêiner, é rápido)
    pk = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                         "-of", "csv=p=0", video], capture_output=True, text=True).stdout.split()
    pts = np.sort(np.array([float(x.strip(",")) for x in pk if x.strip(",") not in ("", "N/A")]))
    if len(pts) > 10:
        dt = np.diff(pts)
        med = float(np.median(dt))
        irregular = float(np.mean(np.abs(dt - med) > 0.25 * med)) if med > 0 else 1.0
        tech["vfr_frac"] = round(irregular, 4)
        if irregular > 0.01:
            warn.append(("aviso", f"Taxa de quadros variável ({irregular:.0%} dos quadros fora do ritmo de "
                                  f"{1 / med:.2f} fps). Exporte em fps constante (`-fps_mode cfr` / `-r 30`): VFR "
                                  "dessincroniza áudio e engasga no upload."))

    if a is None:
        tech["audio"] = None
    else:
        sr = int(a.get("sample_rate") or 0)
        tech["audio"] = f"{a.get('codec_name')} {sr} Hz"
        if a.get("codec_name") != "aac" or sr != 48000:
            warn.append(("aviso", f"Áudio {a.get('codec_name')} {sr} Hz: entregue AAC 48 kHz."))
        vd, ad = float(v.get("duration") or 0), float(a.get("duration") or 0)
        if vd and ad:
            diff = abs(vd - ad)
            tech["av_diff_ms"] = round(diff * 1000)
            if diff >= 0.05:
                warn.append(("aviso", f"Áudio ({ad:.3f}s) e vídeo ({vd:.3f}s) com {diff * 1000:.0f} ms de diferença: "
                                      "o fim fica mudo ou congelado. Renderize com `-shortest`."))

    atoms = _mp4_atoms(video) if video.lower().endswith((".mp4", ".mov", ".m4v")) else []
    if "moov" in atoms and "mdat" in atoms:
        fast = atoms.index("moov") < atoms.index("mdat")
        tech["faststart"] = fast
        if not fast:
            warn.append(("aviso", "MP4 sem +faststart (moov depois do mdat): o vídeo só começa a tocar depois de "
                                  "baixar inteiro. Remuxe com `ffmpeg -i in.mp4 -c copy -movflags +faststart out.mp4`."))

    # duração para a plataforma: só repete aqui se o arquivo cair numa faixa diferente da do plano
    vertical = H > W
    total = sum(seg_out_dur(s) for s in plan["segments"])
    lim_file = _platform_limit(fmt, info["duration"], vertical)
    lim_plan = _platform_limit(fmt, total, fmt in MAX_DUR)
    if lim_file and (not lim_plan or lim_plan[0] != lim_file[0]):
        warn.append(lim_file)
    metrics["tecnico"] = tech
    return warn


def _overlap(a: tuple, b: tuple) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def _sample_luma(video: str, t: float, y0: float, y1: float) -> float | None:
    """Mediana da luminância (0-255) de uma faixa horizontal (y0..y1 normalizados, 80% central da largura) no
    instante t. A mediana ignora o próprio texto, que ocupa a minoria dos pixels."""
    import subprocess

    import numpy as np

    w, h = 180, 320
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf",
                          f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    if len(raw) < w * h:
        return None
    f = np.frombuffer(raw[:w * h], np.uint8).reshape(h, w)
    a, b = max(0, int(y0 * h)), min(h, max(int(y0 * h) + 1, int(y1 * h)))
    return float(np.median(f[a:b, int(w * 0.1):int(w * 0.9)]))


def _contrast_checks(plan: dict, video: str, W: int, H: int, metrics: dict) -> list:
    """Contraste do texto. Borda grossa ou caixa escura garantem leitura em qualquer fundo; só quando a cor do texto
    não contrasta com a própria borda/caixa é que o fundo do vídeo é medido na região do texto."""
    warn, base = [], min(W, H)
    for it in _text_items(plan, W, H):
        guard = it["box"] or (it["edge"] if it["border"] * 1080 / base >= 3 else None)
        weak = [c for c in it["colors"] if not guard or _contrast(_rgb(c), _rgb(guard)) < MIN_CONTRAST]
        if not weak:
            continue
        if it["times"]:
            times = [(it["times"][0] + it["times"][1]) / 2]
        else:  # legenda: amostra alguns instantes ao longo do vídeo
            dur = metrics.get("duracao") or sum(seg_out_dur(s) for s in plan["segments"])
            times = [dur * (k + 0.5) / 6 for k in range(6)]
        half = it["size"] * 0.75 / H
        worst = None
        for t in times:
            bg = _sample_luma(video, t, it["y"] - half, it["y"] + half)
            if bg is None:
                continue
            c = min(_contrast(_rgb(col), bg) for col in weak)
            if worst is None or c < worst[0]:
                worst = (c, t)
        if worst and worst[0] < MIN_CONTRAST:
            warn.append(("aviso", f"{it['name'][0].upper() + it['name'][1:]}: contraste {worst[0]:.1f}:1 com o fundo "
                                  f"em {fmt_time(worst[1])} (mínimo {MIN_CONTRAST:g}:1). Troque a cor do texto ou "
                                  "ponha caixa (`box: true`)."))
    return warn


def _overlay_events(plan: dict, dur: float) -> list:
    """Entradas e saídas de títulos e overlays de motion (no tempo de saída). Cards que deslizam para dentro mudam a
    tela sem que o scdet (diferença entre quadros vizinhos) perceba, então contam como mudança visual pelo plano."""
    ev = []
    for t in plan.get("titles") or []:
        ev += [float(t.get("start", 0)), float(t.get("end", 2.5))]
    if plan.get("motion"):
        try:
            from .remotion_bridge import _motion_cfg, resolve_overlays

            items, _ = _motion_cfg(plan)
            ovs, _ = resolve_overlays(items, remap_words(plan), dur, plan.get("captions"))
            for o in ovs:
                if o.get("type") != "caption-pill":
                    ev += [float(o["start"]), float(o["end"])]
        except (Exception, SystemExit):  # motion inválido: o `edin motion` já acusa; aqui só não conta
            pass
    return sorted(t for t in ev if 0 < t < dur)


def audit_video(plan_path: str, video: str, metrics: dict | None = None) -> list:
    """Confere o arquivo final. `metrics` (opcional) recebe as medidas brutas, para o `--json`."""
    plan = load_plan(plan_path)
    m = metrics if metrics is not None else {}
    warn = []
    info = probe(video)
    dur = info["duration"]
    m["duracao"] = round(dur, 3)
    fmt = plan.get("format", "9:16")
    speech = bool(plan.get("words")) and plan.get("audio", "source") == "source"
    total = sum(seg_out_dur(s) for s in plan["segments"])
    if abs(dur - total) > 0.25:
        warn.append(("aviso", f"Duração do arquivo {dur:.2f}s difere do plano {total:.2f}s."))
    if not info["has_audio"]:
        warn.append(("erro", "Vídeo final sem áudio."))

    warn += _tech_checks(plan, video, info, m)
    vertical = info["h"] > info["w"]
    sc = _scan(video, info["has_audio"], bands=vertical)

    # ------------------------------------------------ faixas (vertical)
    if vertical:
        # faixa no topo atrás de um título no topo é intencional (barra do título): não conta
        tops = [(float(t.get("start", 0)), float(t.get("end", 2.5))) for t in plan.get("titles") or []
                if float(t.get("y", 0.15)) < 0.35]
        bands = find_bands(video, ignore_top=tops, frames=sc["frames"])
        m["faixas"] = [list(b) for b in bands]
        for a, b, lado in bands[:12]:
            warn.append(("erro", f"Faixa na {lado} de {fmt_time(a)} a {fmt_time(b)}: região lisa de cor diferente da cena "
                                 "(vídeo encaixado ou fundo esticado errado). Abra esse quadro e corrija o `fit`."))
        if len(bands) > 12:
            warn.append(("erro", f"... e mais {len(bands) - 12} trechos com faixa."))

    # ------------------------------------------------ quadro preto
    m["preto"] = [[round(a, 2), round(b, 2)] for a, b in sc["black"]]
    for a, b in sc["black"]:
        d = b - a
        if a >= dur - 1.0:  # fade final no último segundo é normal
            continue
        if a < 0.05 and d >= 0.3:
            warn.append(("erro", f"Abre no preto: {d:.1f}s de tela preta no começo. A imagem tem que estar na tela "
                                 "desde o 1º quadro."))
        elif d >= (0.5 if speech else 1.0):
            warn.append(("erro", f"Tela preta de {d:.1f}s em {fmt_time(a)}-{fmt_time(b)} (segmento faltando, b-roll "
                                 "quebrado ou fade longo). Abra esse trecho."))

    # ------------------------------------------------ vídeo congelado
    freezes = list(sc["freeze"]) + ([(sc["open_freeze"], dur)] if sc["open_freeze"] is not None else [])
    m["congelado"] = [[round(a, 2), round(b, 2)] for a, b in freezes]
    lim_fz = 1.5 if speech else 4.0
    for a, b in freezes:
        d = b - a
        if sum(_overlap((a, b), x) for x in sc["black"]) > 0.5 * d:
            continue  # já contado como tela preta
        if b >= dur - 0.1 and d <= 2.5:
            continue  # quadro final segurado
        if d > lim_fz:
            warn.append(("aviso", f"Imagem congelada por {d:.1f}s em {fmt_time(a)}-{fmt_time(b)}"
                                  f"{' com a fala correndo' if speech else ''}. Confira a fonte do trecho (imagem "
                                  "parada, quadro duplicado ou b-roll curto demais)."))

    # ------------------------------------------------ áudio: loudness, pico real, LRA, silêncio
    if info["has_audio"]:
        m["audio"] = {"lufs": sc["lufs"], "true_peak": sc["true_peak"], "lra": sc["lra"]}
        target = float(plan.get("loudness", -14))
        if sc["lufs"] is not None:
            lvl = "ok" if abs(sc["lufs"] - target) <= 1.5 else "aviso"
            extra = f", pico real {sc['true_peak']:.1f} dBTP" if sc["true_peak"] is not None else ""
            extra += f", LRA {sc['lra']:.1f} LU" if sc["lra"] is not None else ""
            warn.append((lvl, f"Loudness {sc['lufs']:.1f} LUFS (alvo {target:g}){extra}."))
        if sc["true_peak"] is not None and sc["true_peak"] > -0.5:
            warn.append(("aviso", f"Pico real {sc['true_peak']:.1f} dBTP: pode distorcer no celular (alvo ≤ -1)."))
        if sc["lra"] is not None and sc["lra"] > 15:
            warn.append(("aviso", f"Variação de volume (LRA) de {sc['lra']:.1f} LU: trechos baixos somem no celular "
                                  "e os altos assustam. Comprima a voz ou baixe a música nos picos (alvo ≤ 15, fala "
                                  "≤ 8)."))
        sils = list(sc["silence"]) + ([(sc["open_silence"], dur)] if sc["open_silence"] is not None else [])
        m["silencio"] = [[round(a, 2), round(b, 2)] for a, b in sils]
        if speech:
            for a, b in sils:
                d = b - a
                if a < 0.05 and d > 0.5:
                    warn.append(("aviso", f"Abre com {d:.1f}s de silêncio: o primeiro som tem que entrar em 0,15s."))
                elif b >= dur - 0.3:
                    if d > 2.0:
                        warn.append(("dica", f"Final mudo de {d:.1f}s: corte o fim em {fmt_time(a + 0.4)}."))
                elif d > 1.2:
                    warn.append(("aviso", f"Silêncio de {d:.1f}s em {fmt_time(a)}-{fmt_time(b)} no meio da fala: "
                                          "pausa que o corte deixou passar. Encurte o segmento."))

    # ------------------------------------------------ ritmo medido (scdet)
    scores = sc["scores"]
    if scores:
        changes = [t for t, s in scores if s >= SCD_CHANGE and t > 0]
        cuts = sum(1 for t, s in scores if s >= SCD_CUT and t > 0)
        pts = [0.0] + sorted(set(changes + _overlay_events(plan, dur))) + [dur]
        gaps = sorted(((b - a, a, b) for a, b in zip(pts, pts[1:])), reverse=True)
        cpm = cuts / dur * 60 if dur else 0.0
        m["ritmo"] = {"cortes": cuts, "cortes_por_minuto": round(cpm, 1), "mudancas": len(changes),
                      "maior_trecho_parado": round(gaps[0][0], 2) if gaps else None,
                      "maior_trecho_parado_em": [round(gaps[0][1], 2), round(gaps[0][2], 2)] if gaps else None}
        if gaps:
            warn.append(("ok", f"Ritmo medido: {cpm:.0f} cortes/min, maior trecho sem mudança visual "
                               f"{gaps[0][0]:.1f}s ({fmt_time(gaps[0][1])}-{fmt_time(gaps[0][2])})."))
        if fmt == "9:16" and speech:
            # o crítico do plano já acusa planos parados longos; aqui só o que ele não viu (ou a câmera lenta demais)
            limit_plan = MAX_SHOT["9:16"]
            shots = _shots(plan)
            flagged = [(s["start"], s["end"]) for s in shots
                       if s["end"] - s["start"] > limit_plan * (1.6 if s["moving"] else 1.0)]
            moving = [(s["start"], s["end"]) for s in shots if s["moving"]]
            n = 0
            for d, a, b in gaps:
                lim = MAX_STILL_916 * (1.6 if sum(_overlap((a, b), x) for x in moving) > 0.5 * d else 1.0)
                if d <= lim or n >= 3:
                    continue
                if any(_overlap((a, b), x) > 0.5 * d for x in flagged):
                    continue
                n += 1
                warn.append(("aviso", f"{d:.1f}s sem mudança visual em {fmt_time(a)}-{fmt_time(b)} (medido no vídeo). "
                                      f"Em 9:16 com fala, algo muda a cada {MAX_STILL_916:g}s no máximo: punch-in, "
                                      "b-roll ou corte."))

    # ------------------------------------------------ contraste do texto
    warn += _contrast_checks(plan, video, info["w"], info["h"], m)
    return warn


def find_bands(video: str, step: float = BAND_STEP, ignore_top: list | None = None, frames=None) -> list:
    """Varre o vídeo (4 quadros/s) atrás de faixas: região lisa no topo ou na base, com >= 8% da altura e cor muito
    diferente do centro da cena (letterbox, borda esticada errada, fundo preto embaixo de tela branca).
    `frames` (opcional) são os quadros já extraídos por `_scan` (4/s, 108x192, cinza).
    Devolve [(início, fim, 'topo'|'base')] agrupados."""
    import subprocess

    import numpy as np

    w, h = BAND_W, BAND_H
    if frames is None:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={1 / step},scale={w}:{h}",
                              "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
        n = len(raw) // (w * h)
        frames = np.frombuffer(raw[:n * w * h], np.uint8).reshape(n, h, w).astype(float)
    hits = []
    for k, f in enumerate(frames):
        m, sd = f.mean(axis=1), f.std(axis=1)
        centro = float(np.median(m[int(h * 0.3):int(h * 0.7)]))
        for lado, rows in (("topo", range(h)), ("base", range(h - 1, -1, -1))):
            rows = list(rows)
            ref, alt = m[rows[0]], 0
            for y in rows:
                if sd[y] < 8 and abs(m[y] - ref) < 6:
                    alt += 1
                else:
                    break
            t = k * step
            if lado == "topo" and any(a <= t <= b for a, b in ignore_top or []):
                continue
            if alt >= 0.08 * h and abs(ref - centro) > 60:
                hits.append((t, lado))
    out = []
    for t, lado in hits:
        if out and out[-1][2] == lado and t - out[-1][1] <= step * 1.5:
            out[-1][1] = t + step
        else:
            out.append([t, t + step, lado])
    return [tuple(x) for x in out if x[1] - x[0] >= step * 2]  # ignora 1 quadro solto (transição)


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


def report_json(warn: list, metrics: dict | None = None, **extra) -> int:
    """Mesmo relatório em JSON (para os agentes): itens ordenados por gravidade, contagens, veredito e medidas."""
    import json

    order = {"erro": 0, "aviso": 1, "dica": 2, "ok": 3}
    errs = sum(1 for lv, _ in warn if lv == "erro")
    avisos = sum(1 for lv, _ in warn if lv == "aviso")
    out = {**extra, "veredito": "publicar" if not errs and not avisos else "mais uma passada",
           "erros": errs, "avisos": avisos,
           "itens": [{"nivel": lv, "msg": msg} for lv, msg in sorted(warn, key=lambda x: order[x[0]])],
           "medidas": metrics or {}}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 1 if errs else 0
