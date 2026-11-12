# Direção de câmera e continuidade (vocabulário do Higgsfield, feito em código)

O Higgsfield (DoP, Mix, Cinema Studio, Soul, Popcorn) virou a referência de nomes de movimento de câmera em vídeo curto. Aqui fica o vocabulário e o porquê de cada movimento, traduzido para cenas 2.5D em HTML/SVG/Remotion. **Não gere nada no Higgsfield**: cena que falta é feita em código (ver `reel-narrativo-sem-voz.md`). Exceção na seção 4.

## 0. Convenções do código (leia antes da tabela)

- **Quadro:** 1080x1920 a 30 fps. `tx`/`ty` em % da largura/altura do quadro; positivo = conteúdo vai para a direita/baixo.
- **Camadas por profundidade** (`k` = fator de parallax): fundo `k=0,25`, meio `k=0,6`, sujeito `k=1`, primeiro plano `k=1,5`. Cada camada recebe `deslocamento_camada = deslocamento_câmera x k` e `S_camada = 1 + (S_câmera - 1) x k`.
- **O porquê que separa os movimentos:** câmera que **gira** (pan, tilt, zoom de lente) não tem parallax: todas as camadas andam e escalam igual (`k=1` para todas). Câmera que **se desloca** (dolly, truck, crane, arc, drone) tem parallax: o perto anda mais que o longe. Se tudo escala igual, o olho lê "zoom", não "dolly". Esse é o erro que deixa cena 2.5D com cara de slide.
- **Lente = perspectiva CSS** (largura 1080): `perspective = 540 / tan(FOV/2)`. 24 mm (FOV 74°) = 720 px; 35 mm (54°) = 1060 px; 50 mm (40°) = 1480 px; 85 mm (24°) = 2540 px. Grande-angular exagera rotateX/Y; tele achata.
- **Easings** (cubic-bezier): `suave` (0.45,0,0.55,1); `inOutCubic` (0.65,0,0.35,1); `inOutQuint` (0.83,0,0.17,1); `outExpo` (0.16,1,0.3,1); `inExpo` (0.7,0,0.84,0); `outCubic` (0.33,1,0.68,1); `linear`.
- **Blur de movimento** (obturador 180°): comprimento do blur direcional = 0,5 x deslocamento por quadro, em px, máximo 40 px. `low-shutter` usa 1,0 x (obturador 360°).
- **Tremor** (`handheld`): ruído simplex com 2 oitavas: 0,8 Hz com 6 px + 7 Hz com 1 px em x/y, `rotateZ` ±0,4° a 0,8 Hz. Calma x0,5; raiva/tensão x2 e irregular.
- **Sobra de quadro (overscan):** camada de fundo com 15% a mais de cada lado. `rotateZ` de θ em 9:16 exige escala ≥ cos θ + 1,78 sen θ (3° = 1,09; 8° = 1,24). Nunca mostre borda de camada.
- **Telas de app continuam sem zoom** (regra de Rafael no SKILL.md): o cartão do app fica em `S=1`; o movimento de câmera acontece só no fundo/degradê e nos elementos em volta.

## 1. Catálogo de presets

Nomes conferidos em higgsfield.ai/camera-controls e higgsfield.ai/motion (nov/2026). `S` = escala da câmera (aplicar por camada com `k`, salvo quando dito "sem parallax").

