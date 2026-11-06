# editor-dinamico

Edição de vídeo dinâmica com IA, **100% grátis e local**, feita para ser dirigida pelo **Claude Code**.

O Claude lê a transcrição do vídeo e decide o que cortar, onde dar zoom, quais palavras destacar e qual o gancho. A ferramenta `edin` executa tudo com ferramentas open source:

| O quê | Como |
|---|---|
| Corte de silêncio, "ahn", "hum" e takes repetidos | timestamps por palavra do **faster-whisper** |
| Reenquadramento 16:9 → 9:16 seguindo o rosto | **OpenCV + YuNet** (modelo de 230 KB incluso) |
| Punch-ins e zoom suave | ffmpeg |
| Legendas animadas palavra a palavra (estilo Hormozi, karaokê, clean) | legendas ASS + fontes livres (Anton, Montserrat) |
| B-roll por cima da fala | ffmpeg |
| Efeitos sonoros (whoosh, pop, boom, ding...) | sintetizados no ffmpeg, sem direitos autorais |
| Música com ducking automático e áudio em -14 LUFS | sidechain + loudnorm |
| Cortes de vídeo longo em vários shorts | Claude escolhe os trechos |
| Montagem cortada no ritmo da música | **librosa** (detecção de BPM) |

## Instalação

Pré-requisitos: Python 3.10+ e [ffmpeg](https://ffmpeg.org/download.html) no PATH.

```bash
git clone https://github.com/RafaelCoutinhoLima/editor-dinamico.git
cd editor-dinamico
./install.sh          # Linux/macOS
```

No Windows (PowerShell):

```powershell
pip install -e .
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .claude\skills\edicao-dinamica "$HOME\.claude\skills\"
edin doctor
```

O `install.sh` instala o pacote em modo editável e liga a skill `edicao-dinamica` em `~/.claude/skills`, então ela funciona no Claude Code em qualquer pasta. Na primeira transcrição o modelo do Whisper é baixado (uns 500 MB para o `small`).

## Uso com o Claude Code

Abra o Claude Code na pasta do vídeo e peça em linguagem natural:

- "edita esse video.mp4 pra reels, bem dinâmico"
- "transforma esse podcast.mp4 em 4 shorts"
- "faz uma montagem de 30s com esses clipes do treino no ritmo dessa música"
- "legenda esse vídeo no estilo karaoke e coloca essas fotos de b-roll quando eu falar da praia"

A skill guia o Claude por: transcrever → ler → planejar → refinar o plano → rascunho → conferir os quadros → render final.

## Uso manual

```bash
edin transcribe video.mp4                    # video.words.json
edin text video.words.json                   # transcrição com tempos e índices
edin plan video.mp4 --preset reels           # video.plan.json
edin timeline video.plan.json                # prévia da linha do tempo
edin render video.plan.json --draft          # rascunho rápido
edin sheet video_rascunho.mp4                # folha de quadros para conferir
edin render video.plan.json -o final.mp4     # final

edin auto video.mp4 --preset reels           # tudo de uma vez, sem refinamento

edin montage a.mp4 b.mp4 --music m.mp3 --duration 30 -o montagem.plan.json
edin render montagem.plan.json -o montagem.mp4
```

Presets: `reels`, `podcast`, `youtube`, `aula`. Referência do plano: [docs/PLANO.md](docs/PLANO.md).

## Dicas de desempenho

- Com GPU NVIDIA, a transcrição usa CUDA sozinha. Aí vale `--model turbo` ou `large-v3`.
- Em CPU, `small` é o equilíbrio bom para português; `base` é mais rápido.
- Use `--draft` enquanto ajusta e só renderize o final no fim.

## Licenças

Código: MIT. Fontes Anton e Montserrat: SIL Open Font License (`assets/fonts`). Modelo YuNet: MIT (`assets/models`).
