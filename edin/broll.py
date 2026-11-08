"""B-roll automático e grátis pela API do Pexels (https://www.pexels.com/api/documentation/).

    edin broll "estudante cansado" --orientation portrait --n 3

Baixa para `broll/` (ao lado do plano ou na pasta atual), com cache das buscas e dos arquivos, e grava os créditos
(autor e URL) em `broll/CREDITOS.txt`. No plano, um segmento com `"broll": {"query": "estudante cansado"}` é
resolvido no render (ou com `edin broll --plan plano.json`) baixando o melhor clipe na orientação do vídeo.
A chave fica na variável de ambiente PEXELS_API_KEY (grátis, 200 buscas por hora).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .utils import load_json, save_json

API = "https://api.pexels.com/videos/search"
UA = "edin/0.1 (+https://github.com/RafaelCoutinhoLima/editor-dinamico)"
SEM_CHAVE = """[edin] Falta a chave da API do Pexels (grátis).
  1. Crie uma conta em https://www.pexels.com/join e abra https://www.pexels.com/api/new/
  2. Preencha o formulário curto (uso: "editar meus vídeos") e copie a chave em "Your API Key".
  3. Coloque no terminal (e no fim do ~/.bashrc para ficar salva):
       export PEXELS_API_KEY="sua_chave"
  Limite grátis: 200 buscas por hora e 20 mil por mês. Os vídeos do Pexels são livres para uso comercial;
  o edin grava o crédito do autor em broll/CREDITOS.txt."""

ORIENT = {"9:16": "portrait", "4:5": "portrait", "16:9": "landscape", "1:1": "square"}


def api_key() -> str:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        raise SystemExit(SEM_CHAVE)
    return key


def _api_get(params: dict) -> dict:
    """GET na API de busca de vídeos (separado para poder testar sem chave)."""
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}",
                                 headers={"Authorization": api_key(), "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise SystemExit("[edin] O Pexels recusou a chave (PEXELS_API_KEY inválida ou revogada).") from e
        if e.code == 429:
            raise SystemExit("[edin] Limite do Pexels atingido (200 buscas/hora). Use o cache ou espere.") from e
        raise


def _best_file(video: dict, orientation: str, min_side: int = 1080) -> dict | None:
    """Arquivo MP4 mais leve que ainda tenha o lado menor >= min_side (senão o maior). Prefere até 30 fps."""
    files = [f for f in video.get("video_files") or [] if f.get("link") and (f.get("file_type") or "").endswith("mp4")
             and f.get("width") and f.get("height")]
    if orientation == "portrait":
        files = [f for f in files if f["height"] >= f["width"]] or files
    elif orientation == "landscape":
        files = [f for f in files if f["width"] >= f["height"]] or files
    if not files:
        return None

    def key(f):
        side = min(f["width"], f["height"])
        return (side < min_side, -side if side < min_side else side, (f.get("fps") or 30) > 31)
    return min(files, key=key)


def _normalize(v: dict, orientation: str) -> dict | None:
    f = _best_file(v, orientation)
    if not f:
        return None
    user = v.get("user") or {}
    return {"id": v["id"], "url": v.get("url", ""), "duration": float(v.get("duration") or 0),
            "author": user.get("name", "?"), "author_url": user.get("url", ""),
            "file": f["link"], "w": f["width"], "h": f["height"], "fps": f.get("fps")}


def search(query: str, orientation: str = "portrait", n: int = 3, cache_dir: Path | None = None,
           locale: str = "pt-BR") -> list:
    """Busca no Pexels (com cache em broll/pexels_cache.json) e devolve candidatos normalizados."""
    cache_file = cache_dir / "pexels_cache.json" if cache_dir else None
    cache = load_json(str(cache_file)) if cache_file and cache_file.exists() else {}
    key = f"{orientation}|{locale}|{query.strip().lower()}"
    if key in cache:
        return cache[key]
    data = _api_get({"query": query, "orientation": orientation, "per_page": max(n * 3, 10), "size": "medium",
                     "locale": locale})
    res = [r for r in (_normalize(v, orientation) for v in data.get("videos") or []) if r]
    if cache_file:
        cache[key] = res
        save_json(cache, str(cache_file))
    return res


def download(item: dict, dest_dir: Path) -> Path:
    """Baixa o clipe (se ainda não estiver em dest_dir) e registra o crédito."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f"pexels_{item['id']}_{min(item['w'], item['h'])}p.mp4"
    if not out.exists() or out.stat().st_size == 0:
        print(f"[edin] Baixando b-roll {out.name} ({item['author']})...")
        tmp = out.with_suffix(".part")
        req = urllib.request.Request(item["file"], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
            while chunk := r.read(1 << 20):
                fh.write(chunk)
        tmp.replace(out)
    credit(dest_dir, out.name, item)
    return out


def credit(dest_dir: Path, name: str, item: dict) -> None:
    f = dest_dir / "CREDITOS.txt"
    txt = f.read_text(encoding="utf-8") if f.exists() else (
        "B-roll do Pexels (https://www.pexels.com/license/): uso livre, inclusive comercial. Créditos:\n")
    if name not in txt:
        txt += f"{name}: vídeo de {item['author']} ({item['author_url']}) no Pexels, {item['url']}\n"
        f.write_text(txt, encoding="utf-8")


def fetch(query: str, orientation: str = "portrait", n: int = 3, dest_dir: Path = Path("broll"),
          min_dur: float = 0.0) -> list:
    """Busca e baixa os n melhores clipes (os que cobrem min_dur primeiro, na ordem de relevância do Pexels)."""
    cands = search(query, orientation, n, dest_dir)
    if not cands:
        raise SystemExit(f"[edin] Nenhum vídeo no Pexels para {query!r} ({orientation}). Tente outra palavra.")
    ordered = [c for c in cands if c["duration"] >= min_dur] + [c for c in cands if c["duration"] < min_dur]
    return [(download(c, dest_dir), c) for c in ordered[:n]]


def resolve_plan(plan: dict, plan_dir: Path) -> int:
    """Troca cada `"broll": {"query": ...}` sem `src` pelo melhor clipe baixado. Devolve quantos resolveu."""
    from .plan import seg_out_dur

    orientation = ORIENT.get(plan.get("format", "9:16"), "portrait")
    done = 0
    for seg in plan["segments"]:
        b = seg.get("broll")
        if not b or b.get("src") or not b.get("query"):
            continue
        pick = int(b.get("pick", 0))
        got = fetch(b["query"], b.get("orientation", orientation), pick + 1, plan_dir / "broll",
                    min_dur=seg_out_dur(seg) + float(b.get("start", 0)))
        path, _ = got[min(pick, len(got) - 1)]
        b["src"] = str(path.resolve())
        done += 1
    return done
