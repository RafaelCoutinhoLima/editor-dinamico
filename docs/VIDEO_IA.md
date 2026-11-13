# Vídeo de IA a partir de foto (`edin animar`)

A foto + parallax (`edin imagem` + `edin-foto3d.js`) dá câmera, mas a pessoa fica parada. Para gente se mexendo
de verdade (andar, correr, sorrir, cumprimentar, pedalar, virar o rosto), o `edin animar` gera um clipe de 1 a
5 s a partir de uma foto aprovada: a foto vira o primeiro quadro e o modelo inventa o movimento descrito no
prompt. Tudo local, na RTX 4050 de 6 GB, sem serviço pago.

```
edin animar foto.png "she walks up the stairs toward the sun" -o clipe.mp4 --duracao 3 --seed 7   # ~4,5 min
edin animar foto.png "..." --qualidade            # Wan2.2 completo, 50 passos: ~27 min por clipe de 3 s
edin animar foto.png "..." --n 3                  # 3 seeds seguidas para escolher
edin animar --lote clipes.json                    # vários clipes de um roteiro (texto codificado uma vez)
edin animar --lote clipes.json --so p13_escada    # só alguns ids do lote
```

Saída: `clipe.mp4` (1080x1920, 24 fps, H.264 CRF 14, sem áudio) e `clipe.nativo.mp4` (704x1280, como o modelo
gerou, CRF 12), mais `edin_animar.json` na pasta (foto, prompt, seed, passos e tempos de cada clipe, para refazer
igual).

## Modelo escolhido: Wan2.2-TI2V-5B (Wan-AI, Apache 2.0), em dois motores

- **Padrão: `fastwan`** (FastWan2.2-TI2V-5B, a versão destilada para 3 passos): ~4,5 min por clipe de 3 s.
  Movimento bom; defeitos conhecidos: pula nos 2 primeiros quadros, satura e às vezes troca o cabelo/rosto
  (ver "FastWan x Wan completo").
- **`--qualidade`: `wan`** (Wan2.2-TI2V-5B oficial, 50 passos com CFG 5): ~27 min por clipe de 3 s, GPU
  ocupada o tempo todo. Parte da foto sem pulo, mantém identidade, cor e luz. Use para **1 ou 2 planos-chave**
  quando houver tempo (ele bloqueia a GPU para o render do resto do vídeo).

| Candidato | Licença | Cabe na RTX 4050 6 GB + 14 GB de RAM? | Resultado |
|---|---|---|---|
| **Wan2.2-TI2V-5B** (`Wan-AI/Wan2.2-TI2V-5B-Diffusers`) | **Apache 2.0** | sim, com streaming por bloco (ver Memória) | **escolhido** (`--qualidade`): movimento natural, rosto e roupa preservados, 24 fps, 704x1280 nativo; ~27 min por clipe de 3 s |
| FastWan2.2-TI2V-5B (`FastVideo/FastWan2.2-TI2V-5B-FullAttn-Diffusers`) | Apache 2.0 | sim (mesma arquitetura) | **padrão** pelo tempo: difusão 35x mais rápida (40 s), mas pula no 1º quadro e às vezes troca a identidade |
| LTX-Video 2B 0.9.8 distilled | LTX Open Weights (grátis abaixo de US$ 10 mi/ano de receita, acima precisa de licença paga) | sim | não testado: licença com teto, codificador T5 de 19 GB em fp32 para baixar a 4 a 8 MB/s, e o 2B é conhecido por rosto e mãos que derretem em gente andando |
| Wan2.1 I2V 14B, Wan2.2 I2V A14B, LTX 13B, HunyuanVideo/FramePack 13B | Apache / Tencent Hunyuan Community (FramePack) | não: 14 a 28 GB de pesos; FramePack pede ~64 GB de RAM para o swap dele | descartados |
| Wan2.1 1.3B | Apache 2.0 | sim | só texto para vídeo (não parte da foto) |
| CogVideoX-5B-I2V | CogVideoX License (comercial com cadastro e teto) | sim, 720x480 a 8 fps | descartado: resolução e fps baixos, licença restrita |