| id | Higgsfield | o que a câmera faz | emoção / uso narrativo | duração | easing | parâmetros em código |
|---|---|---|---|---|---|---|
| `static` | Static | tripé travado | ler texto, deadpan, deixar a ação falar, telas de app | 1 a 4 s | nenhum | `S` 1; opcional respiração `S` 1 a 1,006 em 3 s; tremor 0 |
| `dolly-in` | Dolly In | câmera anda até o sujeito | intimidade, tensão que cresce, "olha isto" | 2 a 4 s | `suave` | `S` 1 a 1,12 com parallax (fundo 1,03, sujeito 1,12, frente 1,18); perspectiva 1480 |
| `dolly-out` | Dolly Out | câmera recua | isolamento, despedida, abrir contexto, fim de bloco | 2 a 4 s | `suave` | inverso do `dolly-in` (1,12 a 1) |
| `super-dolly-in` | Super Dolly In | avanço exagerado e rápido | choque, revelação urgente, gancho dos 0 a 2 s | 0,6 a 1,0 s | `outExpo` | `S` 1 a 1,6 (fundo 1,15, frente 1,9); blur radial 8 a 12 px no pico (primeiros 30%) |
| `super-dolly-out` | Super Dolly Out | recuo exagerado e rápido | revelar escala, virada de contexto | 0,8 a 1,2 s | `outExpo` | `S` 1,6 a 1 com parallax; blur radial 8 px nos primeiros 25% |
| `double-dolly` | Double Dolly | dois empurrões seguidos com pausa | ênfase em duas batidas ("isso... e ISSO") | 1,5 a 3 s | `inOutCubic` por trecho | 0 a 40%: `S` 1 a 1,08; 40 a 55%: parado; 55 a 100%: 1,08 a 1,25; casar cada empurrão com uma batida |
| `dolly-zoom-in` | Dolly Zoom In | anda para frente e abre a lente: sujeito do mesmo tamanho, fundo se afasta | vertigem, percepção súbita (efeito Hitchcock) | 1,5 a 3 s | `inOutCubic` | sujeito `S` 1 fixo; meio 1 a 0,9; fundo 1 a 0,78; perspectiva 1200 a 700 |
| `dolly-zoom-out` | Dolly Zoom Out | recua e fecha a lente: fundo cresce atrás do sujeito | sufoco, o mundo se fechando | 1,5 a 3 s | `inOutCubic` | sujeito `S` 1 fixo; meio 1 a 1,15; fundo 1 a 1,35; perspectiva 1200 a 2400 |
| `crash-zoom-in` | Crash Zoom In | zoom de lente brusco | susto, punchline, detalhe que importa | 0,2 a 0,35 s | `outExpo` | sem parallax: tudo `S` 1 a 1,8; blur radial 10 a 20 px nos 3 primeiros quadros; ao parar, sacudida de 2 quadros com 8 px |
| `crash-zoom-out` | Crash Zoom Out | zoom de lente brusco para trás | desconexão, "e agora o tamanho do problema" | 0,25 a 0,4 s | `outExpo` | sem parallax: `S` 1,8 a 1; blur radial 12 px no início |
| `rapid-zoom-in` | Rapid Zoom In | zoom rápido, menos violento que o crash | ênfase em palavra, número, dica | 0,5 a 0,8 s | `inOutQuint` | sem parallax: `S` 1 a 1,35; blur radial 4 a 6 px no meio (existe também Rapid Zoom Out, mesmo inverso) |
| `yoyo-zoom` | YoYo Zoom | entra e volta como mola | batida de música, humor, loop | 0,8 a 1,2 s | `outCubic` ida, `inCubic` volta | sem parallax: `S` 1 a 1,25 (45% do tempo) e 1,25 a 1,03 (55%); repetível no BPM |
| `crane-up` | Crane Up | câmera sobe e inclina para baixo | do íntimo ao grandioso, revelar escopo | 2,5 a 4 s | `suave` | `ty` +18% com parallax (fundo +4%, frente +27%); `rotateX` 0 a 8° (topo afasta); perspectiva 1200 |
| `crane-down` | Crane Down | desce do alto até o sujeito | apresentar o lugar e pousar no personagem | 2,5 a 4 s | `suave` | inverso do `crane-up` (`ty` -18%, `rotateX` 8 a 0°) |
| `crane-over` | Crane Over The Head | sobe e passa por cima até vista de topo | vulnerabilidade, vigilância, coreografia, mapa | 2 a 3 s | `inOutCubic` | `rotateX` 0 a 55° no grupo câmera + `S` 1 a 1,1 + `ty` -10%; no fim, troca para a versão "vista de cima" da cena (mesa vista de cima) |
| `tilt-up` | Tilt up | câmera gira para cima, parada no lugar | revelar altura, poder, "olha para cima" | 1,5 a 3 s | `suave` | sem parallax: todas as camadas `ty` +15%; `rotateX` -4° para dar curvatura |
| `tilt-down` | Tilt Down | gira para baixo | chegar ao detalhe, peso, derrota | 1,5 a 3 s | `suave` | sem parallax: `ty` -15%; `rotateX` +4° |
| `pan-left` | Pan Left | gira para a esquerda, parada | revelar espaço, acompanhar olhar | 2 a 4 s | `suave` | sem parallax: tudo `tx` +20% (conteúdo vai para a direita); `rotateY` +4° |
| `pan-right` | Pan Right | gira para a direita | idem | 2 a 4 s | `suave` | sem parallax: `tx` -20%; `rotateY` -4° |
| `whip-pan` | Whip Pan | giro lateral violento, borrado | transição entre cenas, energia | 0,15 a 0,3 s por lado | `inExpo` saída + `outExpo` entrada | sem parallax: `tx` 0 a ±100%; blur direcional horizontal 40 a 80 px no meio; corte no quadro de blur máximo |
| `orbit-360` | 360 Orbit | volta inteira em torno do sujeito | ênfase dramática, isolamento, herói | 3 a 6 s | `linear` | 2.5D aguenta ±35°: sujeito `rotateY` ±25° com `tx` frente +30% sen(t) e fundo -15% sen(t) (sentidos opostos). Volta completa só com objeto 3D (three.js) ou sujeito simétrico (logo, ícone) trocando a face a 90° e 270° |
| `arc-left` | Arc Left | meia-lua para a esquerda em torno do sujeito | virada emocional, revelar o segundo elemento | 2 a 4 s | `suave` | sujeito `rotateY` 0 a +30°; fundo `tx` +12%, frente `tx` -20%; perspectiva 1200 |
| `arc-right` | Arc Right | meia-lua para a direita | idem, espelhado | 2 a 4 s | `suave` | sujeito `rotateY` 0 a -30°; fundo `tx` -12%, frente `tx` +20% |
| `lazy-susan` | Lazy Susan | sujeito gira no próprio eixo, câmera parada | produto, apresentar personagem, figurino, logo | 4 a 8 s por volta | `linear` | só o sujeito `rotateY` 0 a 360°; fundo parado; objeto plano precisa de duas faces (`backface-visibility: hidden`) e espessura falsa (3 a 5 cópias a 1 px) |
| `bullet-time` | Bullet Time | tempo congela e a câmera circula | clímax, impacto, "o momento" | 1,5 a 3 s | rampa `outExpo` para 0,1x, `inExpo` de volta | animações internas a 0,1x ou paradas; câmera `arc` de 40° com parallax; partículas congeladas no ar; entrada e saída da rampa em 0,2 s |
| `robo-arm` | Robo Arm | braço robótico: trajetória precisa com 2 a 3 paradas | produto premium, tecnologia, precisão | 2 a 4 s | `inOutQuint` por trecho | 2 a 3 waypoints combinando `tx`, `ty`, `rotateX/Y` ±15°, `S` 1 a 1,2; pausa de 0,15 s entre trechos; zero tremor |
| `fpv-drone` | FPV Drone | voo rápido e ágil, inclina nas curvas | perseguição, energia, atravessar o cenário | 2 a 4 s | quase `linear` com acelerações de 0,3 s | fundo `S` 1 a 1,3; camadas de frente passam pelas bordas (`S` 1 a 3 e saem); `rotateZ` ±8° nas curvas; `ty` balanço ±1,5% a 1,5 Hz; blur pelo deslocamento |
| `aerial-pullback` | Aerial Pullback | recua e sobe ao mesmo tempo, até vista aérea | final épico, sair do personagem para o mundo | 4 a 6 s | `outCubic` | `S` 1,5 a 1 com parallax + `ty` -12% + `rotateX` 0 a 30°; cena precisa de "mundo" desenhado além do quadro inicial |
| `fisheye` | Fisheye | lente olho de peixe | skate, POV, surreal, comédia | qualquer | conforme o movimento | não sai com CSS transform: SVG `feDisplacementMap` com mapa de barril ou shader WebGL, força 0,2 a 0,4; perspectiva 400 a 600; `S` 1,1 para esconder canto |
| `handheld` | Handheld | câmera na mão | documental, realismo, intimidade, caos | qualquer | ruído | tremor da seção 0; nunca em tela de app nem em texto que precisa ser lido |
| `snorricam` | Snorricam | câmera presa ao corpo: sujeito fixo, mundo balança | estresse, embriaguez, pânico | 2 a 4 s | ruído lento | sujeito parado no centro; fundo `rotateZ` ±4° a 8° e `tx` ±6% a 0,5 a 0,8 Hz; escala de cobertura pela fórmula de `rotateZ` |
| `head-tracking` | Head Tracking | câmera travada na cabeça do sujeito | primeira pessoa, desorientação | 2 a 4 s | lerp | câmera segue o centro do sujeito com atraso de 2 a 4 quadros (`pos += (alvo - pos) x 0,25` por quadro); fundo com parallax do deslocamento |
| `through-object` | Through Object In / Out | atravessa uma abertura (janela, fechadura, tela) | transição de espaço, revelar segredo | 0,6 a 1,0 s | `inExpo` | primeiro plano com furo (máscara SVG) `S` 1 a 6 e sai do quadro; cena de trás `S` 1,3 a 1; corte escondido quando o furo cobre 100% do quadro. "Out" é o inverso |
| `hyperlapse` | Hyperlapse | anda pelo espaço enquanto o tempo corre | passagem do tempo, rotina, cidade | 2 a 4 s | `linear` | fundo `S` 1 a 1,4; tempo em degraus (atualiza a cada 2 a 3 quadros); camada de luz troca de cor (dia a noite) e sombras giram 90°; relógio/objetos pulam |
| `rack-focus` | Focus Change | foco passa de um plano para outro | mudar a atenção de A para B, revelar | 0,4 a 0,8 s | `inOutCubic` | blur frente 0 a 8 px e fundo 8 a 0 px (ou o contrário); `S` 1 a 1,02 (respiração da lente) |
| `low-shutter` | Low Shutter | obturador lento, rastro de movimento | velocidade, vertigem, embriaguez, sonho | 1 a 3 s | conforme o movimento | blur direcional = 1,0 x deslocamento por quadro, ou 3 a 5 cópias do sujeito com atraso de 1 a 3 quadros e opacidade 0,5 / 0,3 / 0,15 |

