# Fotos realistas e profundidade (`edin imagem`, `edin profundidade`, `edin-foto3d.js`)

Para vídeo manifesto e campanha: pessoas realistas (fotografia) geradas na própria máquina e animadas como plano
de filme, com parallax real pela profundidade, no kit HTML (60 fps, motion blur 8, câmera sempre andando, presets
do Higgsfield). Nada de serviço pago nem envio de dados: SDXL + SDXL-Lightning para a foto, Depth Anything V2 para
a profundidade, WebGL no Chrome do `edin html` para a câmera.

```
edin imagem "prompt" -o foto.png      SDXL fp16 + LoRA Lightning de 4 passos, nativa 768x1344 -> 1080x1920
edin imagem --lote fotos.lote.json    vários planos de um roteiro, com personagens fixos
edin profundidade foto.png            foto.depth.png (16 bits) + foto.fundo.png + foto.foto3d.js
edin-foto3d.js (kit HTML)             a foto como relevo 3D, câmera do edin-cam por cima
```

## Requisitos

| Item | Mínimo | Testado |
|---|---|---|
| GPU | NVIDIA com 6 GB de VRAM (o SDXL fp16 tem 6,9 GB de pesos: roda em estágios, um modelo por vez na GPU) | RTX 4050 Laptop, 6 GB (5,77 GB visíveis para o PyTorch) |
| Driver | NVIDIA 580+ (o `torch 2.15.0` do PyPI traz CUDA 13.2; não precisa do CUDA Toolkit). Driver 570 a 579: troque o torch pela roda de `https://download.pytorch.org/whl/cu128` | 595.99 |
| RAM | 12 GB (UNet 5,1 GB + text encoders 1,6 GB ficam na RAM enquanto esperam a vez) | 14 GB |
| Disco | ~20 GB livres: 7,4 GB de pesos + 5,4 GB do venv + cache do download | |
| Sistema | Linux x86_64, Python 3.12 (o `uv` baixa), Chrome para o `edin html` | Linux 7.0, Chrome 157 |

Sem GPU NVIDIA o `edin imagem` não roda (na CPU seriam minutos por foto). O `edin profundidade` roda na CPU se
não houver CUDA (mais lento, mas funciona). O `edin-foto3d.js` roda em qualquer Chrome com WebGL 2 (no headless
o SwiftShader da CPU já serve; a GPU é ~5x mais rápida).

## Instalação

```bash
./install.sh --imagem          # ou direto:
./install_imagem.sh            # venv + modelos
./install_imagem.sh --modelos  # só confere/baixa os pesos (retoma download interrompido)
```

- **Venv separado** em `~/.local/share/edin/imagem/venv` (`EDIN_IMAGEM_HOME` muda o lugar), para o PyTorch
  (~5 GB com as libs CUDA) não pesar o edin principal. O edin chama `edin/imagem_worker.py` nesse venv por
  subprocesso com `python -I` (modo isolado: nem a pasta do script nem `PYTHONPATH` entram no `sys.path`).
- **Versões exatas** em `requirements-imagem.txt` (gerado do ambiente testado). Pedidos diretos: `torch 2.15.0`,
  `diffusers 0.43.0`, `transformers 5.22.2`, `accelerate 1.15.0`, `peft 0.21.2`, `safetensors 0.8.0`.
- **Modelos** em `edin/modelos_imagem.json`: repositório, **revisão (commit)** fixa, lista exata de arquivos com o
  tamanho em bytes e licença. O instalador baixa só esses arquivos para `~/.local/share/edin/imagem/modelos` e
  confere o tamanho; o `edin doctor` mostra o que falta. **Os pesos nunca vão para o git** (`.gitignore` bloqueia
  `*.safetensors`, `*.ckpt`, `*.pt`, `*.pth`, `*.onnx`, `*.gguf`).

