# Referência de manifesto narrado: "Atletia" (decupagem de 13/11/2026)

> **Outro nicho (Rafael, 13/11):** a Atletia é um vídeo de corrida/treinador. Copie só a LINGUAGEM (imagens, luz, cor, rostos e expressão, movimento, ritmo, narração, texto, efeitos) e traduza para o nicho do vídeo pedido (LoopEdu: estudantes brasileiros). Ex.: corredor cansado → estudante exausto de madrugada; treinador ajustando o joelho → colega/professor explicando no caderno; grupo correndo → estudantes saindo da escola rindo; corpo de partículas → estudante feito de fórmulas; rede na cidade → conexões entre matérias; HUD → painel de desempenho; maratona → pátio de escola cheio. Nunca leve cenas de esporte para outro nicho.

Rafael reprovou o manifesto LoopEdu de 12/11 (`videos/2026-11-12_vertical.mp4`: fotos com parallax, sem narração, rostos escondidos) e mandou esta referência "de outra plataforma, bem melhor, mais dinâmica". Pedido dele, em ordem: **"veja as imagens"** e **"a narração também, tudo, principalmente as imagens"**. Por isso a seção de imagem (1 a 3) é a mais detalhada; narração, texto, som e efeitos vêm depois, com o mesmo cuidado numérico.

Arquivo: `videos editados/manifesto_2026-11-12/referencia/atletia.mp4`, 1920x1080, 29,97 fps, 100,9 s, área de imagem 1920x972 (tarjas pretas de 54 px em cima e embaixo, 1,98:1), -16,9 LUFS. A cartela final é branca e ocupa o quadro inteiro (sem tarja).

Como foi medido (tudo em streaming, nada inteiro na RAM): cortes com `scdet` (limiar 10, conferidos com 4 quadros em volta de cada corte); rostos com YuNet (`assets/models/face_detection_yunet_2023mar.onnx`) a 2 quadros/s; luz e cor (luma, desvio, percentis, saturação, R-B) a 2 quadros/s; movimento com fluxo óptico LK + afim parcial a 10 quadros/s (o afim é a câmera: zoom, tx, ty, rotação; o resíduo p90 é o que se move **dentro** do plano); áudio com `ebur128` e fluxo espectral (onsets graves e agudos); fala com `atletia.words.json`. Os scripts ficaram no scratchpad da sessão; refazer é rápido com a mesma receita.

---

## 1. Lista de planos (52 cortes, 51 planos com imagem + 0,43 s de preto)

Legenda: **Tam.** = tamanho do plano (DET detalhe, EC extremo close, C close, MC médio-close, M médio, MC2 médio de dois, CJ conjunto, AE aérea). **Câmera** em ids do `higgsfield-camera.md`, com a medida real do conjunto do plano (zoom acumulado, deslocamento em % da largura). **Move** = o que se move no plano: P pessoa, C câmera, P+C os dois. Todas as entradas são **corte seco**, salvo quando dito.