### Outros presets reais do Higgsfield (ids sugeridos)

| id sugerido | Higgsfield | o que faz | código |
|---|---|---|---|
| `truck-left` / `truck-right` | Dolly Left / Dolly Right | trilho lateral acompanhando o sujeito | `tx` ±15% com parallax (fundo ±4%, frente ±22%); 2 a 4 s `suave`. Diferente do pan: tem parallax |
| `zoom-in` / `zoom-out` | Zoom In / Zoom Out | zoom de lente lento | sem parallax, `S` 1 a 1,15 em 3 a 5 s `suave` (é o "Ken Burns"; nunca em tela de app) |
| `jib-up` / `jib-down` | Jib up / Jib down | grua curta, sobe/desce sem passar por cima | `ty` ±10% com parallax, `rotateX` ±4°, 2 a 3 s |
| `dutch-angle` | Dutch Angle | horizonte inclinado | `rotateZ` 8° a 15° fixo ou entrando em 1 s; escala pela fórmula; tensão, algo errado |
| `overhead` | Overhead | vista de cima, travada | cena desenhada de cima (mesa vista de cima); `static` ou `S` 1 a 1,05 |
| `incline` | Incline | câmera que inclina em diagonal | `rotateX` 0 a 10° + `rotateZ` 0 a 5° em 2 s |
| `hero-cam` | Hero Cam | ângulo baixo que sobe no sujeito | `rotateX` -10° a 0 + `ty` +8% a 0, perspectiva 900; poder |
| `action-run` | Action Run | câmera baixa atrás de quem corre | `handheld` x2 + `ty` balanço 2,5 Hz ±1,5% + avanço `S` 1 a 1,1 |
| `car-grip` / `car-chasing` / `buckle-up` / `road-rush` | idem | câmera de carro, perseguição, solavanco, estrada passando | grip: sujeito fixo, fundo `tx` linear rápido com blur; buckle-up: tremor x4 com picos de 12 px |
| `object-pov` | Object POV | visão de um objeto (de dentro da gaveta, da tela) | moldura escura do objeto em primeiro plano + `fisheye` 0,15 |
| `push-to-glass` | Push To Glass | empurra até encostar num vidro | `dolly-in` até o vidro em primeiro plano ocupar o quadro (reflexo + blur 6 px) |
| `dirty-lens` | Dirty Lens | lente suja | PNG de manchas em `screen` 15% a 25% de opacidade, fixo na câmera (não recebe parallax) |
| `eyes-in` / `mouth-in` | Eyes In / Mouth In | entra pelo olho/boca para outro mundo | `through-object` com o furo no olho/boca |
| `rotation-3d` | 3D Rotation | o objeto gira em 3D | igual `lazy-susan` com eixo inclinado (`rotateX` 15° + `rotateY`) |
| `wiggle` | Wiggle | balanço curto e engraçado | `rotateZ` ±3° a 4 Hz amortecendo em 0,6 s |
| `flying-cam-transition` | Flying Cam Transition | voa de uma cena para a outra | `fpv-drone` que termina num `through-object` |
| `timelapse` | Timelapse Human / Landscape / Glam | câmera fixa, tempo acelerado | `static` + tempo em degraus + luz mudando (ver `hyperlapse`) |
| `levitation` | Levitation | subida flutuante, sonho | `crane-up` lento (4 a 6 s) com `ty` senoidal ±0,5% a 0,3 Hz |