Por que o TI2V-5B: é o único modelo aberto, com licença livre para uso comercial, que gera 720p a 24 fps a
partir de uma imagem e cabe nesta máquina. O VAE dele comprime 16x16x4 (o latente de 3 s em 704x1280 tem 19
quadros de 44x80), então a difusão trabalha com ~17 mil tokens: 50 passos com CFG em ~23 min, ou 3 passos
destilados (FastWan) em 40 s.

## Requisitos

| Item | Mínimo | Testado |
|---|---|---|
| GPU | NVIDIA com 6 GB de VRAM | RTX 4050 Laptop, 6 GB (5,64 GiB visíveis para o PyTorch) |
| Driver | 580+ (o torch 2.15 do PyPI traz CUDA 13.2) | 595.99 |
| RAM | 12 GB (cada etapa usa ~1 a 3 GB próprios; os pesos são lidos do disco por mmap) | 14 GB |
| Disco | ~60 GB: FastWan 10 GB + repositório oficial 34,2 GB + cópia bf16 do transformer 9,4 GB (~25 GB com `--sem-qualidade`) | NVMe |
| Venv | o mesmo do `edin imagem` (`~/.local/share/edin/imagem/venv`): torch 2.15, diffusers 0.43, transformers 5.22, accelerate 1.15, safetensors 0.8; o vídeo só acrescenta `ftfy` | |

## Instalação

```bash
./install.sh --video           # ou direto:
./install_video.sh             # pacotes (requirements-video.txt) + modelos + conversão bf16
./install_video.sh --modelos   # só baixa/confere os pesos (retoma download interrompido) e converte
./install_video.sh --sem-qualidade   # sem o transformer oficial (sem --qualidade, 30 GB a menos)
```

- Pesos em `~/.local/share/edin/video/modelos` (`EDIN_VIDEO_HOME` muda o lugar), **nunca no git**.
- `edin/modelos_video.json`: repositório, **revisão (commit) fixa**, cada arquivo com o tamanho em bytes, licença
  e autor. O instalador baixa só esses arquivos (com o mesmo `baixar` do `imagem_worker.py`) e confere o tamanho.
- O transformer oficial vem em **fp32 (20 GB)**. O instalador grava uma cópia em bf16 (9,4 GB, `transformer_bf16/`)
  mantendo em fp32 os módulos que o Wan mantém em fp32 (`time_embedder`, `scale_shift_table`, normas, RoPE):
  metade da leitura de disco por passo. Leva ~20 s com os arquivos no cache (RAM 2,7 GB).
- `edin doctor` mostra `edin animar` OK quando o venv e o FastWan + texto/VAE estão lá, e diz à parte se o
  `--qualidade` (transformer oficial + cópia bf16) está pronto.

| Modelo | Repositório e revisão | Arquivos | Tamanho | Licença |
|---|---|---|---|---|
| Wan2.2-TI2V-5B (Diffusers): texto, VAE e o transformer do `--qualidade` | `Wan-AI/Wan2.2-TI2V-5B-Diffusers` @ `b8fff7315c768468a5333511427288870b2e9635` | `transformer/` 5 shards fp32 (19,999 GB), `text_encoder/` UMT5-XXL 3 shards bf16 (11,362 GB), `vae/` (2,819 GB), tokenizer, scheduler, configs | **34,2 GB** | **Apache 2.0** |
| FastWan2.2-TI2V-5B (motor padrão) | `FastVideo/FastWan2.2-TI2V-5B-FullAttn-Diffusers` @ `3e187042a324f6f5fb68fd22110a78725253de8f` | `transformer/diffusion_pytorch_model.safetensors` (bf16) + config | 10,0 GB | Apache 2.0 |

**Licença, na prática:** Apache 2.0 permite uso comercial dos vídeos e do modelo, sem teto de receita; o Wan-AI
não reivindica direitos sobre o que você gera, e a responsabilidade pelo uso é sua (não gerar conteúdo que viole
lei ou direito de terceiros). Os clipes partem de fotos sintéticas do `edin imagem`: são ilustração, não
"aluno real" nem depoimento.

## Medições