| nº | entra (s) | dur (s) | Tam. | o que acontece | Move | Câmera (medida) | rosto e expressão | luz e cor |
|---|---|---|---|---|---|---|---|---|
| 1 | 0,00 | 2,27 | CJ | casal correndo para a câmera num parque | P+C | `dolly-out` conduzido (câmera recua na frente deles, zoom -31%) | 2 rostos (23% da altura), sérios, olhar à frente | **P&B** duro (sat 8, desvio 69); efeito de fatias verticais deslocadas o plano inteiro |
| 2 | 2,27 | 1,63 | MC | treinador (camiseta roxa) na mesa, mão esfregando a testa, escrevendo | P+C | `dolly-in` (+20%) | cansaço, olhos semicerrados | noite, luminária dura de lado, notebook aceso; Y 66 |
| 3 | 3,90 | 1,30 | M | ele boceja na cozinha, mão na boca | P | `handheld` leve (rot 2°) | exaustão | coifa quente + janela azul (R-B +21) |
| 4 | 5,21 | 1,20 | M | outro homem dormindo sobre cadernos | P (respira) | `static` | exaustão | luminária quente, fundo escuro, relógio na parede |
| 5 | 6,41 | 1,37 | M frontal | treinador diante de quadro branco cheio de gráficos, olha para a lente, mexe as mãos | P+C | `dolly-in` lento (+4%) | vazio, sobrecarga | luz fria de teto; composição simétrica |
| 6 | 7,77 | 1,81 | M | escreve na mesa escura e ergue o olhar até a lente | P+C | `dolly-in` forte com arco (+58% e 7° somando 6 e 7) | preocupação | low key, luz lateral |
| 7 | 9,58 | 1,53 | CJ | notebook aberto no sofá, sala escura, tela branca com a marca | C | `dolly-in` lento | sem pessoa | a tela é a única luz |
| 8 | 11,11 | 1,23 | C | rosto ocupando 76% da altura, olhar fixo na lente | C | `dolly-in` (+23%) | seriedade, determinação | metade do rosto na sombra, key lateral dura; Y 36 |
| 9 a 24 | 12,35 | 3,03 | CJ / C | **rajada**: 17 planos alternando notebook e rosto (durações em quadros: 20, 10, 7, 8, 6, 4, 4, 3, 3, 4, 3, 2, 3, 7, 2, 2, 3); a cada volta o rosto está mais perto (77%, 84%, 89% da altura) e o notebook maior; últimos 4 quadros (15,15 a 15,38) em glitch | C (degraus) | troca de enquadramento a cada volta | olhar fixo, sem piscar | idem 7 e 8 |
| 25 | 15,38 | 1,87 | CJ a DET | notebook com a logo, a tela branca cresce até tomar o quadro | C | `dolly-in` (+29%) | sem pessoa | tela branca; Y 169 (o plano mais claro do filme até ali) |
| 26 | 17,25 | 1,63 | C | sorriso de canto, olhar na lente (a voz entra 0,09 s depois do corte) | P | `static` | **virada**: do cansaço para a confiança | luz lateral dura, pele com textura, fundo preto |
| 27 | 18,89 | 1,47 | DET | pés com tênis verde-limão correndo à noite | P+C | `action-run` baixo (acompanha os pés) | sem rosto | noite, poste, verde da marca no tênis |
| 28 | 20,35 | 1,20 | M | **corpo digital**: corredora feita de partículas e números azuis | P+C | `truck` + push (+21%) | CG | azul-marinho, R-B -39 |
| 29 | 21,55 | 1,80 | M | **blueprint**: corredora em traço branco sobre grade azul; mão real escreve medidas | P (mão) | `static` | sem rosto | azul frio, R-B -57 |
| 30 | 23,36 | 2,34 | M | corredor digital se desfazendo em rastros de luz para a esquerda, termina 100% borrado | P+C | `dolly-out` rápido (-46%) + desfoque nos últimos 0,7 s | CG | frio |
| 31 | 25,69 | 3,27 | C | treinador sorrindo; abre 100% desfocado por 0,6 s, foco chega em 1,3 s | P+C | `rack-focus` longo + push (+12%) | sorriso aberto, rugas nos olhos | **contraluz dourado**, bokeh, R-B +51 |
| 32 | 28,96 | 1,00 | M | treinador ajuda atleta a alongar na rua | P | `static` | concentração | **P&B** |
| 33 | 29,96 | 3,94 | CJ | ciclista e corredora passam diante de um muro com sombra de árvore | P+C | `truck` lateral acompanhando (69% da largura) | pequenos | **P&B** contrastado; 4 cartelas trocam sobre o mesmo plano |
| 34 | 33,90 | 4,30 | EC | olho e bochecha de mulher negra com gotas de suor; pisca devagar | P (pisca) + C | `dolly-out` lento (-18%) | serenidade | **o plano mais quente do filme** (sat 153, R-B +85); P&B vira cor neste corte |
| 35 | 38,20 | 1,64 | M2 | treinador e corredor de branco dão aperto de mão de parceiro e riem | P+C | `truck-right` leve | riso aberto | dourado na orla, mar e morro |
| 36 | 39,84 | 1,30 | CJ plongée | corredores na rua vistos de cima com HUD de métricas | P | `static`/`tilt` | pequenos | P&B + texto verde |
| 37 | 41,14 | 1,40 | M3 | trio (treinador + 2 atletas) rindo em conversa | P+C | `handheld` | riso | dourado |
| 38 | 42,54 | 1,34 | DET | mão aponta gráficos num notebook, xícara de café | P (mão) | `static` | sem rosto | claro e dessaturado (sat 40) |
| 39 | 43,88 | 2,84 | C | mulher erguendo os braços, riso de olhos fechados, suor | P+C | `handheld` com rolagem (-14°) | euforia | contraluz dourado, R-B +77 |
| 40 | 46,71 | 3,74 | CJ | orla ao pôr do sol, corredores em silhueta | P+C | `dolly-in` frontal (+30%) | silhuetas | sol baixo no eixo da pista |
| 41 | 50,45 | 3,90 | CJ contra-plongée | 6 corredores cansados, mãos nos joelhos e na cintura | P (respiram) | `static` | cansaço real | fim de tarde esverdeado |
| 42 | 54,35 | 4,94 | M2 | treinador ajusta o joelho do corredor à beira do rio | P | `static` | atenção | luz suave de manhã |
| 43 | 59,29 | 5,67 | M2 | dupla sentada no chão com tablet, conversa e ri | P | `static` | cumplicidade | pôr do sol rosa e laranja |
| 44 | 64,97 | 5,34 | M2 | treinador e atleta no banco com relógio e caderno | P+C | `truck` lateral (29%) | escuta atenta | tarde dourada, parque |
| 45 | 70,30 | 7,94 | M a AE | corredora de amarelo na passarela; a câmera sobe e recua com borrão (70,9 a 72,0) até a avenida aérea; de 72,4 s uma **rede de linhas** nasce de um ponto e cobre a cidade em ~5 s | P+C | `aerial-pullback` rápido (zoom -83%) que assenta | pequena | dourado; linhas brancas e ciano |
| 46 | 78,25 | 5,10 | M2 | abre desfocado 0,5 s, foco em 0,65 s; treinador explica com prancheta, atleta ri | P+C | `rack-focus` + `tilt` leve | riso | dourado na pista |
| 47 | 83,35 | 3,00 | M2 | treinador de bicicleta e corredor na avenida molhada, vindo para a câmera | P+C | `dolly-out` conduzido (-24%) | foco | anoitecer azul + faróis |
| 48 | 86,35 | 3,14 | AE | vista de cima de 2 corredores com **HUD** ciano (barras, mostradores, gráfico) | P+C | `overhead` com pan lateral (56%) | pequenos | frio, R-B -38 |
| 49 | 89,49 | 2,37 | M2 | dupla correndo para a câmera na orla, conversando e sorrindo | P+C | `dolly-out` conduzido (-31%) | alegria | dourado |
| 50 | 91,86 | 3,27 | AE | multidão de camisetas roxas numa largada; entra empurrando a imagem anterior para a esquerda, com borrão | P+C | `dolly-in` (+21%) | multidão | saturado, roxo da marca |
| 51 | 95,13 | 5,34 | cartela | branco; logo nasce de um ponto; "A tecnologia escala" (96,0 s), "O humano conecta" (98,0 s) | grafismo | `static` | sem pessoa | branco, verde-limão, azul-marinho |
| 52 | 100,47 | 0,43 | preto | | | | | |

---

## 2. Imagens: o que faz a referência parecer boa (números)

### 2.1 Comparação medida (ref = referência sem a cartela final; nosso = `2026-11-12_vertical.mp4`)

