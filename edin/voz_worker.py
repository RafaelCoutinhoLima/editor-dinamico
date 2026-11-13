"""Worker da narração local: roda DENTRO do venv de voz (~/.local/share/edin/voz/venv) com `python -I`.

    python -I voz_worker.py info <modelos_dir>
    python -I voz_worker.py baixar <modelos_voz.json> <modelos_dir> [--piper]
    python -I voz_worker.py sintetizar <job.json>

`sintetizar` gera um WAV por fala (silêncio das pontas aparado) e imprime uma linha JSON por evento.
Job: {"motor": "kokoro"|"piper", "voz": "pm_alex", "falas": [...], "velocidade": 0.95, "pausa_frase": 0.35,
      "modelos": "<dir>", "saida": "<dir>"}
Só usa a biblioteca padrão + numpy/soundfile/onnxruntime do venv de voz (nada do edin principal).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

KOKORO_VOZES_PT = ("pm_alex", "pm_santa", "pf_dora")


def ev(**kw):
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def baixar(manifesto: str, dest: str, piper: bool) -> None:
    man = json.loads(Path(manifesto).read_text(encoding="utf-8"))["modelos"]
    d = Path(dest)
    d.mkdir(parents=True, exist_ok=True)
    for nome, m in man.items():
        if m.get("opcional") and not piper:
            continue
        alvo = d / nome
        if alvo.exists() and _sha(alvo) == m["sha256"]:
            ev(modelo=nome, estado="ok")
            continue
        tmp = alvo.with_suffix(alvo.suffix + ".part")
        ev(modelo=nome, estado="baixando", url=m["url"], mb=round(m["bytes"] / 1e6, 1))
        import shutil
        import subprocess

        if shutil.which("curl"):  # retoma download interrompido (-C -)
            subprocess.run(["curl", "-fsSL", "--retry", "5", "-C", "-", "-o", str(tmp), m["url"]], check=True)
        else:
            req = urllib.request.Request(m["url"], headers={"User-Agent": "edin/0.1"})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
                while b := r.read(1 << 20):
                    f.write(b)
        got = _sha(tmp)
        if got != m["sha256"]:
            tmp.unlink(missing_ok=True)
            raise SystemExit(f"sha256 de {nome} não confere ({got}); download corrompido ou arquivo trocado na origem")
        tmp.replace(alvo)
        ev(modelo=nome, estado="ok")


def info(modelos: str) -> None:
    d = Path(modelos)
    r = {"python": sys.version.split()[0], "kokoro": False, "piper": False, "vozes": []}
    try:
        import kokoro_onnx  # noqa: F401

        r["kokoro"] = (d / "kokoro-v1.0.onnx").exists() and (d / "voices-v1.0.bin").exists()
        if r["kokoro"]:
            r["vozes"] += list(KOKORO_VOZES_PT)
    except ImportError:
        pass
    try:
        import piper  # noqa: F401

        r["piper"] = True
        r["vozes"] += [p.name[:-5] for p in sorted(d.glob("*.onnx")) if (d / (p.name + ".json")).exists()]
    except ImportError:
        pass
    ev(**r)


def _apara(a, sr: int, limiar_db: float = -45.0, folga: float = 0.04):
    """Corta o silêncio das pontas (quadros de 10 ms abaixo de limiar_db do pico), deixando `folga` s."""
    import numpy as np

    if not len(a):
        return a
    q = max(int(sr * 0.01), 1)
    n = len(a) // q
    rms = np.sqrt((a[: n * q].reshape(n, q) ** 2).mean(1) + 1e-12)
    voz = np.nonzero(rms > rms.max() * 10 ** (limiar_db / 20))[0]
    if not len(voz):
        return a
    i0 = max(voz[0] * q - int(folga * sr), 0)
    i1 = min((voz[-1] + 1) * q + int(folga * sr), len(a))
    return a[i0:i1]


def sintetizar(job_path: str) -> None:
    import numpy as np
    import soundfile as sf

    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    d, out = Path(job["modelos"]), Path(job["saida"])
    out.mkdir(parents=True, exist_ok=True)
    voz, vel = job["voz"], float(job.get("velocidade", 1.0))
    t0 = time.time()
    if job["motor"] == "kokoro":
        os.environ.setdefault("ONNX_PROVIDER", "CPUExecutionProvider")
        from kokoro_onnx import Kokoro

        k = Kokoro(str(d / "kokoro-v1.0.onnx"), str(d / "voices-v1.0.bin"))
        if voz not in k.voices:
            raise SystemExit(f"voz {voz} não existe no Kokoro (português: {', '.join(KOKORO_VOZES_PT)})")
        pf = float(job.get("pausa_frase", 0.35))

        def gera(t):
            a, sr = k.create(t, voice=voz, speed=vel, lang="pt-br", sentence_pause=pf, clause_pause=min(pf, 0.15))
            return np.asarray(a, np.float32), sr
    elif job["motor"] == "piper":
        from piper import PiperVoice, SynthesisConfig

        modelo = d / f"{voz}.onnx"
        if not modelo.exists():
            raise SystemExit(f"modelo Piper {modelo} não encontrado (./install_voz.sh --piper)")
        pv = PiperVoice.load(str(modelo))
        cfg = SynthesisConfig(length_scale=1.0 / vel)

        def gera(t):
            a = np.concatenate([c.audio_float_array for c in pv.synthesize(t, cfg)])
            return a.astype(np.float32), pv.config.sample_rate
    else:
        raise SystemExit(f"motor desconhecido: {job['motor']}")
    ev(etapa="modelo", segundos=round(time.time() - t0, 2))
    arquivos, sr = [], 24000
    for i, texto in enumerate(job["falas"]):
        a, sr = gera(texto)
        a = _apara(a, sr)
        p = out / f"fala_{i:03d}.wav"
        sf.write(p, a, sr, subtype="FLOAT")
        arquivos.append(str(p))
        ev(etapa="fala", n=i + 1, segundos_audio=round(len(a) / sr, 3))
    ev(etapa="fim", sr=sr, arquivos=arquivos, segundos=round(time.time() - t0, 2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "info":
        info(sys.argv[2])
    elif cmd == "baixar":
        baixar(sys.argv[2], sys.argv[3], "--piper" in sys.argv[4:])
    elif cmd == "sintetizar":
        sintetizar(sys.argv[2])
    else:
        raise SystemExit(__doc__)