RTX 4050 Laptop 6 GB, 14 GB de RAM, NVMe, 2026-11-13. Clipe de 3 s (73 quadros a 24 fps), 704x1280 nativo.
Tudo rodado dentro do `seguro 9000` (teto de 9 GB de RAM) e com a trava da GPU.

| O quê | wan (50 passos, CFG 5) | fastwan (3 passos DMD, sem CFG) |
|---|---|---|
| texto (UMT5-XXL, por lote) | 9 a 24 s; VRAM 2,5 a 2,8 GB; RAM 1,2 GB | igual |
| carga (VAE codifica a foto + transformer vazio) | ~6 s | ~6 s |
| difusão de 1 clipe de 3 s | **~23 min** (27,5 s por passo = 2 passadas de ~13,8 s) | **40 s** (3 passadas) |
| difusão de 1 clipe de 5 s (121 quadros, 27 mil tokens) | ~40 min estimado (atenção cresce com o quadrado) | ~70 s estimado |
| VAE (decodificar, fp32, blocos 4x3) | **~200 s** por clipe de 3 s | igual |
| ampliar para 1080x1920 (lanczos + nitidez) | ~3 s | igual |
| **total por clipe de 3 s** | **~27 min** | **~4,5 min** (o VAE domina) |
| VRAM pico (PyTorch) | 5,25 GB na difusão (12 blocos fixos); 4,3 GB no VAE; `nvidia-smi` 5,7 de 6,1 GB | 5,2 GB |
| RAM própria pico (RssAnon) | texto 1,2 GB; difusão 1,1 GB; VAE 2,6 a 3,1 GB | igual |
| GPU durante a difusão | 100% de uso, 2490 MHz, ~75 W: limitada pelo cálculo, não pela leitura dos blocos | igual |
| Tremido (diferença média entre quadros / maior salto de brilho, p13) | 4,2 níveis / 0,55 nível | 7,3 / 5,4 (pula nos 2 primeiros quadros) |

Lote de 4 clipes de 3 s no fastwan: **1041 s** (texto 24 s, difusão 193 s, VAE 810 s, ampliação 12 s), ou seja
~4,3 min por clipe. Wan completo, 1 clipe: difusão 1385 s + VAE ~200 s.

Disco e rede: 34,2 GB baixados a 4 a 8 MB/s (Wi-Fi) em ~1h40; FastWan 10 GB em ~30 min em paralelo. A conversão
bf16 leva ~20 s com os arquivos ainda no cache do disco.

## FastWan x Wan completo

O FastWan2.2-TI2V-5B é o mesmo modelo destilado por DMD (FastVideo/Hao AI Lab) para 3 passos sem CFG: a difusão
cai de 23 min para 40 s e o clipe inteiro de ~27 min para ~4,5 min (o VAE, igual nos dois, vira a maior parte).
Comparação direta só no plano da escada (`p13_escada`, mesma foto, prompt e seed 7: `clipes/wan/` x
`clipes/fastwan/`); o lote do Wan completo com os outros 3 planos foi interrompido para liberar a GPU para o
manifesto. Nos 4 testes do FastWan:

- **Pula no começo:** os quadros 1 e 2 já são outra imagem (mais contraste, saturação, céu e grama trocados,
  enquadramento mais fechado). No morro o brilho médio salta 9 níveis entre o quadro 0 e o 2. Com a foto como
  quadro 0, o corte fica visível; sem o quadro 0 o clipe não parte mais da foto aprovada.
- **Troca a identidade:** na rua o cabelo cacheado vira liso e o rosto muda; na escada o cabelo "explode".
- **Cara de IA:** contraste e saturação altos, pele plástica, sol estourado.
- O movimento em si é bom (passos, braços, cabelo no vento, a mão escrevendo). A destilação foi feita só com
  texto para vídeo ("data-free"), o que explica a perda do condicionamento pela imagem.

No Wan completo (escada): o quadro 0 é a foto e os seguintes continuam dela sem salto (brilho varia no máximo
0,55 nível entre quadros), a moça sobe 2 a 3 degraus com passada natural, a mochila balança, cabelo, roupa e
cor da foto se mantêm, câmera parada. Pés e mãos ficam inteiros nos quadros abertos; a imagem é um pouco mais
macia que a foto (704 de largura ampliado para 1080).

