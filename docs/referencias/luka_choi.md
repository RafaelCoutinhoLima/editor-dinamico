# Referência: vídeos curtos do Luka Choi (@lukachoi_)

Análise feita em 08/11/2026.

## Quem é e de onde vieram os vídeos

- **Luka Choi** é um jovem fundador e criador de conteúdo brasileiro sobre empreendedorismo, startups e "founder led growth". Aparece em eventos do G4 (G4 Valley), na Link School of Business e em collabs com outros criadores (@ecleticballs__, João Curry).
- O perfil dele é **@lukachoi_** (com sublinhado). O próprio vídeo 1 mostra o card do perfil "lukachoi_ / Luka Choi", com selo de verificado. O @lukachoi do Instagram, **sem** sublinhado, é outra pessoa: 287 seguidores, bio em chinês e reels de 2019.
- **YouTube:** não tem canal. `ytsearch10:Luka Choi` não achou nada dele e `@lukachoi/shorts` não existe.
- **TikTok:** `@lukachoi_` abriu e foi a fonte de tudo (18 vídeos listados). O `@lukachoi` sem sublinhado é uma conta chinesa sem relação com ele.
- **Instagram:** não abriu. O yt-dlp não decifrou os cookies do Chrome (faltava o `secretstorage`), o extrator `instagram:user` está marcado como quebrado e a URL `/reels/` não é aceita. Pelas legendas ("Segue aqui e na rede vizinha", "Da rede vizinha pra cá"), os vídeos do TikTok são os mesmos do Instagram.
- **Resolução:** o TikTok entrega no máximo **720x1280**. As medidas abaixo foram feitas nessa resolução e multiplicadas por 1,5 para 1080x1920.
- **Como medi:** rosto e olhos pelo YuNet do próprio edin (`assets/models/face_detection_yunet_2023mar.onnx`), uma amostra a cada 3 quadros. A caixa do YuNet é justa e não pega o cabelo: o rosto com cabelo fica 25 a 30% maior que o número da tabela. Legendas e cores medidas por pixel. Cortes contados com `select='gt(scene,0.3)'` e depois com os saltos de escala do rosto, porque o detector de cena não vê jump cut quando o fundo é o mesmo.

### Folhas de contato salvas aqui
- `luka_folha_motion_v1.jpg`: vídeo 1 inteiro, um quadro a cada 1,5 s. É o formato "motion design por cima".
- `luka_legendas_grade.jpg`: 6 quadros com uma grade amarela a cada 5% da altura. Os 5 primeiros são do vídeo 2 e o último é do vídeo 1. Mostram a legenda pequena no peito, a palavra grande, o "MAS" vermelho atrás da cabeça e a palavra preta atrás da cabeça.

## Os dois formatos dele

| Formato | Vídeos | Resumo |
|---|---|---|
| A. Cabeça falante com motion design | 1, 2 (e 3, em versão mais leve) | Ele fala para a lente num plano médio com muito espaço acima da cabeça. Esse espaço recebe palavras gigantes e imagens **atrás da cabeça** (recorte da pessoa). A legenda é pequena e em minúsculas, e só as palavras-chave crescem. A cada 1 a 4 s acontece um evento gráfico. |
| B. Vlog e bastidores | 5, 6, 7 (resumidos no fim) | Câmera na mão em eventos e na faculdade, legenda pequena e branca ou nenhuma, cortes de montagem. Não é falando para a câmera. |

O vídeo 4 é o grau zero do formato A: um plano fixo sem legenda queimada, só com dois cards. Ajuda a ver o que a edição acrescenta.

## Vídeo a vídeo

### Vídeo 1: "Segue aqui e na rede vizinha" (29,9 s, 62,2 mil views, o mais visto)
URL: https://www.tiktok.com/@lukachoi_/video/7694747402799959309

