"""Upscale e nitidez de fontes ruins (720p do WhatsApp, gravação de tela comprimida), grátis e local.

Modos:
- "fast": tudo no ffmpeg. `hqdn3d` leve (tira o "chuvisco" da compressão) + `scale` lanczos + `cas` (nitidez
  adaptativa por contraste). Roda mais rápido que tempo real.
- "esrgan": Real-ESRGAN ncnn/Vulkan (BSD-3, binário oficial de 47 MB, sem Python), na GPU por Vulkan.
  Modelo padrão `realesr-animevideov3` (bom para tela, texto e motion; estável entre quadros). Quadros saem do
  ffmpeg por pipe, são ampliados em lotes e voltam por pipe: o disco só guarda um lote por vez.
  Se o Vulkan/binário falhar, cai para "fast" com aviso.

O resultado sai com o áudio original (copiado), mesmo fps e mesma duração, e fica em cache por arquivo + modo em
~/.local/share/edin/cache/enhance (o plano com `"enhance"` reaproveita o cache em todo render).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import queue
import threading
import time
import zipfile
from pathlib import Path

from .utils import probe, run
from .voice import HOME, _download

ESRGAN_URL = ("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/"
              "realesrgan-ncnn-vulkan-20220424-{}.zip")
ESRGAN_ZIP = {"Linux": "ubuntu", "Darwin": "macos", "Windows": "windows"}
ESRGAN_DIR = HOME / "bin" / "realesrgan"
DEFAULT_MODEL = "realesr-animevideov3"
CACHE = HOME / "cache" / "enhance"

# denoise leve (espacial 1.5, temporal 6 só tira o chuvisco do H.264 sem borrar movimento) e nitidez CAS 0.5
FAST_DENOISE = "hqdn3d=1.5:1.5:6:6"
FAST_CAS = 0.5


def esrgan_binary(download: bool = True) -> Path | None:
    """Caminho do realesrgan-ncnn-vulkan (baixa e extrai o zip oficial uma vez). None se indisponível."""
    exe_name = "realesrgan-ncnn-vulkan" + (".exe" if platform.system() == "Windows" else "")
    found = shutil.which(exe_name)
    if found:
        return Path(found)
    exe = ESRGAN_DIR / exe_name
    if exe.exists():
        return exe
    tag = ESRGAN_ZIP.get(platform.system())
    if not tag or not download:
        return None
    zpath = _download(ESRGAN_URL.format(tag), HOME / "bin" / f"realesrgan-{tag}.zip")
    try:
        ESRGAN_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as z:
            for m in z.infolist():
                name = m.filename.split("/", 1)[-1] if m.filename.startswith("realesrgan-ncnn-vulkan-") else m.filename
                if m.is_dir() or not (name == exe_name or (name.startswith("models/") and ".." not in name)):
                    continue
                dest = ESRGAN_DIR / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(m) as src, open(dest, "wb") as f:
                    shutil.copyfileobj(src, f)
    finally:
        zpath.unlink(missing_ok=True)
    if not exe.exists():
        return None
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return exe


def _model_args(model: str, scale: int) -> tuple[list, int]:
    """Argumentos do binário e o fator nativo do modelo (o animevideov3 tem x2/x3/x4; os outros só x4)."""
    if model == "realesr-animevideov3":
        native = min(4, max(2, scale))
        return ["-n", model, "-s", str(native)], native
    return ["-n", model, "-s", "4"], 4


def _cache_path(src: str, mode: str, scale: float, model: str) -> Path:
    st = Path(src).stat()
    key = json.dumps([2, str(Path(src).resolve()), st.st_size, int(st.st_mtime), mode, scale,  # 2: versão do pipeline
                      model if mode == "esrgan" else FAST_DENOISE + str(FAST_CAS)])
    h = hashlib.sha1(key.encode()).hexdigest()[:12]
    tag = f"{mode}{'-' + model if mode == 'esrgan' and model != DEFAULT_MODEL else ''}_x{scale:g}"
    return CACHE / f"{Path(src).stem}_{tag}_{h}.mp4"


# conversão YUV <-> RGB com arredondamento exato e matriz BT.709 explícita: sem isso o vai e volta do RGB
# escurecia os pretos em ~1,5 nível (fundo de tela escura ficava visivelmente mais preto que o original)
_RGB = "scale=flags=accurate_rnd+full_chroma_int"
_YUV = "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p"
_BT709 = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def _even(x: float) -> int:
    return max(2, int(round(x / 2) * 2))


def _encode_args(out: Path, fps: float, verbose: bool) -> list:
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", f"{fps:.6g}",
            "-c:a", "copy", "-movflags", "+faststart", str(out)]


def enhance_fast(src: str, out: Path, scale: float, verbose: bool = False) -> Path:
    info = probe(src)
    w, h = _even(info["w"] * scale), _even(info["h"] * scale)
    vf = f"{FAST_DENOISE},scale={w}:{h}:flags=lanczos,cas=strength={FAST_CAS},format=yuv420p"
    tmp = out.with_suffix(".part.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
         *_encode_args(tmp, info["fps"], verbose)], verbose=verbose)
    tmp.rename(out)
    return out


def _pick_gpu(exe: Path, model: str, scale: int, tile: int) -> int | None:
    """Roda o binário num quadro pequeno: confirma Vulkan e modelo e escolhe a GPU dedicada.
    O binário usa a GPU 0, que em notebook costuma ser a integrada (Intel): 15x mais lenta que a NVIDIA.
    `llvmpipe` é Vulkan na CPU: lento demais para vídeo, conta como indisponível. EDIN_GPU=n força uma GPU."""
    import re

    import numpy as np
    import cv2

    d = CACHE / "teste_vulkan"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    cv2.imwrite(str(d / "a.png"), (np.random.default_rng(0).random((32, 32, 3)) * 255).astype("uint8"))
    args, _ = _model_args(model, scale)

    def test(g):
        (d / "b.png").unlink(missing_ok=True)
        cmd = [str(exe), "-i", str(d / "a.png"), "-o", str(d / "b.png"), *args, "-t", str(tile or 0),
               "-m", str(exe.parent / "models")] + (["-g", str(g)] if g is not None else [])
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, str(e)
        return p.returncode == 0 and (d / "b.png").exists(), (p.stderr or "") + (p.stdout or "")

    try:
        if os.environ.get("EDIN_GPU"):
            ok, log = test(int(os.environ["EDIN_GPU"]))
            return int(os.environ["EDIN_GPU"]) if ok else None
        ok, log = test(None)
        gpus = dict(re.findall(r"^\[(\d+) ([^\]]+)\]", log, re.M))
        def rank(item):
            name = item[1].lower()
            if "llvmpipe" in name or "swiftshader" in name:
                return 9
            return 0 if any(k in name for k in ("nvidia", "geforce", "radeon", "amd", "apple")) else 1
        for gid, name in sorted(gpus.items(), key=rank):
            if rank((gid, name)) == 9:
                break
            if test(int(gid))[0]:
                print(f"[edin] Real-ESRGAN na GPU {gid}: {name}")
                return int(gid)
        print(f"[edin] Real-ESRGAN sem GPU Vulkan utilizável: {log.strip()[-300:]}")
        return None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def enhance_esrgan(src: str, out: Path, scale: float, model: str = DEFAULT_MODEL, tile: int = 0,
                   batch: int = 60, verbose: bool = False) -> Path:
    import numpy as np
    import cv2

    exe = esrgan_binary()
    gpu = None if exe is None else _pick_gpu(exe, model, int(round(scale)), tile)
    if gpu is None:
        raise RuntimeError("Real-ESRGAN/Vulkan indisponível")
    info = probe(src)
    w, h, fps, dur = info["w"], info["h"], info["fps"], info["duration"]
    total = max(1, int(round(dur * fps)))
    args, native = _model_args(model, int(round(scale)))
    args += ["-g", str(gpu)]
    ow, oh = _even(w * scale), _even(h * scale)
    resize = (w * native, h * native) != (ow, oh)  # ex.: x4plus com --scale 2 -> reduz com lanczos
    wd = out.parent / (out.stem + "_quadros")
    shutil.rmtree(wd, ignore_errors=True)
    wd.mkdir(parents=True)
    # CFR no fps da fonte: o filtro fps decide quadro a quadro pelo tempo (sincronia mantida com o áudio copiado)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-map", "0:v:0", "-vf", f"fps={fps:.6g},{_RGB}",
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    tmp = out.with_suffix(".part.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{ow}x{oh}", "-framerate", f"{fps:.6g}", "-i", "-", "-i", src,
                            "-map", "0:v:0", "-map", "1:a?", "-t", f"{dur:.6f}", "-vf", _YUV, *_BT709,
                            *_encode_args(tmp, fps, verbose)],
                           stdin=subprocess.PIPE)
    fsize = w * h * 3
    # três etapas em paralelo (a GPU é o gargalo, ~6 quadros/s numa RTX 4050 em 720p -> 1440p):
    # ler quadros e gravar PNG do lote k+1 | Real-ESRGAN no lote k | ler o lote k-1 e mandar para o encoder
    q_in, q_out = queue.Queue(maxsize=1), queue.Queue(maxsize=1)
    err = []

    def reader():
        k = 0
        try:
            while True:
                d = wd / f"lote{k:05d}"
                (d / "in").mkdir(parents=True)
                n = 0
                while n < batch:
                    buf = dec.stdout.read(fsize)
                    if len(buf) < fsize:
                        break
                    cv2.imwrite(str(d / "in" / f"{n:05d}.png"), np.frombuffer(buf, np.uint8).reshape(h, w, 3),
                                [cv2.IMWRITE_PNG_COMPRESSION, 1])
                    n += 1
                if n == 0:
                    shutil.rmtree(d, ignore_errors=True)
                    break
                q_in.put((d, n))
                k += 1
        except BaseException as e:  # noqa: BLE001
            err.append(e)
        finally:
            q_in.put(None)

    def writer():
        try:
            while (item := q_out.get()) is not None:
                d, n = item
                for k in range(n):
                    img = cv2.imread(str(d / "out" / f"{k:05d}.png"), cv2.IMREAD_COLOR)
                    if img is None:
                        raise RuntimeError(f"Real-ESRGAN não gerou o quadro {k} de {d.name}")
                    if resize:
                        img = cv2.resize(img, (ow, oh), interpolation=cv2.INTER_LANCZOS4)
                    try:
                        enc.stdin.write(img.tobytes())
                    except BrokenPipeError:  # o encoder já chegou na duração (-t) e fechou: sobra 1 quadro
                        pass
                shutil.rmtree(d, ignore_errors=True)
        except BaseException as e:  # noqa: BLE001
            err.append(e)
            while q_out.get() is not None:  # não trava o laço principal
                pass

    threads = [threading.Thread(target=reader, daemon=True), threading.Thread(target=writer, daemon=True)]
    for t in threads:
        t.start()
    done, t0 = 0, time.time()
    try:
        while (item := q_in.get()) is not None:
            d, n = item
            if err:
                break
            (d / "out").mkdir()
            p = subprocess.run([str(exe), "-i", str(d / "in"), "-o", str(d / "out"), *args, "-t", str(tile or 0),
                                "-m", str(exe.parent / "models"), "-f", "png", "-j", "2:2:6"],
                               capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"Real-ESRGAN falhou (tente --tile 200): {(p.stderr or '')[-400:]}")
            shutil.rmtree(d / "in", ignore_errors=True)
            q_out.put((d, n))
            done += n
            el = time.time() - t0
            rate = done / max(el, 1e-6)
            print(f"\r[edin] Real-ESRGAN {done}/{max(total, done)} quadros ({rate:.1f} q/s, "
                  f"faltam ~{max(0, total - done) / max(rate, 1e-6):.0f}s)", end="", flush=True)
        q_out.put(None)
        threads[1].join()
        print()
        if err:
            raise err[0]
        try:
            enc.stdin.close()
        except BrokenPipeError:
            pass
        if enc.wait() != 0:
            raise RuntimeError("ffmpeg falhou ao remontar o vídeo")
        dec.wait()
    except BaseException:
        for pr in (dec, enc):
            pr.kill()
        tmp.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(wd, ignore_errors=True)
    tmp.rename(out)
    return out


def enhance(src: str, out: str | None = None, mode: str = "fast", scale: float = 2, model: str = DEFAULT_MODEL,
            tile: int = 0, verbose: bool = False, cache: bool = True) -> str:
    """Melhora `src` e devolve o caminho do resultado (do cache, se já feito). `out` copia o resultado para lá."""
    if mode not in ("fast", "esrgan"):
        raise ValueError(f"modo de enhance desconhecido: {mode} (use fast ou esrgan)")
    CACHE.mkdir(parents=True, exist_ok=True)
    cpath = _cache_path(src, mode, scale, model)
    if not (cache and cpath.exists()):
        t0 = time.time()
        dur = probe(src)["duration"]
        if mode == "esrgan":
            try:
                print(f"[edin] Melhorando {Path(src).name} com Real-ESRGAN ({model}, x{scale:g})...")
                enhance_esrgan(src, cpath, scale, model, tile, verbose=verbose)
            except Exception as e:
                print(f"\n[edin] AVISO: Real-ESRGAN indisponível ({str(e).splitlines()[0][:200]}). "
                      "Usando o modo fast (ffmpeg).", file=sys.stderr)
                mode = "fast"
                cpath = _cache_path(src, mode, scale, model)
        if mode == "fast" and not (cache and cpath.exists()):
            print(f"[edin] Melhorando {Path(src).name} (fast: denoise + lanczos + cas, x{scale:g})...")
            enhance_fast(src, cpath, scale, verbose)
        el = time.time() - t0
        print(f"[edin] {mode}: {el:.1f}s para {dur:.1f}s de vídeo ({el / max(dur, 0.01):.2f}s por segundo)")
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cpath, out)
        return str(Path(out).resolve())
    return str(cpath)


def apply_to_plan(plan: dict, verbose: bool = False) -> dict:
    """Gancho do render: `"enhance": {"mode": "fast|esrgan", "scale": 2}` troca a fonte principal (e os segmentos
    que usam o mesmo arquivo) pela versão melhorada do cache. Tempos não mudam (mesmo fps e duração)."""
    cfg = plan.get("enhance")
    if not cfg:
        return plan
    if isinstance(cfg, str):
        cfg = {"mode": cfg}
    src = plan["source"]
    new = enhance(src, None, cfg.get("mode", "fast"), float(cfg.get("scale", 2)), cfg.get("model", DEFAULT_MODEL),
                  int(cfg.get("tile", 0)), verbose)
    plan["source"] = new
    for seg in plan["segments"]:
        if seg.get("src") == src:
            seg["src"] = new
    return plan


def quality(a: str, ref: str) -> dict:
    """SSIM e PSNR (Y) de `a` contra a referência `ref` (redimensiona `a` para o tamanho da referência)."""
    r, fps = probe(ref), probe(a)["fps"]
    # os dois no mesmo fps: celular grava com fps variável e o ssim/psnr compara quadro a quadro
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", a, "-i", ref, "-lavfi",
                        f"[0:v]fps={fps:.6g},scale={r['w']}:{r['h']}:flags=lanczos,setsar=1[a];"
                        f"[1:v]fps={fps:.6g},setsar=1[b];"
                        "[a]split[a1][a2];[b]split[b1][b2];[a1][b1]ssim;[a2][b2]psnr", "-f", "null", "-"],
                       capture_output=True, text=True)
    out = {}
    for line in p.stderr.splitlines():
        if "SSIM Y:" in line:
            out["ssim"] = float(line.split("All:")[1].split()[0])
            out["ssim_y"] = float(line.split("Y:")[1].split()[0])
        if "PSNR y:" in line:
            out["psnr"] = float(line.split("average:")[1].split()[0])
            out["psnr_y"] = float(line.split(" y:")[1].split()[0])
    return out


if __name__ == "__main__":  # pragma: no cover
    print(enhance(sys.argv[1], None, sys.argv[2] if len(sys.argv) > 2 else "fast"))
