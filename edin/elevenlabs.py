"""Narração com o ElevenLabs (API REST) e tabela fala x tempo para a montagem.

    edin voices search "Yuri"                       # procura na conta e na Voice Library compartilhada
    edin voices add "Yuri - Natural Brazilian Narrator"   # traz uma voz da biblioteca para a conta
    edin tts roteiro.txt --voice "Yuri - Natural Brazilian Narrator" -o voz.mp3
    edin falas voz.mp3 roteiro.txt                  # tabela fala x tempo de uma narração pronta (silencedetect)

Roteiro: uma fala por parágrafo, separadas por linha em branco. O texto vai inteiro para a API com as linhas em
branco (é assim que a voz respira entre as falas) e o alinhamento por caractere devolvido pelo endpoint
`/with-timestamps` dá o início e o fim de cada fala.

Saídas do `edin tts ... -o voz.mp3`:
  voz.mp3               a narração
  voz.alignment.json    alinhamento por caractere da API (+ modelo, voz e ajustes usados)
  voz.words.json        palavras com tempos no formato do `edin transcribe` (serve para legenda)
  voz.falas.json        tabela fala x tempo (início, fim, silêncio depois)

Voz resolvida pelo nome nesta ordem: vozes da conta -> Voice Library compartilhada -> adiciona à conta
(`POST /v1/voices/add/{public_owner_id}/{voice_id}`). Assim qualquer voz da biblioteca é usada só pelo nome.

Importante: os modelos eleven_v3 e eleven_v4 IGNORAM `<break time="..."/>`. Não dependa de pausas no texto;
a sincronia com as cenas é feita na montagem, cortando a narração nos silêncios entre as falas.

Chave: variável ELEVENLABS_API_KEY ou o arquivo ~/.config/edin/elevenlabs.key. Nunca grave a chave no repositório.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .utils import fmt_time, save_json

API = "https://api.elevenlabs.io"
UA = "edin/0.1"
KEY_FILE = Path.home() / ".config" / "edin" / "elevenlabs.key"
DEFAULT_VOICE = "Yuri - Natural Brazilian Narrator"
DEFAULT_MODEL = "eleven_v4"
FALLBACK_MODEL = "eleven_v3"
# limite de caracteres por requisição (docs.elevenlabs.io/models); acima disso o roteiro vai em partes
CHAR_LIMIT = {"eleven_v4": 10000, "eleven_v3": 5000, "eleven_multilingual_v2": 10000, "eleven_flash_v2_5": 40000}
SILENCE = {"noise": "-35dB", "d": 0.35}  # mesmo critério da montagem (briefing do Reel tutorial)
MAX_PAUSE = 1.0  # silêncio maior que isso entre falas já reprovou vídeo

SEM_CHAVE = f"""[edin] Falta a chave da API do ElevenLabs.
  1. Entre em https://elevenlabs.io/app/settings/api-keys e crie uma chave (permissões: Text to Speech e
     Voices com leitura e escrita, para poder adicionar vozes da biblioteca).
  2. Guarde num destes lugares (fora do repositório):
       mkdir -p ~/.config/edin && printf '%s' 'sua_chave' > {KEY_FILE} && chmod 600 {KEY_FILE}
     ou no terminal (e no fim do ~/.bashrc para ficar salva):
       export ELEVENLABS_API_KEY="sua_chave"