| Item | Medida (em 1080x1920) |
|---|---|
| Enquadramento | Sentado numa cadeira gamer, parede creme lisa, plano do peito para cima. Linha dos olhos a **47,6%** (y ≈ 915). Rosto com **30%** da largura (≈ 325 px, só a caixa do rosto). Cabeça inteira no quadro, com o topo do cabelo a ~33%: sobram **~630 px de headroom**, reservados para os gráficos. Rosto centralizado (cx 51%). |
| Legenda | **Preta**, em minúsculas, fonte neo-grotesca semibold (tipo Inter, SF Pro ou Helvetica Now). Fica **no alto**, com centro entre 12 e 17% (y ≈ 230 a 330), acima da cabeça, porque o fundo é limpo. A pequena tem ~42 px, de 1 a 4 palavras. Sem contorno, sem sombra e sem caixa. A palavra-chave vira gigante: "impossível" preta com ~190 px atrás da cabeça, "IA" branca dentro de um bloco azul de ~330 x 330 px atrás da cabeça, "editar" com o fundo destacado em azul. |
| Elementos gráficos | Motivo de "UI": colchetes `← { legenda } →`, alças de seleção azuis nos cantos das palavras e traços de ênfase. Cartões em tela cheia: "faturamento em R$ 88.750" (4,3 a 6,0 s), card do perfil do Instagram na metade de baixo (6,1 a 7,2 s), gráfico de barras em fundo escuro "explodindo ↑" (7,3 a 8,6 s), print de um editor riscado com um X azul (10,4 a 12 s), grafo "criador" com rostos (12 a 14,3 s), barra de prompt digitando "o que você quer mostra" (16,5 a 17,7 s), tela azul cheia "{ a ideia sempre foi sua }" (17,7 a 18,8 s), colagem de fotos "pra galera" (20,9 a 21,3 s), carrossel de celulares em fundo escuro "muitas formas" (21,3 a 23 s). Cada cartão dura de **0,4 a 2 s**. Cerca de **50% do tempo é gráfico em tela cheia** e 50% é ele. |
| Ritmo | 10 cortes de cena em 30 s (3,3 a cada 10 s). Contando as entradas de gráfico em cima dele: **~5 mudanças a cada 10 s**. Sem punch-in no rosto: a variação vem dos cartões. |
| Cor e acabamento | Claro e limpo: luma média 149, saturação baixa (12,8). Paleta de marca: creme da parede **#EEDBBC**, azul **#2B69FA**, preto e azul-marinho da camiseta. Áudio alto: **-10,4 LUFS**. |
| Gancho (0 a 3 s) | Metalinguagem com prova. 0 s: "esse vídeo foi editado" com as palavras dos dois lados do rosto e as alças de seleção. 1,5 s: "cada legenda" com o "IA" gigante atrás da cabeça. 3 s: "quer ver?". 4,3 s: o número R$ 88.750 em tela cheia. São 3 eventos visuais em 3 s. |
| Final | Os últimos 4,8 s (25,1 a 29,9 s) mostram um mockup de celular com o perfil dele, a pergunta "{ Por que não você? }" no alto e um botão azul "me segue para mais →" embaixo. O CTA é desenhado, não falado. |

### Vídeo 2: "Conteúdo 100% educativo, não utilizem!!" (48,5 s)
URL: https://www.tiktok.com/@lukachoi_/video/7684005916177452302

