"""Caçador de cortes: acha os melhores trechos de um vídeo longo para shorts e faz o cold open.

`edin hunt video.words.json` gera candidatos de 20 a 60 s com sinais objetivos (frase completa nas bordas,
palavras por segundo, energia e variação de tom da voz, perguntas, números, palavras de gancho) e uma nota
objetiva de 0 a 100. A rubrica estilo OpusClip (Hook, Flow, Value, Trend, 0 a 25 cada) quem preenche é o agente
`cacador-de-cortes`, lendo os candidatos e a transcrição: a nota objetiva só ordena o que vale a pena ler.

Cold open (`edin plan ... --range A-B --cold-open`): a frase mais forte do trecho (1 a 3 s) entra repetida no
início, antes do contexto, como segmento próprio com punch-in. As legendas seguem certas porque remap_words
trata cada segmento fora de ordem como um bloco novo.
"""
from __future__ import annotations

import math
import re
import unicodedata
from pathlib import Path

import numpy as np

from .utils import fmt_time, load_json, parse_range, save_json

# ------------------------------------------------------------------ léxico (português)

# ganchos fortes: prometem um segredo, um erro, uma virada ou falam direto com quem assiste
HOOKS_FORTES = [
    r"o (maior )?erro", r"os erros", r"ningu[eé]m (te |nos |lhe )?(conta|fala|diz|sabe|percebe)", r"pare de",
    r"o segredo", r"a verdade", r"a mentira", r"o problema", r"o pior", r"o melhor", r"o mais importante",
    r"voc[eê] (precisa|n[aã]o sabe|sabia|est[aá] errad)", r"nunca mais", r"cuidado", r"aten[cç][aã]o",
    r"isso muda", r"(é|e) um mito", r"a maioria (das pessoas)?", r"o que (ningu[eé]m|poucos)", r"n[aã]o fa[cç]a",
    r"por que (voc[eê]|a gente|ningu[eé]m)", r"(o )?que eu (aprendi|descobri)", r"a [uú]nica", r"o [uú]nico",
    r"sem (isso|essa)", r"(é|e) simples", r"mudou (a minha|tudo)", r"pouca gente", r"todo mundo (acha|pensa|faz)",
]
# ganchos fracos: tensão, contraste, opinião
HOOKS_FRACOS = [
    r"nunca", r"sempre", r"ningu[eé]m", r"todo mundo", r"importante", r"necess[aá]rio", r"precisa(mos)?",
    r"errad[oa]", r"perigo", r"incr[ií]vel", r"absurd[oa]", r"impressionante", r"fundamental", r"desafio",
    r"verdade", r"mito", r"problema", r"segredo", r"pior", r"melhor", r"de verdade", r"na real", r"olha",
    r"imagina", r"pensa (bem|comigo)", r"sabe (o que|por que)", r"o que (é|e) que", r"por que",
]
# depende de contexto que o espectador do short não viu
DEPENDE = [
    r"como eu (falei|disse|comentei|mostrei)", r"como (o|a) \w+ (j[aá] )?(colocou|falou|disse)",
    r"(isso|aquilo) que eu (falei|disse)", r"voltando", r"nesse slide", r"essa imagem", r"essas imagens",
    r"aqui (ó|olha)", r"como a gente viu", r"l[aá] atr[aá]s", r"antes eu", r"nessa apresenta[cç][aã]o",
]
CONECTIVOS = {"e", "mas", "então", "entao", "aí", "ai", "porque", "que", "né", "ne", "tipo", "ou", "pois", "bom",
              "daí", "dai", "enfim", "inclusive", "também", "tambem", "assim", "aliás", "alias", "nem"}
# preposições: no começo de frase inteira ("Em primeiro lugar") tudo bem; no meio dela, é pedaço solto
PREPOSICOES = {"de", "da", "do", "das", "dos", "na", "no", "nas", "nos", "pelo", "pela", "com", "para", "pra", "em",
               "ao", "aos", "à", "às", "sobre", "entre"}
