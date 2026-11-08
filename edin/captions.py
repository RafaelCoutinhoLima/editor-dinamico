"""Legendas animadas em ASS no padrão Submagic/CapCut.

Cada palavra é um evento com posição fixa (calculada pelas métricas da fonte), então a palavra ativa sobe e cresce
sem empurrar as vizinhas (nada treme). Palavra ativa na cor principal; ênfase e categorias (números, negação) numa
segunda cor. Também títulos e o layout usado para pôr emoji acima da legenda.
"""
from __future__ import annotations

import re
import struct
import unicodedata
from functools import lru_cache

from .utils import FONTS_DIR

WHITE = "&H00FFFFFF&"
BLACK = "&H00000000&"
GREY = "&H00B0B0B0&"
YELLOW = "&H0000E5FF&"   # amarelo quente
GREEN = "&H0014FF39&"    # verde limão
RED = "&H003B30FF&"      # vermelho alerta (#FF303B)

# letter = altura das maiúsculas em px numa saída de 1080 de largura (padrão pro: 65 a 90 px)
STYLES = {
    # estilo Hormozi/Submagic: caixa alta, Anton, palavra ativa amarela que sobe e cresce
    "hormozi": dict(font="Anton", letter=80, outline=0.009, shadow=0.004, active=YELLOW, emph=GREEN,
                    pop=1.10, upper=True),
    # limpo: Montserrat ExtraBold, palavra ativa verde
    "clean": dict(font="Montserrat ExtraBold", letter=70, outline=0.007, shadow=0.0, active=GREEN, emph=YELLOW,
                  pop=1.08, upper=False),
    # karaoke: frase inteira visível, palavras acendem conforme a fala
    "karaoke": dict(font="Montserrat ExtraBold", letter=68, outline=0.007, shadow=0.003, active=YELLOW,
                    emph=GREEN, pop=1.0, upper=False, karaoke=True),
    # mínimo: legenda tradicional para YouTube/aula
    "minimal": dict(font="Montserrat ExtraBold", letter=56, outline=0.005, shadow=0.0, active=None, emph=None,
                    pop=1.0, upper=False),
}

FONT_FILES = {
    "anton": "Anton-Regular.ttf", "montserrat extrabold": "Montserrat-ExtraBold.ttf",
    "montserrat": "Montserrat-ExtraBold.ttf", "archivo black": "ArchivoBlack-Regular.ttf",
    "bebas neue": "BebasNeue-Regular.ttf", "poppins extrabold": "Poppins-ExtraBold.ttf",
    "poppins": "Poppins-ExtraBold.ttf", "plus jakarta sans": "PlusJakartaSans.ttf",
}

# categorias com segunda cor (opcional): `captions.categories`
_NUM_WORDS = {"dois", "duas", "três", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze",
              "doze", "quinze", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta",
              "noventa", "cem", "cento", "duzentos", "trezentos", "quinhentos", "mil", "milhão", "milhões", "milhao",
              "milhoes", "bilhão", "bilhões", "bilhao", "bilhoes", "dobro", "triplo", "metade", "reais", "dólares",
              "dolares", "real", "porcento", "primeiro", "primeira", "segundo", "terceiro"}
_ALERT_WORDS = {"não", "nao", "nunca", "jamais", "nada", "nenhum", "nenhuma", "ninguém", "ninguem", "nem",
                "pare", "cuidado", "erro", "erros", "errado", "errada", "proibido", "perigo", "atenção", "atencao",
                "evite", "pior", "cilada", "armadilha", "golpe", "mentira", "falso", "falsa", "zero"}
CATEGORIES = {
    "numero": dict(color="#39FF14", test=lambda w: bool(re.search(r"\d|r\$|%|us\$", w)) or w in _NUM_WORDS),
    "alerta": dict(color="#FF3B30", test=lambda w: w in _ALERT_WORDS),
}


def _t(sec: float) -> str:
    sec = max(sec, 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(txt: str) -> str:
    return re.sub(r"[{}\\]", "", txt)


def _bare(w: str) -> str:
    return re.sub(r"^[^\wR$%]+|[^\w%$]+$", "", w.lower())


def group_words(words: list, per_group: int, max_chars: int) -> list:
    groups, cur = [], []
    for w in words:
        too_long = len(" ".join(x["w"] for x in cur + [w])) > max_chars
        new_blk = w.get("blk") != cur[-1].get("blk") if cur else False
        if cur and (len(cur) >= per_group or too_long or new_blk or w["s"] - cur[-1]["e"] > 0.5):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1:] in ".?!" and len(cur) >= 1:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def ass_color(c: str | None, default: str = WHITE) -> str:
    """'#RRGGBB' ou '&H00BBGGRR&' -> cor ASS."""
    if not c:
        return default
    if c.startswith("#") and len(c) == 7:
        return f"&H00{c[5:7]}{c[3:5]}{c[1:3]}&".upper()
    return c


