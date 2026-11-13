"""edin quadros: extrai a sequência de quadros de um clipe para o kit de vídeo em HTML (EdinVideo.clipe).

    edin quadros clipes/x.mp4                     -> clipes/x/00000.jpg ... + quadros.js + quadros.json
    edin quadros clipes/x.mp4 --fps 60            -> interpolado para 60 fps (minterpolate mci, sem engasgo)
    edin quadros clipes/x.mp4 --largura 1080 --formato webp

Por que quadros e não <video>: o `edin html` chama EDIN.seek(t) fora de ordem (vários workers, aquecimento,
subtempos do motion blur) e o quadro tem de ser exatamente o mesmo. Uma imagem por quadro com `decode()` é
determinística por construção; o kit mantém só um pool pequeno de <img> (nunca o clipe inteiro na memória).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path


def _probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames:stream_side_data=rotation",
                        "-show_entries", "format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"[edin] ffprobe falhou em {path}: {r.stderr.strip()}")
    d = json.loads(r.stdout)
    if not d.get("streams"):
        sys.exit(f"[edin] {path} não tem trilha de vídeo")
    s = d["streams"][0]
    fr = s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1"
    if fr in ("0/0", "0/1"):
        fr = s.get("r_frame_rate", "24/1")
    nb = int(s.get("nb_frames") or 0)
    return {"w": int(s["width"]), "h": int(s["height"]), "fps": float(Fraction(fr)), "nb": nb,
            "dur": float(d.get("format", {}).get("duration") or 0)}


def _rife() -> str | None:
    return shutil.which("rife-ncnn-vulkan")


def extrair(entrada: str, fps: float | None = None, largura: int | None = None, formato: str = "jpg",
            qualidade: int | None = None, interp: str = "mci", saida: str | None = None,
            inicio: float = 0.0, duracao: float | None = None) -> Path:
    src = Path(entrada).resolve()
    if not src.exists():
        sys.exit(f"[edin] {src} não existe")
    info = _probe(src)
    pasta = Path(saida).resolve() if saida else src.with_suffix("")
    if pasta == src:
        sys.exit("[edin] a pasta de saída não pode ser o próprio arquivo")
    pasta.mkdir(parents=True, exist_ok=True)
    for velho in list(pasta.glob("*.jpg")) + list(pasta.glob("*.webp")):
        velho.unlink()

    fps_src = info["fps"]
    fps_out = fps or fps_src
    # largura: padrão é a resolução do clipe (o lado menor limitado a 1080, nunca amplia): um clipe 16:9
    # usado com cover num quadro vertical precisa de toda a altura que tiver. Pedida explicitamente, vale (lanczos)
    larg = largura or (info["w"] if min(info["w"], info["h"]) <= 1080 else round(info["w"] * 1080 / min(info["w"], info["h"])))
    larg -= larg % 2
    filtros = []
    if larg != info["w"]:
        filtros.append(f"scale={larg}:-2:flags=lanczos+accurate_rnd+full_chroma_int")
    usou = "nenhuma"
    rife = None
    # quantos quadros saem: a duração do clipe (n quadros de origem / fps de origem) x fps de saída
    dur_in = (info["nb"] / fps_src) if info["nb"] else info["dur"]
    dur_in = max(0.0, (min(duracao, dur_in - inicio) if duracao else dur_in - inicio))
    n_alvo = max(1, round(dur_in * fps_out))
    if fps and abs(fps_out - fps_src) > 1e-3:
        if fps_out < fps_src or interp == "dup":
            filtros.append(f"fps={fps_out:g}")
            usou = "fps (repete/descarta quadros)"
        elif interp == "rife":
            rife = _rife()
            if not rife:
                print("[edin] rife-ncnn-vulkan não está instalado; usando minterpolate mci")
                interp = "mci"
        if interp == "mci" and fps_out > fps_src:
            # compensação de movimento bidirecional com blocos sobrepostos (aobmc) e vsbmc: a melhor do ffmpeg.
            # scd=fdiff: em troca de plano não inventa quadro misturado
            # tpad: repete o último quadro para o interpolador cobrir até o fim do clipe (sem ele faltam ~4 quadros)
            filtros.append(f"tpad=stop_mode=clone:stop=2,minterpolate=fps={fps_out:g}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:"
                           f"vsbmc=1:scd=fdiff:scd_threshold=10")
            usou = "minterpolate mci"
        elif interp == "blend" and fps_out > fps_src:
            filtros.append(f"tpad=stop_mode=clone:stop=2,minterpolate=fps={fps_out:g}:mi_mode=blend")
            usou = "minterpolate blend"
    if formato == "jpg":
        q = qualidade or 2  # mjpeg -q:v 2 ~ qualidade 95
        cod = ["-c:v", "mjpeg", "-q:v", str(q), "-qmin", "1", "-pix_fmt", "yuvj444p"]
    elif formato == "webp":
        cod = ["-c:v", "libwebp", "-quality", str(qualidade or 92), "-compression_level", "4"]
    else:
        sys.exit("[edin] --formato: jpg ou webp")
    filtros.append("setsar=1")

    t0 = time.time()
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if inicio:
        cmd += ["-ss", f"{inicio:.3f}"]
    cmd += ["-i", str(src)]
    if duracao:
        cmd += ["-t", f"{duracao:.3f}"]
    cmd += ["-map", "0:v:0", "-an", "-vf", ",".join(filtros), "-fps_mode", "passthrough",
            "-frames:v", str(n_alvo), *cod, "-start_number", "0", str(pasta / f"%05d.{formato}")]
    if rife:
        _rife_pipeline(src, pasta, cmd, filtros, fps_src, fps_out, cod, formato, inicio, duracao, rife)
        usou = "rife-ncnn-vulkan"
    else:
        r = subprocess.run(cmd)
        if r.returncode != 0:
            sys.exit("[edin] ffmpeg falhou ao extrair os quadros")
    quadros = sorted(pasta.glob(f"*.{formato}"))
    n = len(quadros)
    if not n:
        sys.exit("[edin] nenhum quadro extraído")
    import cv2

    im = cv2.imread(str(quadros[0]))
    h, w = im.shape[:2]
    meta = {"n": n, "fps": round(fps_out, 6), "largura": w, "altura": h, "padrao": f"%05d.{formato}",
            "primeiro": 0, "duracao": round(n / fps_out, 4), "origem": src.name, "fps_origem": round(fps_src, 6),
            "interpolacao": usou}
    (pasta / "quadros.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    # carregado pelo kit com <script> (file:// não deixa fetch de JSON); chave = URL absoluta deste script
    (pasta / "quadros.js").write_text(
        "(window.EDIN_CLIPES = window.EDIN_CLIPES || {})[document.currentScript.src] = "
        + json.dumps(meta, ensure_ascii=False) + ";\n")
    mb = sum(q.stat().st_size for q in quadros) / 1e6
    print(f"[edin] {n} quadros {w}x{h} a {fps_out:g} fps ({usou}) em {pasta} ({mb:.0f} MB, "
          f"{time.time() - t0:.1f} s)")
    return pasta


def _rife_pipeline(src, pasta, cmd, filtros, fps_src, fps_out, cod, formato, inicio, duracao, rife):
    """RIFE (rife-ncnn-vulkan): extrai PNG na taxa original, interpola na GPU e reamostra para fps_out."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="edin_rife_") as tmp:
        a, b = Path(tmp) / "in", Path(tmp) / "out"
        a.mkdir(), b.mkdir()
        base = [f for f in filtros if not f.startswith(("fps=", "minterpolate"))]
        c1 = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + (["-ss", f"{inicio:.3f}"] if inicio else []) + \
             ["-i", str(src)] + (["-t", f"{duracao:.3f}"] if duracao else []) + \
             ["-map", "0:v:0", "-vf", ",".join(base), str(a / "%08d.png")]
        subprocess.run(c1, check=True)
        n_in = len(list(a.glob("*.png")))
        n_out = max(2, round(n_in * fps_out / fps_src))
        subprocess.run([rife, "-i", str(a), "-o", str(b), "-n", str(n_out), "-m", "rife-v4.6"], check=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", f"{fps_out:g}",
                        "-i", str(b / "%08d.png"), *cod, "-start_number", "0", str(pasta / f"%05d.{formato}")],
                       check=True)


