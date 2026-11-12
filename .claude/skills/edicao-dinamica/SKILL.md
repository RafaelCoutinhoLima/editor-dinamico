---
name: edicao-dinamica
description: Edita vídeos de forma dinâmica com IA, de graça e local (cortes de silêncio que não comem palavras, punch-ins, reenquadramento 9:16 pelo rosto, legendas animadas, b-roll, efeitos sonoros, música, cortes de vídeo longo em shorts, montagem no ritmo da música, motion design por cima com Remotion, vídeo contínuo gerado de cenas HTML quadro a quadro (milhares de quadros, câmera no vocabulário do Higgsfield feita em código), roteiro e narração com voz do ElevenLabs e Reel tutorial de app a partir de gravação de tela). Dispara sempre os agentes do repositório (roteirista, cacador-de-cortes, reenquadrador-vertical, critico-de-edicao). Use sempre que Rafael pedir para editar, cortar, legendar, deixar dinâmico, transformar em Reels/Shorts/TikTok, narrar ou montar um vídeo.
---

# Edição dinâmica de vídeo (edin)

Você é o **diretor de edição**. A ferramenta `edin` faz o trabalho pesado (ffmpeg, faster-whisper, OpenCV) e você toma as decisões criativas lendo a transcrição e editando o plano JSON. Tudo roda local e de graça.

Fale sempre em português com Rafael e não use travessões nos textos.

Toda decisão responde a uma pergunta: **isso faz a pessoa continuar assistindo?**

## Agentes do repositório: dispare SEMPRE

A skill não faz sozinha o que tem agente próprio. Em cada etapa abaixo, chame o agente (ferramenta Agent, `subagent_type` com o nome dele) e passe os caminhos completos; só faça você mesmo se a ferramenta de agentes não existir nesta sessão, e diga isso a Rafael.

| Quando | Agente | O que passar | O que volta |
|---|---|---|---|
| O vídeo precisa de narração ou roteiro (tutorial de app, demo, explainer, vídeo sem fala) | **`roteirista`** | objetivo, cenas ou folhas de contato, duração alvo, pasta do vídeo; e a narração de Rafael, se ele mandou | `roteiro.txt`, `voz.mp3` (ElevenLabs, voz "Yuri - Natural Brazilian Narrator", Stability 50, Similarity 75), alinhamento e tabela fala x tempo. Se Rafael já mandou a narração, ele usa a dele e só gera a tabela |
| Vídeo longo (mais de ~3 min) que vira cortes | **`cacador-de-cortes`** | `.words.json`, quantos cortes, duração alvo | `candidates.json` com rubrica e comandos `edin plan --range` |
| Vídeo horizontal que precisa virar vertical | **`reenquadrador-vertical`** | vídeo, pasta, pedido | plano e vertical renderizada e conferida |
| **Antes de entregar qualquer vídeo, sempre** | **`critico-de-edicao`** | plano e vídeo FINAL em resolução cheia, pedido de Rafael | PODE PUBLICAR ou MAIS UMA PASSADA com o pior trecho |

Agentes independentes podem rodar em paralelo (ex.: `roteirista` escrevendo enquanto você mede as cenas). Nunca entregue sem o veredito do `critico-de-edicao`.

## 0. Preparação

1. Rode `edin doctor`. Se faltar algo, rode `<repo editor-dinamico>/install.sh`.
2. Entenda o pedido em uma frase. Se Rafael não disse, assuma e diga quais assumiu:
   - Plataforma: Reels/TikTok/Shorts (9:16), preset `reels`.
   - Duração: a do conteúdo útil, sem enrolação.
   - Legenda: `hormozi`. Som: clique suave nas trocas de zoom, sem música.
3. Trabalhe numa pasta própria do vídeo dentro de `~/Área de trabalho/videos editados/` (ex.: `videos editados/loopedu_2026-11-06/`). Nunca sobrescreva o original. Organização padrão:
   - `videos/`: **só os finais**, com nome `AAAA-MM-DD_formato.mp4` (data do vídeo original; formato `vertical`, `horizontal`, `quadrado` ou `retrato`). Mais de um final do mesmo formato: `_2`, `_3`.
   - `rascunhos/`: rascunhos, intermediários, versões rejeitadas e testes.
   - na raiz da pasta: `original.mp4`, `*.words.json`, `*.plan.json`, scripts e folhas de quadros.
   **Copie a fonte crua para `original.mp4` (cópia de verdade, nunca link para Downloads ou WhatsApp).** Rafael limpa os Downloads; sem a fonte crua, nada pode ser refeito sem os zooms e cortes já embutidos. Melhorias (ESRGAN, limpeza de voz) saem sempre do original, nunca de um vídeo já editado.
   O `edin render` sem `-o` já salva assim (rascunho em `rascunhos/AAAA-MM-DD_formato_rascunho.mp4`).
