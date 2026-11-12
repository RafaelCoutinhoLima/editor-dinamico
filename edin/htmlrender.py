"""Página HTML animada -> vídeo, quadro a quadro, determinístico (ver docs/HTML.md).

Cada worker é um Chrome headless próprio, falado por CDP no `--remote-debugging-pipe` (fds 3 e 4, JSON terminado
em \\0): só biblioteca padrão do Python, sem Playwright/Puppeteer, e com acesso direto a `Page.captureScreenshot`
com `optimizeForSpeed`. Os workers pegam faixas curtas do tempo em ordem; o laço principal reordena os quadros e
manda RGB cru ao ffmpeg por pipe (nada de milhares de PNG no disco, a não ser com --frames-dir).

Dois modos:
- contrato: a página define `window.EDIN = {duration, seek(t)}`. Para cada quadro: `await EDIN.seek(t)`, 2 rAF reais,
  captura.
- livre (sem EDIN): relógio virtual injetado antes de qualquer script (Date, performance.now, rAF, setTimeout,
  setInterval e Math.random com semente) + `document.getAnimations()` pausadas em `currentTime`. O worker que pula
  uma faixa "avança" o relógio por todos os quadros intermediários sem capturar, então a página vê exatamente a
  mesma sequência de quadros com 1 ou 16 workers.
"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import quote

from .enhance import _BT709, _YUV

CHROME_CANDIDATES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
WARMUP = 2  # quadros pintados (sem captura) antes de cada faixa, para o compositor ter o mesmo histórico
CHUNK = 6  # quadros por faixa: curta para a fila de reordenação (RGB cru, 6 MB por quadro em 1080x1920) ficar pequena
EPOCH_MS = 1767225600000  # Date.now() do relógio virtual em t=0: 2026-01-01 00:00:00 UTC (fixo = determinístico)
SEED = 20261112

# Relógio virtual. Instalado antes de qualquer script da página. Começa congelado em t=0; no modo contrato o
# renderizador chama __edin.release() e tudo volta ao relógio real (timers e rAF pendentes migram para o real).
CLOCK_JS = r"""
(() => {
  if (window.__edin) return;
  const W = window, R = {
    now: performance.now.bind(performance), raf: W.requestAnimationFrame.bind(W),
    caf: W.cancelAnimationFrame.bind(W), st: W.setTimeout.bind(W), ct: W.clearTimeout.bind(W),
    si: W.setInterval.bind(W), ci: W.clearInterval.bind(W), Date: W.Date, random: Math.random,
  };
  const EPOCH = __EPOCH__;
  let vt = 0, virtual = true, nextId = 1 << 30;
  const timers = new Map(), rafs = new Map(), moved = new Map(), born = new WeakMap();
  // Math.random com semente (mulberry32): mesma sequência em toda execução e em todo worker
  let s = __SEED__ >>> 0;
  Math.random = () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  function VDate(...a) {
    const now = virtual ? EPOCH + vt : R.Date.now();
    if (!new.target) return new R.Date(now).toString();
    return a.length ? new R.Date(...a) : new R.Date(now);
  }
  VDate.prototype = R.Date.prototype; VDate.parse = R.Date.parse; VDate.UTC = R.Date.UTC;
  VDate.now = () => virtual ? EPOCH + vt : R.Date.now();
  W.Date = VDate;
  performance.now = () => virtual ? vt : R.now();
  const fnOf = (f) => typeof f === 'function' ? f : new Function(String(f));
  function addTimer(f, ms, args, every) {
    const id = nextId++; ms = Math.max(0, Number(ms) || 0);
    timers.set(id, {f: fnOf(f), args, due: vt + ms, every: every ? Math.max(1, ms) : 0});
    return id;
  }
  W.setTimeout = (f, ms, ...a) => virtual ? addTimer(f, ms, a, false) : R.st(f, ms, ...a);
  W.setInterval = (f, ms, ...a) => virtual ? addTimer(f, ms, a, true) : R.si(f, ms, ...a);
  const clear = (id) => { if (timers.delete(id)) return; const r = moved.get(id);
    if (r !== undefined) { R.ct(r); R.ci(r); moved.delete(id); } else { R.ct(id); R.ci(id); } };
  W.clearTimeout = clear; W.clearInterval = clear;
  W.requestAnimationFrame = (cb) => { if (!virtual) return R.raf(cb); const id = nextId++; rafs.set(id, cb); return id; };
  W.cancelAnimationFrame = (id) => { if (!rafs.delete(id)) { const r = moved.get(id); R.caf(r !== undefined ? r : id); } };
  const report = (e) => { try { W.reportError(e); } catch (_) { R.st(() => { throw e; }); } };

  function advance(t) {  // t em ms
    let guard = 0;
    for (;;) {  // timers vencidos, em ordem de vencimento
      let id = null, tm = null;
      for (const [k, v] of timers) if (v.due <= t && (!tm || v.due < tm.due)) { id = k; tm = v; }
      if (!tm || ++guard > 20000) break;
      vt = Math.max(vt, tm.due);
      if (tm.every) tm.due += tm.every; else timers.delete(id);
      try { tm.f.apply(W, tm.args); } catch (e) { report(e); }
    }
    vt = t;
    const cbs = [...rafs.values()]; rafs.clear();
    for (const cb of cbs) { try { cb(t); } catch (e) { report(e); } }
    for (const a of document.getAnimations()) {  // CSS animations/transitions e WAAPI: tempo desde que surgiram
      if (!born.has(a)) born.set(a, t);
      try { a.pause(); a.currentTime = Math.max(0, t - born.get(a)); } catch (e) {}
    }
  }
  function release() {
    if (!virtual) return; virtual = false;
    for (const [id, tm] of timers) {
      const ms = Math.max(0, tm.due - vt);
      moved.set(id, tm.every ? R.si(() => tm.f.apply(W, tm.args), tm.every) : R.st(() => tm.f.apply(W, tm.args), ms));
    }
    timers.clear();
    for (const [id, cb] of rafs) moved.set(id, R.raf(cb));
    rafs.clear();
  }
  const raf2 = () => new Promise((r) => R.raf(() => R.raf(r)));
  async function ready() {
    if (document.readyState !== 'complete') await new Promise((r) => W.addEventListener('load', r, {once: true}));
    await document.fonts.ready;
    await Promise.all([...document.images].map((i) => (i.complete ? Promise.resolve() :
      new Promise((r) => { i.addEventListener('load', r, {once: true}); i.addEventListener('error', r, {once: true}); }))
      .then(() => i.decode ? i.decode().catch(() => {}) : 0)));
    await document.fonts.ready;
    return true;
  }
  W.__edin = {advance, ff: (ts) => { for (const t of ts) advance(t); }, release, raf2, ready,
              pump: () => advance(vt), get virtual() { return virtual; }};
})();
""".replace("__EPOCH__", str(EPOCH_MS)).replace("__SEED__", str(SEED))


class PageError(RuntimeError):
    pass


def find_chrome() -> str | None:
    """Chrome/Chromium do sistema (EDIN_CHROME força um caminho)."""
    env = os.environ.get("EDIN_CHROME")
    if env:
        return env if Path(env).exists() else shutil.which(env)
    for name in CHROME_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    for pat in ("chromium-*/chrome-linux*/chrome",):  # Chromium do Playwright, se houver
        hits = sorted((Path.home() / ".cache" / "ms-playwright").glob(pat))
        if hits:
            return str(hits[-1])
    return None


def default_workers(w: int, h: int) -> int:
    """Metade dos núcleos, limitado pela RAM livre (~0,5 GB por Chrome em 1080x1920)."""
    cpu = os.cpu_count() or 2
    avail_mb = 4096
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable:"):
                avail_mb = int(line.split()[1]) // 1024
    except OSError:
        pass
    per = 250 + w * h * 4 * 12 // (1 << 20)  # base do Chrome + texturas/buffers proporcionais à área
    return max(1, min(cpu // 2, int(avail_mb * 0.7 / per)))


class Chrome:
    """Um Chrome headless com uma aba, falado por CDP no pipe. Eventos de erro da página vão para `on_log`."""

    def __init__(self, exe: str, on_log, tag: str = ""):
        self.on_log, self.tag = on_log, tag
        self.udd = tempfile.mkdtemp(prefix="edin_chrome_")
        to_chrome_r, self._w = os.pipe()
        self._r, from_chrome_w = os.pipe()
        # cópias acima de 10 e com CLOEXEC: não vazam para os Chromes dos outros workers
        a = fcntl.fcntl(to_chrome_r, fcntl.F_DUPFD_CLOEXEC, 10)
        b = fcntl.fcntl(from_chrome_w, fcntl.F_DUPFD_CLOEXEC, 10)
        os.close(to_chrome_r)
        os.close(from_chrome_w)
        args = [exe, "--headless", "--remote-debugging-pipe", f"--user-data-dir={self.udd}", "--no-first-run",
                "--no-default-browser-check", "--disable-extensions", "--disable-sync", "--hide-scrollbars",
                "--mute-audio", "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows", "--disable-features=Translate,MediaRouter",
                "--allow-file-access-from-files", "--force-color-profile=srgb", "--disable-lcd-text",
                "--autoplay-policy=no-user-gesture-required", *os.environ.get("EDIN_CHROME_FLAGS", "").split(),
                "about:blank"]
        # posix_spawn com dup2 para os fds 3/4 que o Chrome espera (sem preexec_fn: seguro com várias threads)
        null = os.devnull
        try:
            self.pid = os.posix_spawn(exe, args, os.environ, setpgroup=0, file_actions=[
                (os.POSIX_SPAWN_DUP2, a, 3), (os.POSIX_SPAWN_DUP2, b, 4),
                (os.POSIX_SPAWN_OPEN, 0, null, os.O_RDONLY, 0), (os.POSIX_SPAWN_OPEN, 1, null, os.O_WRONLY, 0),
                (os.POSIX_SPAWN_OPEN, 2, null, os.O_WRONLY, 0)])
        finally:
            os.close(a)
            os.close(b)
        self.buf = bytearray()
        self.nid = 0
        self.session = None
        self.events: list = []

    # ---------------------------------------------------------------- protocolo
    def _read_msg(self, timeout: float) -> dict:
        end = time.time() + timeout
        while True:
            i = self.buf.find(b"\0")
            if i >= 0:
                msg = bytes(self.buf[:i])
                del self.buf[:i + 1]
                return json.loads(msg)
            left = end - time.time()
            if left <= 0 or not select.select([self._r], [], [], left)[0]:
                raise TimeoutError
            chunk = os.read(self._r, 1 << 22)
            if not chunk:
                raise PageError(f"O Chrome{self.tag} fechou (travou ou faltou memória).")
            self.buf += chunk

    def _event(self, d: dict) -> None:
        m, p = d.get("method"), d.get("params", {})
        if m == "Runtime.exceptionThrown":
            ex = p.get("exceptionDetails", {})
            desc = (ex.get("exception") or {}).get("description") or ex.get("text", "")
            where = f" ({ex.get('url', '').rsplit('/', 1)[-1].split('?')[0]}:{ex.get('lineNumber', 0) + 1})" if ex.get("url") else ""
            self.on_log("erro JS", desc.splitlines()[0][:300] + where)
        elif m == "Runtime.consoleAPICalled" and p.get("type") in ("error", "warning", "assert"):
            txt = " ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))
            self.on_log("console." + ("warn" if p["type"] == "warning" else p["type"]), txt[:300])
        elif m == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
            e = p["entry"]
            self.on_log("navegador", (e.get("text", "") + " " + e.get("url", ""))[:300])
        elif m == "Inspector.targetCrashed":
            raise PageError(f"A aba do Chrome{self.tag} travou (falta de memória?).")
        self.events.append(m)
        del self.events[:-50]

    def send(self, method: str, params: dict | None = None, timeout: float = 60.0, session: bool = True) -> dict:
        self.nid += 1
        msg = {"id": self.nid, "method": method, "params": params or {}}
        if session and self.session:
            msg["sessionId"] = self.session
        os.write(self._w, json.dumps(msg).encode() + b"\0")
        end = time.time() + timeout
        while True:
            try:
                d = self._read_msg(max(0.0, end - time.time()))
            except TimeoutError:
                raise TimeoutError(f"{method} sem resposta em {timeout:.0f}s") from None
            if d.get("id") == self.nid:
                if "error" in d:
                    raise PageError(f"{method}: {d['error'].get('message')}")
                return d.get("result", {})
            if "method" in d:
                self._event(d)

    def wait_event(self, name: str, timeout: float) -> bool:
        end = time.time() + timeout
        if name in self.events:
            return True
        while time.time() < end:
            try:
                d = self._read_msg(end - time.time())
            except TimeoutError:
                return False
            if "method" in d:
                self._event(d)
                if d["method"] == name:
                    return True
        return False

    def eval(self, expr: str, timeout: float = 60.0):
        r = self.send("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True},
                      timeout=timeout)
        if "exceptionDetails" in r:
            ex = r["exceptionDetails"]
            desc = (ex.get("exception") or {}).get("description") or ex.get("text", "")
            raise PageError(desc.splitlines()[0][:400] if desc else "erro de JS")
        return r.get("result", {}).get("value")

    # ---------------------------------------------------------------- página
    def open(self, url: str, w: int, h: int, scale: float, timeout: float) -> None:
        targets = self.send("Target.getTargets", session=False, timeout=30)["targetInfos"]
        tid = next(t["targetId"] for t in targets if t["type"] == "page")
        self.session = self.send("Target.attachToTarget", {"targetId": tid, "flatten": True}, session=False)[
            "sessionId"]
        for m in ("Page.enable", "Runtime.enable", "Log.enable", "Inspector.enable"):
            self.send(m)
        self.send("Page.addScriptToEvaluateOnNewDocument", {"source": CLOCK_JS})
        self.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": scale,
                                                         "mobile": False, "screenWidth": w, "screenHeight": h})
        self.events.clear()
        r = self.send("Page.navigate", {"url": url})
        if r.get("errorText"):
            raise PageError(f"não abriu {url}: {r['errorText']}")
        if not self.wait_event("Page.loadEventFired", timeout):
            raise PageError(f"a página não terminou de carregar em {timeout:.0f}s")
        self.eval("__edin.ready()", timeout=timeout)

    def capture(self, fmt: str) -> bytes:
        p = {"format": fmt, "optimizeForSpeed": True, "fromSurface": True, "captureBeyondViewport": False}
        if fmt == "jpeg":
            p["quality"] = 92
        return base64.b64decode(self.send("Page.captureScreenshot", p)["data"])

    def close(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.pid, sig)
            except (ProcessLookupError, PermissionError):
                pass
            end = time.time() + 5
            try:
                while time.time() < end and os.waitpid(self.pid, os.WNOHANG) == (0, 0):
                    time.sleep(0.05)
                if os.waitpid(self.pid, os.WNOHANG) != (0, 0):
                    break
            except ChildProcessError:
                break
        for fd in (self._r, self._w):
            try:
                os.close(fd)
            except OSError:
                pass
        shutil.rmtree(self.udd, ignore_errors=True)


def _sub_times(i: int, fps: float, k: int, shutter: float) -> list[float]:
    """Tempos (s) dos subquadros do quadro i: t + j/K da fração do obturador (180° = metade do intervalo)."""
    t = i / fps
    if k <= 1:
        return [t]
    return [t + j * (shutter / 360.0) / (k * fps) for j in range(k)]


class _Job:
    """Estado compartilhado: distribuição de faixas, fila de reordenação e erros."""

    def __init__(self, first: int, n: int, ahead: int):
        self.first, self.n, self.ahead = first, n, ahead
        self.cond = threading.Condition()
        self.next_chunk = 0
        self.written = 0
        self.results: dict[int, tuple] = {}
        self.error: BaseException | None = None
        self.seen: set = set()
        self.log_lock = threading.Lock()

    def log(self, kind: str, msg: str) -> None:
        key = (kind, msg)
        with self.log_lock:
            if key in self.seen or len(self.seen) > 60:
                return
            self.seen.add(key)
            print(f"\n[edin] {kind} na página: {msg}", file=sys.stderr, flush=True)


def _worker(idx: int, exe: str, url: str, cfg: dict, job: _Job, ready: list, start_evt: threading.Event):
    import cv2
    import numpy as np

    chrome = None
    try:
        chrome = Chrome(exe, job.log, f" (worker {idx + 1})")
        chrome.open(url, cfg["w"], cfg["h"], cfg["scale"], cfg["timeout"])
        mode, dur = cfg["mode"], None
        has = "!!(window.EDIN && typeof window.EDIN.seek === 'function')"
        if mode == "free":
            pass
        elif mode == "contract" or cfg["duration"] is None:
            end = time.time() + cfg["timeout"]
            while not chrome.eval(has):  # rAF/timers de 0 ms rodam (tempo parado) enquanto espera o EDIN
                if time.time() > end:
                    raise PageError(
                        f"window.EDIN não apareceu em {cfg['timeout']:.0f}s. A página precisa definir "
                        "window.EDIN = {duration, seek(t)} (modo contrato) ou rode com --duration S (modo livre).")
                chrome.eval("__edin.pump()")
                time.sleep(0.05)
            mode = "contract"
        else:  # auto com --duration: contrato se o EDIN já existir depois do carregamento, senão livre
            mode = "contract" if chrome.eval(has) else "free"
        if mode == "contract":
            chrome.eval("__edin.release()")
            dur = chrome.eval("Number(window.EDIN.duration)")
        ready[idx] = (mode, dur)
        start_evt.wait()
        if job.error:
            return
        fps, k, shutter = cfg["fps"], cfg["motion_blur"], cfg["shutter"]
        fmt = "jpeg" if cfg["draft"] else "png"
        keep_png = cfg["frames_dir"] is not None and k == 1 and fmt == "png"
        pos = 0  # modo livre: próximo quadro cujo relógio ainda não foi avançado (sempre a partir do 0)
        last = None  # último quadro desenhado por este worker

        def step(i: int, t: float) -> None:
            """Leva a página ao instante t (s) e espera 2 rAF reais (o quadro está pintado)."""
            try:
                if mode == "contract":
                    chrome.eval(f"(async () => {{ await window.EDIN.seek({t!r}); await __edin.raf2(); }})()",
                                timeout=cfg["timeout"])
                else:
                    chrome.eval(f"__edin.advance({t * 1000!r}); __edin.raf2()", timeout=cfg["timeout"])
            except PageError as e:
                raise PageError(f"erro no quadro {i} (t={t:.3f}s): {e}") from None
            except TimeoutError:
                raise PageError(f"a página não respondeu em {cfg['timeout']:.0f}s no quadro {i} "
                                f"(t={t:.3f}s): EDIN.seek nunca terminou?") from None

        def fast_forward(to: int) -> None:
            """Modo livre: roda o relógio pelos quadros pos..to-1 sem pintar (outro worker os captura)."""
            nonlocal pos
            if pos < to:
                ts = [t * 1000 for f in range(pos, to) for t in _sub_times(f, fps, k, shutter)]
                for s in range(0, len(ts), 2000):
                    chrome.eval(f"__edin.ff({json.dumps(ts[s:s + 2000])})", timeout=cfg["timeout"])
                pos = to

        while True:
            with job.cond:
                while (job.error is None and job.next_chunk * CHUNK < job.n
                       and job.next_chunk * CHUNK >= job.written + job.ahead):
                    job.cond.wait(0.5)
                if job.error is not None:
                    return
                c = job.next_chunk
                job.next_chunk += 1
            a, b = c * CHUNK, min(job.n, (c + 1) * CHUNK)
            if a >= job.n:
                return
            i0 = job.first + a
            if last != i0 - 1:
                # aquecimento: pinta os WARMUP quadros anteriores sem capturar. O compositor do Chrome guarda
                # histórico (camadas promovidas, cache de raster); sem isso o 1º quadro da faixa saía, às vezes,
                # com o brilho/borda um pouco diferente do render sequencial (1 em 900 quadros)
                for f in range(max(0, i0 - WARMUP), i0):
                    if mode == "free":
                        if f < pos:  # o relógio virtual nunca volta
                            continue
                        fast_forward(f)
                    for t in _sub_times(f, fps, k, shutter):
                        step(f, t)
                    if mode == "free":
                        pos = f + 1
            for local in range(a, b):
                i = job.first + local
                if mode == "free":
                    fast_forward(i)
                acc, png = None, None
                for t in _sub_times(i, fps, k, shutter):
                    step(i, t)
                    png = chrome.capture(fmt)
                    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
                    if img is None:
                        raise PageError(f"captura vazia no quadro {i}")
                    if k > 1:
                        acc = img.astype(np.uint32) if acc is None else acc + img
                if k > 1:
                    img = ((acc + k // 2) // k).astype(np.uint8)
                last = i
                if mode == "free":
                    pos = i + 1
                with job.cond:
                    job.results[local] = (img, png if keep_png else None)
                    job.cond.notify_all()
    except BaseException as e:  # noqa: BLE001
        with job.cond:
            if job.error is None:
                job.error = e
            job.cond.notify_all()
        if ready[idx] is None:
            ready[idx] = e
    finally:
        if chrome:
            chrome.close()


def _ffmpeg_cmd(out: Path, w: int, h: int, fps: float, dur: float, crf: int, preset: str, audio: str | None,
                audio_start: float, silent: bool) -> list:
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
           "-framerate", f"{fps:.6g}", "-i", "-"]
    if audio:
        cmd += ["-ss", f"{audio_start:.6f}", "-i", audio]
    elif silent:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-map", "0:v:0"]
    if audio or silent:
        cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
        if audio:
            cmd += ["-af", "apad"]  # música mais curta que a cena: completa com silêncio até o fim
    cmd += ["-vf", _YUV, *_BT709, "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-r", f"{fps:.6g}", "-t", f"{dur:.6f}", "-movflags", "+faststart", str(out)]
    return cmd


def html_to_video(page: str, out: str, size: tuple[int, int] = (1080, 1920), fps: float = 30, duration=None,
                  start: float = 0.0, workers: int | None = None, motion_blur: int = 1, shutter: float = 180,
                  audio: str | None = None, audio_start: float | None = None, silent_audio: bool = False,
                  frames_dir: str | None = None, crf: int = 18, draft: bool = False, mode: str = "auto",
                  timeout: float = 30.0, preset: str | None = None) -> dict:
    import cv2

    exe = find_chrome()
    if not exe:
        raise SystemExit("[edin] Chrome/Chromium não encontrado. Instale o Google Chrome ou aponte EDIN_CHROME.")
    src = Path(page).resolve()
    if not src.exists():
        raise SystemExit(f"[edin] {page} não existe.")
    if mode == "free" and duration is None:
        raise SystemExit("[edin] Modo livre precisa de --duration S.")
    w, h = size
    scale = 0.5 if draft else 1.0
    ow, oh = int(round(w * scale)), int(round(h * scale))
    ow, oh = ow + ow % 2, oh + oh % 2
    n_workers = workers or default_workers(w, h)
    url = src.as_uri() + f"?w={w}&h={h}&fps={quote(f'{fps:g}')}&render=1"
    if motion_blur > 1:  # a página sabe que cada seek é 1 de K subtempos do obturador (blur sintético cobre 1/K)
        url += f"&mb={int(motion_blur)}&obturador={quote(f'{shutter:g}')}"
    cfg = {"w": w, "h": h, "scale": scale, "fps": fps, "duration": duration, "mode": mode, "timeout": timeout,
           "motion_blur": max(1, motion_blur), "shutter": shutter, "draft": draft, "frames_dir": frames_dir}

    first = int(round(start * fps))
    job = _Job(first, 0, (n_workers + 2) * CHUNK)  # janela: cada worker com uma faixa + folga
    ready: list = [None] * n_workers
    start_evt = threading.Event()
    threads = [threading.Thread(target=_worker, args=(k, exe, url, cfg, job, ready, start_evt), daemon=True)
               for k in range(n_workers)]
    t_open = time.time()
    print(f"[edin] {src.name}: abrindo {n_workers} Chrome(s) em {w}x{h}"
          f"{' (rascunho: captura em ' + f'{ow}x{oh})' if draft else ''}...", flush=True)
    for t in threads:
        t.start()
    enc = tmp = None
    try:
        while any(r is None for r in ready) and job.error is None:
            time.sleep(0.05)
        if job.error is not None:
            raise job.error
        modes = {r[0] for r in ready}
        if len(modes) > 1:
            raise PageError("os workers viram modos diferentes (EDIN aparece só às vezes?)")
        mode_used = modes.pop()
        page_dur = ready[0][1]
        if mode_used == "contract" and duration is None:
            if not page_dur or page_dur != page_dur or page_dur <= 0:
                raise PageError(f"EDIN.duration inválido ({page_dur}); defina a duração em segundos")
            length = page_dur - start
        else:
            length = float(duration)
        n = int(round(length * fps))
        if n <= 0:
            raise SystemExit("[edin] Nada para renderizar (duração <= 0 depois do --start).")
        job.n = n
        length = n / fps
        print(f"[edin] modo {'contrato (EDIN.seek)' if mode_used == 'contract' else 'livre (relógio virtual)'}, "
              f"{n} quadros ({length:.2f}s a {fps:g} fps) de t={start:g}s, {n_workers} worker(s)"
              f"{f', motion blur {motion_blur}x' if motion_blur > 1 else ''}; páginas prontas em "
              f"{time.time() - t_open:.1f}s", flush=True)

        outp = Path(out).resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)
        tmp = outp.with_name(outp.stem + ".part.mp4")
        fdir = Path(frames_dir).resolve() if frames_dir else None
        if fdir:
            fdir.mkdir(parents=True, exist_ok=True)
        enc = subprocess.Popen(_ffmpeg_cmd(tmp, ow, oh, fps, length, crf, preset or ("veryfast" if draft else "medium"),
                                           audio, start if audio_start is None else audio_start, silent_audio),
                               stdin=subprocess.PIPE)
        start_evt.set()
        t0 = time.time()
        last = 0.0
        for local in range(n):
            with job.cond:
                while local not in job.results and job.error is None:
                    job.cond.wait(0.5)
                if job.error is not None:
                    raise job.error
                img, png = job.results.pop(local)
                job.written = local + 1
                job.cond.notify_all()
            if img.shape[1] != ow or img.shape[0] != oh:
                img = cv2.resize(img, (ow, oh), interpolation=cv2.INTER_AREA)
            enc.stdin.write(img.tobytes())
            if fdir:
                name = fdir / f"{first + local:06d}.png"
                if png is not None:
                    name.write_bytes(png)
                else:
                    cv2.imwrite(str(name), img, [cv2.IMWRITE_PNG_COMPRESSION, 1])
            now = time.time()
            if now - last > 0.25 or local == n - 1:
                last = now
                done = local + 1
                rate = done / max(now - t0, 1e-6)
                bar = "#" * int(24 * done / n)
                print(f"\r[edin] [{bar:<24}] {done}/{n} quadros  {rate:5.1f} q/s  "
                      f"faltam ~{(n - done) / max(rate, 1e-6):4.0f}s ", end="", flush=True)
        print()
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("ffmpeg falhou ao montar o vídeo")
        tmp.replace(outp)
        el = time.time() - t0
        stats = {"out": str(outp), "frames": n, "fps_render": n / max(el, 1e-6), "seconds": el, "mode": mode_used,
                 "workers": n_workers}
        print(f"[edin] Pronto: {outp}  ({n} quadros em {el:.1f}s, {n / max(el, 1e-6):.1f} q/s"
              f"{', quadros PNG em ' + str(fdir) if fdir else ''})")
        return stats
    except BaseException:
        with job.cond:
            if job.error is None:
                job.error = RuntimeError("cancelado")
            job.cond.notify_all()
        if enc:
            enc.kill()
            enc.wait()
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        raise
    finally:
        start_evt.set()
        for t in threads:
            t.join(10)
