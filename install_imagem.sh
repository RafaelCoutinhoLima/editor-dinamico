#!/usr/bin/env bash
# Instala o gerador de fotos realistas do edin (`edin imagem`, `edin profundidade`) num ambiente SEPARADO do
# edin principal: PyTorch CUDA + diffusers + transformers em ~/.local/share/edin/imagem/venv e os pesos em
# ~/.local/share/edin/imagem/modelos. Os pesos nunca vão para o git. Ver docs/IMAGEM.md.
#
#   ./install_imagem.sh            pacotes (requirements-imagem.txt) + modelos (edin/modelos_imagem.json)
#   ./install_imagem.sh --pacotes  só o venv
#   ./install_imagem.sh --modelos  só baixa/confere os modelos (retoma download interrompido)
#   EDIN_IMAGEM_HOME=/outro/lugar ./install_imagem.sh
#
# Requisitos: GPU NVIDIA com 6 GB de VRAM ou mais, driver NVIDIA 580 ou mais novo (o torch 2.15 do PyPI traz CUDA 13.2), 12 GB de RAM,
# ~20 GB livres em disco (7,4 GB de pesos + ~6 GB de pacotes + cache do download), Linux x86_64, uv.
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"
DEST="${EDIN_IMAGEM_HOME:-$HOME/.local/share/edin/imagem}"
VENV="$DEST/venv"

say() { printf '\n\033[1m[edin imagem]\033[0m %s\n' "$*"; }
aviso() { printf '\033[33m[edin imagem] aviso:\033[0m %s\n' "$*"; }

PACOTES=1; MODELOS=1
[[ " $* " == *" --pacotes "* ]] && MODELOS=0
[[ " $* " == *" --modelos "* ]] && PACOTES=0

# ---------------------------------------------------------------- requisitos de hardware
if ! command -v nvidia-smi >/dev/null || ! nvidia-smi -L >/dev/null 2>&1; then
  echo "[edin imagem] precisa de GPU NVIDIA com driver (nvidia-smi não respondeu)."; exit 1
fi
VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
DRV=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | cut -d. -f1)
GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
say "GPU: $GPU, ${VRAM} MB de VRAM, driver $DRV"
(( VRAM < 5800 )) && aviso "menos de 6 GB de VRAM: o SDXL fp16 provavelmente não cabe nem em estágios."
(( DRV < 580 )) && aviso "driver $DRV: o torch 2.15 do PyPI (CUDA 13.2) pede driver 580+. Atualize o driver ou troque o torch pela roda de https://download.pytorch.org/whl/cu128 (ver requirements-imagem.txt)."
RAM=$(awk '/MemTotal/ {print int($2/1048576)}' /proc/meminfo)
(( RAM < 12 )) && aviso "${RAM} GB de RAM: o SDXL carrega ~7 GB na RAM; com menos de 12 GB pode faltar memória."
mkdir -p "$DEST"
LIVRE=$(df -BG --output=avail "$DEST" | tail -1 | tr -dc 0-9)
(( LIVRE < 20 )) && aviso "só ${LIVRE} GB livres em $DEST (precisa de ~20 GB)."

# ---------------------------------------------------------------- pacotes (venv separado)
if (( PACOTES )); then
  command -v uv >/dev/null || { echo "[edin imagem] instale o uv antes (./install.sh instala)."; exit 1; }
  say "Criando o venv separado em $VENV (Python 3.12)"
  uv venv -q --allow-existing -p 3.12 "$VENV"
  say "Instalando PyTorch (CUDA 13.2) + diffusers + transformers, versões exatas de requirements-imagem.txt (~5,4 GB)..."
  VIRTUAL_ENV="$VENV" uv pip install -q -r "$REPO/requirements-imagem.txt"
fi

# ---------------------------------------------------------------- modelos (só os arquivos listados, revisão fixa)
if (( MODELOS )); then
  [[ -x "$VENV/bin/python" ]] || { echo "[edin imagem] rode antes sem --modelos (falta o venv)."; exit 1; }
  say "Baixando/conferindo os modelos de edin/modelos_imagem.json em $DEST/modelos (~7,4 GB)..."
  "$VENV/bin/python" -I "$REPO/edin/imagem_worker.py" baixar "$REPO/edin/modelos_imagem.json" "$DEST/modelos"
fi

# ---------------------------------------------------------------- conferência
"$VENV/bin/python" -I "$REPO/edin/imagem_worker.py" info
say "Pronto. Teste: edin imagem \"a student reading by the window at night\" -o teste.png --seed 1"
