# Kit de vídeo em HTML (edin html)

JavaScript puro, sem build e sem dependências. Abra `exemplo.html` no navegador (file://) para ver e arrastar a barra de tempo; o `edin html` abre a mesma página com `?w=1080&h=1920&fps=60&render=1` (e `&mb=K&obturador=180` com `--motion-blur K`), chama `EDIN.seek(t)` quadro a quadro e captura. `?w=1920&h=1080` gera a versão horizontal. `?t=5.2` abre já nesse instante.

Arquivos: `edin-video.js` (linha do tempo, transições, easings, ruído, grão de película, luz, grade de cor, poeira), `edin-cam.js` (câmera 2.5D com os presets do Higgsfield, valores de `../higgsfield-camera.md`, deriva, profundidade de campo), `exemplo.html` (Reel de 29,2 s em 7 planos, feito para 60 fps com `--motion-blur 8`; o último quadro é o primeiro), `fontes/` (Sora 600 e 700).

Render de filme (o padrão para entregar): `edin html exemplo.html --fps 60 --motion-blur 8 -o videos/final.mp4`. Rascunho para iterar: `--draft --fps 60` sem motion blur; trecho: `--start S --duration D`.

## O exemplo (storyboard)

| # | plano | tempo | câmera | entra por | legenda |
|---|---|---|---|---|---|
| 1 | relógio 22:58 a 00:58, anel nunca fecha | 0 a 3,8 | crash zoom leve + dolly-in + deriva; recua no último 1 s | quadro 0 = capa | 3 horas estudando e não fixa? |
| 2 | caderno, o anel vira o círculo do 4/6 | 3,8 a 7,4 | dolly-in + deriva, lápis desfocado na frente | match cut no anel (continua o recuo) | e nada fecha |
| 3 | ponto laranja entre interrogações | 7,4 a 11,2 | dolly-zoom-out + deriva | whip pan com corte no borrão | o problema não é você |
| 4 | card "ponto de atenção" | 11,2 a 15,6 | arc + dolly-in + foco no card | zoom-through pelo ponto | você não sabe onde trava |
| 5 | a semana se organizando (blocos pousam nos dias) | 15,6 a 19,2 | dolly-in + deriva + truck no fim | travessia: a câmera desce do card até a mesa | e a semana se organiza |
| 6 | plano da semana no app (`data-tela`) | 19,2 a 23,8 | truck que continua o do plano 5 + deriva | dissolve no movimento (mesma velocidade) | um estudo feito pra você |
| 7 | LoopEdu: anel fecha, cresce, vira o relógio do quadro 0 | 23,8 a 29,2 | pullback que volta ao neutro + deriva com saída | dissolve | agora o ciclo fecha. (e a de abertura no fim) |

## Como escrever uma cena

```html
<div id="palco"></div>
<script src="edin-video.js"></script><script src="edin-cam.js"></script>
<script>
const { px, interp, ease, legenda } = EdinVideo;
const v = EdinVideo.video({ fundo: '#0f0c2e', grao: 0.06, vinheta: 0.35 });
v.cena({
  id: 'abertura', duracao: 3,                     // inicio padrão = fim da cena anterior
  entrada: { tipo: 'whip-pan', direcao: 'esquerda', duracao: 0.3 },
  camera: EdinCam.mix([EdinCam.preset('dolly-in'), EdinCam.preset('handheld', { intensidade: 0.5 })]),
  montar(el, ctx) {                                // uma vez: cria o DOM
    el.innerHTML = `<div data-z="0.25" data-sobra="0.15" class="fundo"></div>
                    <div data-z="1"><div class="sujeito"><span class="numero"></span></div></div>`;
    this.leg = legenda(el, { texto: 'todo dia a *mesma* coisa', y: 0.2 });
    this.num = el.querySelector('.numero');
  },
  atualizar(el, t, p, ctx) {                       // todo quadro: t local em s, p de 0 a 1
    this.num.textContent = Math.floor(interp(ctx.tql, [0, 2], [0, 100]));  // discreto: tempo do quadro
    this.leg.atualizar(t, 0.3, 2.8);
  },
});
v.iniciar();                                       // define window.EDIN
</script>
```

- `ctx.tq` é o tempo global do quadro (`EdinVideo.quadro(t)`, arredonda para baixo ao início do quadro) e `ctx.tql` o mesmo no relógio local da cena. **Tudo que é discreto (dígitos, texto que troca, contagem) usa o tempo do quadro**; movimento contínuo usa `t`. Veja "Motion blur" abaixo.
- `ctx.tg` é o tempo global contínuo (para poeira e tudo que atravessa cenas).
- `legenda(el, { texto, y, tamanho, destaque })`: padrão Sora 700 86 px, `y` 0,70 no vertical (centro entre 0,55 e 0,75 da altura: sujeito no terço de cima, legenda embaixo dele; legenda em cima só com motivo escrito na ficha) (fora da faixa de 450 px da base que a interface do Instagram cobre). Uma palavra em laranja por cena: `destaque: 'nada'` ou `*nada*` no texto. Quebra equilibrada (`text-wrap: balance`) e o último espaço não quebra, então não sobra palavra órfã na segunda linha. `atualizar(t, 0, fim)` deixa a legenda visível já no quadro 0 (sem fade nem subida), para o primeiro quadro funcionar como capa.
- Tamanhos com `px(78)` no JS ou `calc(var(--u) * 78)` no CSS (1 unidade = 1 px num quadro de 1080 no lado menor). Posições em %. O palco recebe a classe `vertical` ou `horizontal`.
- Durante a transição, `t` pode ser um pouco negativo ou passar da duração: use `interp`/`clamp`, que já travam nas pontas.
- Não mexa no `transform`/`filter`/`opacity` das camadas `data-z` em `atualizar` (a câmera é dona delas); anime os filhos. Para sumir com uma camada inteira, ponha um `<div class="in">` dentro dela e anime a opacidade dele.
- Camadas: `data-z` = fator de parallax (fundo 0.25, meio 0.6, sujeito 1, frente 1.5). `data-desfoque="6"` = profundidade de campo fixa da camada (px de design), somada ao foco da câmera. `data-decorativo` = texto de enfeite que não entra na conferência de texto pequeno. Toda cena com camadas ganha câmera, mesmo sem `camera:` (as transições de câmera precisam dela). `data-sobra="0.15"` deixa a camada 15% maior de cada lado. Camadas com k < 1 recebem escala de cobertura automática (nunca mostram borda); `data-cobre="0"` desliga. `data-gira` recebe o rotateY do orbit (padrão: só o sujeito). `data-giro` gira no lazy-susan.
- **Tela de app:** ponha a captura dentro de `<div data-tela>` (um filho só, ou marque o elemento com `data-tela-conteudo`). A câmera nela só translada, escala no máximo 1,0, sem rotação, blur nem olho de peixe, e a posição é limitada para a tela inteira caber no quadro. Se um preset tentar ampliar, girar ou cortar, sai um `[edin-cam] ... tentou ...` no console. Largura da tela no máximo a do quadro.
- Camada global que atravessa cenas: `v.camada({ inicio, fim, fade, montar, atualizar(el, t) })`. Se ela começa ou acaba no meio de uma cena sem fade, o kit avisa (camada global nunca corta seco).

## Transições (`entrada` da cena B)

| tipo | o que faz | padrão |
|---|---|---|
| `corte` | corte seco | 0 s |
| `dissolve` | B aparece por cima de A | 0,2 s |
| `fade` | A some no fundo, B nasce dele (também na 1ª cena e como `saida` da última) | 0,4 s |
| `whip-pan` | giro de câmera de verdade: A gira no `direcao` (inExpo) até o borrão máximo, **corte seco no pico**, B sai do borrão no mesmo sentido (outExpo) com a mesma velocidade. `percurso` (% do quadro de cada lado, padrão 35; 60 dá borrão de filme), `blurMax` (px, padrão 110). O quadro do pico ainda é de A, B entra no seguinte: os dois lados igualmente borrados. Nada de tira com as duas cenas lado a lado | 0,3 s (0,4 s a 60 fps) |
| `travessia` | movimento contínuo: a câmera anda de A até B pelo mesmo espaço (`direcao`, `distancia` em quadros, padrão 1), com parallax; A fica por cima e o fundo de A some entre 15% e 55% do percurso, revelando o fundo de B. Nunca mostra faixa lisa nem emenda de cartões. **Use no lugar do `push`** | 0,9 s |
| `push` | B empurra A no sentido do movimento (evite: mostra a emenda entre as cenas e faixa lisa se a cena não ocupa o quadro todo) | 0,5 s |
| `zoom-through` | A mergulha no `alvo` ([x, y] do quadro) até `escala` 2,5 com inExpo; B nasce de dentro (1,3 para 1). Com `raio` (px de design do objeto), B dissolve dentro do portal do objeto e o portal cresce. Os textos de A (`.edin-legenda`, `[data-texto]`) somem no começo do mergulho e os de B só aparecem quando o portal passa de 60% do quadro (marque o texto de cards com `data-texto`) | 0,6 s |
| `match-cut` | `elemento: 'nome'` = `[data-match=nome]` nas duas cenas. B começa encaixado no elemento de A (congelado no corte) e assenta em `duracao`; `duracao: 0` é o corte puro e avisa se o centro difere mais de 2% ou a escala mais de 10%; `dissolve: 0.17` dissolve junto; `escalaMax: 1.2` limita a escala inicial de B (o centro continua encaixado), para uma página clara não encher o quadro | 0,5 s |

Janela: centrada no início de B (`b - d/2` a `b + d/2`); no match-cut vai de `b` a `b + d`. Grão, grade e vinheta ficam numa camada global constante por cima de tudo e nunca piscam entre cenas.

`whip-pan` e `travessia` são transições de câmera: o kit soma o movimento delas à câmera de cada cena, então o blur de movimento, a profundidade e a escala de cobertura (fundo nunca mostra borda) saem da própria câmera. Fora da janela o percurso continua em linha reta, para a velocidade no corte sair certa. Dê `data-sobra` de 0,2 a 0,3 ao fundo das cenas que entram ou saem por elas.

**Corte no movimento sem transição pronta:** termine A com um movimento que acelera e comece B com o mesmo movimento desacelerando, na mesma velocidade (± 20%), e use `dissolve` curto ou `match-cut` (no exemplo: recuo do relógio continuado pelo recuo do caderno; truck da semana continuado pelo truck do plano). Para a câmera não parar dentro da janela da transição, estenda a função em linha reta além do fim da cena (veja `truckSai`/`truckEntra`).

### Nada de clarão

Transição para cena com fundo muito mais claro (página branca, tela de app clara): **o brilho médio não pode saltar mais de ~60 níveis num quadro**. Use dissolve curto (0,15 a 0,4 s) ou comece a cena clara menor (`escalaMax` no match-cut, página que cresce), nunca um quadro 100% branco depois de um escuro. Para medir: `ffprobe -f lavfi -i "movie=video.mp4,signalstats" -show_entries frame_tags=lavfi.signalstats.YAVG -of csv=p=0` e compare quadros vizinhos.

## Motion blur e valores discretos

Com `--motion-blur K` o `edin html` chama `seek` em K subtempos dentro do mesmo quadro e tira a média, e passa `?mb=K&obturador=180` para a página: o blur sintético do kit (câmera, whip, zoom-through) cobre só 1/K do obturador, porque a média dos subtempos já faz o rastro inteiro (sem isso o rastro saía dobrado). Um valor discreto que muda entre os subtempos (relógio 23:07 virando 23:08, contador, texto que troca) sai como dois textos sobrepostos. Por isso dígitos, contagens e trocas de texto usam `ctx.tq`/`ctx.tql` (ou `EdinVideo.quadro(t)`), que é o mesmo em todos os subtempos do quadro. O grão já usa o número do quadro.

K = 2 é estroboscópico: em match cut, zoom-through e push o texto vira duas cópias nítidas, não rastro. **Use 0 (sem a opção) ou K ≥ 8**, de preferência só no trecho de movimento rápido (`--start/--duration`).

## Independente de fps

Tudo é em segundos, nada em quadros: o mesmo HTML sai igual a 24, 30 ou 60 fps. `quadro(t)` usa o fps da URL; a sacudida do crash zoom é em batidas de 1/30 s; o hyperlapse anda em degraus de 1/15 s; o atraso do head-tracking é integrado em passo fixo de 1/120 s; transições e legendas têm durações em segundos; o blur de movimento é o deslocamento durante o obturador (180° = meio intervalo entre quadros). O grão troca a cada `piso(fps / graoHz)` quadros (`graoHz` 30: todo quadro a 30 fps, a cada 2 a 60 fps), determinístico pelo número do quadro.

## Linguagem de filme (o que separa de slideshow)

- **Câmera nunca parada:** `EdinCam.preset('deriva', { intensidade, semente, zeroNoInicio, entrada, saida })` em todo plano, somado ao movimento principal: respiração de escala (de 1 a 1 - 1,2%, nunca amplia, serve em tela de app), deriva lenta com parallax (~0,12 Hz, ±1,2% do quadro) e roll de ±0,25°. `zeroNoInicio` deixa a câmera neutra no t = 0 (capa e loop); `saida: 1.2` leva a amplitude a zero no fim da cena (último quadro neutro).
- **Profundidade de campo:** `data-desfoque` fixo por camada (fundo 2 px, frente 6 a 10 px) e `preset('foco', { foco: 1, abertura: 5 })` para desfocar tudo longe do sujeito; com `focoPara` e `inicio`/`duracao` vira rack focus (a lente respira 1,5% no meio). Objeto que vem de perto da câmera entra grande e desfocado e pousa nítido (blocos da cena 5).
- **Poeira em profundidade:** `EdinVideo.poeira(el, { semente, n, z, desfoque, tamanho, opacidade })` cria uma camada `data-z` com partículas que sobem devagar; atualize com `ctx.tg`. O movimento é periódico na duração do vídeo (emenda no loop) e a mesma semente em cenas vizinhas faz a poeira continuar no corte. No exemplo: uma camada longe (z 0,45, 3 a 7 px) e bokeh perto (z 1,7, 70 a 150 px, desfoque 10).
- **Uma luz só:** `video({ luz: { angulo: 60 } })` (para onde a sombra cai). No CSS: `box-shadow: calc(var(--sx) * 40) calc(var(--sy) * 40) ...`; no JS: `EdinVideo.sombra(dist, raio, opac)`. Gradientes de fundo com o ponto claro em cima à esquerda.
- **Brilho contido:** `EdinVideo.halo(raio, opac, cor)` devolve `0 0 Rpx rgba(...)` limitado a 108 px de design (~10% do lado menor) e opacidade 0,25 (avisa se pedir mais). Nada de radial laranja lavando o quadro.
- **Grade de cor única:** `video({ grade: { luzes: '#ffb68a', sombras: '#1d2470', forca: 0.28 } })`: camada soft-light constante, quente do lado da luz e índigo do outro; vinheta constante (`vinheta: 0.38`).
- **Transição motivada:** whip pan cortando no borrão, travessia, match cut que continua o movimento, zoom-through por um objeto. Corte seco só na batida.

## Texto pequeno

Na prévia (ou com `?checar=1` no render) o kit avisa no console `[edin] texto pequeno na cena ...` quando um texto visível fica com **altura de maiúscula abaixo de 45 px** no quadro de 1080 (Sora: maiúscula = 0,7 da fonte, então fonte mínima ~64 px), já contando a escala de câmera e de `transform`. Vale para tudo que precisa ser lido (dias, chips, callout, marca); enfeite vai com `data-decorativo`. Não confere durante as transições. Tela de app com a deriva fica 0,6% menor: use 66 px nela.

## Presets de câmera (`EdinCam.preset(id, { intensidade, easing, alvo, de, ate, inicio, duracao })`)

`intensidade` multiplica a amplitude (1 = valor do catálogo). `de`/`ate` limitam a um trecho de p; `inicio`/`duracao` (s) fazem o preset rodar por tempo real (padrão dos rápidos: crash, rapid, yoyo, whip, super-dolly, through-object). `alvo` = ponto de origem da escala. `EdinCam.mix([...])` soma presets (escalas multiplicam, deslocamentos e ângulos somam).

| id | o que faz |
|---|---|
| `static` | tripé, respiração 1 a 1,006 |
| `dolly-in` / `dolly-out` | S 1 a 1,12 com parallax (fundo 1,03, frente 1,18), suave |
| `super-dolly-in` / `super-dolly-out` | S 1 a 1,6 em 0,8 s outExpo, blur radial pela velocidade |
| `double-dolly` | 1 a 1,08, pausa, 1,08 a 1,25 |
| `dolly-zoom-in` | sujeito fixo, fundo se afasta (1 a 0,78), perspectiva 1200 a 700 |
| `dolly-zoom-out` | sujeito fixo, fundo cresce (1 a 1,35), perspectiva 1200 a 2400 (o "Vertigo" de impacto) |
| `crash-zoom-in` / `crash-zoom-out` | lente 1 a 1,8 em 0,3 s outExpo, sem parallax, blur radial, sacudida de 2 quadros (use `intensidade: 1.5` para 2,2x) |
| `rapid-zoom-in` | lente 1 a 1,35 em 0,65 s inOutQuint |
| `yoyo-zoom` | 1 a 1,25 e volta a 1,03 em 1 s |
| `crane-up` / `crane-down` | ty 18% com parallax + rotateX 8 graus |
| `crane-over` | rotateX até 55 graus + S 1,1 + ty -10% (vista de cima) |
| `tilt-up` / `tilt-down` | ty 15% sem parallax + rotateX 4 graus |
| `pan-left` / `pan-right` | tx 20% sem parallax + rotateY 4 graus |
| `whip-pan` | tx 100% em 0,25 s inExpo dentro da cena, blur até 80 px (`direcao`) |
| `orbit-360` | rotateY 360 graus no sujeito, fundo e frente em sentidos opostos (volta inteira só com sujeito de duas faces) |
| `arc-left` / `arc-right` | rotateY 30 graus no sujeito, fundo 12% e frente 20% opostos |
| `lazy-susan` | só `data-giro` (ou o sujeito) gira 360 graus, fundo parado |
| `bullet-time` | arc de 40 graus; `estado.tempo` cai a 0,1x; `mov.tempoDeformado(t, D)` dá o tempo lento da ação |
| `robo-arm` | 3 trechos precisos com pausas, inOutQuint, sem tremor |
| `fpv-drone` | avanço rápido, inclina ±8 graus nas curvas, balanço 1,5 Hz, frente passa pela câmera |
| `aerial-pullback` | S 1,5 a 1 + ty -12% + rotateX 30 graus, outCubic (a cena precisa de "mundo" além do quadro) |
| `fisheye` | feDisplacementMap de barril 0,3, perspectiva 500, zoom 1,1 |
| `handheld` | ruído 0,8 Hz 6 px + 7 Hz 1 px, roll ±0,4 graus (`semente`) |
| `snorricam` | sujeito parado, mundo balança ±6 graus e ±6% |
| `head-tracking` | câmera segue o sujeito com atraso (0,25 por quadro), `trajeto(t)` opcional |
| `through-object` | frente (k ≥ 1,2) cresce até 6x e some, o resto avança 15% |
| `hyperlapse` | avanço em degraus de 2 quadros, `estado.tempo` 8 |
| `rack-focus` | foco de `focoDe` (1,5) para `focoPara` (0,25), blur até 8 px |
| `low-shutter` | obturador 360 graus (blur = deslocamento inteiro) com tremor maior |
| `deriva` | câmera viva por baixo de tudo: respiração (escala 1 a 0,988), deriva lenta com parallax, roll ±0,25°; `zeroNoInicio`, `entrada`, `saida` |
| `foco` | profundidade de campo: `foco` (k nítido), `abertura` (px); com `focoPara` vira rack focus |

## Receitas de sequência

- **Gancho:** `crash-zoom-in` com `inicio: 0.1` + `handheld` 0,6; texto entra quando o zoom pousa (0,45 s). Depois, plano mais calmo (o impacto pede descanso).
- **Gancho e capa:** o primeiro quadro é a capa: sujeito já grande, legenda visível desde o quadro 0 (`atualizar(t, 0, fim)`), uma palavra em laranja.
- **Objeto que continua:** anel do relógio vira o círculo no caderno com `match-cut` de 0,55 s, `dissolve: 0.17` e `escalaMax: 1.5`. Para o anel de A caber no círculo de B sem a página encher o quadro, A recua no último 1 s (escala até 0,45 com easeInCubic) e B continua o mesmo recuo: velocidade de escala igual dos dois lados. Dígitos e rótulos de A somem 0,2 s antes do corte: só o anel faz a emenda.
- **Energia:** `whip-pan` esquerda com `percurso: 60`, `duracao: 0.4`, `blurMax: 200 * U`; se houver dois seguidos, mesmo sentido e mesma duração.
- **Descer na mesa:** `travessia` `cima` de 0,9 s do card para a semana (a câmera desce pelo mesmo mundo).
- **Impacto:** `dolly-zoom-out` com `de: 0.15, ate: 0.85` no momento da frase-chave; sujeito no `alvo`.
- **Entrar no assunto:** `zoom-through` com `alvo` e `raio` no objeto (ponto laranja) e a cena seguinte nascendo dentro dele.
- **Produto/card:** `arc-right` + `dolly-in` 0,5; o reflexo do card lê `mov(p, t, D).orbita`.
- **Tela de app:** entra por `dissolve` no movimento ou `travessia` (nunca `push`), `data-tela` (com `data-z="0.5"` a deriva e o truck movem metade e não encostam na borda), destaque com borda laranja pulsando e callout separado (sem lupa na tela). Texto da tela com 66 px.
- **Fim e loop:** a última cena monta as mesmas camadas da primeira (uma função `montarRelogio` usada nas duas). Marca aparece e sai, o anel fecha, cresce até o anel do relógio, o rabo corre a volta inteira e o anel recomeça em 12%; disco, dígitos e a legenda de abertura voltam com fade; a câmera termina neutra (`deriva` com `saida`, pullback que volta a zero) e a da cena 1 começa neutra (`zeroNoInicio`). O último quadro difere do primeiro só pelo grão (diferença média 0,7 nível sem o grão, menor que a de dois quadros vizinhos).

## Checklist antes de renderizar

- [ ] Tudo é função de `t`: nada de CSS animation/transition, `setTimeout`, `requestAnimationFrame` ou estado acumulado entre quadros (cada `atualizar` define tudo de novo).
- [ ] Nada aleatório sem semente: `EdinVideo.aleatorio(semente)` só em `montar`; em `atualizar` use `EdinVideo.ruido(semente)` ou `hash`. (O kit troca `Math.random` por um gerador com semente e avisa.)
- [ ] Fontes locais com `@font-face` (ex.: `fontes/Sora-700.ttf`); nada de Google Fonts. O `seek` espera as fontes e as `<img>` carregarem; imagem em CSS vai em `video({ precarregar: [...] })`.
- [ ] Telas de app inteiras: dentro de `data-tela`, largura ≤ quadro, console sem `tentou ampliar/girar/cortar`.
- [ ] Texto em minúsculas, legenda Sora 700 86 px com centro entre 0,55 e 0,75 da altura e acima dos 450 px da base (9:16), fora da informação da cena; uma palavra em laranja por cena.
- [ ] Console da prévia sem `texto pequeno` (nada com maiúscula abaixo de 45 px no quadro de 1080).
- [ ] Câmera nunca parada (`deriva` em todo plano), profundidade (`data-desfoque`/`foco`), poeira, uma luz (`--sx`/`--sy`), halo pelo `halo()`, grade e vinheta constantes.
- [ ] Transições motivadas: nada de `push`; whip com corte no borrão; corte no movimento com velocidade igual ±20%. Todo quadro de cada transição conferido (sem faixa lisa, sem palavra cortada, sem dígito de A por cima de B).
- [ ] Dígitos, contagens e textos que trocam usam `ctx.tq`/`ctx.tql`; motion blur 0 ou ≥ 8.
- [ ] Sem clarão: brilho médio não salta mais de ~60 níveis entre quadros vizinhos.
- [ ] Primeiro quadro serve de capa; se o vídeo repete, o último emenda com o primeiro (compare os dois quadros: diferença média perto da de dois quadros vizinhos).
- [ ] Rascunho a 60 fps sem motion blur para iterar; final com `--fps 60 --motion-blur 8`.
- [ ] `seek` fora de ordem dá o mesmo quadro (teste: 12, 3, 7 contra a ordem normal) e nenhuma borda de camada aparece nos quadros de início, meio e fim de cada cena e no meio de cada transição.
