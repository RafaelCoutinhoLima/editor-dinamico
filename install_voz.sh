#!/usr/bin/env bash
# Instala a narração LOCAL do edin (`edin tts --local`; o `edin tts` cai nela sozinho quando não há chave do
# ElevenLabs) num ambiente SEPARADO: kokoro-onnx + onnxruntime (CPU) em ~/.local/share/edin/voz/venv e os pesos do
# Kokoro-82M (Apache 2.0) em ~/.local/share/edin/voz/modelos. Sem GPU, sem PyTorch. Ver docs/FERRAMENTAS.md.
#
#   ./install_voz.sh            pacotes (requirements-voz.txt) + modelos do Kokoro (edin/modelos_voz.json, ~354 MB)
#   ./install_voz.sh --piper    também o Piper (piper-tts, GPL-3.0) e a voz pt_BR-faber-medium (MIT, 63 MB)
#   ./install_voz.sh --modelos  só baixa/confere os modelos (sha256)
#   EDIN_VOZ_HOME=/outro/lugar ./install_voz.sh
#
# Requisitos: Linux x86_64, uv (./install.sh instala), ~700 MB em disco, ~1 GB de RAM durante a síntese.
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"
DEST="${EDIN_VOZ_HOME:-$HOME/.local/share/edin/voz}"
VENV="$DEST/venv"

say() { printf '\n\033[1m[edin voz]\033[0m %s\n' "$*"; }

PACOTES=1; PIPER=0
[[ " $* " == *" --modelos "* ]] && PACOTES=0
[[ " $* " == *" --piper "* ]] && PIPER=1
mkdir -p "$DEST/modelos"

if (( PACOTES )); then
  command -v uv >/dev/null || { echo "[edin voz] instale o uv antes (./install.sh instala)."; exit 1; }
  say "Criando o venv separado em $VENV (Python 3.12)"
  uv venv -q --allow-existing -p 3.12 "$VENV"
  say "Instalando kokoro-onnx + onnxruntime (CPU), versões exatas de requirements-voz.txt (~60 MB)..."
  VIRTUAL_ENV="$VENV" uv pip install -q -r "$REPO/requirements-voz.txt"
  if (( PIPER )); then
    say "Instalando o Piper (piper-tts 1.8.0, GPL-3.0)..."
    VIRTUAL_ENV="$VENV" uv pip install -q "piper-tts==1.8.0"
  fi
fi

[[ -x "$VENV/bin/python" ]] || { echo "[edin voz] rode antes sem --modelos (falta o venv)."; exit 1; }
say "Baixando/conferindo os modelos de edin/modelos_voz.json em $DEST/modelos..."
"$VENV/bin/python" -I "$REPO/edin/voz_worker.py" baixar "$REPO/edin/modelos_voz.json" "$DEST/modelos" \
  $( (( PIPER )) && echo --piper )

"$VENV/bin/python" -I "$REPO/edin/voz_worker.py" info "$DEST/modelos"
say "Pronto. Teste: edin tts roteiro.txt --local --voz pm_alex -o voz.mp3"