# ------------------------------------------------------------------ métricas da fonte (sem dependências)

class FontMetrics:
    """Lê do TTF o necessário para medir texto como o libass: avanço de cada glifo e altura das maiúsculas.
    O libass usa fontsize = (usWinAscent + usWinDescent) em px, então 1 em = fontsize * upem / (winA + winD)."""

    def __init__(self, path):
        b = path.read_bytes()
        tables = {}
        for k in range(struct.unpack(">H", b[4:6])[0]):
            tag, _, off, ln = struct.unpack(">4sIII", b[12 + 16 * k:28 + 16 * k])
            tables[tag.decode("latin-1")] = (off, ln)
        o = tables["head"][0]
        self.upem = struct.unpack(">H", b[o + 18:o + 20])[0]
        o = tables["hhea"][0]
        asc, desc = struct.unpack(">hh", b[o + 4:o + 8])
        n_hm = struct.unpack(">H", b[o + 34:o + 36])[0]
        o = tables["OS/2"][0]
        ver = struct.unpack(">H", b[o:o + 2])[0]
        wa, wd = struct.unpack(">HH", b[o + 74:o + 78])
        self.real = (wa + wd) or (asc - desc)
        self.cap = struct.unpack(">h", b[o + 88:o + 90])[0] if ver >= 2 else int(self.upem * 0.7)
        o = tables["hmtx"][0]
        self.adv = [struct.unpack(">H", b[o + 4 * k:o + 4 * k + 2])[0] for k in range(n_hm)]
        self.cmap = self._cmap(b, tables["cmap"][0])

    @staticmethod
    def _cmap(b, base):
        best = None
        for k in range(struct.unpack(">H", b[base + 2:base + 4])[0]):
            pid, eid, off = struct.unpack(">HHI", b[base + 4 + 8 * k:base + 12 + 8 * k])
            fmt = struct.unpack(">H", b[base + off:base + off + 2])[0]
            if pid in (0, 3) and fmt in (4, 12) and (best is None or fmt == 12):
                best = (base + off, fmt)
        cmap = {}
        if not best:
            return cmap
        o, fmt = best
        if fmt == 12:
            for k in range(struct.unpack(">I", b[o + 12:o + 16])[0]):
                s, e, g = struct.unpack(">III", b[o + 16 + 12 * k:o + 28 + 12 * k])
                for c in range(s, min(e, 0x2FFFF) + 1):
                    cmap[c] = g + c - s
            return cmap
        seg = struct.unpack(">H", b[o + 6:o + 8])[0] // 2
        ends = struct.unpack(f">{seg}H", b[o + 14:o + 14 + 2 * seg])
        p = o + 16 + 2 * seg
        starts = struct.unpack(f">{seg}H", b[p:p + 2 * seg])
        deltas = struct.unpack(f">{seg}h", b[p + 2 * seg:p + 4 * seg])
        ro_pos = p + 4 * seg
        ros = struct.unpack(f">{seg}H", b[ro_pos:ro_pos + 2 * seg])
        for k in range(seg):
            for c in range(starts[k], ends[k] + 1):
                if c == 0xFFFF:
                    continue
                if ros[k] == 0:
                    g = (c + deltas[k]) & 0xFFFF
                else:
                    a = ro_pos + 2 * k + ros[k] + 2 * (c - starts[k])
                    g = struct.unpack(">H", b[a:a + 2])[0]
                    g = (g + deltas[k]) & 0xFFFF if g else 0
                cmap[c] = g
        return cmap

    def width(self, text: str, fontsize: float, spacing: float = 0.0) -> float:
        em = fontsize * self.upem / self.real
        units = 0
        for ch in unicodedata.normalize("NFC", text):
            g = self.cmap.get(ord(ch), 0)
            units += self.adv[min(g, len(self.adv) - 1)]
        return units * em / self.upem + spacing * len(text)

    def cap_ratio(self) -> float:
        return self.cap / self.real


