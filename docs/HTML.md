# Cena em código: HTML animado -> vídeo (`edin html`)

Para criar cenas que não existem em filmagem (título cinético, tela de app desenhada, gráfico, transição,
whip pan, contagem) escrevendo HTML/CSS/JS. O `edin html` abre a página no Chrome headless, captura **quadro a
quadro** no tempo da página (não em tempo real) e monta um MP4 com fps constante. Não engasga, não pula quadro e
renderizar duas vezes dá os mesmos quadros.

```bash
edin html cena.html                                   # -> videos/cena.mp4 ao lado da página
edin html cena.html --draft                           # meia resolução, rápido -> rascunhos/cena_rascunho.mp4
edin html cena.html --audio musica.mp3 -o final.mp4   # com música (AAC 48 kHz, cortada na duração)
edin html livre.html --duration 8                     # página sem o contrato (CSS/GSAP/canvas): modo livre
edin html whip.html --motion-blur 6                   # movimento muito rápido sem estroboscopar
```

Requisito: Google Chrome ou Chromium instalado (`edin doctor` mostra qual achou; `EDIN_CHROME=/caminho` força
um). Nenhuma dependência Python nova: o edin fala com o Chrome pelo protocolo DevTools (CDP) num pipe
(`--remote-debugging-pipe`), só com a biblioteca padrão.

## O contrato da página

A página é aberta como `file:///.../cena.html?w=1080&h=1920&fps=30&render=1` (`render=1` avisa a página para esconder controles de pré-visualização), com o viewport exatamente desse tamanho
(em px CSS). Desenhe no tamanho do viewport (`innerWidth`/`innerHeight` ou os parâmetros `w`/`h`).

**Modo contrato (recomendado).** A página define:

```js
window.EDIN = {
  duration: 12,                  // segundos
  seek: (t) => { /* desenha o estado exato do instante t (s) */ },   // pode devolver Promise
};
```

O renderizador espera `window.EDIN` existir, `document.fonts.ready` e todas as `<img>` carregadas (e
decodificadas). Para cada quadro `i`: `await EDIN.seek(i / fps)`, espera 2 `requestAnimationFrame` e captura.
`seek` precisa ser **puro**: o resultado depende só de `t`, não da ordem das chamadas (cada worker pula para a
sua faixa do tempo, e com `--motion-blur` há vários `seek` por quadro).

**Modo livre.** Página sem `window.EDIN` (animação CSS `@keyframes`, transições, WAAPI, GSAP, canvas com rAF).
Exige `--duration`. Antes de qualquer script da página o edin injeta um relógio virtual:

- `Date`, `Date.now()`, `performance.now()` andam no tempo virtual (t=0 é 2026-01-01 00:00:00 UTC).
- `requestAnimationFrame`, `setTimeout` e `setInterval` só disparam quando o edin avança o tempo (um rAF por
  quadro, ou por subquadro com motion blur, com o timestamp virtual).
- `Math.random()` tem semente fixa.
- A cada quadro, `document.getAnimations()` (animações e transições CSS, WAAPI) ficam pausadas em
  `currentTime = t - (instante em que a animação surgiu)`: as que existem no carregamento ficam em `t*1000`; uma
  transição disparada por um `setTimeout` em 1 s começa do zero em 1 s.
- O worker que vai renderizar uma faixa mais adiante avança o relógio por todos os quadros anteriores sem
  capturar. Animação que acumula estado (`x += v*dt` no rAF) dá o mesmo resultado com 1 ou 16 workers.

`--mode auto` (padrão): sem `--duration`, espera o `EDIN` até `--timeout` e falha com mensagem clara se ele
não aparecer; com `--duration`, usa o contrato se o `EDIN` existir depois do carregamento e o modo livre se
não existir. `--mode contract`/`--mode free` forçam.

No modo contrato o relógio virtual é desligado assim que o `EDIN` aparece (timers e rAF voltam ao normal,
`Math.random` continua com semente). Animações CSS que o `seek` não controla rodam em tempo real e **não** são
determinísticas: no contrato, posicione tudo no `seek`.

## Opções

