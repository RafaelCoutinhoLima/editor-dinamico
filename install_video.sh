#!/usr/bin/env bash
# Instala o `edin animar` (foto -> clipe de vídeo com Wan2.2-TI2V-5B, local). Usa o venv do edin imagem
# (~/.local/share/edin/imagem/venv, PyTorch CUDA + diffusers; cria com install_imagem.sh --pacotes se faltar) e
# acrescenta requirements-video.txt. Os pesos ficam em ~/.local/share/edin/video/modelos, nunca no git.
# Ver docs/VIDEO_IA.md.
#
#   ./install_video.sh                 pacotes + modelos: FastWan (motor padrão, 10 GB) + texto/VAE do Wan2.2 (14 GB)
#                                      + transformer oficial do Wan2.2 (20 GB, convertido para bf16) para --qualidade
#   ./install_video.sh --pacotes       só os pacotes
#   ./install_video.sh --modelos       só baixa/confere os modelos e converte (retoma download interrompido)
#   ./install_video.sh --sem-qualidade não baixa o transformer oficial (sem `edin animar --qualidade`; -30 GB)
#   EDIN_VIDEO_HOME=/outro/lugar ./install_video.sh
#
# Requisitos: GPU NVIDIA com 6 GB de VRAM ou mais, driver 580+, 12 GB de RAM, ~60 GB livres em disco
# (FastWan 10 GB + Wan2.2 34 GB + cópia bf16 9,4 GB; ~25 GB com --sem-qualidade), Linux x86_64, uv.
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"
IMG="${EDIN_IMAGEM_HOME:-$HOME/.local/share/edin/imagem}"
VENV="$IMG/venv"
DEST="${EDIN_VIDEO_HOME:-$HOME/.local/share/edin/video}"

say() { printf '\n\033[1m[edin video]\033[0m %s\n' "$*"; }
aviso() { printf '\033[33m[edin video] aviso:\033[0m %s\n' "$*"; }

PACOTES=1; MODELOS=1; QUALIDADE=1
[[ " $* " == *" --pacotes "* ]] && MODELOS=0
[[ " $* " == *" --modelos "* ]] && PACOTES=0
[[ " $* " == *" --sem-qualidade "* ]] && QUALIDADE=0

if ! command -v nvidia-smi >/dev/null || ! nvidia-smi -L >/dev/null 2>&1; then
  echo "[edin video] precisa de GPU NVIDIA com driver (nvidia-smi não respondeu)."; exit 1
fi
VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d ' ')
say "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1), ${VRAM} MB de VRAM"
(( VRAM < 5800 )) && aviso "menos de 6 GB de VRAM: o streaming por bloco ainda funciona, mas mais devagar."
mkdir -p "$DEST/modelos"
LIVRE=$(df -BG --output=avail "$DEST" | tail -1 | tr -dc 0-9)
(( LIVRE < 60 )) && aviso "só ${LIVRE} GB livres em $DEST (precisa de ~60 GB; ~25 GB com --sem-qualidade)."

if (( PACOTES )); then
  if [[ ! -x "$VENV/bin/python" ]]; then
    say "O venv do edin imagem não existe: criando (install_imagem.sh --pacotes)"
    "$REPO/install_imagem.sh" --pacotes
  fi
  say "Acrescentando requirements-video.txt ao venv $VENV"
  VIRTUAL_ENV="$VENV" uv pip install -q -r "$REPO/requirements-video.txt"
fi

if (( MODELOS )); then
  [[ -x "$VENV/bin/python" ]] || { echo "[edin video] rode antes sem --modelos (falta o venv)."; exit 1; }
  MAN="$REPO/edin/modelos_video.json"
  if (( ! QUALIDADE )); then
    # sem os 5 shards fp32 do transformer oficial (só o motor fastwan)
    MAN="$(mktemp --suffix=.json)"
    "$VENV/bin/python" -I -c "import json,sys; m=json.load(open(sys.argv[1])); a=m['modelos']['wan22_ti2v_5b']['arquivos']; [a.pop(k) for k in list(a) if k.startswith('transformer/diffusion_pytorch_model')]; json.dump(m, open(sys.argv[2],'w'))" "$REPO/edin/modelos_video.json" "$MAN"
  fi
  say "Baixando/conferindo os modelos de edin/modelos_video.json em $DEST/modelos (44 GB; 24 GB com --sem-qualidade; só arquivos listados, revisão fixa)..."
  "$VENV/bin/python" -I "$REPO/edin/imagem_worker.py" baixar "$MAN" "$DEST/modelos"
  W="$DEST/modelos/wan2.2-ti2v-5b"
  if (( QUALIDADE )) && [[ ! -f "$W/transformer_bf16/diffusion_pytorch_model.safetensors.index.json" ]]; then
    say "Convertendo o transformer oficial (fp32, 20 GB) para bf16 (9,4 GB), uma vez só..."
    JOB="$(mktemp --suffix=.json)"
    printf '{"origem": "%s/transformer", "destino": "%s/transformer_bf16"}' "$W" "$W" > "$JOB"
    env -u LD_LIBRARY_PATH "$VENV/bin/python" -I "$REPO/edin/video_worker.py" preparar "$JOB"
    rm -f "$JOB"
  fi
fi

env -u LD_LIBRARY_PATH "$VENV/bin/python" -I "$REPO/edin/video_worker.py" info
say "Pronto. Teste: edin animar foto.png \"she walks slowly toward the camera, hair moving in the wind\" -o clipe.mp4 --duracao 3 --seed 1 (ou --qualidade)"