Combinações prontas do próprio Higgsfield (Mix): `lazy-susan + super-dolly-out`, `crane-over + crash-zoom-in`, `snorricam + low-shutter`, `fpv-drone + timelapse`, `arc + zoom`.

## 2. Composição de sequência

**Um movimento por plano.** O Higgsfield chama de "One-Move Rule": empilhar dolly + pan + tilt é a causa nº 1 de imagem tremida e câmera sem intenção. No Mix, no máximo **2 movimentos compatíveis**, um de câmera e um de lente ou tempo (ex.: `arc` + `rapid-zoom-in`, `snorricam` + `low-shutter`). Nunca opostos no mesmo plano (`dolly-in` com `dolly-out`, `crane-up` com `crane-down`). Se precisar de dois movimentos em fases, faça em sequência com tempos: 0 a 1,5 s `pan`, para 0,3 s, 1,8 a 3 s `dolly-in`.

**Corte de duplo contraste.** Todo corte muda o **tamanho do plano** (aberto, médio, fechado, detalhe) **e o caráter da câmera** (parada, na mão, trilho, grua, aérea). Ruim: médio na mão para fechado na mão. Bom: médio na mão para detalhe parado. Nunca repita o mesmo preset em dois planos seguidos.

**Qual movimento casa com qual corte:**