# palavras que não podem fechar uma frase (frase cortada no meio)
FIM_RUIM = {"de", "da", "do", "das", "dos", "a", "o", "as", "os", "um", "uma", "e", "que", "para", "pra", "com",
            "em", "na", "no", "por", "pelo", "pela", "se", "mas", "ou", "como", "mais", "muito", "nos", "nas", "ao",
            "é", "foi", "ser", "são", "seu", "sua", "meu", "minha", "esse", "essa", "este", "esta", "isso"}
NUMEROS = {"dois", "duas", "três", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
           "vinte", "trinta", "quarenta", "cinquenta", "cem", "cento", "mil", "milhão", "milhões", "bilhão",
           "bilhões", "metade", "dobro", "triplo", "primeiro", "primeira", "segundo", "terceiro", "porcento"}


def _plain(t: str) -> str:
    return unicodedata.normalize("NFKC", t.lower()).strip()


def _bare(w: str) -> str:
    return re.sub(r"[^\wà-ú-]", "", _plain(w))


def _count(patterns: list, text: str) -> list:
    t = " " + _plain(text) + " "
    return [m.group(0).strip() for p in patterns for m in re.finditer(r"(?<![\wà-ú])" + p + r"(?![\wà-ú])", t)]


def _has_number(text: str) -> int:
    t = _plain(text)
    return len(re.findall(r"\d+", t)) + sum(1 for w in re.findall(r"[\wà-ú]+", t) if w in NUMEROS) + t.count("%")


# ------------------------------------------------------------------ áudio: energia e tom

class AudioFeats:
    """Energia (dB) e tom (semitons, via YIN) do áudio a cada 50 ms. Sem librosa ou sem áudio: ok=False."""

    HOP = 0.05

    def __init__(self, src: str | None, offset: float = 0.0, duration: float | None = None):
        self.ok, self.offset = False, offset
        if not src or not Path(src).exists():
            return
        try:
            import librosa

            from .transcribe import _load_audio

            sr = 16000
            x = _load_audio(src, sr)
            a = int(offset * sr)
            x = x[a:a + int(duration * sr)] if duration else x[a:]
            hop, win = int(sr * self.HOP), 1024
            if len(x) < win * 4:
                return
            rms = librosa.feature.rms(y=x, frame_length=win, hop_length=hop)[0]
            self.db = 20 * np.log10(rms + 1e-9)
            f0 = librosa.yin(x, fmin=70, fmax=400, sr=sr, frame_length=win * 2, hop_length=hop)
            n = min(len(f0), len(self.db))
            self.db, f0 = self.db[:n], f0[:n]
            voiced = self.db > np.percentile(self.db, 40)
            st = 12 * np.log2(np.maximum(f0, 1) / 100.0)
            self.st = np.where(voiced & (f0 > 72) & (f0 < 395), st, np.nan)
            ref = self.db[voiced]
            self.mu, self.sd = float(ref.mean()), float(ref.std() + 1e-6)
            self.ok = True
        except Exception as e:  # noqa: BLE001 (sem librosa, áudio estranho...: segue só com o texto)
            print(f"[edin] Aviso: sem análise de áudio ({e}). Nota só pelo texto.")

    def _sl(self, s: float, e: float) -> slice:
        a = int(max(0.0, s - self.offset) / self.HOP)
        b = int(max(0.0, e - self.offset) / self.HOP) + 1
        return slice(a, max(a + 1, b))

    def energy_z(self, s: float, e: float) -> float:
        """Energia média do trecho em desvios-padrão acima da média da fala do vídeo."""
        if not self.ok:
            return 0.0
        seg = self.db[self._sl(s, e)]
        seg = seg[seg > self.mu - 2 * self.sd]  # só onde tem voz
        return float((seg.mean() - self.mu) / self.sd) if len(seg) else -1.0

    def pitch_var(self, s: float, e: float) -> float:
        """Variação de tom (desvio-padrão em semitons). Voz monótona < 2; expressiva > 3."""
        if not self.ok:
            return 0.0
        seg = self.st[self._sl(s, e)]
        seg = seg[~np.isnan(seg)]
        if len(seg) < 5:
            return 0.0
        lo, hi = np.percentile(seg, [5, 95])  # descarta oitavas erradas do YIN
        seg = seg[(seg >= lo) & (seg <= hi)]
        return float(seg.std())