| medida | referência | nosso manifesto | diferença |
|---|---|---|---|
| quadros com rosto detectável | **63%** | 11% (rostos minúsculos de multidão) | 5,7x |
| quadros com rosto ≥ 25% da altura (close/médio-close) | **26%** | **0%** | |
| quadros com 2 ou mais rostos | **39%** | 7% | 5,6x |
| altura mediana do rosto, quando há rosto | 23% do lado menor | 7% do lado menor | 3,3x |
| planos com olhar na lente | 5 (todos do protagonista, atos 1 e 2) | 0 | |
| planos com pessoas interagindo (aperto de mão, conversa, ajuste, riso junto) | **12** | 0 | |
| movimento dentro do plano (resíduo p90 do fluxo, % da largura a cada 0,1 s), mediana | **0,53** | 0,16 | 3,3x |
| quadros com ação real dentro do plano (resíduo > 0,5%) | **52%** | 22% | |
| movimento de câmera (translação mediana, % largura/0,1 s) | 0,43 | 0,31 | parecido |
| luma média (0 a 255) | 110 | 82 | +34% |
| contraste (desvio da luma) | **62** | 43 | +44% |
| ponto preto (percentil 2) | **13** | 27 (preto lavado) | |
| ponto branco (percentil 98) | **229** | 194 (sem altas luzes) | |
| saturação média (HSV, 0 a 255) | **100** | 64 | +56% |
| temperatura (R médio - B médio) | **+25** (quente) | -3 (roxo neutro) | |
| nitidez (variância do Laplaciano, ~210 mil px) | ~700 | ~320 | 2,2x (nosso é névoa + bokeh + ampliação lanczos de 768x1344) |
| transições | 50 cortes secos + 1 empurrão + 1 rajada com glitch | 10 dissolves em 18 planos | |

**Conclusão:** a câmera do nosso filme até anda; o que falta é **gente de verdade fazendo algo, com cara, com luz dura ou contraluz, em cor quente e contrastada**. O nosso parece pior por cinco motivos, em ordem: (1) nenhum rosto, porque os prompts tinham `visible face, frontal face, looking at camera` no negativo e "seen from behind" no positivo; (2) nada se move dentro do quadro (foto com parallax = só a câmera anda); (3) luz chapada e enevoada: preto em 27, branco em 194, saturação 64, dominante roxa; (4) ninguém interage com ninguém (multidão de costas e uma pessoa sozinha); (5) dissolves em vez de corte seco, o que amolece o ritmo.

### 2.2 Pessoas

- **Rosto visível e grande é a regra**: 21 dos 35 planos "humanos" têm rosto legível; 8 são closes com o rosto entre 43% e 89% da altura. A expressão conta a história sem texto: mão na testa, bocejo, dormir na mesa, olhar fixo (ato 1); sorriso de canto (virada); sorriso aberto, riso compartilhado, euforia de braços erguidos (subida); atenção e escuta (prova).
- **Um protagonista-âncora com figurino de cor fixa**: o treinador aparece em ~20 planos, **sempre de camiseta roxa** (a cor da marca no mundo real: a multidão final também veste roxo). O tênis verde-limão (plano 27) é a outra cor da marca. Rosto, corte de cabelo e camiseta iguais em todos os planos.
- **Pessoas reais, não modelos**: homem de ~35 a 40 anos com rugas nos olhos e barba por fazer, mulher de ~40 com suor, homens e mulheres negros e brancos, corpos de corredor amador. Pele com poro, suor e brilho; nada de pele de plástico.
- **Interação física**: aperto de mão de parceiro, mão no joelho do atleta, apontar para a tela, sentar lado a lado, correr lado a lado conversando. O "humano conecta" do slogan é mostrado, não dito.
- **Olhar na lente só no começo e só do protagonista** (planos 5, 6, 8, rajada, 26): cria o pacto com o espectador. Da virada em diante ninguém olha para a câmera; as pessoas olham umas para as outras.

### 2.3 Enquadramento, lente e profundidade

- Tamanhos: 9 closes/extremos closes, 14 médios e médios de dois, 10 conjuntos, 4 aéreas, 5 detalhes (pés, mãos, tela). **Todo corte troca o tamanho do plano** (a regra do "duplo contraste" do `higgsfield-camera.md` vale aqui também).
- Closes em tele (equivalente a 85 a 135 mm): fundo em bokeh grande, bolas de luz laranja no dourado. Médios de dois em ~50 mm com fundo legível mas suave. Conjuntos e aéreas com tudo em foco.
- Composição: rosto no terço, **texto no espaço negativo ao lado do rosto** (planos 31, 34). Dois personagens se olhando em perfil, ocupando a metade de baixo do quadro, céu ou fundo dourado em cima.
- Ângulos: contra-plongée no grupo cansado (41), plongée/overhead nos planos de dados (36, 48), altura dos olhos nos closes, câmera baixa nos pés (27).

### 2.4 Luz e cor (três regimes, cada um com uma função)

| regime | onde | medidas | como é a luz |
|---|---|---|---|
| **noite do problema** | planos 2 a 26 | luma 32 a 88, desvio 48 a 74, sat 95 a 145, R-B ~0 a +25 | uma fonte dura de lado (luminária, tela), metade do rosto no preto, fundo quase preto, um prático quente ao fundo |
| **digital/dados** | 28 a 30, 36, 38, 48 | R-B -21 a -57 (azul) ou P&B | azul-marinho com partículas ciano; P&B com HUD |
| **humano dourado** | 31, 34, 35, 37, 39 a 49 | luma 95 a 136, sat 104 a 159, R-B +25 a +85 | **contraluz de sol baixo**, rim light no cabelo e nos ombros, bokeh, flare leve; pele quente e saturada |

Mais duas regras de cor: o **P&B** marca o "antes" e o mundo das tarefas (abertura, "das pessoas, dos medos, dos sonhos") e **vira cor de uma vez, num corte seco**, no plano mais quente do filme (34, a frase "é aí que nasce a conexão"). E a cor de destaque da marca aparece no figurino e nos objetos (camiseta roxa, tênis verde), não em filtro.

### 2.5 Movimento dentro do plano

