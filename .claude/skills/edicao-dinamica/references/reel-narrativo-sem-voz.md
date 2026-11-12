# Reel narrativo sem voz (história + telas do app + texto na tela)

Modelo: `~/Área de trabalho/videos editados/reel_loopedu_ciclo_2026-11-11/` (Remotion: `motion/src/Main.tsx`, `Desk.tsx`).

## Cenas que faltam
- **Não use Canva, Higgsfield nem Gemini pelo navegador** quando faltarem imagens (Rafael: "esqueça isso de canva quero que você mesmo faça o vídeo"). Crie as cenas em código: SVG/HTML no Remotion, com PNG exportado de cada uma (`npx remotion still`). Para cenas com câmera e movimento contínuo, use o fluxo I da skill (kit `html-video/` + `edin html`), com a direção de câmera de `higgsfield-camera.md`.
- Pessoa fotorrealista não sai em código: conte a história com objetos (mesa vista de cima, relógio LED, caderno manuscrito, celular acendendo, bolinhas de papel se acumulando). Vista de cima repetida = sensação de loop.
- Ligue o objeto ao produto: o caderno trazia o mesmo assunto que o app marca como "Ponto de atenção".
- Relógio de 7 segmentos: segmento com folga pequena (2 px). Folga grande deixou os números como manchas. Brilho com um blur só.
- Fotos aprovadas pequenas (~600 px): Real-ESRGAN `realesrgan-x4plus` misturado 65% com o lanczos (evita cara de plástico) + grão de filme.
- Print do Canva vem com moldura branca: meça e recorte.

## Montagem
- Texto em minúsculas, Sora 700 ~78 px, sombra suave, fade de 0,2 s, entre 12% e 80% da altura. Nunca em cima da informação da cena (ex.: o 05:40 do despertador).
- Telas do app: recorte sem a barra lateral (nome da conta de teste), ESRGAN `realesr-animevideov3` x2, cartão de 1000 px sobre degradê da marca, destaque com borda laranja pulsando e lupa da linha num callout separado embaixo (sem zoom na tela).
- Final: o anel aberto da logo LoopEdu se fecha ("agora o ciclo fecha."), em tom quente e claro (o primeiro final ficou marrom e escuro).
- Exporte com AAC silencioso estéreo quando a música vai ser escolhida no Instagram; entregue também a versão sem texto e a grade de quadros.
- Remotion: nunca ponha `opacity` num pai de camadas com `mixBlendMode` (o grupo isola e o multiply vira véu cinza-azulado). Aplique a opacidade em cada camada.
- Camadas globais (grão, vinheta, tom frio) saem junto com o dissolve da cena seguinte, nunca com corte seco no meio dela; meça a luma quadro a quadro nas emendas (`signalstats`).
- Telas do app: borda do recorte só em vão entre blocos (linha de filtros incluída), e sem cursor parado em cima (quadro sem cursor no conteúdo ou apagar e reconstruir o elemento).