4. Leia `docs/REGRAS.md` do repositório (o que nunca fazer). O `edin check` confere boa parte.
   Leia também `docs/REFERENCIA_PRO.md` antes de editar (o padrão dos talking heads profissionais: olhos, legenda, gráficos, ritmo, som e o que parece amador).
   Para conteúdo de negócios/educação em português, use como modelo os criadores medidos em `docs/referencias/` (Alfredo Soares/G4 e Luka Choi): olhos a 33 a 48% da altura com a cabeça inteira e espaço acima dela, legenda sóbria (~40 a 50 px, sem contorno pesado, sem karaokê) e gráficos no espaço acima da cabeça.
5. **Fonte já editada** (legenda ou cards gravados na imagem): avise Rafael que não dá para apagar isso dos pixels e peça a gravação crua. Se ele quiser seguir com aquele arquivo, use o fluxo **E. Refazer a edição de um vídeo já editado**. Nunca resolva encolhendo o vídeo.

## 1. Escolha o fluxo

| Situação | Fluxo |
|---|---|
| Pessoa falando (vlog, dica, aula, review) | **A. Vídeo falado** |
| Vídeo longo (podcast, live, aula) que vira vários cortes | **B. Cortes/shorts** |
| Sem fala (viagem, treino, esporte, produto) + música | **C. Montagem no beat** |
| Tela/tutorial | Fluxo A com `--preset aula` e `--format original` (sem zoom na tela; ver "Telas de app" no fluxo F) |
| Quer efeitos de motion (palavra atrás da cabeça, cards, checklist, título cinético) | Fluxo A + **D. Motion** |
| Vídeo que já vem editado (legenda, cards ou lower third gravados na imagem) | **E. Refazer a edição** (+ D) |
| Vídeo 16:9 pronto (promo, motion, demo de app ou tela) que precisa virar 9:16 | **F. Horizontal para vertical** |
| Reel tutorial de app a partir de gravação de tela, com narração | **G. Reel tutorial de app** (`roteirista` + montagem) |
| Reel narrativo sem voz (fotos/cenas + telas do app + texto na tela), inclusive com imagens faltando | **H.** [references/reel-narrativo-sem-voz.md](references/reel-narrativo-sem-voz.md): cenas que faltam feitas em código (SVG/Remotion), nunca Canva/IA |
| Vídeo inteiro (ou cenas que faltam) feito em código a partir de HTML: cenas desenhadas, câmera com movimento de cinema, transições contínuas, milhares de quadros | **I. Vídeo contínuo de HTML** (`edin html` + kit `references/html-video/`) |
| Vídeo 100% animado, sem filmagem (explainer, anúncio, lyric video) | Skill `cinematic-motion-director` (narração pelo agente `roteirista`) |

## A. Vídeo falado

```bash
edin transcribe video.mp4                      # video.words.json (GPU: --model turbo)
edin text video.words.json                     # leia INTEIRO: [tempo] #índices frase
edin plan video.mp4 --preset reels --speed 1.08  # video.plan.json
edin timeline video.plan.json
```

O `plan` decide o que manter pelas palavras do Whisper e ajusta cada borda de corte pela **energia do áudio**, para não comer o começo nem o fim das palavras. `--speed` acelera a fala depois do corte (1.05 a 1.10 soa natural; pergunte uma vez a preferência de Rafael e mantenha). Sem `--speed`, fica 1.0.

**Refine o plano** (edite o JSON):