| plano termina em | próximo plano começa com | por quê |
|---|---|---|
| `dolly-in` / `super-dolly-in` | `static` mais fechado, ou detalhe | o empurrão "pede" o detalhe; chegar parado dá peso |
| `crash-zoom-in` | corte seco na batida, plano parado | o impacto precisa de um quadro de descanso depois |
| `crane-up` / `aerial-pullback` | plano aberto parado ou texto final | fim de bloco, respiração |
| `tilt-down` | insert (mãos, objeto, número) | o olhar já desceu até ele |
| `whip-pan` direita | `whip-pan` direita (mesmo sentido, mesma velocidade) | o corte some dentro do borrão |
| `pan` / `truck` para a direita | próximo plano com movimento para a direita | sentido de tela contínuo |
| `rack-focus` para o fundo | plano do que estava no fundo | o foco já apresentou o próximo assunto |
| `through-object` | cena nova já a `S` 1,3 descendo para 1 | a abertura é a porta entre espaços |

**Ritmo em Reels (números):** gancho 0 a 2 s com o movimento mais forte do vídeo (`super-dolly-in`, `crash-zoom-in`, `whip-pan`); planos de 1,5 a 3 s; insert de 0,3 a 0,5 s (nunca 1 s inteiro); plano de leitura de texto ou tela de app até 4 s; plano emocional único até 5 s; nada parado e sem mudança por mais de ~3 s (mesma regra do preset `reels`). Movimentos violentos (crash, whip, super dolly) no máximo 1 a cada 4 planos, senão viram ruído.

**Rampa de velocidade (entra rápido, assenta, sai rápido).** Quadros-chave do progresso do movimento: tempo 0 a 20% cobre 0 a 60% do percurso; 20 a 80% cobre 60 a 90%; 80 a 100% cobre 90 a 100% (entrada com energia, meio legível). Para sair em velocidade e emendar no próximo: inverta (lento no início, 80 a 100% do tempo cobre 60% do percurso). Use rampa em no máximo 1 de cada 3 planos.

