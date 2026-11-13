# Vídeo manifesto com pessoas feitas em código

Manifesto de marca é um filme curto que diz **no que a marca acredita**, não o que o produto faz. Funciona quando o espectador se reconhece na tensão do começo e sai com uma frase que dá para repetir. Para Reels: 30 a 60 s, alvo 38 a 45 s. Tudo feito no fluxo I (kit `html-video/` + `edin html`, 60 fps, `--motion-blur 8`), com as pessoas do `edin-pessoas.js` (rig 2D) e a câmera de [higgsfield-camera.md](higgsfield-camera.md). Nada de Canva nem IA geradora de imagem.

Roteiro modelo pronto: [manifesto-loopedu-roteiro.md](manifesto-loopedu-roteiro.md).

## 1. O que a pesquisa mostrou (e virou regra aqui)

- **Forma em U** (a mais usada em manifesto de marca): queda, virada, subida. A metade negativa precisa ser substancial; a virada é curta (uma palavra, uma frase, um silêncio) e cai perto do meio; a subida espelha a queda. Ficar repetindo exemplos do mesmo tipo no meio mata o filme.
- **Fim em "rally"**: estrutura paralela (frases com o mesmo molde) para o convite. A melhor frase fica no fim, sozinha.
- **Nike "You Can't Stop Us"**: de ~4.000 clipes ficaram 72, em 36 pares; o match foi feito no olho e par "quase bom" era trocado. Regra: match cut só vale se a forma casa de verdade; se não casa, troque a imagem, não force.
- **Nike "Dream Crazy"**: narração em chamada e resposta sobre anônimos e quase-anônimos, a voz só se revela no fim; foi assistido até o fim 97% das vezes. Regra: a identidade (quem fala, a marca) chega tarde; o começo é do espectador.
- **Apple "Think Different"**: 60 s em preto e branco, voz baixa, imagens que não ilustram a frase palavra por palavra, logo só no fim. Regra: paleta contida e voz calma dão peso; a marca não aparece antes do último ato.
- **Patagonia**: "interrupção de padrão", fazer o contrário do que se espera de uma marca (consertar em vez de comprar). Regra: a imagem mostra o contrário do óbvio pelo menos uma vez.
- **Narração em contraponto**: narração que repete o que a imagem já mostra deixa a cena menos interessante; a boa narração age contra ou ao lado da imagem.
- **Música**: cortar a música logo antes do momento principal aumenta o impacto; a trilha não pode chegar ao pico antes da frase-chave nem antes da marca. Redes pedem ritmo mais apertado que TV.
- **Leitura**: no máximo ~12 a 15 caracteres por segundo no celular; frase curta fica no mínimo 0,8 a 1,2 s na tela; 1 a 3 palavras de destaque por batida.
- **Reels**: 45% saem nos 3 primeiros segundos; troca visual a cada 1,5 a 3 s; acima de 45 s a retenção despenca, então manifesto de Reels fecha antes de ~45 s.
- **Luz**: contraluz e silhueta são o atalho visual de drama; nascer do sol é o sinal universal de começo; a virada de frio para quente no grade conta a mudança sem palavra.

## 2. Estrutura em atos (alvo 40 s; escale proporcionalmente de 30 a 45 s)

