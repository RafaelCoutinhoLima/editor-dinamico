# Ferramentas grátis no nível profissional (roteiro)

Pesquisa de 2026-11-08: o que OpusClip, CapCut, Premiere Auto Reframe, DaVinci Smart Reframe, Submagic e Descript fazem, e como fazer o mesmo grátis e local no `edin`. Itens marcados com ✅ já estão no edin.

## Já no edin

- ✅ Corte por silêncio com ajuste por energia + verificação por retranscrição (`edin verify`).
- ✅ Reenquadramento por rosto (YuNet), `pan` (manual ou `"auto"`), `extend`, `blur`, `hide` para 16:9 → 9:16 em tela cheia.
- ✅ Crítico automático (`edin check`): ritmo, gancho, legenda, som, loudness e varredura de faixas a 4 quadros/s.

## Próximos passos (por impacto/esforço)

1. ✅ **Limpeza de voz** (feito: `voice` no plano e `edin voice`). O que o Descript Studio Sound faz, misturado com ~15% do original para não soar robótico.
   - Já disponível: filtro `arnndn` do ffmpeg (RNNoise) com o modelo `sh.rnnn` de 300 KB ([rnnoise-models](https://github.com/GregorR/rnnoise-models)).
   - Melhor qualidade: [DeepFilterNet 3](https://github.com/Rikorose/DeepFilterNet) (MIT/Apache), binário `deep-filter` de 36 MB, 5 s de áudio em 1,3 s de CPU, WAV 48 kHz.
   - No plano: `"voice": {"clean": "dfn|rnn", "strength": 24, "chain": "broadcast"}`. Medido num vídeo de celular: ruído de fundo -25 → -40 dBFS, fala/ruído 15 → 28 dB, 231/231 palavras preservadas, atraso 0 ms.
2. **Mais QA no `edin check`**, tudo com o ffmpeg que já existe: `blackdetect` (quadro preto fora do fim), `freezedetect`, `silencedetect` no final, `ebur128` com pico real e LRA, ffprobe (1080x1920, yuv420p, fps constante, AAC 48 kHz, `+faststart`, áudio e vídeo com a mesma duração), cortes por minuto com `scdet`, contraste e altura mínima da legenda.
3. **Câmera virtual suavizada** (o que o Premiere Auto Reframe acerta): mapa de atividade com compensação de movimento global (ORB + RANSAC do OpenCV), zona morta de ~15%, filtro One Euro, velocidade máxima e modo "parado" por plano. Campo: `reframe: {"mode": "static|track|auto", "deadzone": 0.15}`.
4. **Detecção de cenas** com [PySceneDetect](https://scenedetect.com) (`AdaptiveDetector`, BSD-3, 1 MB): `edin scenes video.mp4` → `scenes.json`, para recomeçar o rastreio a cada plano e não deixar `pan` atravessar corte.
5. **Rubrica de cortes estilo OpusClip** no agente `cacador-de-cortes`: Hook, Flow, Value e Trend de 0 a 25 cada, mais sinais objetivos (pico de energia, palavras por segundo, frase completa, 20 a 60 s) e **cold open** (a frase mais forte repetida no início).
6. **Upscale de fontes 720p do WhatsApp.**
   - Rápido: `nlmeans` ou `hqdn3d` + `scale` lanczos + `cas=0.5`, todos no ffmpeg.
   - Qualidade: [Real-ESRGAN ncnn/Vulkan](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0), 47 MB, sem Python. O modelo `realesr-animevideov3` é ótimo para tela, texto e motion.
   - Comando: `edin enhance`.
7. ✅ **Legenda nível Submagic e B-roll automático** (feito: `captions.categories`, `captions.emoji`, `broll.query`, `edin broll`, `edin captions`).
   - Legenda: palavra com posição fixa, subida e pop na palavra ativa sem tremer, letra de 80 px (antes saía com ~56 px), segunda cor por categoria (`numero`, `alerta`).
   - Emoji via PNG do [Twemoji](https://github.com/jdecked/twemoji) (CC BY 4.0, exige crédito), animado em quadros com alfa e posto com `overlay`, acima da legenda e fora do rosto. O libass não desenha emoji colorido de forma confiável.
   - B-roll pela [API do Pexels](https://www.pexels.com/api/documentation/): grátis, 200 req/h, com cache e `broll/CREDITOS.txt`.

## Lições de reenquadramento 16:9 → 9:16

- Os profissionais remontam o layout de motion e texto para o vertical em vez de recortar. Usam "Fill" com rastreio para live-action e "Fit" com fundo da própria cena, nunca faixa sólida.
- O automático propõe e o editor corrige onde errou. O `pan: "auto"` acerta telas alinhadas à esquerda. Em texto centralizado, elemento principal à direita ou fonte com zoom animado, o editor ajusta à mão.
- Fontes: [comparativo Premiere x Resolve](https://elements.tv/blog/comparing-the-auto-reframe-in-davinci-resolve-and-premiere-pro/), [AutoFlip do Google](https://research.google/blog/autoflip-an-open-source-framework-for-intelligent-video-reframing/), [layouts do OpusClip](https://help.opus.pro/docs/article/layout-and-reframing.md), [Virality Score do OpusClip](https://help.opus.pro/docs/article/virality-score).