def cmd_quadros(a):
    # sem a trava pesada (pesado.lock): é só ffmpeg na CPU, pico medido de 1,2 GB no minterpolate mci em 1920x1080
    extrair(a.clipe, a.fps, a.largura, a.formato, a.qualidade, a.interp, a.out, a.inicio, a.duracao)


def add_parser(sp):
    s = sp.add_parser("quadros", help="clipe mp4 -> sequência de quadros + quadros.js para EdinVideo.clipe (kit HTML)")
    s.add_argument("clipe", help="clipe.mp4 (os quadros vão para a pasta clipe/ ao lado)")
    s.add_argument("--fps", type=float, help="taxa de saída (padrão: a do clipe). Acima da original, interpola")
    s.add_argument("--interp", choices=["mci", "blend", "dup", "rife"], default="mci",
                   help="como subir a taxa: mci (minterpolate com compensação de movimento, padrão), blend "
                        "(mistura), dup (repete quadros), rife (rife-ncnn-vulkan, se instalado)")
    s.add_argument("--largura", type=int, help="largura dos quadros (padrão: a do clipe, no máximo 1080)")
    s.add_argument("--formato", choices=["jpg", "webp"], default="jpg")
    s.add_argument("--qualidade", type=int, help="jpg: -q:v (2 = alta, padrão); webp: 0 a 100 (padrão 92)")
    s.add_argument("--inicio", type=float, default=0, help="começa neste ponto do clipe (s)")
    s.add_argument("--duracao", type=float, help="só estes segundos")
    s.add_argument("-o", "--out", help="pasta de saída (padrão: ao lado do clipe, com o nome dele)")
    s.set_defaults(fn=cmd_quadros)