| ato | tempo (40 s) | % | função | planos | ritmo de corte | câmera dominante |
|---|---|---|---|---|---|---|
| 0. Gancho/capa | 0 a 2,5 s | 6% | quadro 0 já é capa: pessoa grande, frase visível, luz fria | 1 | 1 plano | movimento mais forte do vídeo, leve (`crash-zoom-in` x0,6 ou `super-dolly-in`) |
| 1. Tensão (queda) | 2,5 a 14 s | 29% | o espectador se reconhece: rotina, repetição, cansaço. Nada de produto | 4 a 5 | 2,0 a 2,8 s, constante (peso) | `handheld` x0,5, `dolly-out`, `tilt-down`, `snorricam` leve |
| 2. Respiro | 14 a 15 s | 2,5% | silêncio de 0,6 a 1,0 s, quadro quase escuro, só um elemento | 1 | 1 plano | `static` + `deriva` |
| 3. Virada | 15 a 21 s | 15% | a frase-chave sozinha, depois a luz muda (nascer do sol, rim light vira laranja) | 2 | plano longo, 3 a 3,5 s | `dolly-in` lento, `rack-focus`, `dolly-zoom-in` |
| 4. Subida | 21 a 30 s | 22% | o que muda: a marca entra aqui, como ato e não como lista de recursos | 4 a 5 | acelera: 2,2 s, 1,8 s, 1,5 s, inserts de 0,5 s | `truck-right`, `crane-up`, `hero-cam`, `action-run` |
| 5. Convite (rally) | 30 a 36,5 s | 16% | 2 frases paralelas, imagem do contrário do óbvio, multidão vira o indivíduo | 2 | 3 s cada (o pico respira) | `arc`, `aerial-pullback` |
| 6. Assinatura | 36,5 a 41 s | 11% | logo + slogan, emenda com o quadro 0 (loop) | 1 | 4 a 4,5 s | pullback que volta ao neutro |

Regras dos atos:
- **Virada entre 35% e 50% do tempo** (no modelo, 15 s de 41 s = 37%). Antes de 30% não dá tempo de doer; depois de 55% sobra pouco para a subida.
- **Marca (nome, logo, tela) só depois da virada.** No máximo 1 plano de produto (tela do app em `data-tela`, até 2,5 s) e ele vem na subida, nunca na tensão.
- **Curva de corte em U invertido de velocidade**: lento e regular na tensão, parado no respiro, acelerando na subida, respirando de novo no convite. Nunca o mesmo ritmo do começo ao fim.
- Total de planos: 14 a 18 em 40 s (média 2,3 s). Mais que 22 vira clipe de academia; menos que 10 vira slideshow.

## 3. Texto na tela e narração

### Texto (tipografia cinética de manifesto)
- **2 a 6 palavras por cartela, 1 ou 2 linhas.** Nunca 7. Se precisar de mais, são duas cartelas.
- **Minúsculas**, Sora 700, 86 px (legenda do kit), centro entre 0,55 e 0,75 da altura; frase-chave e slogan podem ir maiores (110 a 140 px) e centralizados, porque estão sozinhos no quadro.
- **Entrada palavra por palavra**: 0,16 a 0,22 s por palavra (fade + subida de 12 px em `outCubic`), a frase inteira fica parada pelo menos **0,7 s** depois da última palavra, e o tempo total na tela respeita **≤ 13 caracteres por segundo** (frase de 26 caracteres = 2 s no mínimo).
- **Uma palavra laranja por cartela**, no máximo; no ato de tensão, nenhuma (o laranja nasce na virada, junto com a luz).
- **Estrutura paralela** é o motor: 3 frases com o mesmo molde na tensão ("mais uma hora. / mais um resumo. / mais um vídeo no 2x."), 2 com o mesmo molde no convite. A terceira da série quebra o molde ou fica mais longa.
- **Pausa antes da frase-chave**: o texto anterior some, 0,6 a 1,0 s sem texto nenhum, e a frase-chave entra sozinha (sem palavra por palavra: inteira, em fade de 0,3 s, ou palavra por palavra lento a 0,35 s por palavra). Depois dela, mais 0,4 s sem nada.
- Total de palavras na tela: **40 a 65 em 40 s**. Acima de 70 é texto demais.
- Texto sai **antes** da janela da transição (regra do kit: dissolve de 0,3 s começa 0,15 s antes do corte).
- Proibido: pergunta retórica ("e se...?", "você já...?"), frase de coach ("acredite", "você é capaz", "saia da zona de conforto", "o sucesso é"), ponto de exclamação, emoji, hashtag, travessão.