"""


# ---- API ---------------------------------------------------------------------------------------------------------
def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit(SEM_CHAVE)
    return key


def _request(method: str, path: str, params: dict | None = None, body: dict | None = None) -> dict:
    """Chamada à API (função única para poder simular nos testes sem chave)."""
    q = ""
    if params:
        q = "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{API}{path}{q}", data=data, method=method,
                                 headers={"xi-api-key": api_key(), "User-Agent": UA, "Accept": "application/json",
                                          **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        if e.code == 401:
            raise SystemExit(f"[edin] O ElevenLabs recusou a chave (inválida, revogada ou sem permissão para "
                             f"{path}).\n{detail}") from e
        if e.code in (402, 429) or "quota" in detail.lower():
            raise SystemExit(f"[edin] ElevenLabs sem créditos ou limite atingido ({e.code}).\n{detail}") from e
        raise SystemExit(f"[edin] Erro {e.code} do ElevenLabs em {method} {path}:\n{detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"[edin] Sem conexão com o ElevenLabs: {e.reason}") from e


# ---- vozes -------------------------------------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("–", "-").replace("—", "-")).strip().casefold()


def _looks_like_id(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]{16,32}", s or ""))


def account_voices(search: str | None = None, voice_ids: list | None = None) -> list:
    """Vozes da conta (GET /v2/voices), todas as páginas."""
    out, token = [], None
    while True:
        d = _request("GET", "/v2/voices", {"search": search, "voice_ids": voice_ids, "page_size": 100,
                                           "next_page_token": token, "include_total_count": "false"})
        for v in d.get("voices") or []:
            labels = v.get("labels") or {}
            out.append({"origem": "conta", "name": v.get("name", ""), "voice_id": v["voice_id"],
                        "public_owner_id": (v.get("sharing") or {}).get("public_owner_id") or "",
                        "language": labels.get("language") or "", "category": v.get("category") or ""})
        token = d.get("next_page_token")
        if not d.get("has_more") or not token:
            return out


def library_voices(search: str, language: str | None = None, n: int = 30) -> list:
    """Voice Library compartilhada (GET /v1/shared-voices)."""
    d = _request("GET", "/v1/shared-voices", {"search": search, "language": language, "page_size": min(n, 100)})
    return [{"origem": "biblioteca", "name": v.get("name", ""), "voice_id": v["voice_id"],
             "public_owner_id": v.get("public_owner_id") or "", "language": v.get("language") or "",
             "category": v.get("category") or "", "accent": v.get("accent") or "",
             "adicionada": bool(v.get("is_added_by_user")), "preview_url": v.get("preview_url") or ""}
            for v in d.get("voices") or []]


def search_voices(name: str, language: str | None = None, n: int = 30) -> list:
    acc = account_voices(voice_ids=[name]) if _looks_like_id(name) else account_voices(search=name)
    return acc + library_voices(name, language, n)


def _pick(cands: list, name: str) -> dict | None:
    """Escolhe pelo id, pelo nome exato, ou pelo único que começa com / contém o nome."""
    key = _norm(name)
    exact = [v for v in cands if v["voice_id"] == name or _norm(v["name"]) == key]
    if exact:
        return exact[0]
    for test in (lambda v: _norm(v["name"]).startswith(key), lambda v: key in _norm(v["name"])):
        hits = {v["voice_id"]: v for v in cands if test(v)}
        if len(hits) == 1:
            return next(iter(hits.values()))
        if len(hits) > 1:
            return None  # ambíguo: melhor pedir o nome exato do que gastar créditos com a voz errada
    return None


def add_voice(name_or_id: str, new_name: str | None = None) -> dict:
    """Garante a voz na conta: se já está, devolve; senão acha na biblioteca e adiciona."""
    acc = account_voices(voice_ids=[name_or_id]) if _looks_like_id(name_or_id) else account_voices(search=name_or_id)
    hit = _pick(acc, name_or_id)
    if hit:
        return hit
    lib = library_voices(name_or_id, n=50)
    hit = _pick(lib, name_or_id)
    if not hit:
        nomes = "\n".join(f"  {v['name']}  ({v['voice_id']}, {v['language']})" for v in lib[:15]) or "  (nenhuma)"
        raise SystemExit(f"[edin] Voz \"{name_or_id}\" não encontrada de forma única na conta nem na Voice "
                         f"Library. Parecidas:\n{nomes}\nUse o nome exato ou o voice_id (edin voices search).")
    if not hit["public_owner_id"]:
        raise SystemExit(f"[edin] A voz {hit['name']} não tem public_owner_id; não dá para adicionar pela API.")
    r = _request("POST", f"/v1/voices/add/{hit['public_owner_id']}/{hit['voice_id']}",
                 body={"new_name": new_name or hit["name"]})
    print(f"[edin] Voz adicionada à conta: {new_name or hit['name']} ({r.get('voice_id', hit['voice_id'])})")
    return {**hit, "origem": "conta (adicionada agora)", "voice_id": r.get("voice_id", hit["voice_id"])}


def print_voices(voices: list) -> None:
    if not voices:
        print("Nenhuma voz encontrada.")
        return
    for v in voices:
        extra = " [já na conta]" if v.get("adicionada") else ""
        print(f"{v['origem']:<10} {v['name']}  voice_id={v['voice_id']}  owner={v['public_owner_id'] or '-'}  "
              f"idioma={v['language'] or '-'}  categoria={v['category'] or '-'}{extra}")


# ---- modelo ------------------------------------------------------------------------------------------------------
def pick_model(wanted: str = DEFAULT_MODEL) -> str:
    """Confere o model_id em GET /v1/models; sem o v4 na conta, cai para o eleven_v3 e avisa."""
    models = _request("GET", "/v1/models")
    tts_ids = [m.get("model_id") for m in (models if isinstance(models, list) else models.get("models", []))
               if m.get("can_do_text_to_speech", True)]
    if wanted in tts_ids:
        return wanted
    if FALLBACK_MODEL in tts_ids:
        print(f"[edin] Aviso: o modelo {wanted} não está disponível nesta conta. Usando {FALLBACK_MODEL}.")
        return FALLBACK_MODEL
    raise SystemExit(f"[edin] Modelo {wanted} indisponível. Modelos de voz da conta: {', '.join(tts_ids)}")


# ---- roteiro e alinhamento ---------------------------------------------------------------------------------------
def read_script(path: str) -> list:
    """Falas do roteiro: parágrafos separados por linha em branco (quebras simples viram espaço)."""
    txt = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    falas = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", txt)]
    falas = [f for f in falas if f]
    if not falas:
        raise SystemExit(f"[edin] {path} está vazio.")
    if any(ch in txt for ch in "—–"):
        print("[edin] Aviso: o roteiro tem travessão. Rafael não usa; troque por vírgula ou ponto.")
    return falas


def _chunks(falas: list, limit: int) -> list:
    """Agrupa falas inteiras em partes abaixo do limite de caracteres do modelo."""
    out, cur = [], []
    for i, f in enumerate(falas):
        if len(f) > limit:
            raise SystemExit(f"[edin] A fala {i + 1} sozinha passa de {limit} caracteres.")
        if cur and len("\n\n".join(falas[j] for j in cur + [i])) > limit:
            out.append(cur)
            cur = []
        cur.append(i)
    return out + [cur] if cur else out


def _speech_chars(alignment: dict, offset: float = 0.0) -> list:
    """[(caractere, início, fim)] do alinhamento da API, com deslocamento de tempo."""
    a = alignment or {}
    return [(c, s + offset, e + offset) for c, s, e in zip(a.get("characters") or [],
                                                           a.get("character_start_times_seconds") or [],
                                                           a.get("character_end_times_seconds") or [])]


def falas_from_alignment(falas: list, chars: list) -> list | None:
    """Início/fim de cada fala casando os caracteres não brancos do roteiro com os do alinhamento."""
    alvo = [(k, c) for k, f in enumerate(falas) for c in f if not c.isspace()]
    vis = [(c, s, e) for c, s, e in chars if not c.isspace()]
    if len(alvo) != len(vis) or any(a[1] != v[0] for a, v in zip(alvo, vis)):
        return None
    out = []
    for k, f in enumerate(falas):
        ts = [v for a, v in zip(alvo, vis) if a[0] == k]
        out.append({"n": k + 1, "texto": f, "inicio": round(ts[0][1], 3), "fim": round(ts[-1][2], 3)})
    return out


def words_from_chars(chars: list) -> list:
    words, cur = [], []
    for c, s, e in chars + [(" ", 0, 0)]:
        if c.isspace():
            if cur:
                words.append({"i": len(words), "w": "".join(x[0] for x in cur), "s": round(cur[0][1], 3),
                              "e": round(cur[-1][2], 3), "p": 1.0})
            cur = []
        else:
            cur.append((c, s, e))
    return words


def silences(audio: str, noise: str = SILENCE["noise"], d: float = SILENCE["d"]) -> tuple[list, float]:
    """Silêncios [(início, fim)] pelo silencedetect e a duração do áudio."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", audio, "-af", f"silencedetect=noise={noise}:d={d}",
                        "-f", "null", "-"], capture_output=True, text=True)
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    dur = _duration(audio)
    return [(max(a, 0.0), en[i] if i < len(en) else dur) for i, a in enumerate(st)], dur