- 52% dos quadros têm ação real do sujeito. Ninguém está "posando": esfrega a testa, boceja, escreve, corre, ri, ergue os braços, ajusta o joelho, aponta, pisca.
- A câmera quase sempre anda junto, com movimento simples: `dolly-in` (10 planos), `dolly-out` conduzido na frente de quem corre (5), `truck` lateral (4), `static` (12, sempre com a pessoa se mexendo), `handheld` (4), `rack-focus` (2), `aerial-pullback` (1), `overhead` (1).
- Planos parados de câmera existem, mas só quando a pessoa faz algo (dorme e respira, alonga, conversa). **Nunca** câmera parada com pessoa parada.

---

## 3. Regras de imagem para o `edin imagem` (SDXL) e para o gerador de vídeo local

### 3.1 Regras de prompt (SDXL, `edin imagem`)

1. **Rosto é o assunto.** Tirar do negativo `visible face, frontal face, looking at camera, portrait` (estava em todos os lotes de 12/11). Pôr no positivo o tamanho do plano e a expressão: `close-up of ...`, `medium shot of two ...`, `genuine laugh`, `tired eyes`, `crow's feet`, `looking into the camera` (só no ato 1, só o protagonista).
2. **O CLIP lê 77 tokens** e o kit acrescenta personagem, lente e estilo no fim: o texto do plano fica em **até ~35 palavras**, na ordem: tamanho do plano + quem + ação/expressão + interação + luz + lugar/hora.
3. **Rosto pequeno deforma no SDXL**: rosto que vai ficar nítido precisa de ≥ 15% da altura da imagem. Em conjunto/multidão, as pessoas ficam desfocadas, de perfil ou contra o sol; o rosto nítido fica para close e médio.
4. **Luz explícita em todo prompt**, uma das três: `hard side light from a desk lamp, half of the face in shadow, dark room` (noite), `golden hour backlight, warm rim light on hair and shoulders, sun flare, bokeh` (dourado), `black and white, high contrast` (P&B). Nunca deixar a luz implícita: o default do modelo é luz chapada.
5. **Negativo novo** (só funciona com `--sem-lightning`, que já é o padrão de qualidade máxima): o `NEGATIVO` do kit + `hazy, foggy, washed out, flat lighting, low contrast, muted colors, purple tint, plastic skin, airbrushed, model pose, stock photo`.
6. **Pele e idade reais**: `visible skin pores, light sweat, stubble, 35-year-old` para o protagonista; idades e etnias variadas nos coadjuvantes, sem clones.
7. **Figurino-âncora**: o protagonista descrito igual em todos os planos (no `personagens` do lote), com uma peça na cor da marca (ex.: LoopEdu: moletom ou camiseta `indigo #4F46E5` e um detalhe laranja; a camiseta roxa da referência). A seed do personagem fixa e o mesmo texto de descrição.
8. **Interação**: pelo menos 1 em cada 3 planos com 2 ou 3 pessoas se tocando, olhando uma para a outra ou dividindo um objeto (`clasping hands`, `pointing at the tablet`, `adjusting his knee`, `sitting side by side laughing`).
9. **9:16 nativo** (768x1344): dupla em profundidade (uma pessoa mais perto, a outra atrás e de lado, `over-the-shoulder`) em vez de lado a lado; o close cabe inteiro; aérea e conjunto com o assunto no terço de baixo e céu/cidade em cima para o texto.
10. **Tela de aparelho sai vazia** (`blank white screen`) e a interface entra pelo HTML (o SDXL desenha letra ilegível).
11. Conferir antes de usar: rosto com 2 olhos alinhados, 5 dedos, sem pessoa duplicada, preto ≤ 20 e branco ≥ 220 no histograma (`signalstats`), saturação média ≥ 85. Se falhar, outra seed, não outro filtro.

### 3.2 Modelos de prompt por tipo de plano (inglês, para colar)

| plano | prompt (sem personagem/lente/estilo, que o lote acrescenta) | lente | estilo |
|---|---|---|---|
| rosto cansado à noite | `medium close-up of a tired man rubbing his forehead, eyes half closed, writing in a notebook at a desk at night, hard side light from a desk lamp, half of the face in shadow, dark room, laptop glow` | 50 | noite |
| bocejo / exaustão em casa | `medium shot of an exhausted man yawning and covering his mouth in a small kitchen at night, warm light from the stove hood, blue window behind` | 35 | noite |
| olhar fixo na lente | `close-up of a serious man looking straight into the camera, hard light from the left, half of the face in deep shadow, black background, visible skin pores, stubble` | 85 | noite |
| sorriso de virada no escuro | `close-up of a man with a confident half smile looking into the camera, hard side light, deep shadows, black background` | 85 | noite |
| sorriso em contraluz dourado | `close-up of a smiling man with crow's feet and light sweat, genuine smile, golden hour backlight, warm rim light on hair, sun bokeh behind, park` | 85 | campanha |
| duas pessoas se cumprimentando | `medium shot of two men laughing and clasping hands in a firm handshake, one in a purple t-shirt, seaside running path, golden hour backlight, palm trees` | 35 | campanha |
| trio conversando | `three runners laughing together after training, coach in the foreground facing two athletes, sports field, late afternoon sun, backlight` | 50 | campanha |
| treinador ajustando atleta | `coach kneeling and adjusting the knee of a runner, both focused, riverside path, soft morning light, trees` | 35 | documental |
| dupla sentada com tablet | `two friends sitting on the ground after a run, looking at a tablet and laughing, pink and orange sunset sky, palm trees` | 35 | campanha |
| grupo cansado (prova real) | `low angle wide shot of six tired amateur runners, hands on knees, catching their breath on a city avenue at sunset` | 24 | documental |
| grupo correndo para a câmera | `group of diverse runners jogging toward the camera on a city avenue at sunrise, low angle, sun flare between buildings` | 35 | campanha |
| close de olho com suor | `extreme close-up of a woman's eye and cheek covered in sweat drops, brown skin, golden backlight, warm orange bokeh` | macro | campanha |
| alegria de braços erguidos | `close-up of a woman runner raising both arms, laughing with eyes closed, sweat, golden hour backlight, low angle` | 85 | campanha |
| pés correndo à noite | `close-up of running shoes hitting a wet track at night, motion, street light, low angle` | 35 | noite |
| mão no notebook | `close-up of a hand pointing at a laptop with a blank white screen, coffee cup, bright window light, shallow depth of field` | 50 | documental |
| P&B do "antes" | `black and white, high contrast, a cyclist and a runner passing a white wall with long tree shadows` | 35 | nenhum |
| cidade para a rede de linhas | `aerial view of a dense Brazilian city avenue at golden hour, runners on the street, tall buildings, trees` | 24 | campanha |
| multidão da largada | `aerial drone shot of a huge street race crowd in purple shirts, city street, bright daylight` | 24 | documental |