### Narração (quando houver; quem gera é o agente `roteirista`)
- **1,4 a 1,9 palavras por segundo** (mais lento que tutorial): 55 a 75 palavras em 40 s. Pausas marcadas no roteiro com `...` (curta, 0,3 s) e `[pausa 0,8]`.
- Voz baixa e próxima, sem tom de locutor de anúncio. Para o ElevenLabs: Stability um pouco maior que o padrão (0,55 a 0,60) para não dramatizar.
- **Texto na tela ≠ cópia da fala.** Com narração, a cartela mostra 2 a 3 palavras-chave da frase falada (subconjunto, nunca outra frase), para quem assiste sem som ainda entender; fala de até 4 palavras pode ser igual à cartela. Sem narração, a cartela carrega a frase inteira.
- **Contraponto**: a fala diz o sentimento, a imagem mostra outra coisa que o sugere. Pelo menos 1 plano em 3 sem relação literal com a frase.
- A frase-chave tem que sobreviver sozinha (sem a imagem e sem o resto do roteiro). Teste: escreva só ela num papel; se precisar de explicação, reescreva.
- Silêncio da voz no respiro e nos últimos 1,5 s (a marca fecha sem fala por cima da música, ou com uma palavra só: o nome).

## 4. Gramática visual com pessoas em código

### Princípios
- **Pessoas anônimas.** Rosto nunca detalhado: silhueta, de costas, perfil em contraluz, closes de mãos, olhos de perfil e pés. Quanto menos rosto, mais o espectador se põe no lugar. Expressão facial desenhada em código vira caricatura.
- **Um protagonista com silhueta reconhecível** (ex.: coque alto + mochila de uma alça + moletom com capuz baixado). Ele aparece em pelo menos 5 planos e é o único que muda de pose ao longo do filme. Mesma proporção, mesmo perfil, mesmo objeto (mochila), como o "Element" do Higgsfield.
- **Multidão = contexto; indivíduo = emoção.** Multidão na tensão (todos iguais, todos na mesma pose: o problema é coletivo); indivíduo na virada (a mudança é pessoal); multidão de novo no convite, agora variada e em poses diferentes (o convite é coletivo). Multidão com 3 profundidades (`data-z` 0,4 / 0,7 / 1) e desfoque crescente para trás; variar altura, cabelo (crespo, trançado, liso, raspado), boné, óculos, mochila; nunca clones lado a lado.
- **Proporção adulta**: 7 a 7,5 cabeças de altura, ombros mais largos que a cabeça, mãos com dedos. Cabeça grande, olho de desenho e cor primária saturada = ilustração infantil (reprovado).
- **Movimento só com intenção.** Pessoa parada respira (peito e ombro ±1 a 1,5%, 0,25 Hz) e só. Gesto (virar a cabeça, erguer a mão) acontece uma vez por plano, motivado pela frase ou pelo corte. Nada de balanço em loop, braço oscilando, "dancinha" de idle.
- **Sentido de tela**: progresso anda da esquerda para a direita no vídeo todo. Na tensão, quem anda vai para a esquerda ou fica parado; da virada em diante, para a direita.
- **Luz de um lado só, contraluz sempre.** Fonte atrás do sujeito, levemente acima e à direita (o sol nasce à direita, mesmo lado para onde o progresso anda). Rim light de 2 a 4 px de design na borda voltada para a luz.

### Estilo por momento (um estilo dominante por filme)
| estilo | quando | por quê |
|---|---|---|
| `silhueta` (rim light) | **dominante, 70 a 100% dos planos** | anônimo por definição, funciona em contraluz, o rim light carrega a virada de cor (azul frio para laranja) |
| `traco` | secundário, só com motivo: o que é escrito, pensado ou lembrado (mão escrevendo cujo traço vira a pessoa; a semana se desenhando) | liga a pessoa ao estudo (caneta, caderno); nunca mais de 25% dos planos |
| `ilustracao` (chapada) | só se o filme inteiro for nesse estilo (versão clara, de dia) ou num plano de memória com moldura | misturar chapado com silhueta no mesmo trecho parece dois filmes |

