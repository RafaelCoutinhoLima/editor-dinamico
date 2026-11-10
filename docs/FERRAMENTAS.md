# Ferramentas grátis no nível profissional (roteiro)

Pesquisa de 2026-11-08: o que OpusClip, CapCut, Premiere Auto Reframe, DaVinci Smart Reframe, Submagic e Descript fazem, e como fazer o mesmo grátis e local no `edin`. Itens marcados com ✅ já estão no edin.

## Já no edin

- ✅ Corte por silêncio com ajuste por energia + verificação por retranscrição (`edin verify`).
- ✅ Reenquadramento por rosto (YuNet) com câmera virtual por plano, `pan` (manual ou `"auto"`), `extend`, `blur`, `hide` para 16:9 → 9:16 em tela cheia.
- ✅ Crítico automático (`edin check`): ritmo, gancho, legenda, som, loudness e varredura de faixas a 4 quadros/s; no vídeo final também preto, congelado, silêncio, LRA, ffprobe técnico, ritmo medido, legibilidade e contraste (`--json`).

## Próximos passos (por impacto/esforço)

1. ✅ **Limpeza de voz** (feito: `voice` no plano e `edin voice`). O que o Descript Studio Sound faz, misturado com ~15% do original para não soar robótico.
   - Já disponível: filtro `arnndn` do ffmpeg (RNNoise) com o modelo `sh.rnnn` de 300 KB ([rnnoise-models](https://github.com/GregorR/rnnoise-models)).
   - Melhor qualidade: [DeepFilterNet 3](https://github.com/Rikorose/DeepFilterNet) (MIT/Apache), binário `deep-filter` de 36 MB, 5 s de áudio em 1,3 s de CPU, WAV 48 kHz.
   - No plano: `"voice": {"clean": "dfn|rnn", "strength": 24, "chain": "broadcast"}`. Medido num vídeo de celular: ruído de fundo -25 → -40 dBFS, fala/ruído 15 → 28 dB, 231/231 palavras preservadas, atraso 0 ms.
2. ✅ **Mais QA no `edin check`** (feito, ver "O que o `edin check` mede" em [REGRAS.md](REGRAS.md)), tudo com o ffmpeg que já existe e numa passada só: `blackdetect` (quadro preto fora do fim), `freezedetect`, `silencedetect` no final, `ebur128` com pico real e LRA, ffprobe (1080x1920, yuv420p, fps constante, AAC 48 kHz, `+faststart`, áudio e vídeo com a mesma duração), cortes por minuto com `scdet`, contraste e altura mínima da legenda. `edin check plano.json final.mp4 --json` para os agentes.
3. ✅ **Câmera virtual suavizada** (feito: `focus: "face"`/`"auto"` + `reframe` no plano). O que o Premiere Auto Reframe acerta: por plano, zona morta de 15%, One Euro de ida e volta, mola com velocidade máxima e modo parado quando o alvo varia pouco; sem rosto confiável, mapa de atividade com compensação de movimento global (ORB + RANSAC do OpenCV) e saliência por resíduo espectral. Campo: `reframe: {"mode": "static|track|auto", "deadzone": 0.15, "smooth": 1.0, "max_speed": 1.0}`. Medido numa palestra 16:9 → 9:16: rosto no quadro 78,6% → 99,9%, tremor (dp da derivada de x) 24,6 → 6,2 px/quadro contra o rastreio cru.
4. ✅ **Detecção de cenas** (feito: `edin scenes`) com [PySceneDetect](https://scenedetect.com) (`AdaptiveDetector`, BSD-3): `edin scenes video.mp4` → `video.scenes.json`. Cada corte tem nota (troca de plano de verdade x conteúdo mudando no mesmo enquadramento). Rastreio e `pan` recomeçam a cada plano, `edin montage` não deixa pedaço atravessar corte (7 de 10 → 0 de 10 num teste) e `--segments` gera um segmento por cena para o reenquadrador.
5. ✅ **Rubrica de cortes estilo OpusClip** (feito: `edin hunt`, agente `cacador-de-cortes` e `edin plan --cold-open`). Hook, Flow, Value e Trend de 0 a 25 cada, preenchidos pelo agente sobre sinais objetivos do edin (frase completa nas bordas, 20 a 60 s, palavras por segundo, energia e variação de tom, perguntas, números, palavras de gancho) e **cold open** (a frase mais forte repetida no início). Medido numa palestra de 10,5 min: 74 trechos analisados em 6 s; dois shorts com cold open renderizados com 100% das palavras preservadas no `edin verify`.
6. ✅ **Upscale de fontes 720p do WhatsApp** (feito: `edin enhance` e `"enhance"` no plano, com cache por arquivo + modo; o `edin check` avisa fonte abaixo de 1080).
   - `fast`: `hqdn3d=1.5:1.5:6:6` + `scale` lanczos + `cas=0.5`, tudo no ffmpeg. O `nlmeans` dá o mesmo resultado 8x mais devagar.
   - `esrgan`: [Real-ESRGAN ncnn/Vulkan](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0) (BSD-3, 47 MB, sem Python), modelo `realesr-animevideov3` x2, quadros por pipe em lotes de 60 com leitura, GPU e encoder em paralelo. Escolhe a GPU dedicada (o binário usa a integrada Intel por padrão, 15x mais lenta). Sem Vulkan cai para `fast`.
   - Medido (degradei o original 1080x1920 para 720x1280 crf 32, melhorei de volta e comparei com o original, 10 s): só lanczos SSIM 0,9690 / PSNR 37,22 dB; `fast` 0,9673 / 36,95; `esrgan` **0,9742** / 37,11, com nitidez (variância do Laplaciano) 273 contra 252 do original e 83 do lanczos. Tela de app 1280x720 crf 30 contra o 1080p original: lanczos 0,9958, `fast` 0,9948, `esrgan` 0,9942 (texto visivelmente mais nítido que o próprio original; a métrica pune isso e o desfoque intencional que ele "conserta").
   - `realesrgan-x4plus` no rosto: SSIM 0,9645 contra 0,9709 do animevideov3 no mesmo trecho, aspecto pintado e 184 s por segundo de vídeo. Ficou o animevideov3.
   - Tempo por segundo de vídeo (RTX 4050, máquina com outros jobs): `fast` 0,5 a 1 s; `esrgan` 5,5 a 7 s (~5 quadros/s em 720p -> 1440p).
7. ✅ **Legenda nível Submagic e B-roll automático** (feito: `captions.categories`, `captions.emoji`, `broll.query`, `edin broll`, `edin captions`).
   - Legenda: palavra com posição fixa, subida e pop na palavra ativa sem tremer, letra de 80 px (antes saía com ~56 px), segunda cor por categoria (`numero`, `alerta`).
   - Emoji via PNG do [Twemoji](https://github.com/jdecked/twemoji) (CC BY 4.0, exige crédito), animado em quadros com alfa e posto com `overlay`, acima da legenda e fora do rosto. O libass não desenha emoji colorido de forma confiável.
   - B-roll pela [API do Pexels](https://www.pexels.com/api/documentation/): grátis, 200 req/h, com cache e `broll/CREDITOS.txt`.

8. ✅ **Roteiro e narração com o ElevenLabs** (feito: `edin voices`, `edin tts`, `edin falas` em `edin/elevenlabs.py` e agente `roteirista`).
   - API REST oficial ([docs](https://elevenlabs.io/docs/api-reference)), chave em `ELEVENLABS_API_KEY` ou `~/.config/edin/elevenlabs.key` (nunca no repositório). `edin doctor` mostra se achou a chave.
   - `edin voices search "Yuri"`: procura nas vozes da conta (`GET /v2/voices?search=`) e na Voice Library compartilhada (`GET /v1/shared-voices?search=`), com nome, voice_id, public_owner_id, idioma e categoria.
   - `edin voices add "<nome ou voice_id>"`: se a voz não está na conta, adiciona da biblioteca (`POST /v1/voices/add/{public_owner_id}/{voice_id}` com `new_name`). Qualquer voz da biblioteca vira utilizável só pelo nome; nome ambíguo para e lista as parecidas.
   - `edin tts roteiro.txt --voice "Yuri - Natural Brazilian Narrator" -o voz.mp3`: resolve a voz (conta → biblioteca → adiciona), confere o modelo em `GET /v1/models` (padrão `eleven_v4`; sem ele cai para `eleven_v3` e avisa), Stability 0.50, Similarity 0.75, `language_code` pt, e usa `POST /v1/text-to-speech/{voice_id}/with-timestamps`. Roteiro maior que o limite do modelo (v4 10 mil, v3 5 mil caracteres) vai em partes com `previous_text`/`next_text` e é emendado. Saídas: `voz.mp3`, `voz.alignment.json` (por caractere), `voz.words.json` (formato do `edin transcribe`, serve para legenda) e `voz.falas.json` (início, fim, silêncio depois e corte sugerido de cada fala; avisa silêncio maior que 1 s).
   - `edin falas narracao.mp3 roteiro.txt [--alignment voz.alignment.json]`: tabela fala x tempo de uma narração pronta (a de Rafael), pelo alinhamento ou por `silencedetect=noise=-35dB:d=0.35` nos N-1 maiores silêncios.
   - v3 e v4 ignoram `<break time>`: a pausa vem da linha em branco entre as falas e a sincronia é feita na montagem.
   - Testado só com respostas simuladas da API (sem chave nesta máquina): resolução de voz, queda para v3, partes e emenda, tabela por alinhamento e por silencedetect. Falta a primeira geração real.

## Lições de reenquadramento 16:9 → 9:16

- Os profissionais remontam o layout de motion e texto para o vertical em vez de recortar. Usam "Fill" com rastreio para live-action e "Fit" com fundo da própria cena, nunca faixa sólida.
- O automático propõe e o editor corrige onde errou. O `pan: "auto"` acerta telas alinhadas à esquerda. Em texto centralizado, elemento principal à direita ou fonte com zoom animado, o editor ajusta à mão.
- Fontes: [comparativo Premiere x Resolve](https://elements.tv/blog/comparing-the-auto-reframe-in-davinci-resolve-and-premiere-pro/), [AutoFlip do Google](https://research.google/blog/autoflip-an-open-source-framework-for-intelligent-video-reframing/), [layouts do OpusClip](https://help.opus.pro/docs/article/layout-and-reframing.md), [Virality Score do OpusClip](https://help.opus.pro/docs/article/virality-score).