Para o LoopEdu, troque corredor e treinador por estudante e professor/monitor, pista por escola, quadra, ônibus, cozinha de casa; mantenha luz, tamanho de plano, expressão e interação iguais.

### 3.3 Direção para o gerador de vídeo local (foto do SDXL -> clipe; Wan2.2-TI2V-5B no `edin animar`)

- **Prompt de vídeo = ação do sujeito + movimento de câmera + luz**, em uma frase, **uma ação por clipe**: `the tired man slowly rubs his forehead and looks up, slow dolly in, hard side light`; `the two men laugh and shake hands, camera trucks right slowly, golden backlight`; `the woman raises both arms and laughs, handheld camera, sun flare`; `two runners jog toward the camera talking, camera moves backward in front of them`; `the eye blinks slowly, slow dolly out`.
- Vocabulário de câmera em inglês simples (o modelo entende melhor que nome de preset): `static camera`, `slow dolly in`, `camera moves backward`, `camera trucks left/right`, `handheld camera`, `rack focus from background to face`, `aerial camera rising and pulling back`.
- **Expressão que muda dentro do clipe** é o ouro da referência (cansaço que vira sorriso de canto; foco que vira riso): peça a mudança explícita (`his tired face slowly turns into a confident half smile`).
- Gere 5 s (121 quadros a 24 fps) e use **1,2 a 5,5 s** do melhor trecho; 2 a 3 seeds por plano; descarte clipe com mão derretendo, rosto que troca de identidade ou pessoa que surge do nada.
- Câmera do clipe e câmera do HTML não se somam: se o clipe já tem `dolly-in`, o HTML fica `static` (no máximo deriva). A regra "um movimento por plano" continua valendo.
- Movimento moderado: corrida, riso, gesto de mão e piscar saem bem; giro de corpo inteiro, mão segurando objeto pequeno e multidão em movimento costumam deformar; nesses, prefira câmera andando e pessoa quase parada.

---

## 4. Ritmo e montagem

| ato | trecho (s) | planos | média (s) | mediana (s) | min a max (s) | cortes/min |
|---|---|---|---|---|---|---|
| 1. abertura sem voz (o problema em rostos) | 0 a 12,3 | 8 | 1,54 | 1,37 | 1,20 a 2,27 | 39 |
| 1b. rajada + glitch | 12,3 a 15,4 | 17 | 0,18 | 0,13 | 0,07 a 0,67 | 331 |
| 1c. impacto e logo na tela | 15,4 a 17,3 | 1 | 1,87 | | | 32 |
| 2. problema, digital x humano, P&B, virada | 17,3 a 38,2 | 9 | 2,33 | 1,80 | 1,00 a 4,30 | 26 |
| 3. série paralela (1 plano por oração) | 38,2 a 46,7 | 5 | 1,70 | 1,40 | 1,30 a 2,84 | 35 |
| 4. prova humana (planos longos de dupla) | 46,7 a 70,3 | 5 | 4,72 | 4,94 | 3,74 a 5,67 | 13 |
| 5. escala: cidade, rede, HUD, multidão | 70,3 a 95,1 | 6 | 4,14 | 3,20 | 2,37 a 7,94 | 15 |
| 6. assinatura | 95,1 a 100,9 | 1 + preto | 5,34 | | | |
| **total até 95 s** | | 50 | 1,90 | 1,38 | | 32 |
| sem a rajada | | 33 | 2,79 | 2,34 | | 21 |

- **Curva**: rápido e seco no começo (1,2 a 1,6 s), explode na rajada (2 a 3 quadros), respira na virada (3 a 4 s), volta a 1,3 a 1,7 s na série paralela, **desacelera muito na prova** (4 a 5,7 s, gente conversando) e fecha com planos de escala de 3 a 8 s. O dinamismo vem do **contraste** de velocidade e do movimento dentro do plano, não de cortar rápido o tempo todo.
- **Corte x narração**: dos 25 cortes com voz, a mediana é **0,03 s antes do início da palavra** e 0,01 s depois do início da frase; 18 de 25 caem a ±0,1 s de um ataque de palavra. Na série "o treinador inspira / a Atletia acelera / o treinador conecta / a Atletia otimiza" há **um plano por oração**, cortado exatamente no artigo que abre cada uma (38,20; 39,84; 41,14; 42,54).
- **Corte x música**: a distância média do corte ao onset grave mais próximo é 0,109 s contra 0,127 s ao acaso: **não corta na batida**. A trilha é cinematográfica, sem grade forte (autocorrelação 0,09 a 0,24). Quem manda no corte é a voz. Exceção: a rajada, em que cada troca tem um estalo agudo, e o impacto grave em 15,33 s que lança a logo.
- **Transições**: corte seco em 50 de 52. As exceções têm motivo: borrão para borrão (plano 30 desfoca em 0,7 s e o 31 abre desfocado: o corte some no borrão), empurrão lateral com borrão para a multidão (50) e a cartela branca com a logo nascendo de um ponto. **Nenhum dissolve.**