Nunca três estilos no mesmo manifesto. Troca de estilo só por transição motivada (match cut da forma, `through-object`), nunca por corte seco.

### Pose x momento emocional x câmera
| momento | pose (`edin-pessoas`) | enquadramento | câmera (`higgsfield-camera.md`) | luz e cor |
|---|---|---|---|---|
| gancho / rotina | `sentado-estudando` | médio de perfil, mesa na frente (k 1,5 desfocada) | `crash-zoom-in` x0,6 ou `super-dolly-in` + `handheld` x0,5 | luz fria de tela vindo de baixo, fundo índigo quase preto |
| repetição, cansaço | `cabeca-baixa` | médio de trás ou de perfil | `dolly-out` lento ou deriva para baixo (`ty` +2% em 3 s) | frio, vinheta mais forte |
| distração | `olhando-celular` | close do celular iluminando o perfil | `rack-focus` do celular para o rosto em silhueta | a única luz é a tela (azul) |
| tempo passando | `close-pes` embaixo da mesa ou `andando` para a esquerda | detalhe | `hyperlapse` ou `static` + janela ao fundo trocando luzes | frio |
| o problema é de todos | multidão `cabeca-baixa` / `sentado-estudando`, todos iguais | aberto, vista frontal ou `overhead` | `crane-up` lento ou `aerial-pullback` curto | frio, sem nenhum laranja |
| respiro | protagonista `em-pe` ou só o ponto de luz | aberto, pessoa pequena (≤ 20% da altura) | `static` + `deriva` | quase escuro, um ponto laranja |
| percepção (frase-chave) | `close-olho-perfil` | detalhe do olho em silhueta, reflexo laranja na íris | `dolly-in` muito lento (S 1 a 1,05) ou `dolly-zoom-in` | primeiro laranja do filme, pequeno |
| virada | `cabeca-baixa` que ergue para `olhando-horizonte` (transição de pose no mesmo plano) | médio de costas, horizonte no terço de baixo | `dolly-in` + `rack-focus` para o horizonte | sol nascendo atrás: rim light passa de azul para laranja em 1,5 s |
| decisão | `close-maos`: mão fecha o caderno, ou mão escrevendo que para | detalhe | `static` com `deriva` | quente começando |
| movimento | `andando` para a direita, depois `correndo` | médio lateral | `truck-right` com parallax (frente passa desfocada) | quente, céu clareando |
| esforço que agora rende | `subindo` (escada, ladeira) | contra-plongée, céu ocupando 60% | `hero-cam` ou `crane-up` | contraluz forte |
| convite (contrário do óbvio) | grupo `em-pe` / `bracos-abertos` ao ar livre, ninguém estudando | aberto | `arc-right` ou `aerial-pullback` | dourado |
| apontar caminho | `apontando` (um só, para a direita) | médio | `truck-right` curto | quente |
| comemoração | `comemorando` ou `punho-erguido` | **no máximo 1 plano no filme, até 1,2 s, e longe** (pessoa ≤ 30% da altura) | `static` | quente |

## 5. Receitas de transição de manifesto

Todas com os tipos do kit (`match-cut`, `zoom-through`, `travessia`, `whip-pan`, `dissolve`). Regras do `higgsfield-camera.md` valem: forma comum no mesmo centro ±2% e escala ±10%, velocidade igual ±20% nos dois lados do corte, texto da cena A some 0,2 s antes.