**Como usar os dois:** FastWan para todos os planos (cabe no tempo de um manifesto: 18 planos em ~1h20) e, se o
salto inicial aparecer, **cortar os primeiros 3 quadros** (0,125 s) e começar o clipe do quadro 3 (a foto
original deixa de ser o 1º quadro, mas o resto é contínuo). `--qualidade` só nos 1 ou 2 planos em que a
identidade e a continuidade com a foto importam (rosto em close, plano de abertura), rodando quando a GPU não é
necessária para mais nada (ex.: à noite, em lote).


## Clipes de teste

Em `videos editados/manifesto_2026-11-12/clipes/` (cada pasta tem o `edin_animar.json` com prompt, seed e tempos;
os lotes são `fastwan.lote.json` e `wan.lote.json`):

| Plano | Prompt | `fastwan/` | `wan/` (`--qualidade`) |
|---|---|---|---|
| p13_escada | she walks up the stairs toward the sun, her backpack bouncing gently with each step | sobe bem; pula nos 1os quadros, contraste alto, cabelo "explode" | **bom**: contínuo desde a foto, identidade e luz mantidas |
| p02_mao | the hand writes in the notebook with the pen, small natural handwriting movements | a mão escreve rabiscos plausíveis, dedos inteiros; o 1º quadro é mais escuro e o enquadramento muda | não gerado (lote interrompido) |
| p17_morro | they walk slowly along the hilltop at sunset, hair and clothes moving in the wind | grupo anda, cabelo ao vento; céu e grama mudam do quadro 0 para o 2 (salto de brilho de 9 níveis) | não gerado |
| p12_rua | she walks fast down the street, arms swinging, the camera tracking alongside her | passada rápida convincente; cabelo cacheado vira liso e o rosto muda | não gerado |



## Como funciona (memória)

Três etapas, cada uma num processo `python -I edin/video_worker.py <etapa>` do venv de IA, todas com a trava
`~/.cache/edin/pesado.lock` (a mesma do `edin imagem` e do `edin html`: nunca rodam juntos) e sem
`LD_LIBRARY_PATH` (ver docs/IMAGEM.md). Cada processo começa com a VRAM inteira livre.

1. **texto**: o UMT5-XXL tem 5,7 B de parâmetros (11,4 GB em bf16): não cabe nem na VRAM nem na RAM livre. O
   modelo é montado vazio (device meta), o embedding (2,1 GB) vai para a GPU e cada um dos 24 blocos é lido do
   safetensors (mmap) e posto na GPU só na hora de rodar. Todos os prompts do lote passam juntos, então os 11 GB
   são lidos uma vez por lote. 9 a 24 s, VRAM 2,5 a 2,8 GB, RAM própria 1,2 GB.
2. **gerar**: o VAE (fp32) codifica a foto (recortada para cobrir 704x1280, sem esticar) e sai da memória; o
   transformer de 5 B (9,4 GB em bf16) é montado vazio, as partes pequenas e os primeiros 10 a 12 blocos ficam
   fixos na GPU e os outros 18 a 20 são lidos do disco a cada passada, por um thread, para dois buffers de memória
   fixada (pinned) e copiados para a GPU num stream próprio enquanto a GPU calcula o bloco anterior. A GPU fica
   em 100%: a leitura não atrasa nada. RAM própria ~1 GB.
   - **Modulação por quadro:** o TI2V condiciona pela foto dando timestep 0 aos tokens do 1º quadro latente. O
     pipeline do diffusers faz isso com um timestep por token, e a modulação vira um tensor fp32 de 6x3072 por
     token (1,2 GB com 17 mil tokens, recriado em cada bloco): não cabe. O worker calcula a modulação por quadro
     e aplica por broadcast: mesma conta (diferença 0,0 no teste), ~1/900 da memória. O FFN roda em 4 fatias.
   - Sampler: UniPC de 50 passos, flow shift 5, CFG 5 com o negativo oficial do Wan (em chinês), igual ao
     `generate.py` do Wan2.2.