class _Approx:
    """Reserva quando a fonte não está em assets/fonts (medida aproximada)."""

    def width(self, text, fontsize, spacing=0.0):
        return len(text) * fontsize * 0.42 + spacing * len(text)

    def cap_ratio(self):
        return 0.48


@lru_cache(maxsize=None)
def font_metrics(name: str):
    f = FONT_FILES.get(name.lower())
    path = FONTS_DIR / f if f else None
    if path and path.exists():
        try:
            return FontMetrics(path)
        except Exception:  # fonte com tabela inesperada: medida aproximada
            pass
    return _Approx()


# ------------------------------------------------------------------ categorias e layout

def word_categories(words: list, cfg: dict) -> dict:
    """{índice da palavra: cor ASS} para as categorias ligadas em `captions.categories`.
    Aceita true (todas), ["numero", "alerta"] ou {"numero": "#39FF14", "alerta": {"color": "#FF3B30", "words": [...]}}."""
    spec = cfg.get("categories")
    if not spec:
        return {}
    if spec is True:
        spec = {k: {} for k in CATEGORIES}
    elif isinstance(spec, (list, tuple)):
        spec = {k: {} for k in spec}
    out = {}
    for name, opt in spec.items():
        if isinstance(opt, str):
            opt = {"color": opt}
        base = CATEGORIES.get(name, {})
        color = ass_color(opt.get("color") or base.get("color"), GREEN)
        extra = {_bare(x) for x in opt.get("words") or []}
        test = base.get("test", lambda w: False)
        for w in words:
            b = _bare(w["w"])
            if b and (test(b) or b in extra) and w["i"] not in out:
                out[w["i"]] = color
    return out


def caption_params(cfg: dict, out_w: int, out_h: int) -> dict:
    st = dict(STYLES.get(cfg.get("style", "hormozi"), STYLES["hormozi"]))
    if cfg.get("font"):
        st["font"] = cfg["font"]
    base = min(out_w, out_h)
    fm = font_metrics(st["font"])
    letter = float(cfg.get("letter_px", st["letter"])) * float(cfg.get("scale", 1.0))  # em px de 1080
    size = letter * base / 1080 / fm.cap_ratio()
    vertical = out_h > out_w
    # zona segura (1080x1920): >= 90 px à esquerda, >= 120 px à direita (botões); horizontal: 7% de cada lado
    ml = int(out_w * (90 / 1080 if vertical else 0.07))
    mr = int(out_w * (120 / 1080 if vertical else 0.07))
    return dict(st=st, fm=fm, base=base, letter=letter, size=size, ml=ml, mr=mr,
                outline=max(1, int(base * st["outline"])), shadow=int(base * st["shadow"]),
                upper=cfg.get("uppercase", st["upper"]), pos_y=int(out_h * float(cfg.get("position", 0.7))),
                per=max(1, min(4 if st["active"] else 12, int(cfg.get("words_per_group", 3)))),
                max_chars=int(cfg.get("max_chars", 22 if vertical else 42)),
                active=ass_color(cfg.get("active_color"), st["active"]) if st["active"] else None,
                emph=ass_color(cfg.get("emphasis_color"), st["emph"] or YELLOW))


def caption_warnings(cfg: dict, out_w: int, out_h: int) -> list:
    """Avisos do padrão profissional (tamanho, posição, cores) para o plano."""
    if not cfg:
        return []
    p = caption_params(cfg, out_w, out_h)
    warns = []
    if p["st"].get("active") and not 65 <= p["letter"] <= 90:
        warns.append(f"legenda com {p['letter']:.0f} px de altura de letra (padrão pro: 65 a 90 px em 1080)")
    pos = float(cfg.get("position", 0.7))
    if out_h > out_w and not 0.55 <= pos <= 0.78:
        warns.append(f"legenda em position {pos} fora da zona segura do 9:16 (0.55 a 0.78)")
    if p["st"].get("active") and int(cfg.get("words_per_group", 3)) > 4:
        warns.append("words_per_group acima de 4: o padrão pro é 1 a 4 palavras por tela (usando 4)")
    spec = cfg.get("categories")
    if isinstance(spec, dict):
        cols = {str(v.get("color") if isinstance(v, dict) else v).lower() for v in spec.values() if v}
        if len(cols) > 2:
            warns.append("mais de 2 cores de categoria: fica poluído; use a cor principal + no máximo 2 secundárias")
    return warns