1. **Silhueta para silhueta (match cut de contorno)**: o protagonista na mesma pose e no mesmo lugar do quadro em dois tempos (noite `sentado-estudando` para manhã `sentado-estudando`, ou `cabeca-baixa` para `em-pe`). `data-match="protagonista"` no grupo da pessoa nas duas cenas; `match-cut` com `duracao: 0` (corte puro) se o contorno casa, ou `dissolve: 0.17` se a luz muda muito. Só o fundo e a cor do rim light trocam. Confira sobrepondo os dois quadros com 50% de opacidade: o contorno não pode "pular".
2. **Multidão para um**: plano aberto com a multidão igual; `dolly-in` + `foco` com `focoPara` no protagonista (que está na fileira do meio, `data-z` 0,7); a multidão desfoca até 10 px e escurece 30% em 1,5 s, o protagonista é o único que recebe rim light laranja. Corte no movimento para o médio dele, mesma velocidade de escala.
3. **Um para multidão (o inverso, no convite)**: médio do protagonista `bracos-abertos`; `aerial-pullback` revela que ao redor há outras pessoas, cada uma numa pose diferente (`em-pe`, `apontando`, `olhando-horizonte`). Recomenda-se ao fim do filme.
4. **Mão escrevendo para mão erguida**: `close-maos` escrevendo (caneta da esquerda para a direita), a mão para, solta a caneta e sobe; `match-cut` na mão (`data-match="mao"`) para a mão erguida contra o céu, mesmo centro, mesma escala, rotação de até 15°. Variante: o traço da caneta continua e vira o horizonte (troca de `traco` para `silhueta` pela forma da linha).
5. **Olho para sol**: `close-olho-perfil` com o reflexo laranja na íris; `zoom-through` com `alvo` no reflexo e `raio` dele; a cena seguinte (nascer do sol, protagonista de costas) nasce de dentro. Curva cúbica, véu escuro saindo em 0,5 s (lição do demo).
6. **Tela do celular para janela**: `olhando-celular` em close; `through-object` pela tela; do outro lado, a janela com o céu clareando. É a troca da luz azul (tela) pela luz do dia.
7. **Pés para pés**: `close-pes` parados embaixo da mesa (tensão) e `close-pes` andando na calçada (subida): match cut no pé, mesmo centro. Ritmo: o primeiro passo cai na batida.
8. **Andando para correndo**: dois planos `truck-right` seguidos com velocidade de tela igual no corte e a do segundo crescendo depois; corte no meio do passo (pé no ar).
9. **Cabeça baixa para cabeça erguida sem corte**: transição de pose no próprio rig (interpolação de 0,8 a 1,2 s em `inOutCubic`), com `dolly-in` lento; é o momento mais forte do filme, então não corte: deixe a pessoa mudar na frente do espectador.

Não use em manifesto: `whip-pan` em sequência (vira clipe de esporte), `crash-zoom` fora do gancho, `push`, `yoyo-zoom`, `fisheye`, `wiggle`.

## 6. Cor, luz e som