3. **decodificar**: o decodificador do VAE do Wan2.2 trabalha com 256 canais a 352x640 por 4 quadros: o
   decode inteiro não cabe em 6 GB nem em bf16, e o tiling do diffusers guarda o vídeo inteiro na GPU. O worker
   decodifica em blocos espaciais 4x3 (sobreposição de 64 px com rampa linear), um latente por vez com o cache
   causal do próprio VAE, e tira cada pedaço da GPU na hora. **fp32**: em bf16 caberia em 2x2 (88 s em vez de
   ~200 s), mas pele, tecido e degraus saem visivelmente mais lisos. Depois `ffmpeg` grava o nativo (CRF 12) e o
   `edin` amplia para 1080 no lado menor (lanczos + nitidez leve; `--upscale esrgan` usa o `edin enhance`).

## Lote (`--lote`)

```json
{
  "pasta": "clipes",
  "motor": "fastwan",
  "duracao": 3,
  "clipes": [
    {"id": "p13_escada", "foto": "../fotos/novas/p13_escada_s4243.png",
     "prompt": "she walks up the stairs toward the sun, her backpack bouncing gently with each step", "seed": 7},
    {"id": "p12_rua", "foto": "../fotos/novas/p12_rua_s4243.png",
     "prompt": "she walks fast down the street, arms swinging", "seed": 7, "duracao": 4, "n": 2}
  ]
}
```

Caminhos relativos ao JSON. Saída `<pasta>/<id>.mp4` (com `n` > 1: `<id>_s<seed>.mp4`). Por clipe ou no topo:
`duracao`, `seed`, `n`, `resolucao` (`vertical` 704x1280, `horizontal` 1280x704, `quadrado` 960x960 ou WxH), `motor` (`fastwan` ou `wan`; `--qualidade` na linha de comando força `wan`),
`passos`, `cfg`, `shift`, `negativo`, `sufixo`. O texto de todos os clipes é codificado de uma vez; cada clipe
paga a difusão inteira. Entre uma etapa e outra outro trabalho pesado (`edin imagem`, `edin html`) pode pegar a
trava; o lote espera e continua.

## Boas práticas de prompt de movimento

O Wan lê o prompt pelo UMT5 (até 512 tokens, multilíngue, mas foi treinado sobretudo com descrições em inglês e
chinês). O `edin animar` acrescenta no fim `natural realistic motion, steady camera, cinematic film look,
consistent face and identity` (`--sufixo ""` tira).

- **Descreva o que acontece, não a foto.** A foto já define pessoa, roupa, luz e lugar. O prompt diz a ação,
  o ritmo e o que se mexe junto: "she walks up the stairs toward the sun, her backpack bouncing gently with each
  step" é melhor que "a girl with curly hair and a backpack on stairs".
- **Uma ação por clipe**, contínua, que caiba em 3 a 5 s: andar, correr, virar o rosto e sorrir, acenar,
  escrever, pedalar, o vento no cabelo. "Ela sobe, para, vira e acena" em 3 s vira pressa e deformação.
- **Diga o ritmo:** `slowly`, `gently`, `briskly`. Sem isso o modelo escolhe, e costuma acelerar.
- **Detalhes secundários dão vida:** `hair and clothes moving in the wind`, `leaves drifting`, `light flickering
  on her face`, `she blinks and smiles softly`.
- **Câmera:** se não quiser movimento de câmera, peça `static camera` ou `steady camera` (o sufixo já pede). Para
  câmera: `the camera slowly pushes in`, `tracking shot following her`, `slow orbit`. A câmera do kit HTML pode
  andar por cima do clipe (zoom/pan leves), então em geral prefira câmera parada no clipe e mexa no HTML.
