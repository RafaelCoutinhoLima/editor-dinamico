"""Legendas animadas em ASS (palavra ativa destacada, pop de escala, palavras de ênfase, títulos)."""
from __future__ import annotations

import re

WHITE = "&H00FFFFFF&"
BLACK = "&H00000000&"
YELLOW = "&H0000E5FF&"   # amarelo quente
GREEN = "&H0014FF39&"    # verde limão
RED = "&H003030FF&"

STYLES = {
    # estilo Hormozi/Reels: caixa alta, Anton, palavra ativa amarela com pop
    "hormozi": dict(font="Anton", size=0.105, outline=0.009, shadow=0.004, active=YELLOW, emph=GREEN,
                    pop=1.18, upper=True),
    # limpo: Montserrat ExtraBold, palavra ativa verde
    "clean": dict(font="Montserrat ExtraBold", size=0.072, outline=0.007, shadow=0.0, active=GREEN, emph=YELLOW,
                  pop=1.10, upper=False),
    # karaoke: frase inteira visível, palavras acendem conforme a fala
    "karaoke": dict(font="Montserrat ExtraBold", size=0.068, outline=0.007, shadow=0.003, active=YELLOW,
                    emph=GREEN, pop=1.0, upper=False, karaoke=True),
    # mínimo: legenda tradicional para YouTube/aula
    "minimal": dict(font="Montserrat ExtraBold", size=0.056, outline=0.005, shadow=0.0, active=None, emph=None,
                    pop=1.0, upper=False),
}


def _t(sec: float) -> str:
    sec = max(sec, 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(txt: str) -> str:
    return re.sub(r"[{}\\]", "", txt)


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


def build_ass(words: list, cfg: dict, out_w: int, out_h: int, titles: list | None = None,
              total: float | None = None) -> str:
    st = STYLES.get(cfg.get("style", "hormozi"), STYLES["hormozi"])
    base = min(out_w, out_h)
    size = int(base * st["size"] * float(cfg.get("scale", 1.0)))
    outline = max(1, int(base * st["outline"]))
    shadow = int(base * st["shadow"])
    upper = cfg.get("uppercase", st["upper"])
    emphasis = set(cfg.get("emphasis") or [])
    pos_y = int(out_h * float(cfg.get("position", 0.7)))
    per = int(cfg.get("words_per_group", 3))
    max_chars = int(cfg.get("max_chars", 22 if out_w < out_h else 42))
    active_c = cfg.get("active_color", st["active"])
    emph_c = cfg.get("emphasis_color", st["emph"]) or YELLOW
    margin = int(out_w * 0.07)

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {out_w}
PlayResY: {out_h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{st['font']},{size},{WHITE},{WHITE},{BLACK},&H80000000&,0,0,0,0,100,100,1,0,1,{outline},{shadow},5,{margin},{margin},0,1
Style: Title,Anton,{int(base * 0.10)},{WHITE},{WHITE},&H00101010&,&H00101010&,0,0,0,0,100,100,1,0,3,{int(base * 0.028)},0,8,{margin},{margin},{int(out_h * 0.12)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    groups = group_words(words, per, max_chars) if words else []
    for gi, g in enumerate(groups):
        nxt = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else (total or g[-1]["e"] + 0.6)
        g_end = nxt if nxt - g[-1]["e"] < 0.45 else g[-1]["e"] + 0.3
        texts = [_clean(w["w"].upper() if upper else w["w"]) for w in g]
        pos = f"\\an5\\pos({out_w // 2},{pos_y})"
        if not active_c:  # minimal: linha estática
            line = " ".join(texts)
            ev.append(f"Dialogue: 0,{_t(g[0]['s'])},{_t(g_end)},Cap,,0,0,0,,{{{pos}}}{line}")
            continue
        for k, w in enumerate(g):
            s = w["s"]
            e = g[k + 1]["s"] if k + 1 < len(g) else g_end
            if e <= s:
                continue
            parts = []
            for j, txt in enumerate(texts):
                is_emph = g[j].get("i") in emphasis
                if st.get("karaoke") and j > k:
                    color = "&H00B0B0B0&"
                elif j == k:
                    color = emph_c if is_emph else active_c
                else:
                    color = emph_c if is_emph else WHITE
                if j == k and st["pop"] > 1.0:
                    p = int(st["pop"] * (112 if is_emph else 100))
                    parts.append(f"{{\\c{color}\\fscx{p}\\fscy{p}\\t(0,110,\\fscx100\\fscy100)}}{txt}"
                                 f"{{\\fscx100\\fscy100}}")
                else:
                    parts.append(f"{{\\c{color}}}{txt}")
            intro = "\\fscx92\\fscy92\\t(0,70,\\fscx100\\fscy100)" if k == 0 else ""
            ev.append(f"Dialogue: 0,{_t(s)},{_t(e)},Cap,,0,0,0,,{{{pos}{intro}}}" + " ".join(parts))

    for t in titles or []:
        ev.append(_title_event(t, out_w, out_h, base))
    return head + "\n".join(ev) + "\n"
