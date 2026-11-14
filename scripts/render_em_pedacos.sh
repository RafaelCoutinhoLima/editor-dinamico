#!/usr/bin/env bash
# Render longo do `edin html` em pedaços retomáveis: cada pedaço vira um mp4 salvo no disco; se o PC cair,
# rodar de novo pula os pedaços prontos. No fim emenda sem recomprimir (mesmo codec/parâmetros) e põe o áudio.
# Em 13/11 um render de 52 min se perdeu a 90% quando o PC reiniciou.
# Uso: render_em_pedacos.sh pagina.html saida.mp4 DURACAO_TOTAL [PEDACO_S=7] -- [flags do edin html]
set -euo pipefail
pag="$1"; out="$2"; total="$3"; ped="${4:-7}"; shift 4; [ "${1:-}" = "--" ] && shift
# --audio X não vai para os pedaços (cada um começaria a voz do zero): sai daqui e entra só na emenda.
audio=""; args=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--audio" ]; then audio="$(realpath "$2")"; shift 2; else args+=("$1"); shift; fi
done
set -- "${args[@]}"
dir="$(dirname "$out")/.pedacos_$(basename "$out" .mp4)"; mkdir -p "$dir"
n=$(python3 -c "import math;print(math.ceil($total/$ped - 1e-9))")
: > "$dir/lista.txt"
for ((i=0; i<n; i++)); do
  s=$(python3 -c "print(round($i*$ped,6))"); d=$(python3 -c "print(round(min($ped, $total-$i*$ped),6))")
  f="$dir/p$(printf %03d $i).mp4"
  if [ ! -s "$f" ]; then
    echo "[pedaços] $((i+1))/$n: t=$s s, $d s"
    TMPDIR="${TMPDIR:-$HOME/.cache/edin-tmp}" seguro "${SEGURO_MB:-6000}" edin html "$pag" --start "$s" --duration "$d" "$@" -o "$f.part.mp4"
    mv "$f.part.mp4" "$f"
  else
    echo "[pedaços] $((i+1))/$n já pronto"
  fi
  echo "file '$(realpath "$f")'" >> "$dir/lista.txt"
done
if [ -n "$audio" ]; then
  ain=(-i "$audio"); af=(-af "apad,atrim=0:$total")
else
  ain=(-f lavfi -t "$total" -i anullsrc=r=48000:cl=stereo); af=()
fi
ffmpeg -v error -y -f concat -safe 0 -i "$dir/lista.txt" "${ain[@]}" \
  -map 0:v -map 1:a -c:v copy "${af[@]}" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$out"
echo "[pedaços] pronto: $out"