| Modelo | Repositório e revisão | Arquivos | Tamanho | Licença |
|---|---|---|---|---|
| SDXL base 1.0 (fp16) | `stabilityai/stable-diffusion-xl-base-1.0` @ `462165984030d82259a11f4367a4eed129e94a7b` | `unet/…fp16.safetensors` 5135 MB, `text_encoder_2/model.fp16` 1389 MB, `text_encoder/model.fp16` 246 MB, `vae/…fp16` 167 MB, configs e tokenizers | 6,94 GB | CreativeML Open RAIL++-M |
| SDXL-Lightning (LoRA 4 passos) | `ByteDance/SDXL-Lightning` @ `c9a24f48e1c025556787b0c58dd67a091ece2e44` | `sdxl_lightning_4step_lora.safetensors` | 394 MB | CreativeML Open RAIL++-M |
| Depth Anything V2 Small | `depth-anything/Depth-Anything-V2-Small-hf` @ `5426e4f0f36572d16453bbda7a8389317b1bef99` | `model.safetensors`, `config.json`, `preprocessor_config.json` | 99 MB | Apache 2.0 |

**Licenças, na prática:** a Open RAIL++-M permite uso comercial das imagens geradas, mas proíbe usos listados na
licença (enganar, difamar, gerar conteúdo de pessoa real sem consentimento, etc.) e exige repassar essas
restrições se o modelo for redistribuído. As imagens são sintéticas: não use como "foto de aluno real" nem como
depoimento; no vídeo manifesto elas são ilustração. Depth Anything V2 **Small** é Apache 2.0 (os tamanhos
Base/Large são CC BY-NC, não use).

## `edin imagem`

```bash
edin imagem "back view of a student at a desk by the window at night, lit by a phone screen" \
  -o fotos/janela.png --estilo noite --lente 35 --n 4 --seed 4242
edin imagem --lote fotos.lote.json                 # todos os planos do roteiro
edin imagem --lote fotos.lote.json --so 02_caderno # só um plano (regerar com outra seed: mude "seed")
edin imagem "..." --profundidade                   # já roda o edin profundidade nas fotos geradas
```

| Opção | O que faz |
|---|---|
| `-o foto.png` | saída; com `--n 4` vira `foto_1.png` ... `foto_4.png` (seeds seguidas) |
| `--size 1080x1920` | tamanho final. Gera na resolução nativa do SDXL de proporção mais próxima (9:16 -> **768x1344**, 16:9 -> 1344x768, 1:1 -> 1024x1024, 4:5 -> 896x1152) e amplia com recorte central |
| `--seed N`, `--n 4` | semente (padrão sorteada e impressa) e variações |
| `--estilo` | `campanha` (padrão: `campaign photo, natural backlight, 35mm film, Portra 400, film grain, shallow depth of field`), `noite` (Vision3 500T, luz prática), `documental`, `nenhum` ou texto livre. Curtos de propósito: o prompt final é sujeito, personagem, lente, estilo, e o CLIP só lê 77 tokens |
| `--lente` | `24`, `35`, `50`, `85` (f/1.8, bokeh), `macro` ou texto |
| `--personagem "..."` | descrição física fixa (igual em todos os planos dela) |
| `--upscale` | `lanczos` (padrão: lanczos + nitidez leve) ou `esrgan` (Real-ESRGAN x4plus e redução; ver "Medições") |
| `--negativo` | prompt negativo; padrão contra mãos/dedos deformados, rosto distorcido, texto, marca d'água, logo, ilustração, pele de plástico. **Só tem efeito com `--cfg` > 1 ou `--sem-lightning`** (o Lightning roda sem CFG) |
| `--sem-lightning` | SDXL puro, 28 passos com CFG 5,5 e negativo: mais lento, às vezes melhores mãos |
| `--mostrar-prompt` | imprime o prompt final montado |

Cada pasta de saída ganha um `edin_imagem.json` com prompt, seed, passos, CFG, tempos e VRAM de cada imagem (para
refazer igual).