# ------------------------------------------------------------------ frases

def _ends_sentence(w: dict) -> bool:
    return w["w"][-1:] in ".?!…"


def sentences(words: list) -> list:
    """Frases: pontuação final, pausa >= 0,6 s, ou pausa >= 0,3 s seguida de maiúscula (Whisper sem pontuação)."""
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        gap = (nxt["s"] - w["e"]) if nxt else 9.0
        cap = bool(nxt) and nxt["w"][:1].isupper() and gap >= 0.3
        # "Em <pausa> primeiro lugar": palavra de ligação não fecha frase, mesmo com pausa
        if _ends_sentence(w) or ((gap >= 0.6 or cap) and _bare(w["w"]) not in FIM_RUIM):
            out.append(cur)
            cur = []
        elif gap >= 0.6 and w["w"][:1].isupper() and len(cur) > 1:  # "... humanos Em <pausa> primeiro lugar"
            out.append(cur[:-1])
            cur = [w]
    if cur:
        out.append(cur)
    res = []
    for ws in out:
        res.append({"i0": ws[0]["i"], "i1": ws[-1]["i"], "s": ws[0]["s"], "e": ws[-1]["e"],
                    "texto": " ".join(w["w"] for w in ws), "words": ws})
    for a, b in zip(res, res[1:]):
        a["gap_depois"] = b["s"] - a["e"]
        b["gap_antes"] = b["s"] - a["e"]
    if res:
        res[0]["gap_antes"] = 9.0
        res[-1]["gap_depois"] = 9.0
    return res


def _start_quality(sent: dict, prev_word: dict | None) -> tuple:
    """(pontos 0-10, motivo) da borda de início."""
    w0 = sent["words"][0]["w"]
    first = _bare(w0)
    # minúscula depois de pausa sem pontuação costuma ser meio de frase (pausa para respirar)
    clean = prev_word is None or _ends_sentence(prev_word) or (sent.get("gap_antes", 9) >= 0.5 and w0[:1].isupper())
    pts = 10 if clean else 4
    bad = first in CONECTIVOS or (first in PREPOSICOES and not clean)
    if re.match(r"(nesse|neste|desse|dessa) sentido|por isso|al[eé]m disso|dessa forma|com isso|da[ií] ",
                _plain(sent["texto"])):
        bad, first = True, " ".join(sent["texto"].split()[:2]).rstrip(",")
    if bad:
        pts -= 6
    return max(pts, 0), ("limpo" if clean else "meio de frase") + (f", começa com '{first}'" if bad else "")


def _end_quality(sent: dict) -> tuple:
    last = sent["words"][-1]
    if _bare(last["w"]) in FIM_RUIM:
        return 0, f"termina em '{_bare(last['w'])}'"
    if last["w"][-1:] in ".!?…":
        return 10, "pontuação"
    if sent.get("gap_depois", 9) >= 0.6:
        return 7, "pausa"
    return 3, "pausa curta"


# ------------------------------------------------------------------ frase forte (gancho / cold open)