| Item | Medida (em 1080x1920) |
|---|---|
| Enquadramento | Em pé num auditório, plano médio da cintura para cima. Linha dos olhos a **40,8%** (39 a 42%, y ≈ 785). Rosto com **20%** da largura (18 a 24%, ≈ 215 px). Cabeça inteira, com o topo do cabelo a ~32%: sobram **~610 px de headroom**, ocupados por palavras e imagens atrás dele. Centralizado. |
| Legenda | **Branca levemente acinzentada** (os pixels medem ~#D2D2D2, provavelmente branco com 85 a 90% de opacidade), em minúsculas, sans geométrica semibold (tipo Gilroy ou Satoshi). Centro a **62 a 64%** da altura (y ≈ 1195 a 1225), **no peito**. Bloco pequeno de **~42 px** (x-height ~30 px), de 1 a 3 palavras, sem contorno e sem caixa, com sombra quase imperceptível. Palavra de ênfase empilhada **embaixo** e maior, com **~95 a 100 px** ("provavelmente", "por lei", "falar", "2"), e as pequenas em cima ("não é permitido", "eu vou"). Palavra emocional em **vermelho**: "dor" em vermelho no meio da frase, e "empreendedorismo" e "cautela" em letra manuscrita vermelha por ~1 s. Sem palavra ativa em karaokê: cada grupo aparece inteiro. |
| Elementos gráficos | Palavras gigantes **vermelhas condensadas em caixa alta** (tipo Anton ou Bebas), vermelho **#B80200**, **atrás da cabeça**: "NÃO" com brilho desfocado (0,75 s, ~0,4 s), "MAS" com ~475 px de altura entre 15 e 40% da altura (7,4 a 8,6 s), "1º" e "2º" com brilho vermelho (~0,5 s cada). Imagens de filme **atrás dele** (fundo trocado com recorte da pessoa): ficha policial do Scarface (1,25 a 2,2 s e 40,5 s), meme do DiCaprio apontando (5,6 a 6,2 s). Imagens em tela cheia, escuras e puxadas para o vermelho, com a legenda continuando por cima: Poderoso Chefão "é o conceito de take door" (9,1 a 10,6 s) e o mafioso "é o mafia offer" (22,5 s, ~1,5 s). |
| Ritmo | 1 corte de cena (>0,3), mas **~22 jump cuts** em 48 s, achados pelos saltos de escala do rosto: **~4,5 cortes a cada 10 s**. A cada corte o zoom alterna entre **100% e ~115 a 120%** (rosto de 18% para 22 a 24% da largura), sem animação: é punch-in seco. Os eventos gráficos se concentram nos primeiros 11 s (~8 eventos) e voltam aos 21 a 23 s e aos 40 s. O meio (24 a 40 s) fica só na legenda e no punch-in. |
| Cor e acabamento | Escuro e cinematográfico: luma média **81**, branco máximo em 213 (altas comprimidas), preto mínimo em 10 (pretos levantados), quente, saturação 13,7. Áudio a **-11,7 LUFS**. |
| Gancho (0 a 3 s) | Pergunta polêmica com 4 eventos em 3 s. 0 s: "é ético?". 0,75 s: "NÃO" vermelho atrás da cabeça. 1,25 s: Scarface atrás dele, "dá cadeia? / provavelmente". 2,5 s: "eu vou / falar" com a mão para cima. 3 s: "dos 2 conceitos". |
| Final | CTA falado ("então se vocês quiserem saber aplicar isso por conta de vocês...") com legenda simples e **sem card**. Corta seco. |

### Vídeo 3: "Segredo de viralizar com o @ecleticballs__" (61,8 s, collab)
URL: https://www.tiktok.com/@lukachoi_/video/7681027434984000782

| Item | Medida (em 1080x1920) |
|---|---|
| Enquadramento | Dois em pé, **corpo inteiro** na frente de uma TV azul. Olhos a **42,6%**, rosto com **12%** da largura. Muito headroom, onde entram as palavras grandes. Na segunda parte (45 a 62 s), selfie com câmera na mão em preto e branco (rosto de 30 a 60%). |
| Legenda | Branca, em minúsculas, a mesma fonte do vídeo 2, ~36 a 42 px, centro a **~74%** (na cintura, porque o plano é aberto). De 1 a 3 palavras. Ênfase gigante no alto: "técnica secreta" a ~24% (acima das cabeças) e "7 anos" com brilho a ~60%. A fala do convidado vem em letra manuscrita branca ("Eu tô na Laaaaras") e uma palavra sai em vermelho ("estourar"). |
| Elementos gráficos | No gancho, um círculo branco desenhado à mão em volta do convidado caído (0,8 a 2,9 s). Card do perfil @ecleticballs no alto à esquerda (~9 a 11 s) e card @fecler__ (55 s). Imagem em **preto e branco na punchline** ("7 anos e gravar 1 mil vídeos", 31 a 34 s). |
| Ritmo | 2 cortes de cena (6,0 e 45,6 s) mais ~13 saltos de zoom e cortes: **~2,4 por 10 s**. |
| Cor e acabamento | Luma 103, saturação 17, quente. Áudio a **-9,8 LUFS**. |
| Gancho (0 a 3 s) | Ele de braços abertos, o convidado caído e circulado no canto, e "hoje eu trouxe um cara muito legal aqui pra Link". Contraste de comédia. |
| Final | Selfie P&B do convidado se afastando, "mas é isso irmão". Sem card. |

### Vídeo 4: "Da rede vizinha pra cá" (87,8 s, plano fixo, grau zero)
URL: https://www.tiktok.com/@lukachoi_/video/7691144273659530509

| Item | Medida (em 1080x1920) |
|---|---|
| Enquadramento | Corpo inteiro na frente de um quadro branco, câmera fixa. Olhos a **42,6%**, rosto com **12%**, deslocado para a esquerda (cx 34%). |
| Legenda | **Nenhuma queimada.** |
| Elementos gráficos | Print do painel de insights do Instagram no alto à esquerda (0 a 2,5 s): "945,6 mil visualizações, 4,1 mil novos seguidores". Foto de b-roll no alto (18 a 20,5 s). |
| Ritmo | ~8 mudanças em 88 s (**0,9 a cada 10 s**). |
| Cor e acabamento | Claro (luma 148), saturação 7, sem grade. Áudio cru a **-18,8 LUFS**. |
| Gancho e final | O gancho é a prova numérica no card. O final corta seco. |

### Vlogs (sem fala para a câmera, só para registro)

| Vídeo | URL | Notas |
|---|---|---|
| 5. Evento G4 (37,9 s) | https://www.tiktok.com/@lukachoi_/video/7692044412276313357 | Uma tomada contínua com a câmera na mão. Legenda branca pequena (~35 px) a ~78%, 1 a 4 palavras, sem ênfase. 0 cortes. |
| 6. "1 dia normal na Link School" (59 s) | https://www.tiktok.com/@lukachoi_/video/7678045339030523150 | Vlog em primeira pessoa. Gancho com o card do perfil do João Curry em P&B (0 a 3 s). Título amarelo grande e pesado "1 dia na melhor faculdade de negócios do país", entrando palavra por palavra (3 a 7 s). 18 cortes, **3,1 a cada 10 s**. |
| 7. "Buscando a sorte" (29,7 s) | https://www.tiktok.com/@lukachoi_/video/7702911432798506254 | Montagem de bastidores sem legenda. 26 cortes, **8,7 a cada 10 s**. |

Ficaram de fora por serem horizontais (1280x720): "Um passo pra frente, 2 pra trás" (7683555764312526093, 49,7 mil views, 4,3 cortes a cada 10 s), "Você tem?" (7675492456716111118) e "o NÃO já tenho" (7692445257983724814).

## O padrão Luka (regras para copiar)

1. **Olhos entre 41 e 48% da altura**, não no terço de cima. Com o plano médio, o rosto ocupa 20% da largura em pé e 30% sentado (caixa do YuNet). Sobram **600 a 650 px de headroom** em 1080x1920, e esse espaço é a tela dos gráficos.
2. **A palavra-chave vai atrás da cabeça:** palavra gigante de 190 a 475 px de altura no headroom, com o recorte da pessoa por cima (o "behind the head"). Use **1 a cada 4 a 8 s** e deixe cada uma por **0,4 a 1,2 s**.
3. **Legenda pequena e em minúsculas, ~42 px** (x-height ~30 px), de 1 a 3 palavras por tela, sem contorno, sem caixa e sem karaokê de palavra ativa.
4. **Lugar da legenda:** no **peito, com centro a 62 a 64%**, quando o plano é médio e o fundo tem informação. **No alto, a 12 a 17%**, quando o fundo é uma parede lisa. **A ~74%** no plano de corpo inteiro.
5. **Ênfase por tamanho, não por cor:** a palavra forte entra empilhada embaixo das pequenas com **2,3x o tamanho (~95 a 100 px)**, na mesma fonte e na mesma cor.
6. **Duas fontes no máximo**, mais um acento. Uma sans semibold em minúsculas para a fala e uma condensada pesada em CAIXA ALTA só para as palavras gigantes. Uma manuscrita aparece no máximo 2 vezes por vídeo, para palavras carregadas ou para a fala do convidado.
7. **Uma cor de acento por vídeo:** vermelho **#B80200** no tema "proibido ou máfia", azul **#2B69FA** no tema "tech ou IA". O acento pinta 1 palavra da legenda ("dor") e as palavras gigantes. O resto fica branco (fundo escuro) ou preto (fundo claro).
8. **Jump cut com punch-in seco:** ~4,5 cortes a cada 10 s, alternando o zoom entre **100% e 115 a 120%**, sem animação de zoom.
9. **Gancho com 3 a 4 eventos visuais nos 3 primeiros segundos:** pergunta curta ("é ético?"), palavra gigante, imagem atrás e promessa ("eu vou falar dos 2 conceitos"). Nenhum plano limpo dura mais de ~0,8 s no começo.
10. **Prova logo cedo, até os 5 s:** um número ou print real (R$ 88.750, 945,6 mil views, card de perfil com seguidores) por **1,5 a 2,5 s**.
11. **Referências de cultura pop** (filmes, memes) no lugar de b-roll genérico: atrás dele por **0,6 a 1 s** ou em tela cheia por **1,5 s**, escurecidas e puxadas para a cor do acento, **com a legenda continuando por cima**.
12. **Densidade de gráficos que cai:** ~8 eventos nos primeiros 11 s, depois só legenda e punch-in por **10 a 15 s** seguidos, e um evento de novo antes do final. No formato motion (vídeo 1), até **50% do tempo** pode ser cartão em tela cheia, de 0,4 a 2 s cada.
13. **Preto e branco ou tom vermelho como pontuação:** troque a cor por **2 a 3 s** na punchline ("7 anos", Poderoso Chefão) e volte.
14. **Cor:** fundo escuro e "de cinema", com luma média ~80, altas comprimidas (máx. ~213) e pretos levantados (~10), quente. Ou fundo claro e limpo com luma ~150 e saturação baixa. Nunca saturado. **Áudio a -10 a -12 LUFS.**
15. **Final:** CTA desenhado nos últimos **~4,5 s** (mockup do perfil + pergunta + botão "me segue para mais →") no formato motion. Ou CTA falado com corte seco no formato cabeça falante. Sem tela preta e sem vinheta de fim.