1. **Takes repetidos e erros:** se Rafael repetiu uma frase, apague os segmentos do take ruim e mantenha o melhor (normalmente o último).
2. **Enrolação:** remova introduções longas, "deixa eu ver", tangentes. Pergunte só se for cortar algo grande e ambíguo.
3. **Gancho:** o vídeo prende nos primeiros 1,5 s. Se a frase mais forte está no meio, mova o segmento dela para o início (a ordem dos segmentos é a ordem do vídeo) e adicione um `titles` de até 6 palavras de 0 a ~2,5 s.
4. **Transcrição:** confira nomes, marcas e números. Corrija o campo `w` no `.words.json` (mantenha os tempos). O `edin check` lista palavras com baixa confiança.
5. **Ênfase e emoji:** em `captions.emphasis` coloque os `#n` de palavras-chave (impacto). No máximo uma a cada 2 ou 3 s. `"categories": true` pinta números e negações numa segunda cor sozinho. Emoji: `"emoji": [{"word": 41, "emoji": "🔥"}]` em 1 a cada 2 a 4 frases, nunca menos de 3 s entre eles, na palavra que ele ilustra. Confira com `edin captions plano.json`.
6. **Ritmo:** o plano alterna zoom 1.0 e 1.18 a cada ~3 s. Impacto: `zoom` 1.3 num segmento curto. Fala emotiva: `zoom_to` para um zoom lento. Nada parado por mais de ~3 s em 9:16.
7. **B-roll:** se Rafael tiver imagens/vídeos de apoio, `"broll": {"src": "arquivo"}` onde ele cita aquilo. Sem material, `"broll": {"query": "estudante cansado"}` baixa um clipe grátis do Pexels (precisa de `PEXELS_API_KEY`; revise com `edin broll --plan plano.json`). A fala continua. 1,5 a 3 s por plano, no máximo 30% do tempo.
8. **Som:** o `reels` já põe `softclick` nas trocas de zoom. Acentos manuais só nos momentos chave: `boom` no gancho, `ding` em número/dica, `whoosh` numa transição grande. `boom`/`riser` no máximo 2 por vídeo. Lista: `edin sfx`. Menos é mais.
9. **Voz:** o `edin plan` já liga a limpeza (`"voice": {"clean": "dfn", "strength": 24, "chain": "broadcast"}`). Em gravação já limpa de estúdio, use `strength` 12 ou desligue (`"voice": null`); em lugar muito barulhento, suba para 36. Para comparar antes de decidir: `edin voice video.mp4`.
10. **Narração nova** (o vídeo não tem fala, ou Rafael pediu locução): agente **`roteirista`** (seção "Agentes do repositório").
11. **Música:** só se Rafael mandar o arquivo. `"music": {"file": "...", "volume": 0.12, "duck": true}`. Se ele vai pôr música no app, entregue sem.

Referência dos campos: `docs/PLANO.md`.

## B. Cortes de vídeo longo em shorts

1. `edin transcribe` do vídeo inteiro.
2. Delegue a escolha ao agente **`cacador-de-cortes`**, sempre (passe o `.words.json`, quantos cortes e a duração alvo). Ele parte do `edin hunt video.words.json` (candidatos com sinais objetivos e `nota_objetiva` em `video.candidates.json`), lê tudo e dá a rubrica Hook, Flow, Value, Trend (0 a 25 cada). Sem o agente, faça você o mesmo: `hunt`, leitura completa e de 3 a 6 trechos de 20 a 60 s que funcionem sozinhos.
3. Apresente a lista para Rafael (tempo, título, rubrica, cold open) e siga com os aprovados.
4. Para cada um: `edin plan video.mp4 --range INICIO-FIM --name short1 --cold-open [A-B]` (frase mais forte de 1 a 3 s repetida no início; sem valor escolhe sozinha, `A-B` são índices do `edin text`; omita se o começo já é o gancho). Refine como no fluxo A (título obrigatório) e corte do trecho o que depende de contexto ("como o fulano falou").
5. Renderize e revise cada um (seção 2). Os cortes são independentes: pode renderizar em paralelo.

## C. Montagem no ritmo da música

```bash
edin montage clip1.mp4 clip2.mp4 clip3.mp4 --music musica.mp3 --duration 30 --music-start 12 -o montagem.plan.json
```

Detecta o BPM e corta nas batidas (a cada batida nas partes mais fortes). Revise: troque `start` dos segmentos para os melhores momentos de cada clipe (`edin sheet clip.mp4 -n 16` para ver), `speed` 0.5 para câmera lenta e 1.5 a 2 para acelerar. Duração ideal: múltiplo de compassos (4 batidas).

## D. Motion por cima (Remotion)

Para efeitos que o ffmpeg não faz bem (palavra gigante atrás da cabeça, cards, checklist, lower-third, título cinético): primeiro edite e renderize com o edin (fluxo A), depois adicione a chave `"motion"` no plano e rode `edin motion plano.json video_editado.mp4 -o final.mp4`. Campos e exemplos em `docs/MOTION.md`. Para direção de arte, regras de movimento e receitas de cena, consulte a skill `cinematic-motion-director` (referências `talking-head-effects.md`, `motion-principles.md`, `never-do.md`). Remotion é grátis para pessoa física e empresas de até 3 pessoas.