def phrase_score(ws: list, audio: AudioFeats, at_sentence_start: bool) -> tuple:
    """Nota 0-100 de uma frase curta para abrir o vídeo, e os motivos."""
    txt = " ".join(w["w"] for w in ws)
    dur = ws[-1]["e"] - ws[0]["s"]
    fortes, fracos = _count(HOOKS_FORTES, txt), _count(HOOKS_FRACOS, txt)
    pts, why = 20.0, []
    if fortes:
        pts += 30
        why.append("gancho: " + ", ".join(sorted(set(fortes))))
    elif fracos:
        pts += 12
        why.append("tensão: " + ", ".join(sorted(set(fracos))[:3]))
    if "?" in txt:
        pts += 14
        why.append("pergunta")
    if "!" in txt:
        pts += 8
    if _has_number(txt):
        pts += 12
        why.append("número")
    if _count(DEPENDE, txt):
        pts -= 25
    first, last = _bare(ws[0]["w"]), _bare(ws[-1]["w"])
    if first in CONECTIVOS or (first in PREPOSICOES and not at_sentence_start):  # "de movimentos sociais"
        pts -= 18
    elif not at_sentence_start and not ws[0]["w"][:1].isupper():
        pts -= 8
    if last in FIM_RUIM:
        pts -= 30
    if _ends_sentence(ws[-1]):
        pts += 8
    if at_sentence_start:
        pts += 8
        if _ends_sentence(ws[-1]):  # frase inteira
            pts += 8
            why.append("frase inteira")
    if audio.ok:
        ez, pv = audio.energy_z(ws[0]["s"], ws[-1]["e"]), audio.pitch_var(ws[0]["s"], ws[-1]["e"])
        pts += max(-10.0, min(15.0, ez * 10))
        pts += max(-5.0, min(10.0, (pv - 2.0) * 4))
        if ez > 0.6:
            why.append(f"voz forte (+{ez:.1f}σ)")
        if pv > 3.2:
            why.append(f"tom variado ({pv:.1f} st)")
    if not 1.0 <= dur <= 3.2:
        pts -= 15
    if len(ws) < 3:
        pts -= 10
    return max(0.0, min(100.0, pts)), why


def best_phrase(words: list, audio: AudioFeats, t0: float, t1: float, skip_first: float = 4.0,
                min_d: float = 1.0, max_d: float = 3.0) -> dict | None:
    """Frase de 1 a 3 s com a maior nota dentro de [t0, t1], começando e terminando em borda natural
    (pontuação, vírgula ou pausa). Ignora os primeiros `skip_first` s: ela já abriria o vídeo."""
    ws = [w for w in words if w["s"] >= t0 - 0.05 and w["e"] <= t1 + 0.05]
    if len(ws) < 3:
        return None

    def gap(k):  # pausa depois de ws[k]
        return ws[k + 1]["s"] - ws[k]["e"] if k + 1 < len(ws) else 9.0

    def is_start(k):
        return k == 0 or ws[k - 1]["w"][-1:] in ".,;:?!…" or gap(k - 1) >= 0.2

    def is_end(k):
        return ws[k]["w"][-1:] in ".,;:?!…" or gap(k) >= 0.2

    best = None
    for a in range(len(ws)):
        if ws[a]["s"] < t0 + skip_first or not is_start(a):
            continue
        for b in range(a + 1, len(ws)):
            d = ws[b]["e"] - ws[a]["s"]
            if d > max_d + 0.2:
                break
            if d < min_d or not is_end(b) or any(gap(k) > 0.7 for k in range(a, b)):
                continue
            sent_start = a == 0 or ws[a - 1]["w"][-1:] in ".?!…" or (gap(a - 1) >= 0.5 and ws[a]["w"][:1].isupper())
            sc, why = phrase_score(ws[a:b + 1], audio, sent_start)
            if best is None or sc > best["nota"]:
                best = {"i0": ws[a]["i"], "i1": ws[b]["i"], "start": ws[a]["s"], "end": ws[b]["e"],
                        "texto": " ".join(w["w"] for w in ws[a:b + 1]), "nota": round(sc, 1), "motivos": why}
    return best


# ------------------------------------------------------------------ candidatos

def _rng_str(s: float, e: float) -> str:
    return f"{math.floor(s * 100) / 100:.2f}-{math.ceil(e * 100) / 100:.2f}"


