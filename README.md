# editor-dinamico

**Edição de vídeo dinâmica com IA, grátis e local.** Você grava, a IA edita: corta pausas e erros, dá zoom no ritmo da fala, reenquadra para vertical seguindo o rosto, coloca legenda animada, efeitos sonoros e música. Serve para Reels, TikTok, Shorts, YouTube, cortes de podcast, aulas, vlogs e montagens no ritmo da música.

Tudo roda no seu computador com ferramentas open source, sem assinatura e sem API paga. A ferramenta de linha de comando se chama `edin` e foi feita para ser dirigida pelo **Claude Code**: o Claude lê a transcrição, decide o que cortar, onde dar zoom e qual o gancho, e o `edin` executa.

## O que ele faz

- **Corta silêncio, "ahn", "hum" e takes repetidos** sem comer o começo ou o fim das palavras (o corte é ajustado pela energia do áudio).
- **Reenquadra 16:9 para 9:16** com câmera virtual suave (estilo Premiere Auto Reframe: parada quando a pessoa quase não se mexe, segue sem tremer quando anda, recomeça a cada troca de plano detectada pelo `edin scenes`), ou encaixa o quadro inteiro com fundo desfocado ou de cor sólida.
- **Punch-ins e zoom suave** para esconder cortes e dar ritmo.
- **Legendas animadas** palavra a palavra no padrão Submagic (estilos `hormozi`, `clean`, `karaoke`, `minimal`), segunda cor para números e negações, **emojis animados** acima da legenda e títulos com qualquer fonte.
- **B-roll automático grátis** do Pexels (`edin broll "consulta"` ou `"broll": {"query": ...}` no plano), com créditos em `broll/CREDITOS.txt`.
- **Limpeza de voz** de gravação de celular (o que o Descript Studio Sound faz): DeepFilterNet ou RNNoise + cadeia broadcast (EQ, de-esser, compressor). Ligada por padrão; `edin voice` para um arquivo avulso.
- **Melhora fonte ruim** (`edin enhance`): upscale e nitidez de 720p do WhatsApp ou tela comprimida, rápido no ffmpeg ou com Real-ESRGAN na GPU.
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
| **PySceneDetect** | detecta trocas de plano (`edin scenes`; a câmera e o `pan` recomeçam por plano) | automático |
| **DeepFilterNet / RNNoise** | limpeza de voz (ruído de fundo, chiado, ventilador) | automático (baixados uma vez para `~/.local/share/edin`) |
| **Real-ESRGAN ncnn/Vulkan** | opcional: upscale de fonte ruim (720p do WhatsApp, tela comprimida) com `edin enhance --mode esrgan` ou `"enhance"` no plano; sem ele o modo `fast` usa só o ffmpeg | baixado no 1º uso (47 MB, BSD-3) para `~/.local/share/edin/bin`; precisa de GPU com Vulkan |
| **librosa** | detecta as batidas da música nas montagens | automático |
| **numpy** | cálculos de áudio e imagem | automático |
| **CUDA (cuBLAS/cuDNN)** | opcional: transcrição até ~13x mais rápida em GPU NVIDIA | automático se houver GPU |
| **Node.js 20+ e Remotion** | opcional: só para o motion design (`edin motion`) | `./install.sh --motion` |
| **PyTorch + diffusers + SDXL/Lightning + Depth Anything V2** | opcional: fotos realistas geradas na máquina (`edin imagem`) e parallax 3D por profundidade (`edin profundidade` + `edin-foto3d.js`). Precisa de GPU NVIDIA com 6 GB de VRAM ou mais, driver 580+, 12 GB de RAM e ~20 GB de disco | `./install.sh --imagem` (ou `./install_imagem.sh`): venv separado em `~/.local/share/edin/imagem` com as versões de `requirements-imagem.txt` e os modelos de `edin/modelos_imagem.json` (7,4 GB, revisões fixas). Ver [docs/IMAGEM.md](docs/IMAGEM.md) |
| **Claude Code** | opcional, mas recomendado: é quem toma as decisões criativas | [claude.com/claude-code](https://claude.com/claude-code) |

Na primeira transcrição o modelo do Whisper é baixado (uns 500 MB para o `small`).

## Instalação

```bash
git clone https://github.com/RafaelCoutinhoLima/editor-dinamico.git
cd editor-dinamico
./install.sh            # Linux/macOS
./install.sh --motion   # opcional: + Remotion para motion design
./install.sh --imagem   # opcional: + fotos realistas e profundidade (GPU NVIDIA 6 GB+, ~13 GB de download)
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
edin captions video.plan.json              # confere legenda, categorias e emojis
edin broll "estudante cansado" --n 3       # b-roll grátis do Pexels (PEXELS_API_KEY) -> broll/
edin render video.plan.json --draft        # rascunho rápido -> rascunhos/
edin render video.plan.json                # vídeo final -> videos/2026-11-06_vertical.mp4

edin auto video.mp4 --preset reels         # tudo de uma vez, sem refinar
edin enhance video.mp4 --mode fast         # fonte 720p mole -> 2x com denoise e nitidez (ou --mode esrgan)
edin imagem "student by the window at night" -o foto.png --seed 7   # foto realista 1080x1920 (docs/IMAGEM.md)
edin profundidade foto.png                 # profundidade + fundo + foto.foto3d.js para o parallax no kit HTML
```

Presets: `reels`, `podcast`, `youtube` e `aula`. Veja todos os comandos com `edin --help`.

Sem `-o`, os vídeos saem organizados: finais em `videos/AAAA-MM-DD_formato.mp4` (data do vídeo original; formato `vertical`, `horizontal`, `quadrado` ou `retrato`) e rascunhos em `rascunhos/`. Nada é sobrescrito: um segundo final do mesmo formato vira `_2`.

## Documentação

- [docs/PLANO.md](docs/PLANO.md): todos os campos do plano de edição.
- [docs/REGRAS.md](docs/REGRAS.md): regras de edição (o que nunca fazer).
- [docs/MOTION.md](docs/MOTION.md): motion design com Remotion.
- [docs/IMAGEM.md](docs/IMAGEM.md): fotos realistas (SDXL + Lightning), profundidade e parallax 3D no kit HTML; requisitos, modelos e licenças.

## Licenças

Código: MIT. Skill `cinematic-motion-director`: MIT, Fabio Fernandes. Emojis: gráficos do [Twemoji](https://github.com/jdecked/twemoji), Copyright 2019 Twitter, Inc and other contributors, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (baixados só os usados, para `~/.local/share/edin/emoji`). B-roll: vídeos do [Pexels](https://www.pexels.com/license/), créditos de cada clipe em `broll/CREDITOS.txt`. Fontes (Anton, Montserrat, Archivo Black, Poppins, Bebas Neue, Plus Jakarta Sans): SIL Open Font License. Modelo YuNet: MIT. O Remotion tem licença própria: grátis para pessoa física e empresas de até 3 pessoas. Modelos do `edin imagem` (baixados pelo instalador, fora do git): SDXL base 1.0 e SDXL-Lightning, [CreativeML Open RAIL++-M](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md); Depth Anything V2 Small, Apache 2.0.