Use motion com parcimônia: um efeito assinatura a cada 5 a 10 s, sempre ilustrando exatamente o que está sendo dito naquele momento, nunca cobrindo o rosto.

**O vídeo da pessoa ocupa a tela inteira o tempo todo.** Nunca encolha a filmagem numa janela, moldura, split ou letterbox com faixas sólidas fixas em cima ou embaixo para abrir espaço para cards e legenda. Cards, títulos, gráficos e legenda flutuam por cima do vídeo: entram quando a fala os nomeia e saem depois. Nada de painel permanente; deixe o vídeo respirar entre um card e outro. Tela cheia de texto só por poucos segundos num momento de impacto.

## E. Refazer a edição de um vídeo já editado

Os elementos antigos não saem dos pixels: a câmera fica em tela cheia, as zonas antigas recebem uma cópia desfocada e escurecida do próprio vídeo e os elementos novos entram por cima. Referência que funcionou: `~/Área de trabalho/videos editados/whatsapp_2026-11-06/motion/src/Main.tsx` (componentes `Camera`, `Name`, `Captions`, `FullText`, `Freeze`).

1. **Meça as zonas antes, nada de chute.** Recortes com grade de 50 px em 4 a 6 quadros (início, meio, fim, trechos com e sem card): `ffmpeg -ss T -i fonte.mp4 -frames:v 1 -vf "crop=1080:700:0:0,drawgrid=w=50:h=50:c=red@0.5" topo.png`. Anote y0..y1 de cada elemento (cards, legenda, lower third) e quando cada um aparece. Para conferir um tempo específico use sempre `ffmpeg -i arquivo -ss T -frames:v 1` (seek preciso): os rótulos do `edin sheet` podem sair defasados.
2. **Máscara de desfoque** em coordenadas da fonte, dentro da camada que recebe o zoom, para acompanhar o punch-in. Borda curta (≈30 px) logo depois do fim do elemento antigo: nunca pega cabelo nem rosto.
3. **Legenda nova centralizada vertical e horizontalmente na faixa desfocada** e acompanhando o punch-in: com a zona em y0..y1 da fonte e zoom `s` em torno de `FACE_Y`, o centro na tela é `FACE_Y + ((y0+y1)/2 - FACE_Y) * s`.
4. **Cards no topo cabem dentro da zona desfocada em todos os zooms.** Com punch-in a zona sobe: a base do card fica acima de `FACE_Y + (y1 - FACE_Y) * s_max`.
5. **Cards com vida curta:** cada um entra na palavra que o nomeia e sai quando a ideia acaba (≈2 a 5 s), com câmera limpa entre eles. Cards emendados leem como faixa fixa. Corte os redundantes, que repetem o que a legenda ou a pessoa já mostram.
6. **Lower third antigo:** cubra com um novo no mesmo lugar, em coordenadas da fonte (dentro da camada com zoom), entrando um pouco antes do antigo aparecer.
7. **Trechos sem câmera na fonte** (telas só de texto): viram telas cheias de texto novas, sincronizadas palavra a palavra.
8. **Fim:** se a pessoa pega o celular ou a câmera treme, segure o último quadro limpo (`Freeze`) e só depois entre o encerramento.
9. Revise com recortes do final nos zooms 1.0 e máximo (legenda no centro da faixa, card dentro da zona, nada do antigo vazando) e rode o agente **`critico-de-edicao`**. Corrija o pior trecho apontado (seção 2).

## F. Horizontal para vertical (tela cheia)

Delegue sempre ao agente **`reenquadrador-vertical`** (ele faz o processo abaixo, renderiza, roda o `check` e pede a crítica). Sem o agente, siga você mesmo.

**A vertical usa a tela inteira.** Nunca encaixe o quadro 16:9 no meio com faixas em cima e embaixo (letterbox), nem disfarçado com a cor do fundo: no celular isso vira "vídeo pequeno com fundo preto". Decida cena por cena (um segmento por troca de cena; ache as trocas com `ffmpeg -vf "select='gt(scene,0.25)',showinfo"`):