def _window_signals(sents: list, a: int, b: int, words_by_i: dict, audio: AudioFeats) -> dict:
    ss = sents[a:b + 1]
    ws = [w for s in ss for w in s["words"]]
    s0, e0 = ws[0]["s"], ws[-1]["e"]
    dur = e0 - s0
    txt = " ".join(s["texto"] for s in ss)
    gancho = ss[0]["texto"] if ss[0]["e"] - s0 >= 1.2 or len(ss) == 1 else ss[0]["texto"] + " " + ss[1]["texto"]
    head = [w for w in ws if w["s"] < s0 + 3.0]
    head_txt = " ".join(w["w"] for w in head)
    pauses = [ws[k + 1]["s"] - ws[k]["e"] for k in range(len(ws) - 1)]
    dead = sum(p for p in pauses if p > 0.7)
    ini_pts, ini_why = _start_quality(ss[0], words_by_i.get(ws[0]["i"] - 1))
    fim_pts, fim_why = _end_quality(ss[-1])
    sig = {
        "inicio": ini_why, "fim": fim_why,
        "palavras_por_s": round(len(ws) / dur, 2),
        "silencio_morto_s": round(dead, 1),
        "perguntas": txt.count("?"),
        "numeros": _has_number(txt),
        "ganchos": sorted(set(_count(HOOKS_FORTES, txt))),
        "ganchos_no_inicio": sorted(set(_count(HOOKS_FORTES, head_txt) + _count(HOOKS_FRACOS, head_txt))),
        "tensao": len(_count(HOOKS_FRACOS, txt)),
        "depende_de_contexto": sorted(set(_count(DEPENDE, txt))),
    }
    if audio.ok:
        sig["energia_z"] = round(audio.energy_z(s0, e0), 2)
        sig["energia_inicio_z"] = round(audio.energy_z(s0, min(e0, s0 + 3.0)), 2)
        sig["tom_var_st"] = round(audio.pitch_var(s0, e0), 2)
        # picos: palavras bem acima da média (ênfase natural da fala)
        sig["picos"] = sum(1 for w in ws if w["e"] - w["s"] >= 0.12 and audio.energy_z(w["s"], w["e"]) > 1.2)

    # ---- nota objetiva (0-100)
    pts = {}
    # gancho (0-30): o que se ouve nos primeiros 3 s
    g = 6 * min(len(sig["ganchos_no_inicio"]), 2) + (8 if "?" in head_txt else 0) + (5 if _has_number(head_txt) else 0)
    g += 10 if _count(HOOKS_FORTES, head_txt) else 0
    if audio.ok:
        g += max(-4.0, min(6.0, sig["energia_inicio_z"] * 6))
    pts["gancho"] = max(0.0, min(30.0, g))
    # completude (0-20): começa e termina em frase inteira, sem depender do resto do vídeo
    c = ini_pts + fim_pts - 8 * len(sig["depende_de_contexto"])
    pts["completude"] = max(0.0, min(20.0, c))
    # ritmo (0-15): 2,3 a 3,6 palavras/s é fala viva em português; silêncio morto derruba
    wps = sig["palavras_por_s"]
    r = 15 - max(0.0, 2.3 - wps) * 10 - max(0.0, wps - 3.8) * 6 - dead * 2
    pts["ritmo"] = max(0.0, min(15.0, r))
    # voz (0-20): energia e variação de tom acima da média do próprio vídeo
    if audio.ok:
        v = 10 + sig["energia_z"] * 8 + (sig["tom_var_st"] - 2.5) * 3 + min(sig["picos"] / max(dur / 10, 1), 3) * 1.5
        pts["voz"] = max(0.0, min(20.0, v))
    else:
        pts["voz"] = 10.0
    # conteúdo (0-15): perguntas, números e ganchos ao longo do trecho (por 30 s)
    dens = (sig["perguntas"] * 2 + min(sig["numeros"], 4) + len(sig["ganchos"]) * 2 + min(sig["tensao"], 6) * 0.7)
    pts["conteudo"] = max(0.0, min(15.0, dens * 30 / max(dur, 20) * 1.5))
    nota = sum(pts.values())
    if not 25 <= dur <= 50:  # ponto ideal de retenção
        nota -= 3
    sig["pontos"] = {k: round(v, 1) for k, v in pts.items()}
    return {"start": round(s0, 2), "end": round(e0, 2), "duracao": round(dur, 1), "texto": txt,
            "gancho_texto": gancho, "sinais": sig, "nota_objetiva": round(max(0.0, min(100.0, nota)), 1),
            "i0": ws[0]["i"], "i1": ws[-1]["i"]}