**Continuidade entre planos:**
- **Corte no movimento:** a velocidade na tela (px/quadro) dos dois lados do corte fica igual ±20%, mesmo sentido. Corte no 2º ou 3º quadro do movimento do plano novo, nunca no começo parado.
- **Match cut:** a forma em comum (relógio redondo para anel da logo, caderno para tela do app) fica no mesmo centro ±2% do quadro e escala ±10%. Pode dissolver 4 a 6 quadros se as luzes forem diferentes.
- **Sentido de tela:** escolha um (ex.: tempo e progresso andam da esquerda para a direita) e mantenha o vídeo todo; nunca espelhe uma cena para "caber".
- **Whip pan como transição:** 4 a 6 quadros de cada lado, blur direcional 40 a 80 px, os dois lados no mesmo sentido; som `whoosh` centrado no quadro do corte.
- **Zoom-through:** plano A `S` 1 a 2,5 em `inExpo` nos últimos 0,25 s; corte no pico; plano B entra de `S` 0,7 a 1 em `outExpo` nos primeiros 0,3 s. Fica melhor passando por algo escuro ou por uma abertura (`through-object`).

**Câmera é o dublê emocional do sujeito** (guia de Higgsfield):

| emoção | câmera |
|---|---|
| calma, controle | `static` ou `handheld` x0,5, `dolly-in` lento |
| tensão, raiva | `handheld` x2 irregular, `dutch-angle` 8° |
| tristeza | `handheld` lento, deriva para baixo (`ty` +2% em 4 s), `dolly-out` |
| choque, revelação | `static` + `dolly-in` muito lento, ou `crash-zoom-in`; depois 0,5 a 2 s quase parado |
| veredito, final | vista de cima parada 0,3 a 0,5 s, ou `aerial-pullback` |
| precisa de espaço | recuo lento de médio para aberto ("deixar o personagem sozinho") |

Por gênero: produto/app = `orbit`, `dolly-in` lento, `static`, `crane-down` (evitar `handheld`, `whip-pan`); lifestyle = `handheld` leve, `static`, `pan` lento; humor = `static` + `crash-zoom-in`/`yoyo-zoom`; tutorial = `static` e corte entre telas.

**Consistência de personagem, paleta e set (o que Soul e Popcorn resolvem, feito em código).** O Popcorn gera até 8 quadros com o mesmo personagem, luz e atmosfera a partir de até 4 referências; o Soul ID trava um rosto entre gerações (treina com 20 a 80 fotos); o Cinema Studio usa "Elements" (@Personagem, @Local) definidos uma vez e chamados em todo plano. Os guias deles insistem: luz sempre do mesmo lado, mesma paleta e mesmo "film setup" em todo ângulo da cena, e comparar todo plano novo com o plano de estabelecimento. Em código isso vira:
- `theme.ts` único: 5 a 6 cores da paleta, fonte, ângulo da luz (ex.: luz vindo de 135°, sombra caindo para baixo e à direita, `drop-shadow` com o mesmo offset em todos os componentes), temperatura (quente/fria) e um nível de grão (4% a 6%) e vinheta fixos.
- **Set reutilizável**: um componente por lugar (ex.: `Desk.tsx` vista de cima) e cada "ângulo" é a mesma cena com outra câmera, nunca um desenho novo.
- **Personagem/objeto como componente** com props fixas (cor, tamanho, traço); varia só pose e posição.
- Camadas globais (grão, vinheta, tom) por cima de tudo, constantes; quando mudam, mudam junto com um dissolve (regra já existente).
- Conferência: grade de quadros lado a lado com o plano de estabelecimento; luz, cor e tamanho relativo do objeto principal iguais.

## 3. Ficha de plano

Adaptação da fórmula de prompt do Higgsfield (Camera, Subject, Look, Action; Popcorn: sujeito, cenário, estilo, ação, atmosfera). Preencha uma ficha por plano antes de escrever o componente; a sequência de fichas é o storyboard.