---

## 5. Narração

- Voz masculina grave (F0 mediana 114 Hz, p10 88, p90 157), tom de documentário, próxima, sem gritar.
- Entra só aos **17,3 s** (o token "A" em 3,8 s tem confiança 0,37: é respiração/efeito). Os 17 primeiros segundos são só imagem, música e efeitos.
- **177 palavras** em 81 s de voz: 2,0 a 2,3 palavras/s brutas por ato, **3,0 palavras/s enquanto fala** (ritmo firme, mais rápido que o 1,4 a 1,9 do `manifesto.md`).
- **Pausas**: 39 pausas ≥ 0,3 s, mediana 0,42 s (uma por frase). Três pausas longas, todas antes de uma virada: **2,79 s** depois de "é aí que nasce a conexão" (sobre o olho com suor), **1,72 s** antes de "a comunidade está pronta", **1,35 s** antes do nome "Atletia". A música não para nas pausas: cai ~5 dB (short-term -24,8 LUFS em 38 s contra -17 a -19 em volta).
- Estrutura do texto: (1) o problema dito como fato ("assume o humanamente impossível, milhares de cálculos, volumes, intensidades, o caos"), lista de 3 a 4 itens; (2) o contrário humano ("cuida do que realmente importa: das pessoas, dos medos, dos sonhos"); (3) frase-chave curta e sozinha; (4) **série paralela alternando humano e máquina** (4 orações de 2 a 3 palavras); (5) escala ("agora, imagine milhões..."); (6) **anáfora** de 3 ("Quando o treinador recomenda, eles escutam. Quando indicam tênis, eles compram. Quando sugerem uma marca, ela vira parte da jornada."); (7) **corrente** ("recomendação vira relacionamento, relacionamento vira comunidade, comunidade vira movimento"); (8) 2 frases declarativas de 3 a 4 palavras ("A comunidade está pronta. Os dados estão vivos."); (9) promessa ("a corrida no Brasil vai acontecer aqui"); (10) **nome sozinho**, depois slogan em 2 metades paralelas ("A tecnologia escala. O humano conecta.").
- Imagem x fala: a imagem ilustra a fala de forma direta mas não literal (fala "inspira", vemos aperto de mão rindo; fala "dados", vemos HUD). Fala de máquina sobre imagem digital/P&B; fala de gente sobre gente em cor quente.

## 6. Texto na tela

- **É a própria narração em pedaços**, palavra por palavra do que é dito, em blocos de **2 a 4 palavras** (mediana 2 a 3; máximo 7 acumuladas em 3 linhas no plano 31). Uma cartela nova a cada ~1,1 s de fala.
- Sincronia: o bloco entra **junto com a primeira palavra dele** (de 0,1 s antes a 0,4 s depois); dentro do mesmo plano os blocos se **acumulam** linha a linha ("O treinador / cuida do que / realmente importa") ou trocam no mesmo lugar (plano 33). Sai no corte.
- Tamanho: altura de maiúscula/ascendente **42 px** em 1080 (fonte ≈ **56 px**, 5,2% da altura), entrelinha ≈ 58 px (1,0). Sans geométrica seminegrito (tipo Gilroy/Sora 600), branca, sem caixa, sombra quase imperceptível. Pequena e elegante, nunca "legenda de TikTok".
- Posição: **no meio do quadro** (centro vertical entre 0,50 e 0,65 da área de imagem), centralizada ou alinhada à esquerda no espaço negativo ao lado do rosto. Nunca no terço de baixo.
- Destaque: **1 palavra em verde #25FC6C** (o verde-limão da marca, medido) em ~1 de cada 3 cartelas, sempre a palavra-conceito: Atletia, conexão, compram, escutam, ecossistema, descoberta, dados, recomendação, conecta.
- Entrada: a primeira cartela de um plano com `rack-focus` entra **desfocada junto com a imagem** e ganha foco em ~0,3 s; as linhas seguintes aparecem secas (1 a 2 quadros). Sem subir, sem escala, sem máquina de escrever.
- Em 9:16 (1080 de largura): **60 a 72 px** (Sora 600), centro entre 0,50 e 0,62 da altura, blocos de 2 a 4 palavras, no máximo 3 linhas acumuladas.

## 7. Som

- Loudness short-term por trecho: abertura sem voz -17 a -20 LUFS; rajada sobe de -18 a -14; **pico do filme no impacto da logo, -9,1 LUFS em 16 s** (grave +32 dB acima do normal); com voz -15,5 (17 a 28 s), -17 a -19 (28 a 95 s); pausa-chave -24,8; cartela final -20 a -21. Integrado -16,9 LUFS.
- Música: cinematográfica, pulso grave irregular, sem batida dançante; cresce do começo até o impacto de 15,3 s, assenta embaixo da voz (voz bem à frente) e não tem um "drop" depois da logo: a energia vem das imagens e da voz.
- Efeitos: estalo/clique agudo em cada troca da rajada (onsets agudos em 12,31; 12,91; 13,82; 15,12), ruído digital nos 4 quadros de glitch, **impacto grave (boom) em 15,33 s** casado com a entrada da logo, whoosh no `aerial-pullback` (70,9 a 72,0) e no empurrão da multidão (91,9).
- Silêncio total: nenhum. A pausa é da voz; a música baixa ~5 dB e continua.

## 8. Efeitos e transições: como recriar no kit HTML sobre clipes

O kit (`references/html-video/` + `edin html`) renderiza a página quadro a quadro por `seek(t)` e não toca `<video>`. **Clipe de vídeo entra como sequência de quadros**: `ffmpeg -i clipe.mp4 -vf fps=30 -q:v 2 quadros/c01_%04d.jpg` e uma `<img>` cujo `src` troca em `seek` (`Math.floor((t - inicio) * 30)`), com o próximo quadro pré-carregado; a 60 fps com `--motion-blur 8` cada quadro do clipe aparece 2 vezes (normal). Os efeitos vão num `<canvas>` ou SVG por cima. Isso precisa de um helper novo no `edin-video.js` (não existe ainda).