def falas_from_silence(falas: list, audio: str) -> list:
    """Divide a narração nos N-1 maiores silêncios internos (uma fala por parte), em ordem."""
    sil, dur = silences(audio)
    head = next((b for a, b in sil if a <= 0.01), 0.0)
    tail = next((a for a, b in sil if b >= dur - 0.01 and a > head), dur)
    inner = [(a, b) for a, b in sil if a > head + 0.01 and b < tail - 0.01]
    n = len(falas)
    if len(inner) < n - 1:
        print(f"[edin] Aviso: {n} falas mas só {len(inner) + 1} trechos de voz separados por silêncio "
              f"(noise={SILENCE['noise']}, d={SILENCE['d']}). Confira a tabela no ouvido.")
    cut = sorted(sorted(inner, key=lambda x: x[1] - x[0], reverse=True)[:n - 1])
    bounds = [head] + [x for a, b in cut for x in (a, b)] + [tail]
    out = []
    for k in range(min(n, len(bounds) // 2)):
        out.append({"n": k + 1, "texto": falas[k], "inicio": round(bounds[2 * k], 3),
                    "fim": round(bounds[2 * k + 1], 3)})
    return out


def finish_table(table: list, dur: float) -> list:
    for k, f in enumerate(table):
        nxt = table[k + 1]["inicio"] if k + 1 < len(table) else dur
        f["duracao"] = round(f["fim"] - f["inicio"], 3)
        f["silencio_depois"] = round(max(nxt - f["fim"], 0.0), 3)
        f["corte_sugerido"] = round((f["fim"] + nxt) / 2, 3) if k + 1 < len(table) else round(dur, 3)
    return table


def print_table(table: list, dur: float, metodo: str) -> None:
    print(f"\nFala x tempo ({metodo}), narração de {dur:.2f} s ({fmt_time(dur)}):")
    print(f"{'#':>2}  {'início':>7} {'fim':>7} {'dur':>6} {'silêncio':>8}  texto")
    for f in table:
        flag = "  <- silêncio > 1 s" if f["silencio_depois"] > MAX_PAUSE and f is not table[-1] else ""
        txt = f["texto"] if len(f["texto"]) <= 70 else f["texto"][:67] + "..."
        print(f"{f['n']:>2}  {f['inicio']:7.2f} {f['fim']:7.2f} {f['duracao']:6.2f} {f['silencio_depois']:8.2f}  "
              f"{txt}{flag}")


def _duration(path: str) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def _concat(parts: list, out: str) -> None:
    lst = Path(out).with_suffix(".concat.txt")
    lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts), encoding="utf-8")
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a",
                        "libmp3lame", "-b:a", "128k", "-ar", "44100", out], check=True)
    finally:
        lst.unlink(missing_ok=True)