- **Coerente com a foto:** pessoa de costas não "sorri para a câmera" sem virar; peça a virada ("she turns her
  head over her shoulder and smiles"). Mão em close: movimentos pequenos ("small natural handwriting movements").
- **Duração:** 3 s (73 quadros) é o ponto bom de custo; 5 s (121 quadros) é o máximo de treino e custa ~2x. Mais
  que isso: encadeie clipes (o último quadro de um vira a foto do próximo) ou corte.
- **Gere 2 a 3 seeds** (`--n 3`) por plano importante e escolha abrindo os quadros.

## O que evitar

- Mãos fazendo gesto fino em close (pegar, contar nos dedos): é onde mais derrete.
- Rosto muito pequeno no quadro com movimento grande (multidão correndo): rostos viram borrão.
- Texto, placas, telas de celular legíveis: o modelo não preserva letras em movimento.
- Pessoas entrando no quadro do nada, pessoas se cruzando: identidade troca.
- Pedir duas pessoas fazendo ações diferentes ao mesmo tempo.
- Prompt longo descrevendo de novo a pessoa da foto: compete com a foto e muda a identidade.

## O que ainda não convence

- **Tempo do `--qualidade`:** 23 min de difusão por clipe de 3 s (5 s: ~40 min) com a GPU a 100%, travando o
  `edin html` e o `edin imagem`. Não dá para um manifesto inteiro; só planos-chave.
- **Salto inicial do FastWan** (quadros 1 e 2) e troca de identidade em parte das seeds: gere 2 a 3 seeds e
  corte os 3 primeiros quadros quando o salto aparecer.
- **VAE lento:** ~200 s por clipe de 3 s em fp32 (blocos 4x3). É ~75% do tempo no FastWan. Em bf16 cai para 88 s,
  mas a textura fica lisa; não há opção na CLI ainda (o job aceita `"vae_bf16": true`).
- **24 fps nativo:** o kit HTML roda a 60 fps; o clipe entra repetindo quadros (sem interpolação). Interpolar
  (RIFE) seria o próximo passo se o andar parecer "picado" ao lado da câmera de 60 fps.
- **Resolução:** 704x1280 ampliado para 1080x1920 (lanczos + nitidez). Fica um pouco mais macio que as fotos do
  `edin imagem`. `--upscale esrgan` existe (usa o `edin enhance`), mas não foi testado nos clipes por falta de GPU
  livre; nas fotos ele pintava a pele.
- **Mãos e rostos pequenos:** no teste a mão escrevendo saiu inteira, mas não houve teste de gesto fino nem de
  rosto em close falando ou sorrindo.
- **Só a escada foi comparada** entre os dois motores (o lote do Wan completo foi interrompido).
- **LTX-Video não testado** (ver tabela de candidatos).

## Estabilidade (correções de 2026-11-13)

- **Vídeo virava ruído puro:** os pesos de cada bloco eram copiados para a GPU num stream próprio e usados no
  stream de cálculo; sem `record_stream`, o alocador do PyTorch reaproveitava a memória do bloco para a cópia
  seguinte enquanto a GPU ainda calculava com ele. Corrigido (`Streamer._carrega`).
- **Falta de VRAM na difusão:** timestep por token (pipeline do diffusers) pedia 1,2 GB por bloco; trocado pela
  modulação por quadro (mesma conta).
- **Falta de VRAM no VAE:** decode inteiro e o tiling do diffusers não cabem; decode em blocos 4x3 com o vídeo
  indo para a CPU pedaço a pedaço.
- **RAM:** `pin_memory()` por tensor fazia o cache de memória fixada do PyTorch crescer +3 GB; trocado por 2
  buffers fixados reaproveitados. O pico de RAM informado é o `RssAnon` (memória própria): o `VmHWM` conta
  também as páginas dos safetensors mapeados (cache de disco que o kernel recupera) e chega a 6,5 GB.
- **Trava:** cada etapa pega e solta `~/.cache/edin/pesado.lock`; outro `edin imagem` pode entrar entre a difusão
  e o VAE (aconteceu: o VAE esperou 16 min). Os tempos do `edin_animar.json` separam o tempo do worker (`s`) da
  espera (`parede_s`).
- Falha de uma etapa grava o log em `~/.cache/edin/video_erro.log` e o job em `video_erro_job_<etapa>.json`
  (rode `python -I edin/video_worker.py <etapa> <job>` com o python do venv de imagem para reproduzir).