| Tipo de cena | Como fazer | Campos |
|---|---|---|
| Pessoa / ação | recorte 9:16 seguindo o rosto | `fit` padrão, `focus: "face"` |
| Tela de app, site, planilha, demo de produto (conteúdo largo) | **cena remontada**: recorta só a tela/card da fonte (sem rótulo e fundo antigos), na largura do celular, sobre fundo desenhado com brilho da cor da marca; rótulo curto e grande acima, frase completa menor abaixo | `"fit": "card"`, `card` = contorno medido da área clara, `card_width: 0.96`, `bg_colors`; fonte passada antes no `edin enhance --mode esrgan` |
| Texto, logo, motion em fundo liso ou degradê | conteúdo ampliado até ~80% da largura (meça a largura do conteúdo) e as bordas da própria cena esticadas até o topo e a base | `"fit": "extend"`, `zoom` calculado |
| Texto em fundo branco liso | igual, estendendo a cor exata | `"fit": "pad"`, `pad_color` amostrado no canto |

**Telas de app, em qualquer formato (lição de Rafael: "deu zoom nas telas do app, cortou e perdeu qualidade"):**
- **Tela de app aparece inteira e nítida.** Sem punch-in, sem Ken Burns, sem recorte: `zoom` e `zoom_to` 1.0 nessas cenas, também no 16:9 e no `aula`. O movimento vem do corte entre telas, do título entrando e do próprio app (cursor, rolagem). Zoom lento só em tela de texto/logo.
- **Conta da ampliação real:** `zoom x altura de saída / altura da fonte`. Fonte 720p em saída 1080p já é 1,5x antes de qualquer zoom; acima de ~1,5x o texto da tela borra. Se a conta passa disso, passe a fonte no ESRGAN ou não amplie.
- **Destaque de um detalhe** (botão, número) só como callout separado (`detail`) ou com a fonte em 1080p+ e no máximo 1,3x, mantendo o texto inteiro no quadro. Nunca por recorte da tela inteira.
- No vertical:
  - **Nunca amplie e recorte uma tela de app para encher a vertical** (altura cheia + câmera lateral). Corta a tela, borra o texto (fonte 720p do WhatsApp não aguenta 1,8x) e a pessoa não entende o app.
  - Faça como anúncio vertical de produto: **título curto em cima (y ≈ 0.25), tela INTEIRA no meio na largura do celular, frase de apoio embaixo (y ≈ 0.75), fundo desenhado com brilho da cor da marca** (`fit: "card"`). A tela fica reduzida (~0,8x), nítida e sem corte.
  - Recorte o card pelo **contorno medido** da área clara (sem o halo escuro da fonte, que vira moldura) e **abaixo do rótulo antigo** (ele some sem `hide`).
  - Passe o `original.mp4` no `edin enhance --mode esrgan` antes (texto de tela fica mais nítido que o original) e use o arquivo melhorado no `src` dessas cenas.
  - Fundo nunca liso e preto: o `card` desenha um brilho radial que vai até as bordas. Não use `extend` em tela de app (o espelho pega a borda branca do card e o rótulo antigo transparece).
  - `detail` (destaque ampliado num card abaixo da tela) existe, mas só use se a tela for pequena e sem zoom animado na fonte: em geral duplica a informação e colide com o card.
- **Confira a nitidez:** recorte 1:1 do final numa tela de app (`ffmpeg -ss T -i final.mp4 -frames:v 1 -vf crop=540:540 nitidez.png`) e leia o menor texto da tela. Se não dá para ler no recorte, não dá no celular.

**Outras regras do vertical:**
- **Rótulo ou legenda gravados na fonte** que ficariam cortados ou duplicados: esconda com `"hide": [[x0, y0, x1, y1]]` (normalizado na fonte; cópia desfocada e escurecida do próprio vídeo) e ponha o texto novo por cima, grande, com `titles` (`font`, `accent`, `box: true`).
- `fit: "blur"` (desfoque da cena atrás) só serve para fonte com fundo de foto/vídeo; em tela branca vira cinza e em degradê mostra a emenda. Para texto/logo use `extend` (espelha a própria cena até as bordas), que funciona em fundo branco, escuro, colorido e em transições.
- **Confira o arquivo final em resolução cheia**, nunca só o rascunho (um filtro do ffmpeg só quebrava em 1080x1920 e deixou a base preta em telas brancas). `edin check plano.json video.mp4` varre o vídeo a 4 quadros/s e acusa qualquer faixa como ERRO.
- Confira a folha de quadros procurando: faixa ou retângulo visível, texto cortado nas laterais, texto antigo aparecendo atrás do novo.

## G. Reel tutorial de app a partir de gravação de tela

Detalhes, roteiro modelo e o briefing completo de Rafael: [references/reel-tutorial-app.md](references/reel-tutorial-app.md). Leia inteiro antes de começar. Resumo:

1. **Cenas:** `edin scenes gravacao.mp4 --hard-only` e folhas de contato a cada 3 a 4 s. Só o que ensina a usar o app, na ordem do uso. Nada de cadastro nem dado pessoal; comece quando o nome certo começa a ser digitado.
2. **Roteiro e voz: agente `roteirista`** (objetivo, lista de cenas ou folhas, duração abaixo de 2 min). Uma fala por cena, frases curtas afirmativas, sem pergunta retórica, "LoopEdu" no masculino, sem travessão. Voz padrão "Yuri - Natural Brazilian Narrator", Stability 50, Similarity 75, modelo `eleven_v4` (`edin tts`). Se Rafael mandou a narração, use a dele e gere só a tabela (`edin falas`).
3. **Montagem 1080x1920 quadro a quadro** (Python + OpenCV + PIL para o ffmpeg): fundo degradê índigo da marca com halos, cartão do vídeo de 1000 px centrado, legenda em pílula de vidro acima do cartão no imperativo falando com o aluno, rodapé com ícone e "LoopEdu", intro de 4,5 s e fechamento de ~3,7 s ("Estude melhor." / "Viva por inteiro.", "Link na bio").
4. **Câmera** por quadros-chave com smoothstep e empurrão de ~3,5%. **A borda do enquadramento só cai no vão entre blocos da tela, nunca no meio de um painel, cartão, linha, coluna ou campo** (Rafael: "cuidado com esses zooms, perde partes das imagens"). Meça na grade de coordenadas os limites de cada bloco; telas com duas colunas ou grade (lista + ementa, semana, resumo + plano) ficam na largura do conteúdo inteiro; zoom fechado só quando o bloco inteiro cabe e o vizinho fica de fora por inteiro. Nunca zoom em insígnia bloqueada. **Velocidade perto de 1x** (no máximo 1,15x; só a digitação pode ir a 1,5x): Rafael reprovou 1,5x a 1,8x como "muito acelerado". Sobrou gravação? Corte tempo parado em vez de acelerar. Ajuda e correção a 1x; congelar a correção 2 a 3 s.
5. **Sincronia pela tabela fala x tempo:** corta a narração no `corte_sugerido` (meio do silêncio), fala entra 0,15 s depois do início da cena (0,3 s na intro), cena = fala + 0,3 a 0,6 s. **Nenhum silêncio maior que 1 s** no final.
6. **Cursor redesenhado, sempre:** o cursor de gravação de tela vem travado (para e salta 100+ px num quadro). Detecte seta e mão por modelo, apague com o fundo de um quadro vizinho e redesenhe numa trajetória suavizada (gaussiana de 2,5 quadros), interpolada no tempo fracionário da fonte. Scripts prontos em [references/reel-tutorial/](references/reel-tutorial/).
7. **Ampliação (ESRGAN) de TODOS os quadros usados**, sem juntar quadros "quase iguais": juntar fez o cursor e as rolagens andarem aos saltos ("lagzinho").
8. **Dado pessoal da conta de teste** (nome na barra lateral, saudação "Boa noite, Fulano", nome no cartão de nível): tape no quadro (lista `HIDE` em `cenas.py`), mesmo que só apareça por meio segundo.
9. **Áudio:** voz em -14 LUFS, pico até -1,5 dBTP, estéreo (`loudnorm` + ganho, `-ac 2`). O primeiro saiu em -25 LUFS e mono.
10. **Conferência** (folhas a cada 3 a 4 s, quadros dos momentos críticos, tabela de silêncio do final, duração abaixo de 2 min) e depois o agente `critico-de-edicao`.

## I. Vídeo contínuo a partir de HTML (milhares de quadros)

Quando o vídeo (ou as cenas que faltam) é desenhado em código, prefira este fluxo ao Remotion para cenas novas: é JS puro, abre no navegador para pré-visualizar e o `edin html` renderiza em paralelo, quadro a quadro, sem engasgo. Leia antes [references/html-video/LEIAME.md](references/html-video/LEIAME.md) (API do kit), [references/higgsfield-camera.md](references/higgsfield-camera.md) (direção de câmera e continuidade) e `docs/HTML.md` do repositório (flags e armadilhas do renderizador). Modelo pronto: `references/html-video/exemplo.html` (Reel de 20,6 s, 6 cenas; renderizado em `~/Área de trabalho/videos editados/demo_html_video_2026-11-12/`).