### Lote (`--lote`)

```json
{
  "pasta": "fotos", "size": "1080x1920", "estilo": "campanha", "upscale": "lanczos",
  "personagens": {
    "lu": { "descricao": "young Brazilian woman, 18, brown skin, curly dark hair bun, grey hoodie",
            "seed": 4242 }
  },
  "planos": [
    { "id": "01_janela", "personagem": "lu", "lente": "35", "estilo": "noite", "n": 2,
      "prompt": "seen from behind, a student at a desk by a big window at night, face lit by a phone screen, city lights outside" },
    { "id": "02_caderno", "lente": "50", "n": 3, "seed": 2101,
      "prompt": "close-up of one hand writing in a notebook with a pencil, warm desk lamp, wooden desk" }
  ]
}
```

Saída: `<pasta>/<id>.png` (com `n` > 1: `<id>_s<seed>.png`). O lote inteiro roda numa carga só dos modelos (os
prompts todos no text encoder, depois todas as imagens na UNet, depois todas no VAE): a partir da segunda imagem
o custo é só a UNet.

### Consistência de personagem (e o limite dela)

Nesta versão a consistência é **só por texto e semente**: a mesma descrição física fixa (idade, pele, cabelo,
roupa) entra em todos os planos do personagem e a seed padrão é a dele. Isso mantém cabelo, roupa, tom de pele e
"tipo" da pessoa, mas **o rosto muda de um plano para outro** (não há IP-Adapter, InstantID nem LoRA de
personagem). Por isso, planos de personagem recorrente:

- **prefira** costas, perfil, contraluz/silhueta, mãos, pés, sombra, reflexo, desfoque, rosto parcialmente
  coberto (capuz, cabelo, celular), plano aberto com a pessoa pequena;
- **evite** rosto frontal em close em mais de um plano (o espectador nota que são duas pessoas);
- **roupa e cabelo marcantes** carregam a continuidade (moletom cinza largo, coque de cachos);
- mesma luz e mesma hora do dia em planos vizinhos ajudam mais que a seed.

### Boas práticas de prompt (pessoas realistas brasileiras, estudantes)

- **Inglês**, sujeito primeiro, depois ação, lugar, luz e lente. O CLIP lê só os primeiros **77 tokens**: o
  `edin` avisa quando passa (o estilo vai no fim e é o que se perde). Prompt curto e concreto rende mais.
- **Brasileiros de verdade:** diga a pele e o cabelo (`brown skin`, `dark skin`, `light brown skin`, `curly`,
  `coily`, `straight black hair`), não só "Brazilian" (sozinho puxa estereótipo). Para grupo: `diverse group of
  Brazilian students, mixed skin tones`. Ambientes daqui: `Brazilian public school courtyard`, `concrete stairs`,
  `bus stop`, `small bedroom with a ceiling fan`, `tiled kitchen table`.
- **Idade:** estudante de vestibular é `18` ou `young woman/man, 18`. Não descreva menores.
- **Luz conta a história:** `backlight`, `rim light`, `golden hour`, `blue hour`, `lit by a phone screen`,
  `warm desk lamp`, `window light`. Contraluz e silhueta escondem as falhas do modelo (mãos e rosto).
- **Lente:** `35mm` para ambiente, `50mm` para meio corpo, `85mm` para retrato com fundo desfocado (separa bem o
  sujeito: a profundidade sai limpa e o parallax fica bonito).
- **Mãos:** o ponto fraco do SDXL. Peça a mão fazendo uma coisa simples (`holding a pencil`, `hands on a
  notebook`), gere `n: 3` ou mais e **abra todas**; descarte dedo a mais/fundido e regere com outra seed.
- **Multidão:** comece o prompt por `blurry crowd` e peça `long exposure motion blur, out of focus`: só
  "out of focus" no fim foi ignorado no teste e saíram rostos pequenos nítidos (deformados).