# ---- texto para voz ----------------------------------------------------------------------------------------------
def tts(script: str, out: str, voice: str = DEFAULT_VOICE, model: str = DEFAULT_MODEL, stability: float = 0.5,
        similarity: float = 0.75, style: float = 0.0, speed: float = 1.0, language: str | None = "pt",
        seed: int | None = None, output_format: str = "mp3_44100_128") -> dict:
    falas = read_script(script)
    v = add_voice(voice)
    model = pick_model(model)
    print(f"[edin] Voz {v['name']} ({v['voice_id']}), modelo {model}, stability {stability}, "
          f"similarity {similarity}, {len(falas)} falas")
    if model in ("eleven_v3", "eleven_v4") and "<break" in Path(script).read_text(encoding="utf-8"):
        print("[edin] Aviso: v3/v4 ignoram <break time>. As pausas saem da linha em branco e da montagem.")
    settings = {"stability": stability, "similarity_boost": similarity, "style": style, "speed": speed,
                "use_speaker_boost": True}
    groups = _chunks(falas, CHAR_LIMIT.get(model, 5000))
    out_p = Path(out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    stem = out_p.with_suffix("")
    chars, raw, parts, offset = [], [], [], 0.0
    with tempfile.TemporaryDirectory() as td:
        for gi, g in enumerate(groups):
            text = "\n\n".join(falas[i] for i in g)
            body = {"text": text, "model_id": model, "voice_settings": settings}
            if language and model != "eleven_multilingual_v2":
                body["language_code"] = language
            if seed is not None:
                body["seed"] = seed
            if len(groups) > 1:  # continuidade de entonação entre as partes
                if gi > 0:
                    body["previous_text"] = "\n\n".join(falas[i] for i in groups[gi - 1])
                if gi + 1 < len(groups):
                    body["next_text"] = "\n\n".join(falas[i] for i in groups[gi + 1])
            print(f"[edin] Gerando parte {gi + 1}/{len(groups)} ({len(text)} caracteres)...")
            r = _request("POST", f"/v1/text-to-speech/{v['voice_id']}/with-timestamps",
                         {"output_format": output_format}, body)
            part = Path(td) / f"parte_{gi:02d}.mp3"
            part.write_bytes(base64.b64decode(r["audio_base64"]))
            parts.append(str(part))
            chars += _speech_chars(r.get("alignment"), offset)
            if gi + 1 < len(groups):
                chars.append(("\n", offset, offset))
            raw.append({"texto": text, "offset": round(offset, 3), "alignment": r.get("alignment"),
                        "normalized_alignment": r.get("normalized_alignment")})
            offset += _duration(str(part))
        if len(parts) == 1:
            out_p.write_bytes(Path(parts[0]).read_bytes())
        else:
            _concat(parts, str(out_p))
    dur = _duration(str(out_p)) or offset
    table, metodo = falas_from_alignment(falas, chars), "alinhamento da API"
    if table is None:
        print("[edin] Aviso: o alinhamento não casou com o roteiro caractere a caractere; usando silencedetect.")
        table, metodo = falas_from_silence(falas, str(out_p)), "silencedetect"
    finish_table(table, dur)
    meta = {"voz": v["name"], "voice_id": v["voice_id"], "modelo": model, "voice_settings": settings,
            "language_code": language, "seed": seed, "roteiro": str(Path(script).resolve()), "partes": raw}
    save_json(meta, f"{stem}.alignment.json")
    save_json({"source": str(out_p.resolve()), "language": language or "pt", "duration": dur,
               "words": words_from_chars(chars)}, f"{stem}.words.json")
    save_json({"audio": str(out_p.resolve()), "duracao": dur, "metodo": metodo, "falas": table}, f"{stem}.falas.json")
    print_table(table, dur, metodo)
    print(f"\n[edin] {out_p}\n       {stem}.alignment.json | {stem}.words.json | {stem}.falas.json")
    return {"audio": str(out_p), "falas": table, "duracao": dur}


def falas_table(audio: str, script: str, alignment: str | None = None, out: str | None = None) -> list:
    """Tabela fala x tempo de uma narração pronta (a de Rafael ou uma já gerada)."""
    falas = read_script(script)
    dur, table, metodo = _duration(audio), None, "silencedetect"
    if alignment:
        meta = json.loads(Path(alignment).read_text(encoding="utf-8"))
        chars = []
        for p in meta.get("partes", []):
            chars += _speech_chars(p.get("alignment"), p.get("offset", 0.0))
            chars.append(("\n", 0, 0))
        table, metodo = falas_from_alignment(falas, chars), "alinhamento da API"
    if table is None:
        table, metodo = falas_from_silence(falas, audio), "silencedetect"
    finish_table(table, dur)
    dest = out or str(Path(audio).with_suffix("")) + ".falas.json"
    save_json({"audio": str(Path(audio).resolve()), "duracao": dur, "metodo": metodo, "falas": table}, dest)
    print_table(table, dur, metodo)
    print(f"\n[edin] {dest}")
    return table