**Padrão de Rafael (12/11): "as gerações das imagens têm que ser milhares para ficar como se fosse um filme realmente".** Vídeo de HTML sai em **60 fps** com `--motion-blur 8` (obturador de 180°, como câmera de cinema): 30 s = 1.800 quadros no vídeo e ~14.400 imagens renderizadas. Câmera nunca parada (sempre um movimento lento por baixo, parallax entre camadas), profundidade de campo, luz de um ângulo só, color grade e grão de película únicos no vídeo todo. Nada de slideshow: cada cena nasce do movimento da anterior.

1. **Copie o kit** (`references/html-video/*` com `fontes/`) para a pasta do vídeo e escreva `cenas.html` lá. Imagens e fontes sempre locais, nunca da web.
2. **Planeje numa ficha de plano por cena** (seção 3 do `higgsfield-camera.md`): sujeito, ação, câmera (preset), duração, transição de entrada e saída. Regras que valem sempre:
   - Um movimento por plano; no `EdinCam.mix` no máximo 2, nunca opostos. Nunca o mesmo preset em dois planos seguidos; cada corte muda o tamanho do plano e o tipo de câmera.
   - Gancho de 0 a 2 s com o movimento mais forte; planos de 1,5 a 3 s; movimento violento (crash, whip, super-dolly) no máximo 1 a cada 4 planos.
   - Câmera que anda (dolly, crane, arc, drone) tem parallax entre camadas `data-z`; câmera que gira (pan, tilt, zoom) não. Tudo escalado igual parece slide.
   - Continuidade: mesmo sentido de tela no vídeo todo; corte no movimento com velocidade igual ±20% dos dois lados; whip pan cortando no borrão máximo (4 a 6 quadros por lado); match cut com a forma comum no mesmo centro ±2% e escala ±10%.
   - Transições, lições do demo de 12/11: no `push` a borda entre os dois fundos aparece como faixa lisa (já reprovada); prefira `whip-pan` ou `dissolve`, ou deixe o topo do fundo novo igual à base do antigo. No `zoom-through` o conteúdo da cena de destino aparece cortado dentro do portal: deixe os textos dela invisíveis até o portal passar de ~60% do quadro. No `match-cut` só a forma comum faz a emenda: apague o resto da cena A (dígitos, rótulos) 0,2 s antes, senão os textos das duas cenas se sobrepõem. Brilho/halo desfocado nunca acima de ~10% da tela nem com opacidade acima de 0,25 (deixa tudo lavado).
   - Consistência: um tema só (paleta, ângulo da luz, grão 4 a 6%, vinheta), o mesmo "set" reaproveitado com câmera nova a cada ângulo, nunca um desenho novo por cena.
3. **Legível no celular:** legenda 86 px, a de baixo em y ≈ 0,68 (a base de 450 px é coberta pela interface do Instagram), até 5 palavras em linhas equilibradas, uma palavra de destaque em laranja por cena. Texto desenhado de tela de app com no mínimo ~45 px de altura de maiúscula: mostre menos coisa (3 dias em vez de 5) em vez de encolher. O quadro 0 é a capa: gancho escrito já visível e sujeito grande. Nada de clarão (brilho médio saltando mais de ~60 níveis num quadro; escuro para página branca em tela cheia): dissolve curto ou a cena clara começa menor. O final emenda com o início (Reel em loop).
4. **Tudo é função do tempo.** `seek(t)` fora de ordem tem que dar o mesmo quadro (o render é paralelo): nada de CSS animation, `setTimeout`, rAF ou `Math.random` sem semente (use `EdinVideo.ruido`/`aleatorio`). Tudo que é discreto (dígitos, contagem, texto que troca) usa o tempo do quadro (`EdinVideo.quadro(t)` / `ctx.tq`), senão o motion blur mistura dois valores. Telas de app vão em `data-tela` (o kit impede zoom, giro e corte; regra das telas de app do fluxo F).
5. **Pré-visualize** abrindo o HTML no navegador (barra de tempo; `?t=5.2` abre num instante) e confira quadros com `edin html cenas.html --draft`.
6. **Renderize:** `edin html cenas.html -o videos/AAAA-MM-DD_vertical.mp4 --fps 60 --motion-blur 8 [--audio voz.mp3 | --silent-audio]`. Horizontal: `--size 1920x1080` (o kit se adapta). **Motion blur 0 ou no mínimo 8, nunca 2 a 4:** com poucas amostras o texto em movimento sai em duas cópias nítidas (match cut, zoom-through, push) e o primeiro demo foi reprovado por isso. Custa K vezes o tempo; para iterar use `--draft` sem blur. `--frames-dir` só se Rafael quiser a sequência PNG (~1 MB por quadro). Medido: ~30 quadros/s em 1080x1920 com 8 workers numa cena pesada, no exemplo de 20 s, 8,6 quadros/s com motion blur 2 e 2,4 quadros/s (4 min) com motion blur 8; 4200 quadros sem vazar memória; 1, 4 ou 8 workers dão quadros idênticos.
7. **Narração:** agente `roteirista` antes de fixar as durações; a duração de cada cena sai da tabela fala x tempo.
8. **Confira:** folha de quadros (`edin sheet ... -n 16`, mova para `rascunhos/`) procurando controles de pré-visualização no quadro, texto cortado, anel/destaque em cima da informação, emendas piscando; recorte 1:1 do menor texto; depois o agente `critico-de-edicao` (passe o HTML no lugar do plano).