| efeito | na referência | duração e quando | como fazer no kit |
|---|---|---|---|
| **glitch de fatias** (P&B de abertura) | faixas verticais de 20 a 60 px deslocadas ±2 a 6% na horizontal, P&B | o plano 1 inteiro (2,27 s), abre o filme | canvas: desenhe o quadro em fatias com deslocamento por ruído que muda a cada 2 a 3 quadros (valor discreto, sem motion blur); `filter: grayscale(1) contrast(1.35)` |
| **rajada com glitch** | alternância rosto/tela acelerando de 20 para 2 quadros, cada volta mais perto; 4 quadros finais com blocos em limiar P&B, faixas horizontais deslocadas e canal RGB separado | 3,0 s, entre o problema e a marca | lista de trocas em quadros (20, 10, 7, 8, 6, 4, 4, 3, 3, 4, 3, 2, 3, 7, 2, 2, 3); escala de cada volta +4 a 6%; nos 4 quadros finais: faixas de 8 a 40 px com `drawImage` deslocado ±5 a 15%, blocos com `threshold`, separação RGB de 6 a 12 px; `--motion-blur` desligado nesse trecho (valor discreto por quadro); som: clique por troca + boom no fim |
| **corpo digital (partículas)** | silhueta de corredor feita de pontos e dígitos azuis, rastros para trás, se desfaz | 3 planos em 5,1 s (20,35 a 25,69), sobre a fala dos "milhares de cálculos" | máscara da pessoa (recorte do quadro do clipe ou `person-matte.py` da skill de motion); 3.000 a 6.000 pontos amostrados dentro da máscara, `globalCompositeOperation='lighter'`, ciano #4FC3FF a #BFE9FF, rastro de 10 a 30 px no sentido contrário ao movimento; no último plano os pontos voam com ruído e a imagem desfoca até 30 px em 0,7 s |
| **blueprint com mão** | traço branco sobre grade azul, mão real escrevendo | 1,8 s, no meio da sequência digital | SVG com `stroke-dashoffset` desenhando o contorno + grade; a mão é um clipe gerado sobre fundo azul ou foto recortada |
| **rack focus** | abre 100% desfocado, segura 0,5 a 0,6 s, foco chega em 0,65 a 1,3 s; o plano anterior desfoca antes do corte | 2 vezes (25,7 e 78,3), sempre entrando num close humano dourado | `filter: blur()` de 30 px para 0 em `inOutCubic` (ou o `foco` do `edin-cam.js`), com a primeira cartela desfocando junto; plano anterior: blur 0 a 30 px nos últimos 0,7 s |
| **P&B vira cor** | bloco P&B de 2 planos (4,9 s), corte seco para o close mais quente | 1 vez, na frase-chave | `grayscale(1) contrast(1.3)` nos planos do bloco; o plano seguinte entra com grade quente (`grade: { luzes: '#ffb68a' }`) e saturação +20%; corte seco, sem rampa |
| **rede de linhas na cidade** | ponto de luz nasce no centro da avenida, linhas crescem para ~30 nós, pulsos correm nas linhas | 5,5 s (72,4 a 78,2), depois que a aérea assenta | SVG sobre o clipe aéreo **quase parado** (senão as linhas escorregam): nós em cruzamentos, `stroke-dasharray` crescendo do centro para fora em 2,5 s, brilho `lighter` branco-ciano, pulsos de 6 px percorrendo cada linha a cada 1,2 s, halo nos nós (`EdinVideo.halo`) |
| **HUD de dados** | painéis ciano semitransparentes (barras subindo, mostradores circulares, gráfico de linha) sobre vista de cima; texto de métricas sobre P&B | 3,1 s e 1,3 s, nos trechos "dados" | SVG/HTML com opacidade 0,6 a 0,8, linhas de 2 px ciano #5FE3FF, barras animando altura em `outCubic` 0,4 s, números contando; fonte mono pequena; entra em 0,2 s |
| **tela de notebook** | a tela branca com a marca é a única luz do quarto; a câmera avança até a tela tomar o quadro | 1,5 s + 1,9 s | clipe com tela vazia; logo/interface em HTML com `perspective` casando os 4 cantos da tela; `dolly-in` até a tela ocupar 100% e virar a cena seguinte (é o `through-object` do catálogo) |
| **empurrão lateral com borrão** | a multidão entra pela direita empurrando o plano anterior | ~0,2 s | transição `push` do kit com blur direcional 40 px e whoosh |
| **cartela final branca** | fundo branco; logo nasce de um ponto com pop (0,5 s, overshoot ~8%); slogan em 2 linhas entrando 1 e 3 s depois; a 2ª linha com a palavra verde | 5,3 s + 0,43 s de preto | página branca; logo `scale` 0 a 1,08 a 1 em `outExpo`; linhas com fade de 0,2 s; sem câmera; preto final de 0,4 s |

---

## 9. Diferenças concretas, em ordem de impacto (referência x nosso de 12/11)