```yaml
plano: 03
tempo: 4.2 a 6.4 s        # 2.2 s; corte na palavra de ênfase
sujeito: celular sobre a mesa, tela acendendo     # quem/o quê + aparência fixa do theme
acao: tela acende com a notificação "Ponto de atenção"   # UMA ação principal
camera: dolly-in            # id do catálogo
  override: { S: [1, 1.10], easing: suave }
lente: 50mm (perspectiva 1480)
luz: janela à esquerda (135°), quente 3200K, sombra para baixo-direita
camadas: [fundo: madeira k0.25, meio: caderno k0.6, sujeito: celular k1, frente: caneta desfocada k1.5]
entrada: corte seco no movimento (velocidade igual à do plano 02)
saida: rack-focus para o caderno, emenda com plano 04 (detalhe do caderno)
texto: "e o alarme toca de novo." 12% a 80% da altura, fora da tela do celular
som: softclick no corte
checar: luz do mesmo lado do plano 01; nenhuma borda de camada aparece; texto não cobre a notificação
```

Regras da ficha: uma ação principal (no máximo 1 a 2 secundárias); o movimento declarado precisa conseguir chegar ao enquadramento final (um `dolly-in` de `S` 1,1 não sai de aberto para detalhe: use `super-dolly-in` ou corte); mude uma coisa por vez ao refazer um plano reprovado.

## 4. Quando usar o Higgsfield de verdade

Só quando Rafael pedir **explicitamente** ângulos de IA em cima de filmagem real de pessoa falando. Aí vale a skill `camera-dinamica` (`~/.claude/skills/synced/*/camera-dinamica/SKILL.md`), cujas boas regras são:
- **~40% do tempo no plano original (âncora)**, ~60% em ângulos gerados; nunca o mesmo ângulo duas vezes seguidas.
- **Troca a cada 1,5 a 3 s, no início de palavra de ênfase** (timestamps por palavra do Whisper).
- **Ângulos sem boca visível são os preferidos** (vista de cima a 90°, por cima do ombro com rosto fora de foco, por trás em plano aberto, câmera escondida atrás de objeto desfocado, detalhe das mãos). Rosto visível só com modelo vídeo-para-vídeo que preserve a boca do trecho original.
- Prompt de cada trecho: "mesmo momento, mesma pessoa, mesma roupa, mesmo cenário e iluminação, mesmos gestos; nova câmera: <ângulo>; câmera estática, aparência de filmagem real, sem texto, mesma duração". Trecho recortado com 0,3 s de folga de cada lado.
- Geração ruim (pessoa diferente, membro deformado): refaz uma vez; falhou de novo, fica o plano original.
- **Áudio original contínuo** por cima de tudo (descarta o áudio dos clipes gerados); duração final igual à original ±0,1 s; grade de quadros para conferir.
- Vídeo acima de 30 s: avisar numa linha quantas gerações serão feitas (custa crédito).

Fora desse caso, o Higgsfield serve só de dicionário: os nomes desta página.

## 5. Fontes

- Lista de presets de câmera: https://higgsfield.ai/camera-controls
- Biblioteca de motions (DoP, Kling, Hailuo, WAN) e combinações do Mix: https://higgsfield.ai/motion
- Controle de câmera no Cinema Studio (pan, dolly, zoom, orbit, tracking, Tempo): https://higgsfield.ai/blog/ai-video-camera-control
- Personagens e locais consistentes (luz do mesmo lado, sentido de tela, cortes em tempos fixos): https://higgsfield.ai/blog/consistent-characters-locations
- Popcorn (até 8 quadros, 4 referências, modos Manual/Auto): https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-popcorn
- Higgsfield DoP: https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-dop
- Lançamento do Mix: https://higgsfield.ai/blog/Introducing-Higgsfield-Mix-Motion-Reimagined
- Dolly zoom e grua: https://geo.higgsfield.ai/blog/crane-shot-dolly-zoom-presets-ai-video-generation
- Guia de prompts de terceiros (One-Move Rule, duplo contraste, emoção para câmera, durações por tipo de plano, MCSLA): https://github.com/osidemedia/higgsfield-ai-prompt-skill (`skills/higgsfield-camera`, `skills/higgsfield-prompt`)
- Whip pan e transições: https://www.premiumbeat.com/blog/3-effects-whip-pan-transition ; https://www.capcut.com/resource/ai-camera-transitions-whip-pan-match-cut