def _wrap(texts: list, widths: list, gaps: list, avail: float):
    """Quebra o grupo em 1 ou 2 linhas (a mais equilibrada que caiba)."""
    def lw(a, b):
        return sum(widths[a:b]) + sum(gaps[a:b - 1])
    n = len(texts)
    if lw(0, n) <= avail or n == 1:
        return [(0, n)]
    best = min(range(1, n), key=lambda k: max(lw(0, k), lw(k, n)))
    return [(0, best), (best, n)]


def layout_captions(words: list, cfg: dict, out_w: int, out_h: int, total: float | None = None) -> dict:
    """Posição fixa de cada palavra de cada grupo. Devolve params + grupos:
    [{"start", "end", "words": [{"w", "i", "s", "e", "text", "x", "y", "width"}], "top", "bottom", "lines"}]."""
    p = caption_params(cfg, out_w, out_h)
    st, fm, size = p["st"], p["fm"], p["size"]
    hold = st["pop"] if st["pop"] > 1 else 1.0
    avail = out_w - p["ml"] - p["mr"]
    cx = (p["ml"] + out_w - p["mr"]) / 2
    line_h = p["letter"] * p["base"] / 1080 * 1.55
    out = []
    groups = group_words(words, p["per"], p["max_chars"]) if words else []
    for gi, g in enumerate(groups):
        nxt = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else (total or g[-1]["e"] + 0.6)
        g_end = nxt if nxt - g[-1]["e"] < 0.45 else g[-1]["e"] + 0.3
        texts = [_clean(w["w"].upper() if p["upper"] else w["w"]) for w in g]
        widths = [fm.width(t, size, 1) for t in texts]
        space = fm.width(" ", size) + p["outline"]
        # a palavra ativa cresce (hold + pico de 3%): espaço extra para o contorno não encostar na vizinha
        gaps = [space + (hold + 0.03 - 1) / 2 * max(widths[k], widths[k + 1]) for k in range(len(texts) - 1)]
        lines = _wrap(texts, widths, gaps, avail)
        fit = 1.0
        for a, b in lines:
            lw = sum(widths[a:b]) + sum(gaps[a:b - 1])
            fit = min(fit, avail / lw if lw > avail else 1.0)
        top = p["pos_y"] - line_h * len(lines) / 2
        items = []
        for li, (a, b) in enumerate(lines):
            y = top + line_h * (li + 0.5)
            lw = (sum(widths[a:b]) + sum(gaps[a:b - 1])) * fit
            x = cx - lw / 2
            for k in range(a, b):
                wd = widths[k] * fit
                items.append({**g[k], "text": texts[k], "x": round(x + wd / 2), "y": round(y), "width": wd})
                x += wd + (gaps[k] * fit if k < b - 1 else 0)
        out.append({"start": g[0]["s"], "end": g_end, "words": items, "fit": fit, "lines": len(lines),
                    "top": top, "bottom": top + line_h * len(lines)})
    return {"params": p, "groups": out}


# ------------------------------------------------------------------ ASS

def _title_event(t: dict, out_w: int, out_h: int, base: int) -> str:
    """Título com opções: font, size (fração do lado menor), color, accent (palavras entre *asteriscos*),
    y (0 topo, 1 base), box (caixa escura atrás), uppercase."""
    upper = t.get("uppercase", "font" not in t)
    raw = t["text"].upper() if upper else t["text"]
    color, accent = ass_color(t.get("color")), ass_color(t.get("accent"), YELLOW)
    parts = re.split(r"(\*[^*]+\*)", raw)
    txt = "".join(f"{{\\c{accent}}}{_clean(p[1:-1])}{{\\c{color}}}" if p.startswith("*") and p.endswith("*")
                  else _clean(p) for p in parts)
    txt = txt.replace("\n", "\\N")
    tags = "\\fad(120,150)\\fscx80\\fscy80\\t(0,160,\\fscx100\\fscy100)"
    if "font" in t or "size" in t or "y" in t or "color" in t:
        fs = int(base * float(t.get("size", 0.10)))
        y = int(out_h * float(t.get("y", 0.15)))
        tags = (f"\\an5\\pos({out_w // 2},{y})\\fn{t.get('font', 'Anton')}\\fs{fs}\\c{color}"
                f"\\bord{max(2, fs // 14)}\\3c&H00101010&\\shad0\\b{1 if t.get('bold', True) else 0}") + tags
        style = "Title" if t.get("box", False) else "Cap"
    else:
        style = "Title"
    return f"Dialogue: 1,{_t(t.get('start', 0))},{_t(t.get('end', 2.5))},{style},,0,0,0,,{{{tags}}}{txt}"