def hunt(words_json: str, video: str | None = None, top: int = 5, min_d: float = 20.0, max_d: float = 60.0,
         out: str | None = None, max_overlap: float = 0.25) -> dict:
    data = load_json(words_json)
    words = data["words"]
    if not words:
        raise SystemExit("[edin] Transcrição vazia.")
    by_i = {w["i"]: w for w in words}
    src = video or data.get("source")
    if src and not Path(src).is_absolute():
        src = str((Path(words_json).resolve().parent / src).resolve())
    if src and not Path(src).exists():
        guess = [p for p in Path(words_json).resolve().parent.glob(Path(words_json).name.split(".words")[0] + ".*")
                 if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm", ".m4a", ".mp3", ".wav")]
        src = str(guess[0]) if guess else None
    print(f"[edin] Analisando {len(words)} palavras" + (f" e o áudio de {Path(src).name}..." if src else
                                                          " (sem áudio: passe --video para energia e tom)"))
    audio = AudioFeats(src)
    sents = sentences(words)

    cands = []
    for a in range(len(sents)):
        for b in range(a, len(sents)):
            d = sents[b]["e"] - sents[a]["s"]
            if d > max_d:
                break
            if d < min_d:
                continue
            cands.append(_window_signals(sents, a, b, by_i, audio))
    if not cands:
        raise SystemExit(f"[edin] Nenhum trecho entre {min_d:.0f} e {max_d:.0f} s com frases inteiras nas bordas.")

    # melhores sem sobreposição (mais de max_overlap do menor trecho = mesma ideia)
    cands.sort(key=lambda c: -c["nota_objetiva"])
    chosen = []
    for c in cands:
        ok = True
        for k in chosen:
            inter = min(c["end"], k["end"]) - max(c["start"], k["start"])
            if inter > max_overlap * min(c["duracao"], k["duracao"]):
                ok = False
                break
        if ok:
            chosen.append(c)
        if len(chosen) >= top:
            break

    stem = re.sub(r"\.words$", "", str(Path(words_json).with_suffix("")))
    video_arg = src or "video.mp4"
    for n, c in enumerate(chosen, 1):
        c["range"] = _rng_str(c["start"], c["end"])
        fr = best_phrase(words, audio, c["start"], c["end"])
        c["frase_forte"] = fr
        co = f' --cold-open {fr["i0"]}-{fr["i1"]}' if fr and fr["nota"] >= 35 else ""
        c["comando"] = f'edin plan "{video_arg}" --range {c["range"]} --name short{n}{co}'
        c["rubrica"] = {"hook": None, "flow": None, "value": None, "trend": None, "total": None}
    res = {"words": str(Path(words_json).resolve()), "video": src, "min": min_d, "max": max_d,
           "analisados": len(cands), "rubrica": "Hook, Flow, Value, Trend: 0 a 25 cada (preenchida pelo agente "
                                                "cacador-de-cortes)", "candidates": chosen}
    out = out or stem + ".candidates.json"
    save_json(res, out)
    print_table(chosen)
    print(f"[edin] {len(cands)} trechos analisados, {len(chosen)} candidatos -> {out}")
    return res


def print_table(cands: list) -> None:
    print(f"{'#':>2} {'nota':>5}  {'trecho':<15} {'dur':>5}  {'gnc':>4} {'cmp':>4} {'rit':>4} {'voz':>4} {'cnt':>4}  gancho")
    for n, c in enumerate(cands, 1):
        p = c["sinais"]["pontos"]
        g = c["gancho_texto"]
        g = g if len(g) <= 70 else g[:67] + "..."
        print(f"{n:>2} {c['nota_objetiva']:>5.1f}  {fmt_time(c['start'])}-{fmt_time(c['end'])} {c['duracao']:>4.0f}s  "
              f"{p['gancho']:>4.0f} {p['completude']:>4.0f} {p['ritmo']:>4.0f} {p['voz']:>4.0f} {p['conteudo']:>4.0f}  {g}")
        fr = c.get("frase_forte")
        if fr:
            print(f"{'':>9}cold open #{fr['i0']}-{fr['i1']} ({fr['nota']:.0f}): \"{fr['texto']}\"")


# ------------------------------------------------------------------ cold open no plano

def apply_cold_open(plan: dict, spec: str = "auto", rng: str | None = None, zoom: float = 1.25) -> dict | None:
    """Põe no início do plano um segmento de 1 a 3 s com a frase mais forte do trecho (repetida: ela continua
    no lugar dela depois). `spec`: "auto" (pela nota da frase) ou "A-B" (índices de palavra do `edin text`)."""
    from .audio import Energy

    words = load_json(plan["words"])["words"]
    by_i = {w["i"]: w for w in words}
    segs = [s for s in plan["segments"] if not s.get("cold_open")]
    t0 = parse_range(rng)[0] if rng else segs[0]["start"]
    t1 = parse_range(rng)[1] if rng else segs[-1]["end"]
    if spec in (None, "", "auto", True):
        audio = AudioFeats(plan["source"], offset=max(0.0, t0 - 1), duration=t1 - t0 + 2)
        fr = best_phrase(words, audio, t0, t1)
        if not fr:
            print("[edin] Cold open: nenhuma frase de 1 a 3 s com borda natural no trecho. Indique com --cold-open A-B.")
            return None
        a, b = fr["i0"], fr["i1"]
        if fr["nota"] < 35:
            print(f"[edin] Aviso: a frase mais forte do trecho tem nota baixa ({fr['nota']:.0f}). Leia o `edin text` "
                  "e indique uma melhor com --cold-open A-B, ou faça sem cold open.")
    else:
        a, b = (int(x) for x in str(spec).lstrip("#").split("-"))
        fr = None
    if a not in by_i or b not in by_i or b < a:
        raise SystemExit(f"[edin] Cold open: índices {a}-{b} fora da transcrição.")
    wa, wb = by_i[a], by_i[b]
    prv, nxt = by_i.get(a - 1), by_i.get(b + 1)
    lo = prv["e"] + 0.02 if prv else 0.0
    hi = nxt["s"] - 0.02 if nxt else wb["e"] + 0.3
    start, end = max(lo, wa["s"] - 0.04), min(hi, wb["e"] + 0.08)
    try:  # mesma regra do plano: a energia do áudio decide onde cortar, sem pegar a palavra vizinha
        en = Energy(plan["source"])
        start, end = en.extend_start(start, lo), en.extend_end(end, hi)
    except Exception:  # noqa: BLE001
        pass
    seg = {"start": round(start, 3), "end": round(end, 3), "zoom": zoom, "zoom_to": round(zoom + 0.05, 3),
           "focus": "face", "cold_open": True}
    sp = segs[0].get("speed")
    if sp:
        seg["speed"] = sp
    if abs(float(segs[0].get("zoom", 1.0)) - zoom) < 0.01:  # o contexto tem que voltar visivelmente
        segs[0]["zoom"], segs[0]["zoom_to"] = 1.0, 1.0 + (float(segs[0].get("zoom_to", zoom)) - zoom)
    plan["segments"] = [seg] + segs
    texto = " ".join(by_i[k]["w"] for k in range(a, b + 1) if k in by_i)
    plan["cold_open"] = {"words": [a, b], "texto": texto}
    print(f"[edin] Cold open #{a}-{b} ({end - start:.1f}s): \"{texto}\""
          + (f" nota {fr['nota']:.0f}" if fr else ""))
    return plan["cold_open"]
