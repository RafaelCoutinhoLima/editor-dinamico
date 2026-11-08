# editor-dinamico

**Edição de vídeo dinâmica com IA, grátis e local.** Você grava, a IA edita: corta pausas e erros, dá zoom no ritmo da fala, reenquadra para vertical seguindo o rosto, coloca legenda animada, efeitos sonoros e música. Serve para Reels, TikTok, Shorts, YouTube, cortes de podcast, aulas, vlogs e montagens no ritmo da música.

Tudo roda no seu computador com ferramentas open source, sem assinatura e sem API paga. A ferramenta de linha de comando se chama `edin` e foi feita para ser dirigida pelo **Claude Code**: o Claude lê a transcrição, decide o que cortar, onde dar zoom e qual o gancho, e o `edin` executa.

## O que ele faz

- **Corta silêncio, "ahn", "hum" e takes repetidos** sem comer o começo ou o fim das palavras (o corte é ajustado pela energia do áudio).
- **Reenquadra 16:9 para 9:16** seguindo o rosto, ou encaixa o quadro inteiro com fundo desfocado ou de cor sólida.
- **Punch-ins e zoom suave** para esconder cortes e dar ritmo.
- **Legendas animadas** palavra a palavra (estilos `hormozi`, `clean`, `karaoke`, `minimal`) e títulos com qualquer fonte.
- **B-roll, efeitos sonoros e música** com ducking automático e áudio final em -14 LUFS.
- **Cortes de vídeo longo em vários shorts** e **montagem no ritmo da música** (detecção de BPM).
- **Crítico automático** (`edin check`) que aponta problemas de ritmo, gancho, legenda e som, e **verificação** (`edin verify`) que retranscreve o vídeo final para achar palavras perdidas.
- **Motion design por cima** (opcional, com Remotion): palavra gigante atrás da cabeça, cards, checklist, títulos animados.

## Dependências

| Dependência | Para que serve | Como é instalada |
|---|---|---|
| **Python 3.12** | roda o `edin` | automático pelo `install.sh` (via [uv](https://docs.astral.sh/uv/)) |
| **ffmpeg** | corta, junta, aplica zoom, legendas e mixa o áudio | `sudo apt install ffmpeg` (se não houver, o `install.sh` baixa uma versão estática) |
| **faster-whisper** | transcreve a fala com o tempo de cada palavra | automático |
| **OpenCV** | detecta o rosto para reenquadrar (modelo YuNet de 230 KB já incluso) | automático |
| **librosa** | detecta as batidas da música nas montagens | automático |
| **numpy** | cálculos de áudio e imagem | automático |
| **CUDA (cuBLAS/cuDNN)** | opcional: transcrição até ~13x mais rápida em GPU NVIDIA | automático se houver GPU |
| **Node.js 20+ e Remotion** | opcional: só para o motion design (`edin motion`) | `./install.sh --motion` |
| **Claude Code** | opcional, mas recomendado: é quem toma as decisões criativas | [claude.com/claude-code](https://claude.com/claude-code) |

Na primeira transcrição o modelo do Whisper é baixado (uns 500 MB para o `small`).

## Instalação

```bash
git clone https://github.com/RafaelCoutinhoLima/editor-dinamico.git
cd editor-dinamico
./install.sh            # Linux/macOS
./install.sh --motion   # opcional: + Remotion para motion design
```

O `install.sh` não precisa de `pip` nem de `sudo`. Ele cria um ambiente Python próprio em `~/.local/share/edin/venv`, coloca o comando `edin` em `~/.local/bin` e liga as skills e os agentes em `~/.claude`, para funcionarem no Claude Code em qualquer pasta. No fim roda `edin doctor` para conferir tudo.

No Windows (PowerShell), com Python e ffmpeg já instalados:

```powershell
pip install -e .
Copy-Item -Recurse -Force .claude\skills\* "$HOME\.claude\skills\"
Copy-Item -Force .claude\agents\* "$HOME\.claude\agents\"
edin doctor
```

## Como usar

### Com o Claude Code (recomendado)

Abra o Claude Code na pasta do vídeo e peça em português:

- "edita esse video.mp4 pra reels, bem dinâmico"
- "transforma esse podcast.mp4 em 4 shorts"
- "faz uma montagem de 30s com esses clipes no ritmo dessa música"

O que vem junto:

| Tipo | Nome | O que faz |
|---|---|---|
| Skill | `edicao-dinamica` | guia o Claude pelo processo inteiro de edição |
| Skill | `cinematic-motion-director` | direção de motion design em Remotion (de [Fabio Fernandes](https://github.com/fabiofernandesss/skills), MIT) |
| Agente | `critico-de-edicao` | revisa o vídeo pronto e diz "pode publicar" ou "mais uma passada", com o pior trecho |
| Agente | `cacador-de-cortes` | escolhe os melhores trechos de um vídeo longo para virar shorts |

### Manual

```bash
edin transcribe video.mp4                  # transcreve -> video.words.json
edin plan video.mp4 --preset reels         # plano de edição -> video.plan.json
edin check video.plan.json                 # aponta problemas antes de renderizar
edin render video.plan.json --draft        # rascunho rápido
edin render video.plan.json -o final.mp4   # vídeo final

edin auto video.mp4 --preset reels         # tudo de uma vez, sem refinar
```

Presets: `reels`, `podcast`, `youtube` e `aula`. Veja todos os comandos com `edin --help`.

## Documentação

- [docs/PLANO.md](docs/PLANO.md): todos os campos do plano de edição.
- [docs/REGRAS.md](docs/REGRAS.md): regras de edição (o que nunca fazer).
- [docs/MOTION.md](docs/MOTION.md): motion design com Remotion.

## Licenças

Código: MIT. Skill `cinematic-motion-director`: MIT, Fabio Fernandes. Fontes (Anton, Montserrat, Archivo Black, Poppins, Bebas Neue, Plus Jakarta Sans): SIL Open Font License. Modelo YuNet: MIT. O Remotion tem licença própria: grátis para pessoa física e empresas de até 3 pessoas.