def _ms(x: float) -> int:
    return max(0, int(round(x * 1000)))


def build_ass(words: list, cfg: dict, out_w: int, out_h: int, titles: list | None = None,
              total: float | None = None, layout: dict | None = None) -> str:
    lay = layout or layout_captions(words, cfg, out_w, out_h, total)
    p = lay["params"]
    st, base = p["st"], p["base"]
    size = int(round(p["size"]))
    emphasis = set(cfg.get("emphasis") or [])
    cats = word_categories(words, cfg)
    active_c, emph_c = p["active"], p["emph"]
    margin = int(out_w * 0.07)
    unit = p["letter"] * base / 1080  # altura da letra em px nesta saída

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {out_w}
PlayResY: {out_h}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['font']},{size},{WHITE},{WHITE},{BLACK},&H60000000&,0,0,0,0,100,100,1,0,1,{p['outline']},{p['shadow']},5,{margin},{margin},0,1
Style: Title,Anton,{int(base * 0.10)},{WHITE},{WHITE},&H00101010&,&H00101010&,0,0,0,0,100,100,1,0,3,{int(base * 0.028)},0,8,{margin},{margin},{int(out_h * 0.12)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    rise_g = max(2, int(unit * 0.22))   # o grupo entra subindo ~18 px
    rise_w = max(1, int(unit * 0.10))   # a palavra ativa sobe ~8 px
    for g in lay["groups"]:
        gs, ge = g["start"], g["end"]
        fs = f"\\fs{int(size * g['fit'])}" if g["fit"] < 0.999 else ""
        if not active_c:  # minimal: linha estática
            line = " ".join(w["text"] for w in g["words"])
            y = round((g["top"] + g["bottom"]) / 2)
            ev.append(f"Dialogue: 0,{_t(gs)},{_t(ge)},Cap,,0,0,0,,{{\\an5\\pos({out_w // 2},{y})\\fad(60,0)}}{line}")
            continue
        n = len(g["words"])
        for k, w in enumerate(g["words"]):
            x, y = w["x"], w["y"]
            is_emph = w.get("i") in emphasis
            rest = emph_c if is_emph else cats.get(w.get("i"), WHITE)   # cor fora do momento ativo
            hot = emph_c if is_emph else cats.get(w.get("i"), active_c)  # cor enquanto é falada
            before = GREY if st.get("karaoke") else rest
            a = max(gs, w["s"]) if k else gs
            e = g["words"][k + 1]["s"] if k + 1 < n else ge
            e = min(max(e, a), ge)
            # 1) do começo do grupo até a palavra ser falada: parada, cor de repouso (grupo entra subindo)
            if a - gs >= 0.02:
                ev.append(f"Dialogue: 0,{_t(gs)},{_t(a)},Cap,,0,0,0,,{{\\an5\\move({x},{y + rise_g},{x},{y},0,140)"
                          f"\\fad(90,0){fs}\\c{before}}}{w['text']}")
            if ge - a < 0.02:
                continue
            # 2) palavra ativa: sobe um pouco e cresce (pop com overshoot), depois volta à cor de repouso
            entry = f"\\move({x},{y + rise_g},{x},{y},0,140)\\fad(90,0)" if k == 0 else \
                f"\\move({x},{y + rise_w},{x},{y},0,110)"
            hold = st["pop"] * (1.04 if is_emph else 1.0)
            if hold > 1.0:
                h, pk = int(hold * 100), int(hold * 100 + 3)
                pop = f"\\fscx92\\fscy92\\t(0,90,\\fscx{pk}\\fscy{pk})\\t(90,170,\\fscx{h}\\fscy{h})"
                back = f"\\t({_ms(e - a)},{_ms(e - a) + 50},\\fscx100\\fscy100\\c{rest})"
            else:
                pop, back = "", f"\\t({_ms(e - a)},{_ms(e - a) + 40},\\c{rest})"
            ev.append(f"Dialogue: 1,{_t(a)},{_t(ge)},Cap,,0,0,0,,{{\\an5{entry}{fs}\\c{hot}{pop}{back}}}{w['text']}")

    for t in titles or []:
        ev.append(_title_event(t, out_w, out_h, base))
    return head + "\n".join(ev) + "\n"