- **Grade em duas metades**: até a virada, `grade: { luzes: '#8ea2ff', sombras: '#0f0c2e' }`, fundo índigo quase preto (#0f0c2e a #1d2470), rim light azul (#8ea2ff); da virada em diante, luzes laranja (#ffb68a / #F97316 no rim), sombras índigo (#4F46E5 a #7C3AED). A troca acontece num plano só, com a luz subindo em 1,5 a 2 s, nunca por corte. Camadas globais (grão 4 a 6%, vinheta) constantes; só a cor muda.
- **O laranja é o fio da história**: não aparece na tensão (ou aparece como um ponto pequeno e longe, ≤ 1% do quadro, que o olho mal registra), nasce na virada e domina o fim. A palavra laranja das cartelas segue a mesma regra.
- **Sol**: disco com halo pelo `EdinVideo.halo()` (≤ 108 px, opacidade ≤ 0,25), horizonte no terço de baixo, sobe 3 a 6% da altura durante a subida. Nada de clarão: o céu clareia em degradê, salto de brilho médio < 10 por quadro.
- **Música** (se Rafael for escolher no Instagram, entregue com AAC silencioso estéreo e marque as batidas no roteiro):
  - Tensão: pulso grave e pad frio, sem melodia, volume -6 dB abaixo do pico do filme.
  - Respiro: **silêncio total de 0,6 a 1,0 s** (só ruído de sala ou uma respiração). É o corte mais importante do filme.
  - Virada: entra uma nota única (piano ou sintetizador limpo) na frase-chave; batida entra no início da subida.
  - Subida: crescendo, cortes na batida a partir do 2º plano da subida.
  - Pico: na 2ª frase do convite (85 a 90% do filme), nunca antes da frase-chave nem da marca.
  - Assinatura: a música resolve numa nota com reverb de 1,5 a 2 s; o loop recomeça no pulso grave.
- Voz em -14 LUFS, pico -1,5 dBTP; música 10 a 14 dB abaixo da voz.

## 7. Checklist do manifesto

- [ ] Duração 30 a 45 s (alvo 38 a 42), 14 a 18 planos, quadro 0 é capa com pessoa grande e frase visível.
- [ ] Atos com os tempos da seção 2; virada entre 35% e 50%; marca só depois da virada; no máximo 1 plano de produto.
- [ ] Silêncio de 0,6 a 1,0 s antes da frase-chave (música e texto); a frase-chave entra sozinha.
- [ ] Cartelas de 2 a 6 palavras, ≤ 13 caracteres/s, 40 a 65 palavras no total, minúsculas, uma palavra laranja no máximo (nenhuma na tensão).
- [ ] Pelo menos 1 série paralela de 3 na tensão e 1 de 2 no convite.
- [ ] Pelo menos 1 plano em 3 sugere em vez de ilustrar; pelo menos 1 imagem do contrário do óbvio (ex.: "estude melhor" sobre gente que não está estudando).
- [ ] Rostos sem detalhe; protagonista reconhecível pela silhueta em todos os planos dele; multidão variada, sem clones.
- [ ] Um estilo dominante (`silhueta`), no máximo um secundário com motivo escrito na ficha.
- [ ] Toda pessoa parada só respira; cada gesto tem motivo; `comemorando`/`punho-erguido` no máximo 1 vez, longe e curto.
- [ ] Sentido de tela: progresso para a direita da virada em diante; contraluz sempre do mesmo lado.
- [ ] Grade fria até a virada, quente depois, troca dentro de um plano; sem clarão.
- [ ] Ritmo: tensão regular (2 a 2,8 s), respiro parado, subida acelerando, convite respirando.
- [ ] Narração (se houver) 1,4 a 1,9 palavras/s, sem repetir a cartela, sem voz no respiro.
- [ ] Final emenda com o quadro 0 (loop) e o checklist do `html-video/LEIAME.md` passou.
- [ ] Agente `critico-de-edicao` com o HTML e o vídeo final.

## 8. O que evitar

- **Clichês visuais**: escalar montanha com bandeira, linha de chegada, lâmpada acendendo, foguete, pódio, câmera girando em volta de alguém de braços abertos no topo, pessoa pulando em câmera lenta contra o pôr do sol, mão estendida puxando outra. Se a imagem aparece em banco de imagem com a palavra "sucesso", não use.
- **Clichês de texto**: "acredite", "você é capaz", "não desista", "o impossível", "a jornada", "seja a sua melhor versão", "e se eu te dissesse", qualquer pergunta retórica, "nós acreditamos que" no começo.
- **Pessoa "dançando" sem motivo**: balanço de idle em loop, gesto repetido, todo mundo se mexendo ao mesmo tempo na multidão. Na multidão, no máximo 1 pessoa em 5 se mexe por vez, e só respirando.
- **Ilustração infantil**: cabeça grande, olho de desenho, sorriso desenhado, cores primárias saturadas, contorno grosso e arredondado, fundo com nuvem de desenho.
- **Texto demais**: frase de 7 palavras ou mais, 3 linhas, texto em todo plano (deixe 2 a 3 planos sem texto: o respiro, a virada da luz, um plano da subida).
- **Produto cedo**: logo, nome ou tela antes da virada; lista de recursos ("com IA, com plano, com relatório"); manifesto que vira tutorial.
- **Música no pico cedo** ou sem o silêncio antes da frase-chave.
- **Tudo literal**: cartela "estudar" sobre gente estudando, "correr" sobre gente correndo, do começo ao fim.
- Três estilos de pessoa no mesmo filme; troca de estilo por corte seco.
- Ritmo constante do começo ao fim; mais de 1 movimento violento a cada 4 planos.

## 9. Fontes

- Formas de manifesto (U, S, J, Z, W, E; virada no meio, rally em estrutura paralela): https://brandmanifestos-bullet.pages.dev/how-to-write-a-manifesto ; https://brandmanifestos-bullet.pages.dev/u-shape-deep-dive ; https://brandmanifestos-bullet.pages.dev/s-shape-deep-dive
- Arcos emocionais em vídeo de marca: https://editframe.com/skills/brand-video-generator/emotional-arcs
- Nike "You Can't Stop Us" (4.000 clipes, 72 escolhidos, 36 pares, match no olho): https://www.adweek.com/creativity/the-hardest-commercial-i-have-ever-edited-how-nike-created-its-split-screen-masterpiece/ ; https://www.adgully.com/what-makes-nike-s-you-can-t-stop-us-an-editing-marvel-95285.html ; https://lbbonline.com/news/work-of-the-week-310720
- Nike "Dream Crazy" (voz revelada no fim, 97% assistido até o fim): https://tvrev.com/digging-deeper-into-nikes-crazy-advertising/ ; https://reelchicago.com/article/kaepernick-just-do-it-nike-commercial/
- Apple "Think Different" (60 s, preto e branco, voz baixa): https://www.creativereview.co.uk/apple-think-different-slogan/ ; https://brandingstrategyinsider.com/the-real-story-of-apples-think-different-campaign/
- Patagonia e interrupção de padrão: https://conversion-rate-experts.com/beware-of-any-endeavor-copywriting-friday/ ; https://www.skyword.com/contentstandard/marketing/the-documentarians-how-patagonias-video-content-is-redefining-brand-storytelling/
- Campanhas brasileiras (Itaú "Feito de Futuro", O Boticário): https://marcaspelomundo.com.br/anunciantes/itau-unibanco-apresenta-novo-filme-para-a-acao-feito-de-futuro-estrelado-por-jorge-ben-jor/ ; https://www.meioemensagem.com.br/videos/mercados-em-foco/esforco-para-fugir-dos-cliches
- Narração em contraponto: https://blog.finaldraft.com/when-narration-works ; https://fiveable.me/screenwriting-ii/key-terms/voice-over
- Leitura de texto cinético (12 a 15 caracteres/s, 0,8 a 1,2 s mínimo): https://cursa.app/en/page/caption-systems-and-kinetic-text-for-clarity ; https://oakgen.ai/blog/kinetic-typography-without-after-effects
- Música, silêncio antes da revelação, pico depois da marca: https://blog.biblo.tv/how-editors-use-music-to-build-tempo-across-tvc-short-film-and-long-film-formats/ ; https://www.foximusic.com/blog/?p=603 ; https://atomicamusic.com/best-production-music-for-tv-commercials-vs-social-ads
- Reels (duração, 3 primeiros segundos, troca a cada 1,5 a 3 s): https://www.opus.pro/blog/ideal-instagram-reels-length ; https://klap.app/blog/how-long-should-reels-be
- Contraluz, silhueta e nascer do sol: https://cined.com/the-power-of-backlight-in-film-what-it-reveals-and-conceals ; https://www.studiobinder.com/blog/what-is-backlight/