1. **Rostos**: 63% dos quadros com rosto e 26% em close, contra 11% e 0%. Os nossos prompts pediam rosto escondido. Rafael quer rosto e expressão.
2. **Movimento dentro do plano**: 0,53 contra 0,16 (3,3x) e 52% contra 22% dos quadros com ação. Foto com parallax nunca chega lá; precisa de clipe (gerador de vídeo) ou, no mínimo, foto com gesto forte e câmera andando.
3. **Luz e cor**: contraste 62 contra 43, preto 13 contra 27, branco 229 contra 194, saturação 100 contra 64, temperatura +25 contra -3. A referência tem luz dura ou contraluz em todo plano; o nosso é névoa roxa.
4. **Interação**: 12 planos de pessoas se relacionando contra 0.
5. **Narração**: 177 palavras, 3 palavras/s ao falar, cortes no ataque das frases; o nosso não tinha voz.
6. **Montagem**: corte seco em 50 de 52 contra 10 dissolves em 18; contraste de ritmo de 0,07 a 7,9 s (13 a 331 cortes/min por ato) contra 0,6 a 4,2 s quase uniforme.
7. **Efeitos com função**: 6 efeitos digitais (glitch, partículas, blueprint, rede, HUD, P&B) que contam "máquina" contra o "humano" em cor; o nosso não tinha nenhum, só grão e o ponto laranja.
8. **Âncora visual**: protagonista de camiseta roxa em ~20 planos, olhando na lente no começo; o nosso tinha a "lu" de costas, de moletom bege, sem rosto.
9. **Texto**: a fala em blocos de 2 a 4 palavras, 56 px em 1080, no meio do quadro, destaque verde em 1 palavra; o nosso tinha frases próprias de 86 px.
10. **Nitidez**: ~700 contra ~320 (névoa, bokeh em tudo e ampliação de 768x1344).
11. Duração: 100,9 s e 16:9; para Reels, o molde abaixo comprime para 30 a 60 s em 9:16.

---

## 10. Molde reaplicável: manifesto narrado dinâmico (9:16)

### Atos e tempos

| ato | função | 30 s | 45 s | 60 s | planos e duração | imagem |
|---|---|---|---|---|---|---|
| A0 abertura sem voz | a dor em rostos; o espectador se reconhece | 0 a 3,5 | 0 a 5 | 0 a 7 | 3 / 4 / 5 planos de 1,1 a 1,5 s | protagonista com rosto: cansaço, bocejo, mão na testa, olhar na lente; noite com luz lateral dura; 1º plano P&B com glitch de fatias |
| A1 rajada + impacto | a solução aparece | 3,5 a 5 | 5 a 7 | 7 a 9,5 | 8 a 17 trocas de 20 até 2 quadros + 3 a 4 quadros de glitch; impacto na marca | rosto x tela, cada volta mais perto; boom grave na marca |
| A2 problema x humano | voz entra; máquina em azul/P&B, gente em cor | 5 a 12 | 7 a 17 | 9,5 a 22 | 4 / 6 / 7 planos, 1,2 a 2,3 s | partículas/HUD para "dados"; rack focus de borrão para o sorriso dourado |
| A3 virada | frase-chave sozinha + pausa de voz | 12 a 14,5 | 17 a 20 | 22 a 26 | 1 plano de 2,5 a 4 s | P&B vira cor no close mais quente (olho, suor, contraluz); pausa de voz de 0,8 / 1,5 / 2,5 s com a música 5 dB abaixo |
| A4 série paralela | 2 a 4 orações de 2 a 3 palavras, alternando | 14,5 a 18 | 20 a 25 | 26 a 31,5 | **1 plano por oração**, 1,2 a 1,7 s, corte no artigo que abre a oração | aperto de mão, trio rindo, mão na tela, braços erguidos |
| A5 prova humana | anáfora de 2 a 3 ("Quando..."), gente real | 18 a 23,5 | 25 a 33 | 31,5 a 43 | 2 / 3 / 3 planos de 2,7 a 4,5 s | duplas conversando, ajustando, rindo; grupo cansado real; câmera parada ou `truck` lento |
| A6 escala | corrente "X vira Y", "agora...", promessa | 23,5 a 27 | 33 a 41 | 43 a 54 | 2 / 3 / 4 planos de 1,5 a 4 s | `aerial-pullback` até a cidade com rede de linhas; HUD; multidão na cor da marca |
| A7 nome + assinatura | pausa, nome sozinho, slogan em 2 metades | 27 a 30 | 41 a 45 | 54 a 60 | cartela branca 2,5 / 3,5 / 5 s + 0,3 s de preto | logo nasce de um ponto, slogan com 1 palavra na cor de destaque |

Narração: 2,2 palavras/s brutas na parte com voz, 3 palavras/s ao falar: **~45 palavras em 30 s, ~70 em 45 s, ~100 em 60 s**. Voz entra no fim da A1.

### Regras de corte
- Corte seco por padrão; dissolve proibido. Exceções: borrão para borrão, empurrão lateral com borrão (1 vez), rajada.
- Corte a ±0,1 s do ataque da palavra que abre a frase (mediana -0,03 s). Não corte na batida.
- Todo corte troca o tamanho do plano. Contraste de velocidade entre atos: A0/A4 ~1,4 s; A1 0,07 a 0,6 s; A5 3 a 5 s.
- Nada de câmera parada com pessoa parada.

### Regras de texto
- A fala em blocos de 2 a 4 palavras, entrando com a 1ª palavra, acumulando até 3 linhas no mesmo plano, saindo no corte.
- 9:16: Sora 600, 60 a 72 px, branco, centro entre 0,50 e 0,62 da altura, no espaço negativo ao lado do rosto.
- 1 palavra-conceito na cor de destaque em ~1 de cada 3 blocos.

### Regras de som
- Abertura sem voz com música crescendo e efeitos; boom grave na marca (o pico do filme, ~-9 LUFS short-term).
- Voz em -15 a -17 LUFS short-term, música bem abaixo; nas pausas-chave a música desce ~5 dB, sem silêncio total.
- Clique por troca na rajada, ruído digital no glitch, whoosh em pullback e empurrão. Integrado -14 a -17 LUFS, pico -1,5 dBTP.

### Regras de imagem (resumo)
- Rosto visível em ≥ 50% do tempo e close em ≥ 20%; olhar na lente só do protagonista e só antes da virada.
- Protagonista com figurino na cor da marca em ≥ 40% dos planos.
- ≥ 1 em 3 planos com 2 ou mais pessoas interagindo.
- Três regimes de luz (noite dura, digital frio/P&B, dourado em contraluz); grade final com preto ≤ 20, branco ≥ 220, saturação ≥ 85, R-B positivo nos planos humanos.
- Clipes com ação (gerador de vídeo); foto com parallax só em aérea, detalhe ou plano de 1 s.