- **De costas:** `seen from behind` no começo do prompt funciona; "back view" no meio foi ignorado.
- **Uma mão só:** `one hand writing` reduz mão extra (com "hands" vinham três).

### O que evitar

- Texto na cena (placa, camiseta com frase, capa de livro legível): sai garrafal. O negativo ajuda pouco no
  Lightning; se aparecer, regere ou cubra no HTML.
- Logo/marca real, uniforme de escola real, pessoa famosa ou real: proibido pela licença e pelo bom senso.
- Close frontal de rosto como plano principal recorrente (consistência), dedos entrelaçados, duas pessoas se
  tocando (anatomia se mistura), espelho (o reflexo não bate).
- Cabelo solto e fino contra fundo claro: a profundidade erra os fios e no parallax eles grudam no fundo.

## `edin profundidade`

```bash
edin profundidade fotos/01_janela.png fotos/03_escada.png     # várias numa carga só
edin profundidade foto.png --folga 0.08 --nome janela
```

Saídas ao lado da foto:

- `foto.depth.png`: **16 bits**, 0 = longe, 65535 = perto (disparidade relativa do Depth Anything V2 Small,
  normalizada nos percentis 0,5 e 99,5, com a borda presa à borda da cor por um filtro guiado: sem halo de fundo
  grudado no sujeito). A rede roda com o lado menor em 770 px (`--lado`, múltiplo de 14), não os 518 padrão:
  borda mais fina.
- `foto.fundo.png`: a foto com as **bordas de oclusão preenchidas**: na faixa de `--folga` (padrão 6% do lado
  menor = 65 px em 1080) para dentro de cada degrau de profundidade, a cor vem só de pixels com a mesma
  profundidade do fundo (convolução normalizada por fatias de profundidade), nunca do sujeito, com grão parecido
  com o da foto. É o que aparece atrás do ombro quando a câmera anda.
- `foto.foto3d.js`: foto (JPEG 93), fundo (JPEG 90) e as duas profundidades (PNG 8 bits, R = frente, G = fundo)
  embutidas em data URL, mais `meta` (foco = profundidade do sujeito, centro do sujeito). Carregar por `<script>`
  funciona no `file://` do navegador comum (sem bloqueio de CORS) e no `edin html`.

## Parallax no kit HTML

Ver "Fotos realistas com profundidade" no `LEIAME.md` do kit
(`.claude/skills/edicao-dinamica/references/html-video/`). Resumo: `<div data-z="1" data-foto3d>` +
`EdinFoto3D.criar(el, { foto: 'nome', ... }, ctx)`; a câmera do `edin-cam` (qualquer preset ou `mix`) move a
foto em 3D. O `edin html` liga a GPU sozinho para essas páginas (`--gpu auto`).

**WebGL no Chrome headless:** o Chrome 157 headless do `edin html` já tem WebGL 2 sem flag nenhuma (ANGLE sobre
SwiftShader, na CPU). Com `--gpu sim` (automático quando a página usa o `edin-foto3d.js` e existe
`/usr/share/glvnd/egl_vendor.d/10_nvidia.json`) o edin acrescenta `--use-gl=angle --use-angle=gl-egl
--ignore-gpu-blocklist --enable-gpu` e `__EGL_VENDOR_LIBRARY_FILENAMES` da NVIDIA: WebGL na RTX.

## Medições

RTX 4050 Laptop 6 GB, 14 GB de RAM, Chrome 157, 2026-11-12. Download pela rede desta máquina (~3 a 4,6 MB/s).

