#!/usr/bin/env bash
# Instala o edin e liga a skill do Claude Code em ~/.claude/skills
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v ffmpeg >/dev/null; then
  echo "ffmpeg não encontrado. Instale antes:"
  echo "  macOS:  brew install ffmpeg"
  echo "  Ubuntu: sudo apt install ffmpeg"
  exit 1
fi

python3 -m pip install -e . || python3 -m pip install --break-system-packages -e .

mkdir -p "$HOME/.claude/skills"
ln -sfn "$(pwd)/.claude/skills/edicao-dinamica" "$HOME/.claude/skills/edicao-dinamica"
echo "Skill ligada em ~/.claude/skills/edicao-dinamica"

edin doctor