O Higgsfield de verdade (IA) só entra quando Rafael pedir ângulos gerados em filmagem real de pessoa (skill `camera-dinamica`, resumo na seção 4 do `higgsfield-camera.md`). Para cenas que faltam, código.

## 2. Revisar e entregar

1. `edin check plano.json` e corrija erros e avisos que fizerem sentido.
2. `edin render plano.json --draft` (meia resolução, rápido; vai para `rascunhos/`).
3. `edin sheet video_rascunho.mp4 -n 12` e **abra a imagem**: rosto enquadrado e cabeça inteira, legenda legível sem cobrir o rosto, título aparecendo, b-roll no lugar. Ajuste `captions.position` (0 topo, 1 base, zona segura 0.55 a 0.78) ou `focus` (`"center"` ou `[x, y]`).
4. Render final: `edin render plano.json` (sai em `videos/AAAA-MM-DD_formato.mp4`).
5. **Crítica independente, sempre:** chame o agente **`critico-de-edicao`** com o plano e o `final.mp4` (ele roda `check`, `verify`, folha de quadros e devolve PODE PUBLICAR ou MAIS UMA PASSADA com o pior trecho). Sem o agente, rode você mesmo `edin check plano.json final.mp4` e `edin verify plano.json final.mp4`.
6. Antes de entregar, pergunte-se o que Rafael já reprovou: faixa preta ou letterbox, tela de app ampliada/cortada/borrada, legenda cobrindo o rosto, vídeo encolhido numa janela, gravação de tela acelerada demais, cursor travado ou imagem engasgando. Se qualquer um aparecer, não entregue.
7. Se o veredito for MAIS UMA PASSADA, corrija **só o trecho apontado**, renderize de novo e repita no máximo 2 vezes.
8. Entregue com 2 ou 3 linhas: duração final, o que foi cortado, as escolhas criativas principais e o que foi conferido. Ofereça uma variação (outro gancho, outro estilo de legenda) se fizer sentido.

## Presets

| Preset | Formato | Corte de pausa | Zoom | Legenda | Som |
|---|---|---|---|---|---|
| `reels` | 9:16 | > 0,30 s | 1.0 / 1.18 a cada ~3 s + drift | `hormozi` 3 palavras | `softclick` no zoom |
| `podcast` | 9:16 | > 0,45 s | 1.0 / 1.12 a cada ~4,5 s | `clean` 4 palavras | nenhum |
| `youtube` | 16:9 | > 0,50 s | 1.0 / 1.10 a cada ~7 s | `minimal` | nenhum |
| `aula` | original | > 0,70 s | sem zoom | `minimal` | nenhum |

Legendas: `hormozi`, `clean`, `karaoke`, `minimal`. Efeitos: `softclick`, `click`, `tock`, `pop`, `snap`, `ding`, `whoosh`, `swoosh`, `boom`, `riser`, `glitch`.

## Problemas comuns

- **Palavra comida no corte** (`edin verify` acusa): aumente o `end` do segmento anterior ou diminua o `start` do seguinte em 0,05 a 0,15 s.
- **Respiração ou "ahn" sobrando:** diminua o `end`/aumente o `start` do segmento, ou apague o segmento do filler.
- **Rosto não detectado** (de lado, escuro): `"focus": [0.6, 0.35]` no segmento.
- **Lento:** `--draft` para iterar. Transcrição em CPU: `--model small` (padrão) ou `base`; com GPU: `turbo`.
- Temporários ficam em `.edin_tmp/` (pasta oculta ao lado da saída: cache de rosto, efeitos e segmentos). Apague com `edin clean saida.mp4`.