| O quê | Resultado |
|---|---|
| Instalação | venv 5,4 GB (torch com libs CUDA 13.2) em 16,5 min; pesos 7,4 GB em ~45 min |
| 1 imagem, a frio (`edin imagem "..."`) | **29,7 s**: carga 0,6 s, prompts 2,1 s, UNet para a GPU + LoRA fundido 12,1 s, **UNet 2,0 s**, VAE 2,4 s, ampliação 0,12 s (o resto é importar o torch) |
| Lote de 9 imagens | 53,7 s (**6,0 s por imagem**) |
| Lote de 16 imagens | 76,4 s (**4,8 s por imagem**): UNet 1,4 s, VAE 1,9 s (fp32, sem tiling) por imagem |
| `--sem-lightning` (28 passos, CFG 5,5, negativo) | UNet 19,4 s por imagem; 39,5 s a frio |
| VRAM (pico do PyTorch por estágio) | text encoders 1592 MB, **UNet 5128 MB** (5350 sem Lightning, com CFG), VAE fp32 4898 MB; `nvidia-smi` no máximo **5261 de 6141 MB**. A UNet inteira coube: o offload por camadas (plano B automático se faltar VRAM) não foi preciso |
| RAM | pico de 6,3 GB (processo do worker) |
| `--upscale esrgan` | +17 s por imagem e a pele/grão ficam pintados; o lanczos + nitidez (0,12 s) preserva o grão: ficou o padrão |
| `edin profundidade` | rede 0,3 a 0,5 s por foto (lado 770), pós (filtro guiado, fundo, pacote) 0,6 a 1,2 s; 4 fotos em 11,4 s com a carga; VRAM 716 MB |
| `.foto3d.js` | 1,0 a 1,5 MB por foto |
| `edin html` com 2 fotos, 8 s, rascunho (`--draft --fps 30`) | 240 quadros em 3,5 s (68 q/s) |
| idem, filme (`--fps 60 --motion-blur 8`) | **480 quadros (3840 subquadros) em 104 s** (4,6 q/s), 8 workers, GPU |
| WebGL na GPU x CPU (1080x1920, 30 fps, sem blur) | 16,5 q/s x 3,0 q/s (SwiftShader) |
| Determinismo | 0 pixels diferentes entre 1 e 4 workers na GPU; GPU x CPU diferença média 0,03 nível |

**Taxa de descarte (abrindo todas as imagens):** no primeiro lote (prompts longos, estilo cortado pelos 77 tokens)
5 de 9 foram descartadas: 2 de 3 mãos deformadas, 1 pessoa duplicada (duas cabeças), 1 pessoa flutuando, e a
multidão saiu nítida com rostos pequenos. No segundo lote (estilos curtos, "seen from behind", "one hand",
"blurry crowd ... motion blur") 3 de 16: 1 pessoa duplicada, 2 mãos estranhas (pinça, garra). Conte com
**gerar 3 a 4 por plano e escolher**; em close de mão, 1 em 2 sai ruim.

## O que ainda não convence

- **Faixa revelada no arc:** o fundo preenchido não inventa textura (degrau, tijolo): onde a câmera revela mais
  de ~30 px atrás do sujeito, aparece uma mancha borrada com a cor do que está ao lado (no teste, uma faixa
  clara ao lado do braço no fim do arc de 3,6 graus). Em fundo desfocado (bokeh de cidade) não se nota; em
  fundo nítido e texturado, use arc menor (`orbita: 0.08`) ou dolly/truck em vez de arc. Inpainting de verdade
  (SDXL inpaint) resolveria, mas exige outro modelo de 5 GB.
- **Figuras pequenas no fundo** (pessoas longe na escada) viram "recortes" com borda dura quando o arc as
  descola do céu: a profundidade delas é boa, mas o fundo atrás delas é céu liso preenchido.
- **Consistência de rosto:** só por descrição + seed (sem IP-Adapter). Ver acima.
- **Mãos** no Lightning: ~50% de descarte em close; `--sem-lightning` acerta mais, mas leva 20 s por imagem.
- **Negativo** não age no Lightning (CFG 0); texto e marca d'água dependem do prompt e da escolha.
- **Respiração (`vida`)**: 0,6% de escala local é sutil a ponto de quase não se ver em silhueta de costas; mais
  que ~1,5% deforma a roupa contra o fundo.
