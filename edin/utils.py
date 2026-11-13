"""Utilitários: chamadas ao ffmpeg/ffprobe, leitura de JSON, caminhos."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
FONTS_DIR = ROOT_DIR / "assets" / "fonts"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def check_tools() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"[edin] '{tool}' não encontrado no PATH. Instale o ffmpeg primeiro.")


def run(cmd: list, cwd: str | None = None, verbose: bool = False) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    if verbose:
        print("[edin] $", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if p.returncode != 0:
        raise RuntimeError(f"Comando falhou: {' '.join(cmd)[:600]}\n--- stderr ---\n{p.stderr[-4000:]}")
    return p


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXT


def probe(path: str) -> dict:
    """Retorna largura/altura efetivas (já considerando rotação), fps, duração e se tem áudio."""
    p = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    d = json.loads(p.stdout)
    streams = d.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v is None:
        raise RuntimeError(f"Sem trilha de vídeo em {path}")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    if "rotate" in (v.get("tags") or {}):
        rot = int(v["tags"]["rotate"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    fps = 30.0
    for key in ("avg_frame_rate", "r_frame_rate"):
        fr = v.get(key, "0/0")
        try:
            num, den = fr.split("/")
            if float(den) > 0 and float(num) > 0:
                fps = float(num) / float(den)
                break
        except ValueError:
            pass
    dur = float(d.get("format", {}).get("duration") or v.get("duration") or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return {"w": w, "h": h, "fps": fps, "duration": dur, "has_audio": has_audio}


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def fmt_time(t: float) -> str:
    m, s = divmod(max(t, 0), 60)
    return f"{int(m):02d}:{s:04.1f}"


def parse_range(r: str | None):
    """'90-150' ou '1:30-2:30' -> (90.0, 150.0)."""
    if not r:
        return None

    def to_s(x: str) -> float:
        parts = [float(p) for p in x.strip().split(":")]
        t = 0.0
        for p in parts:
            t = t * 60 + p
        return t

    a, b = r.split("-")
    return to_s(a), to_s(b)


def ffmpeg_filter_path(path: str) -> str:
    """Escapa um caminho para uso dentro de um filtro (subtitles=...)."""
    p = str(Path(path).resolve()).replace("\\", "/")
    return p.replace(":", r"\:").replace("'", r"\'").replace(",", r"\,")


def workdir_for(output: str) -> Path:
    # pasta oculta ao lado da saída: não suja videos/ (cache de rosto, efeitos e segmentos)
    wd = Path(output).resolve().parent / ".edin_tmp" / Path(output).stem
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").lower() in {"1", "true", "yes"}


class TravaPesada:
    """Serializa os trabalhos pesados do edin (gerador de imagem na GPU e render do `edin html`).

    Juntos (SDXL com 6 GB de pesos + vários Chromes com WebGL) eles esgotaram a RAM de 14 GB e a VRAM de 6 GB
    e derrubaram a sessão em 2026-11-12. Com a trava, o segundo espera o primeiro terminar.
    """

    def __init__(self, nome: str):
        self.nome = nome
        self.f = None

    def __enter__(self):
        import fcntl

        d = Path.home() / ".cache" / "edin"
        d.mkdir(parents=True, exist_ok=True)
        self.f = open(d / "pesado.lock", "a+")
        try:
            fcntl.flock(self.f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"[edin] {self.nome}: outro trabalho pesado do edin está rodando (render ou imagem); esperando...",
                  flush=True)
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        import fcntl

        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()
        return False


def mem_disponivel_mb() -> int:
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 4096
