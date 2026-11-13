"""Narração LOCAL e grátis em português do Brasil (Kokoro-82M; Piper opcional), alternativa ao ElevenLabs.

    edin tts roteiro.txt --local -o voz.mp3                       # voz pm_alex, velocidade 1.0, pausa 0,35 s
    edin tts roteiro.txt --local --voz pm_alex --speed 0.95 --pausa 0.4 -o voz.mp3   # manifesto
    edin tts roteiro.txt -o voz.mp3      # sem chave do ElevenLabs cai aqui sozinho (com aviso)

Gera os MESMOS arquivos do caminho ElevenLabs, que o resto do pipeline lê:
  voz.mp3              48 kHz estéreo, -15 LUFS integrado (loudnorm em duas passadas, pico real -1,5 dBTP)
  voz.words.json       palavras com tempos no formato do `edin transcribe` (faster-whisper sobre o áudio gerado;
                       a grafia é a do roteiro, os tempos são os do whisper)
  voz.falas.json       tabela fala x tempo (início, fim, silêncio depois, corte sugerido), uma fala por
                       parágrafo do roteiro (ou por linha, se o roteiro não tiver linha em branco)
  voz.alignment.json   o que foi usado (motor, voz, velocidade, pausa, pronúncias) e a conferência do whisper

Cada fala é sintetizada separada (entonação de frase completa, como manifesto pede) e a montagem encosta as falas
com a pausa pedida, então os tempos da tabela são exatos (não dependem de silencedetect).

O motor roda num venv separado (~/.local/share/edin/voz/venv, instalado pelo ./install_voz.sh), chamado por
subprocesso com `python -I` (edin/voz_worker.py), sempre em CPU. Ver docs/FERRAMENTAS.md.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from .elevenlabs import _duration, finish_table, print_table, read_script
from .utils import save_json
from .voice import HOME

VOZ_HOME = Path(os.environ.get("EDIN_VOZ_HOME", HOME / "voz"))
VENV_PY = VOZ_HOME / "venv" / "bin" / "python"
MODELOS = VOZ_HOME / "modelos"
AQUI = Path(__file__).resolve().parent
WORKER = AQUI / "voz_worker.py"
MANIFESTO = AQUI / "modelos_voz.json"

DEFAULT_VOZ = "pm_alex"  # masculina, a mais grave e calma das vozes pt-BR do Kokoro (comparação de 2026-11-13)
VOZES_KOKORO = ("pm_alex", "pm_santa", "pf_dora")
PAUSA = 0.35  # silêncio entre falas (mesmo d do silencedetect da montagem)
LUFS = -15.0
TRUE_PEAK = -1.5
CABECA, CAUDA = 0.15, 0.5  # silêncio no começo e no fim do mp3
WHISPER = "large-v3-turbo"  # só confere e marca o tempo das palavras; em CPU leva poucos segundos por minuto de voz


def estado() -> dict:
    """Para o `edin doctor`."""
    r = {"venv": VENV_PY.exists(), "pasta": str(VOZ_HOME), "kokoro": False, "piper": False, "vozes": []}
    if r["venv"]:
        try:
            p = subprocess.run([str(VENV_PY), "-I", str(WORKER), "info", str(MODELOS)], capture_output=True,
                               text=True, timeout=60)
            r.update(json.loads(p.stdout.strip().splitlines()[-1]))
        except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
            pass
    return r


def motor_da_voz(voz: str) -> str:
    return "kokoro" if voz in VOZES_KOKORO else "piper"


def pronuncia(texto: str) -> str:
    """Troca palavras que a voz lê errado (ex.: LoopEdu -> "Lup Edú"); só no texto que vai para a voz."""
    tab = json.loads(MANIFESTO.read_text(encoding="utf-8")).get("pronuncia", {})
    for k, v in tab.items():
        if not k.startswith("_"):
            texto = re.sub(rf"(?<!\w){re.escape(k)}(?!\w)", v, texto)
    return texto


def _worker(job: dict) -> dict:
    if not VENV_PY.exists():
        raise SystemExit(f"[edin] A narração local não está instalada ({VENV_PY} não existe). "
                         f"Rode ./install_voz.sh (ou ./install.sh --voz) no repositório do edin.")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False)
        jp = f.name
    env = dict(os.environ, ONNX_PROVIDER="CPUExecutionProvider")
    env.pop("PYTHONPATH", None)
    env.pop("LD_LIBRARY_PATH", None)
    try:
        p = subprocess.run([str(VENV_PY), "-I", str(WORKER), "sintetizar", jp], capture_output=True, text=True,
                           env=env)
    finally:
        os.unlink(jp)
    evs = [json.loads(x) for x in p.stdout.splitlines() if x.startswith("{")]
    if p.returncode != 0 or not evs or evs[-1].get("etapa") != "fim":
        raise SystemExit(f"[edin] A síntese local falhou:\n{p.stderr[-2500:]}")
    return evs[-1]


def _bordas_voz(a, sr: int, limiar_db: float = -40.0) -> tuple[float, float]:
    """Primeiro e último instante com voz (quadros de 10 ms acima de limiar_db do pico da fala)."""
    import numpy as np

    q = max(int(sr * 0.01), 1)
    n = len(a) // q
    if n == 0:
        return 0.0, len(a) / sr
    rms = np.sqrt((a[: n * q].reshape(n, q) ** 2).mean(1) + 1e-12)
    v = np.nonzero(rms > rms.max() * 10 ** (limiar_db / 20))[0]
    if not len(v):
        return 0.0, len(a) / sr
    return v[0] * q / sr, (v[-1] + 1) * q / sr


def _monta(arquivos: list, pausa: float, wav_out: str) -> list:
    """Encosta as falas com `pausa` s de silêncio entre a voz de uma e a da outra. Devolve [(início, fim)]."""
    import numpy as np
    import soundfile as sf

    partes, bordas, t, sr = [], [], 0.0, None
    for i, arq in enumerate(arquivos):
        a, sr_i = sf.read(arq, dtype="float32")
        if a.ndim > 1:
            a = a.mean(1)
        sr = sr or sr_i
        if i == 0:
            partes.append(np.zeros(int(CABECA * sr), np.float32))
            t = CABECA
        v0, v1 = _bordas_voz(a, sr)
        if i > 0:  # silêncio entre o fim da voz anterior e o começo desta = pausa
            gap = max(pausa - bordas[-1][2] - v0, 0.0)
            partes.append(np.zeros(int(round(gap * sr)), np.float32))
            t += int(round(gap * sr)) / sr
        bordas.append((t + v0, t + v1, len(a) / sr - v1))  # (início voz, fim voz, sobra depois da voz)
        partes.append(a)
        t += len(a) / sr
    partes.append(np.zeros(int(CAUDA * sr), np.float32))
    sf.write(wav_out, np.concatenate(partes), sr, subtype="FLOAT")
    return [(b[0], b[1]) for b in bordas]


def _loudnorm(wav: str, mp3: str, lufs: float, tom: float) -> dict:
    """Pitch opcional (rubberband, formantes preservados), loudnorm em 2 passadas, 48 kHz estéreo, mp3 192k."""
    pre = f"rubberband=pitch={2 ** (tom / 12):.6f}:formant=preserved:pitchq=quality," if tom else ""
    # estéreo ANTES do loudnorm: a medida é a do arquivo final (o upmix mono -> estéreo muda o nível)
    pre += "aformat=sample_fmts=flt:channel_layouts=stereo,"
    alvo = f"I={lufs}:TP={TRUE_PEAK}:LRA=11"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", wav, "-af",
                        f"{pre}loudnorm={alvo}:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1])
    medido = (f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
              f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-af",
                    f"{pre}loudnorm={alvo}:{medido},aresample=48000:resampler=soxr:precision=28",
                    "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "48000", "-ac", "2", mp3], check=True)
    return medir_lufs(mp3)


def medir_lufs(audio: str) -> dict:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", audio, "-af", "ebur128=peak=true", "-f", "null",
                        "-"], capture_output=True, text=True)
    s = p.stderr[p.stderr.rfind("Summary:"):]
    num = lambda pat: float(re.search(pat, s, re.S).group(1))  # noqa: E731
    return {"lufs": num(r"I:\s+(-?[\d.]+) LUFS"), "lra": num(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak": num(r"Peak:\s+(-?[\d.]+) dBFS")}


# ---- palavras: tempos do whisper, grafia do roteiro --------------------------------------------------------------
def _n(w: str) -> str:
    return re.sub(r"[^\w]", "", w.casefold())


def _casa(script: list, wh: list) -> tuple[list, list]:
    """Casa as palavras do roteiro inteiro com as do whisper (difflib, a sequência toda de uma vez: o whisper às
    vezes põe o "E" do começo de uma fala no fim da anterior). Devolve ([s, e, p] ou None por palavra do roteiro,
    se cada palavra foi ouvida igual) e os índices do whisper ligados a cada palavra."""
    tempos, igual, ligados = [None] * len(script), [False] * len(script), [[] for _ in script]
    sm = difflib.SequenceMatcher(a=[_n(w) for w in script], b=[_n(w["w"]) for w in wh], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                w = wh[j1 + k]
                tempos[i1 + k], igual[i1 + k], ligados[i1 + k] = [w["s"], w["e"], w["p"]], True, [j1 + k]
        elif op == "replace":  # ex.: "LoopEdu" x "Lope Edu": reparte o trecho do whisper pelas letras
            mesmo = "".join(_n(w) for w in script[i1:i2]) == "".join(_n(w["w"]) for w in wh[j1:j2])
            a, b = wh[j1]["s"], wh[j2 - 1]["e"]
            pesos = [max(len(_n(w)), 1) for w in script[i1:i2]]
            t = a
            for k, pk in enumerate(pesos):
                d = (b - a) * pk / sum(pesos)
                tempos[i1 + k], igual[i1 + k], ligados[i1 + k] = [t, t + d, 0.5], mesmo, list(range(j1, j2))
                t += d
    return tempos, igual, ligados


def _preenche(ws: list, tempos: list, ini: float, fim: float) -> list:
    """Palavras sem par ficam entre a anterior e a próxima (pelas letras); tudo preso nas bordas exatas da fala
    (o whisper erra as pontas em ~0,2 s; as bordas vêm da montagem)."""
    out = [[min(max(t[0], ini), fim), min(max(t[1], ini), fim), t[2]] if t else None for t in tempos]
    k = 0
    while k < len(out):
        if out[k] is not None:
            k += 1
            continue
        j = k
        while j < len(out) and out[j] is None:
            j += 1
        a = out[k - 1][1] if k > 0 else ini
        b = out[j][0] if j < len(out) else fim
        pesos = [max(len(_n(w)), 1) for w in ws[k:j]]
        t = a
        for m, pm in enumerate(pesos):
            d = max(b - a, 0.0) * pm / sum(pesos)
            out[k + m] = [t, t + d, 0.3]
            t += d
        k = j
    if out:
        out[0][0], out[-1][1] = ini, fim
    for k in range(1, len(out)):  # sem sobreposição
        out[k][0] = max(out[k][0], out[k - 1][1])
    return [{"w": w, "s": round(s, 3), "e": round(max(e, s), 3), "p": round(p, 3)} for w, (s, e, p) in zip(ws, out)]


def palavras(audio: str, falas: list, bordas: list, modelo: str, device: str) -> tuple[list, list]:
    """Roda o whisper sobre a narração gerada; devolve (words no formato do edin transcribe, conferência)."""
    from .transcribe import _whisper

    marcas = sorted({w.strip(".,;:!?") for f in falas for w in f.split() if re.search(r"[a-z][A-Z]", w)})
    segs, _ = _whisper(audio, modelo, "pt", device, vad_parameters={"min_silence_duration_ms": 300},
                       initial_prompt=(", ".join(marcas) + ".") if marcas else None)
    wh = [{"w": w.word.strip(), "s": w.start, "e": w.end, "p": w.probability} for s in segs for w in (s.words or [])
          if w.word.strip()]
    script = [(k, w) for k, f in enumerate(falas) for w in f.split()]
    tempos, igual, ligados = _casa([w for _, w in script], wh)
    words, conf = [], []
    for k, (f, (ini, fim)) in enumerate(zip(falas, bordas)):
        idx = [i for i, (kk, _) in enumerate(script) if kk == k]
        for w in _preenche([script[i][1] for i in idx], [tempos[i] for i in idx], ini, fim):
            words.append({"i": len(words), **w})
        js = sorted({j for i in idx for j in ligados[i]})
        conf.append({"n": k + 1, "roteiro": f, "whisper": " ".join(wh[j]["w"] for j in js),
                     "igual": all(igual[i] for i in idx)})
    return words, conf


# ---- comando -----------------------------------------------------------------------------------------------------
def tts_local(script: str, out: str, voz: str = DEFAULT_VOZ, velocidade: float = 1.0, pausa: float = PAUSA,
              tom: float = 0.0, lufs: float = LUFS, whisper: str = WHISPER, device: str = "cpu") -> dict:
    t0 = time.time()
    falas = read_script(script)
    textos = [pronuncia(f) for f in falas]
    motor = motor_da_voz(voz)
    print(f"[edin] Narração local: {motor} voz {voz}, velocidade {velocidade}, pausa {pausa} s"
          f"{f', tom {tom:+g} semitons' if tom else ''}, {len(falas)} falas (CPU)")
    for f, t in zip(falas, textos):
        if f != t:
            print(f"[edin] pronúncia: \"{f}\" -> voz lê \"{t}\"")
    out_p = Path(out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    stem = out_p.with_suffix("")
    with tempfile.TemporaryDirectory() as td:
        r = _worker({"motor": motor, "voz": voz, "falas": textos, "velocidade": velocidade, "pausa_frase": pausa,
                     "modelos": str(MODELOS), "saida": td})
        t_sint = r["segundos"]
        wav = str(Path(td) / "voz.wav")
        bordas = _monta(r["arquivos"], pausa, wav)
        medida = _loudnorm(wav, str(out_p), lufs, tom)
    dur = _duration(str(out_p))
    table = [{"n": k + 1, "texto": f, "inicio": round(a, 3), "fim": round(b, 3)}
             for k, (f, (a, b)) in enumerate(zip(falas, bordas))]
    finish_table(table, dur)
    t1 = time.time()
    words, conf = palavras(str(out_p), falas, bordas, whisper, device)
    t_whisper = time.time() - t1
    metodo = "síntese local (tempos exatos da montagem das falas)"
    meta = {"motor": motor, "voz": voz, "velocidade": velocidade, "pausa": pausa, "tom_semitons": tom,
            "lufs_alvo": lufs, "medido": medida, "roteiro": str(Path(script).resolve()),
            "texto_para_voz": textos, "whisper": whisper, "conferencia": conf,
            "segundos": {"sintese": t_sint, "whisper": round(t_whisper, 2), "total": round(time.time() - t0, 2)},
            "partes": []}
    save_json(meta, f"{stem}.alignment.json")
    save_json({"source": str(out_p.resolve()), "language": "pt", "duration": dur, "words": words},
              f"{stem}.words.json")
    save_json({"audio": str(out_p.resolve()), "duracao": dur, "metodo": metodo, "falas": table},
              f"{stem}.falas.json")
    print_table(table, dur, metodo)
    print(f"\n[edin] Loudness: {medida['lufs']:.1f} LUFS, pico real {medida['true_peak']:.1f} dBTP, "
          f"LRA {medida['lra']:.1f} LU (48 kHz estéreo)")
    ruins = [c for c in conf if not c["igual"]]
    print(f"[edin] Conferência pelo whisper ({whisper}): {len(conf) - len(ruins)}/{len(conf)} falas ouvidas iguais "
          f"ao roteiro")
    for c in ruins:
        print(f"   fala {c['n']}: roteiro \"{c['roteiro']}\" | ouvido \"{c['whisper']}\"")
    if ruins:
        print("   (marca e nome próprio costumam divergir só na grafia; ouça essas falas. Pronúncia errada: "
              "acrescente em \"pronuncia\" de edin/modelos_voz.json)")
    print(f"[edin] Tempo: síntese {t_sint:.1f} s, whisper {t_whisper:.1f} s, total {time.time() - t0:.1f} s")
    print(f"\n[edin] {out_p}\n       {stem}.alignment.json | {stem}.words.json | {stem}.falas.json")
    return {"audio": str(out_p), "falas": table, "duracao": dur, "medido": medida, "conferencia": conf}