| Opção | O que faz |
|---|---|
| `-o saida.mp4` | padrão `<pasta da página>/videos/<nome>.mp4` (não sobrescreve: `_2`, `_3`); `--draft` vai para `rascunhos/<nome>_rascunho.mp4` |
| `--size 1080x1920` | viewport (padrão vertical 1080x1920; `1920x1080` para horizontal) |
| `--fps 30` | quadros por segundo da saída e do tempo da página |
| `--duration S` | quantos segundos renderizar a partir de `--start`. Obrigatório no modo livre; no contrato o padrão é `EDIN.duration - start` |
| `--start S` | começa no instante S da página (para refazer só um trecho) |
| `--workers N` | Chromes em paralelo. Padrão: metade dos núcleos, limitado pela RAM livre (~0,5 GB cada em 1080x1920) |
| `--motion-blur K` | K subquadros por quadro, nos tempos `t + j/K * (obturador/360) / fps`, com média. 4 a 8 para whip pan e crash zoom. Custa K vezes o tempo. A página recebe `&mb=K&obturador=180` na URL (o kit `html-video` usa isso para o blur sintético cobrir só 1/K do obturador e o rastro não sair dobrado) |
| `--shutter 180` | ângulo do obturador do motion blur (180° = metade do intervalo entre quadros, o padrão do cinema) |
| `--audio musica.mp3` | mux AAC 48 kHz estéreo, cortado na duração (completa com silêncio se for mais curto) |
| `--audio-start S` | ponto do áudio que coincide com o início do vídeo (padrão: o mesmo `--start`) |
| `--silent-audio` | sem `--audio`, põe uma trilha AAC silenciosa (para pôr música depois no Instagram) |
| `--frames-dir pasta` | também grava a sequência PNG numerada pelo quadro da página (`000000.png`...) |
| `--crf 18`, `--preset` | qualidade/velocidade do x264 (padrão `medium`; `veryfast` no `--draft`) |
| `--draft` | `deviceScaleFactor` 0.5: o layout continua 1080x1920 mas a captura sai 540x960 (JPEG), bem mais rápido |
| `--timeout 30` | espera máxima por carregar, pelo `EDIN` e por cada `seek` |

Saída: H.264 `yuv420p` BT.709, fps constante, `+faststart`; sem áudio não há trilha (a não ser com
`--silent-audio`). Erros de JS da página (`exceptions`, `console.error`/`warn`, recurso que não carregou)
aparecem no terminal, uma vez cada. Exceção dentro do `seek` para o render e diz o quadro.

`EDIN_CHROME_FLAGS="..."` acrescenta flags ao Chrome (ex.: GPU, ver abaixo).

## Como funciona (e por que assim)

- **CDP direto no pipe, sem Playwright.** Um Chrome por worker, aberto com `--remote-debugging-pipe` (fds 3 e
  4, mensagens JSON terminadas em `\0`), lançado por `posix_spawn` (seguro com várias threads). Sem instalar
  nada (o Playwright são ~100 MB de driver Node + navegador e esconde opções de captura) e com acesso direto a
  `Page.captureScreenshot` com `optimizeForSpeed` (PNG 3x mais rápido que o padrão). Um processo por worker em
  vez de várias abas: nada de aba em segundo plano com rAF estrangulado, e um travamento derruba só um worker.
- **Faixas curtas, em ordem.** O tempo é dividido em faixas de 6 quadros; cada worker pega a próxima faixa
  livre. Um worker não pega faixa além de uma janela de `(workers + 2) x 6` quadros à frente do último gravado,
  então a fila de reordenação fica pequena (a memória não cresce com a duração).
- **Aquecimento antes de cada faixa.** O compositor do Chrome guarda histórico (camadas promovidas, cache de
  raster). Quem salta direto para o quadro 786 pinta um pouco diferente de quem veio do 785. Antes de cada faixa
  o worker pinta os 2 quadros anteriores sem capturar (custo desprezível: não há captura).
- **Pipe para o ffmpeg.** O worker decodifica o PNG (OpenCV) e o laço principal manda RGB cru, em ordem, ao
  ffmpeg (`rawvideo` -> `libx264`), com a mesma conversão BT.709 do `edin enhance`. Disco só com `--frames-dir`.
- **Raster na CPU (SwiftShader), não na GPU.** Medido numa página pesada (backdrop-filter, sombras): captura
  125 ms na CPU, 98 ms na RTX 4050 e 103 ms na Intel. A GPU ganha só ~25% por worker, e com 8 workers os
  Chromes disputariam a mesma GPU; a CPU escala com os núcleos e é estável. Para tentar a GPU:
  `__EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json EDIN_CHROME_FLAGS="--use-gl=angle --use-angle=gl-egl --ignore-gpu-blocklist --enable-gpu-rasterization"`.
  `--use-angle=vulkan` travou o Chrome headless nesta máquina.

## Números medidos

Máquina: 16 núcleos, 14 GB, RTX 4050 (sem uso), Chrome 157. Página de teste pesada de propósito: 6 cards
com `backdrop-filter`, sombras, bola com `filter: drop-shadow`, texto com `text-shadow`, tudo mudando a cada
quadro (o custo é a rasterização, ~125 ms por captura PNG em 1080x1920 num Chrome; o `seek` leva ~1 ms).

