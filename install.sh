#!/usr/bin/env bash
# Instala o edin num ambiente próprio, liga a skill e os agentes do Claude Code e confere tudo.
#   ./install.sh            instala
#   ./install.sh --motion   também instala o Remotion (motion design por cima do vídeo)
set -euo pipefail
cd "$(dirname "$0")"
REPO="$(pwd)"
BIN="$HOME/.local/bin"
VENV="${EDIN_VENV:-$HOME/.local/share/edin/venv}"
mkdir -p "$BIN"
export PATH="$BIN:$PATH"

say() { printf '\n\033[1m[edin]\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------- uv (gerencia Python e pacotes sem sudo)
if ! command -v uv >/dev/null; then
  say "Instalando uv (gerenciador de Python)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# ---------------------------------------------------------------- Python 3.12 + edin
# 3.12: faster-whisper/ctranslate2 e opencv têm wheels prontos; versões muito novas do Python às vezes não.
say "Criando ambiente em $VENV"
uv venv -q --allow-existing -p 3.12 "$VENV"
VIRTUAL_ENV="$VENV" uv pip install -q -e "$REPO"
# bibliotecas CUDA para o whisper usar a GPU NVIDIA (se houver)
if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then
  say "GPU NVIDIA encontrada: instalando cuBLAS/cuDNN para o whisper"
  VIRTUAL_ENV="$VENV" uv pip install -q "nvidia-cublas-cu12" "nvidia-cudnn-cu12==9.*" || true
fi

cat > "$BIN/edin" <<EOF
#!/usr/bin/env bash
# atalho gerado pelo install.sh do editor-dinamico
NV="\$("$VENV/bin/python" -c 'import nvidia.cublas.lib as a,nvidia.cudnn.lib as b;print(list(a.__path__)[0]+":"+list(b.__path__)[0])' 2>/dev/null)"
[ -n "\$NV" ] && export LD_LIBRARY_PATH="\$NV\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"
exec "$VENV/bin/edin" "\$@"
EOF
chmod +x "$BIN/edin"

# ---------------------------------------------------------------- ffmpeg
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  if command -v apt-get >/dev/null && sudo -n true 2>/dev/null; then
    say "Instalando ffmpeg pelo apt..."
    sudo apt-get install -y ffmpeg
  elif command -v brew >/dev/null; then
    brew install ffmpeg
  else
    say "ffmpeg não encontrado e sem sudo: baixando ffmpeg estático (o ideal é 'sudo apt install ffmpeg')"
    VIRTUAL_ENV="$VENV" uv pip install -q static-ffmpeg
    "$VENV/bin/python" -c "import static_ffmpeg; static_ffmpeg.add_paths()"
    SF="$("$VENV/bin/python" -c 'import static_ffmpeg,os;print(os.path.dirname(static_ffmpeg.__file__))')/bin/linux"
    ln -sfn "$SF/ffmpeg" "$BIN/ffmpeg"
    ln -sfn "$SF/ffprobe" "$BIN/ffprobe"
  fi
fi

# ---------------------------------------------------------------- skill e agentes do Claude Code
mkdir -p "$HOME/.claude/skills" "$HOME/.claude/agents"
ln -sfn "$REPO/.claude/skills/edicao-dinamica" "$HOME/.claude/skills/edicao-dinamica"
for a in "$REPO"/.claude/agents/*.md; do
  ln -sfn "$a" "$HOME/.claude/agents/$(basename "$a")"
done
say "Skill e agentes ligados em ~/.claude (edicao-dinamica, $(ls "$REPO"/.claude/agents | sed 's/\.md//' | tr '\n' ' '))"

# ---------------------------------------------------------------- motion (Remotion), opcional
if [[ "${1:-}" == "--motion" ]]; then
  if ! command -v npm >/dev/null; then
    say "Node.js não encontrado. Instale o Node 20+ (https://nodejs.org) e rode de novo com --motion."
  elif [ -f "$REPO/remotion/package.json" ]; then
    say "Instalando o Remotion em remotion/ ..."
    (cd "$REPO/remotion" && npm install --no-fund --no-audit)
  fi
  # skill de motion design (MIT, fabiofernandesss/skills), versionada neste repositório
  ln -sfn "$REPO/.claude/skills/cinematic-motion-director" "$HOME/.claude/skills/cinematic-motion-director"
  say "Skill cinematic-motion-director ligada em ~/.claude/skills"
fi

case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *)
  say "Adicione ~/.local/bin ao PATH: echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc" ;;
esac

edin doctor