| Teste | Resultado |
|---|---|
| 60 s, 1800 quadros, 1080x1920, 1 worker | **6,0 q/s** (301 s) |
| idem, 4 workers | **21,2 q/s** (85 s) |
| idem, 8 workers | **31,8 q/s** (57 s, mais rápido que tempo real). CPU a 97%: o x264 `medium` sozinho usa ~5 núcleos |
| 15 s com 8 workers: normal / `--preset veryfast` / `--draft` | 29,1 / 32,1 / **63,6 q/s** |
| Longo: 4200 quadros (140 s) em 720x1280, 8 workers | 57,6 q/s; memória estável do início ao fim (PSS dos 8 Chromes entre 1,6 e 2,0 GB, Python ~170 MB), 4200 quadros e 140,000 s na saída |
| Modo livre (`@keyframes` linear, transição disparada por `setTimeout` em 1 s, canvas por timestamp e canvas que acumula estado), 240 quadros | passo constante em todos (8,33 px/quadro, e a transição começa exatamente no quadro 30); 0 quadros repetidos por hash; `mpdecimate` mantém 240 de 240; `freezedetect` 0 congelamentos |
| Determinismo, contrato: 900 quadros com 1, 4 e 8 workers, PNG comparado pixel a pixel | **0 diferentes** (8 x 4 workers no render de 1800 quadros: `framemd5` idêntico) |
| Determinismo, modo livre: 240 quadros com 8, 3 e 2 workers e duas execuções | 0 diferentes |
| Whip pan, 120 quadros, 8 workers: sem / com `--motion-blur 4` | 70,2 / 17,1 q/s; o quadro no meio do giro vira 4 cópias sobrepostas com rastro (sem blur: uma cópia nítida que "pula" 300 px) |

Sem o aquecimento (ver abaixo) 1 em 900 quadros saía com o brilho de um `drop-shadow` levemente diferente
(até 32 níveis em 3 mil pixels) no primeiro quadro de uma faixa. Com ele, 0 em 900.

## Armadilhas

- **Fontes web**: use arquivos locais (`@font-face { src: url(fonts/Inter.woff2) }`) ou espere
  `document.fonts.ready` antes de definir o `EDIN`. Fonte do Google Fonts pela rede pode não chegar a tempo e o
  primeiro quadro sai com a fonte de reserva. O edin espera `document.fonts.ready`, mas fonte declarada e ainda
  não usada não entra nessa espera: use `document.fonts.load('800 100px Inter')` no início.
- **Nada de `Math.random()` sem semente no contrato**: o edin fixa a semente do `Math.random`, mas cada
  worker chama o `seek` numa ordem diferente; sorteie tudo uma vez no carregamento (partículas, posições) ou use
  um gerador com semente derivada de `t`/índice. `crypto.getRandomValues` não tem semente.
- **`seek` puro**: nada de estado que dependa do quadro anterior (`x += 5` dentro do `seek`). Calcule tudo a
  partir de `t`. Física/partículas: simule de 0 até `t` com passo fixo, ou pré-calcule a trajetória.
- **`<video>` dentro da página** não acompanha o relógio: no `seek`, faça `video.currentTime = t` e espere
  o evento `seeked` (devolva a Promise). No modo livre o `<video>` toca em tempo real (não use). Prefira
  sequência de imagens ou recorte o vídeo depois no `edin render`.
- **Lottie/GSAP/anime.js no contrato**: use o seek da própria biblioteca (`anim.goToAndStop(t*1000)`,
  `timeline.seek(t)`, `tl.pause()`), não deixe tocando sozinha.
- **Imagens**: `<img>` são esperadas e decodificadas; imagens de fundo CSS e `new Image()` não. Pré-carregue no
  JS e só defina o `EDIN` depois.
- **Timers no carregamento (modo livre)**: o tempo começa parado em 0. Um `setTimeout(init, 100)` só roda quando
  o render chega em 0,1 s. Enquanto espera o `EDIN` (contrato), o edin roda rAF e timers de 0 ms, mas não os
  com atraso.
- **Tela inteira**: `html, body { margin: 0; overflow: hidden }`; a barra de rolagem já vem escondida.
- **Texto pequeno ou fino tremendo**: subpixel não é usado (`--disable-lcd-text`); mova em px inteiros ou
  use `will-change: transform` para movimento suave.
- **Motion blur só em movimento rápido**: K subquadros = K vezes o tempo. Movimento extremo (whip pan de
  ~9000 px/s) com K=4 ainda mostra as 4 cópias separadas; use 8 a 16 nesses trechos. Use `--start/--duration` para
  renderizar só o trecho do whip pan com `--motion-blur` e emende, ou aceite o custo na cena toda.
- **Disco com `--frames-dir`**: PNG de 1080x1920 tem ~1 MB; 60 s a 30 fps são ~2 GB.
- **Memória**: cada Chrome em 1080x1920 ocupa ~0,3 a 0,5 GB (PSS medido: 285 MB por Chrome). Com pouca RAM livre o padrão já reduz os workers.
