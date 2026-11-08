---
name: edicao-dinamica
description: Edita vídeos de forma dinâmica com IA, de graça e local (cortes de silêncio que não comem palavras, punch-ins, reenquadramento 9:16 pelo rosto, legendas animadas, b-roll, efeitos sonoros, música, cortes de vídeo longo em shorts, montagem no ritmo da música e motion design por cima com Remotion). Use sempre que Rafael pedir para editar, cortar, legendar, deixar dinâmico, transformar em Reels/Shorts/TikTok ou montar um vídeo.
---

# Edição dinâmica de vídeo (edin)

Você é o **diretor de edição**. A ferramenta `edin` faz o trabalho pesado (ffmpeg, faster-whisper, OpenCV) e você toma as decisões criativas lendo a transcrição e editando o plano JSON. Tudo roda local e de graça.

Fale sempre em português com Rafael e não use travessões nos textos.

Toda decisão responde a uma pergunta: **isso faz a pessoa continuar assistindo?**

## 0. Preparação

1. Rode `edin doctor`. Se faltar algo, rode `<repo editor-dinamico>/install.sh`.
2. Entenda o pedido em uma frase. Se Rafael não disse, assuma e diga quais assumiu:
   - Plataforma: Reels/TikTok/Shorts (9:16), preset `reels`.
   - Duração: a do conteúdo útil, sem enrolação.
   - Legenda: `hormozi`. Som: clique suave nas trocas de zoom, sem música.
3. Trabalhe numa pasta própria do vídeo dentro de `~/Área de trabalho/videos editados/` (ex.: `videos editados/loopedu_2026-11-06/`). Nunca sobrescreva o original. Organização padrão:
   - `videos/`: **só os finais**, com nome `AAAA-MM-DD_formato.mp4` (data do vídeo original; formato `vertical`, `horizontal`, `quadrado` ou `retrato`). Mais de um final do mesmo formato: `_2`, `_3`.
   - `rascunhos/`: rascunhos, intermediários, versões rejeitadas e testes.
   - na raiz da pasta: original, `*.words.json`, `*.plan.json`, scripts e folhas de quadros.
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
| Tela/tutorial | Fluxo A com `--preset aula` e `--format original` |
| Quer efeitos de motion (palavra atrás da cabeça, cards, checklist, título cinético) | Fluxo A + **D. Motion** |
| Vídeo que já vem editado (legenda, cards ou lower third gravados na imagem) | **E. Refazer a edição** (+ D) |
| Vídeo 16:9 pronto (promo, motion, demo de app ou tela) que precisa virar 9:16 | **F. Horizontal para vertical** |
| Vídeo 100% animado, sem filmagem (explainer, anúncio, lyric video) | Skill `cinematic-motion-director` |

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
10. **Música:** só se Rafael mandar o arquivo. `"music": {"file": "...", "volume": 0.12, "duck": true}`. Se ele vai pôr música no app, entregue sem.

Referência dos campos: `docs/PLANO.md`.

## B. Cortes de vídeo longo em shorts

1. `edin transcribe` do vídeo inteiro.
2. Delegue a escolha ao agente **`cacador-de-cortes`** (passe o `.words.json`, quantos cortes e a duração alvo). Ele parte do `edin hunt video.words.json` (candidatos com sinais objetivos e `nota_objetiva` em `video.candidates.json`), lê tudo e dá a rubrica Hook, Flow, Value, Trend (0 a 25 cada). Sem o agente, faça você o mesmo: `hunt`, leitura completa e de 3 a 6 trechos de 20 a 60 s que funcionem sozinhos.
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

Delegue ao agente **`reenquadrador-vertical`** (ele faz o processo abaixo, renderiza, roda o `check` e pede a crítica). Sem o agente, siga você mesmo.

**A vertical usa a tela inteira.** Nunca encaixe o quadro 16:9 no meio com faixas em cima e embaixo (letterbox), nem disfarçado com a cor do fundo: no celular isso vira "vídeo pequeno com fundo preto". Decida cena por cena (um segmento por troca de cena; ache as trocas com `ffmpeg -vf "select='gt(scene,0.25)',showinfo"`):

| Tipo de cena | Como fazer | Campos |
|---|---|---|
| Pessoa / ação | recorte 9:16 seguindo o rosto | `fit` padrão, `focus: "face"` |
| Tela de app, site, planilha, demo de produto (conteúdo largo) | **cena remontada**: recorta só a tela/card da fonte (sem rótulo e fundo antigos), na largura do celular, sobre fundo desenhado com brilho da cor da marca; rótulo curto e grande acima, frase completa menor abaixo | `"fit": "card"`, `card` = contorno medido da área clara, `card_width: 0.96`, `bg_colors`; fonte passada antes no `edin enhance --mode esrgan` |
| Texto, logo, motion em fundo liso ou degradê | conteúdo ampliado até ~80% da largura (meça a largura do conteúdo) e as bordas da própria cena esticadas até o topo e a base | `"fit": "extend"`, `zoom` calculado |
| Texto em fundo branco liso | igual, estendendo a cor exata | `"fit": "pad"`, `pad_color` amostrado no canto |

**Telas de app em vertical (lição de Rafael: "deu zoom nas telas do app, cortou e perdeu qualidade"):**
- **No horizontal também:** tela de app sem zoom (`zoom_to: 1.0`) e com `src` da fonte melhorada no ESRGAN; zoom lento só em tela de texto/logo. Copie a fonte crua para dentro do projeto (nunca link para Downloads) e gere o ESRGAN a partir dela, não do vídeo já editado.
- **Nunca amplie e recorte uma tela de app para encher a vertical** (altura cheia + câmera lateral). Corta a tela, borra o texto (fonte 720p do WhatsApp não aguenta 1,8x) e a pessoa não entende o app.
- Faça como anúncio vertical de produto: **título curto em cima (y ≈ 0.25), tela INTEIRA no meio na largura do celular, frase de apoio embaixo (y ≈ 0.75), fundo desenhado com brilho da cor da marca** (`fit: "card"`). A tela fica reduzida (~0,8x), nítida e sem corte.
- Recorte o card pelo **contorno medido** da área clara (sem o halo escuro da fonte, que vira moldura) e **abaixo do rótulo antigo** (ele some sem `hide`).
- Passe a fonte no `edin enhance --mode esrgan` antes (texto de tela fica mais nítido que o original) e use o arquivo melhorado no `src` dessas cenas.
- Fundo nunca liso e preto: o `card` desenha um brilho radial que vai até as bordas. Não use `extend` em tela de app (o espelho pega a borda branca do card e o rótulo antigo transparece).
- `detail` (destaque ampliado num card abaixo da tela) existe, mas só use se a tela for pequena e sem zoom animado na fonte: em geral duplica a informação e colide com o card.


- **Rótulo ou legenda gravados na fonte** que ficariam cortados ou duplicados: esconda com `"hide": [[x0, y0, x1, y1]]` (normalizado na fonte; cópia desfocada e escurecida do próprio vídeo) e ponha o texto novo por cima, grande, com `titles` (`font`, `accent`, `box: true`).
- `fit: "blur"` (desfoque da cena atrás) só serve para fonte com fundo de foto/vídeo; em tela branca vira cinza e em degradê mostra a emenda. Para texto/logo use `extend` (espelha a própria cena até as bordas), que funciona em fundo branco, escuro, colorido e em transições.
- **Confira o arquivo final em resolução cheia**, nunca só o rascunho (um filtro do ffmpeg só quebrava em 1080x1920 e deixou a base preta em telas brancas). `edin check plano.json video.mp4` varre o vídeo a 4 quadros/s e acusa qualquer faixa como ERRO.
- Confira a folha de quadros procurando: faixa ou retângulo visível, texto cortado nas laterais, texto antigo aparecendo atrás do novo.

## 2. Revisar e entregar

1. `edin check plano.json` e corrija erros e avisos que fizerem sentido.
2. `edin render plano.json --draft` (meia resolução, rápido; vai para `rascunhos/`).
3. `edin sheet video_rascunho.mp4 -n 12` e **abra a imagem**: rosto enquadrado e cabeça inteira, legenda legível sem cobrir o rosto, título aparecendo, b-roll no lugar. Ajuste `captions.position` (0 topo, 1 base, zona segura 0.55 a 0.78) ou `focus` (`"center"` ou `[x, y]`).
4. Render final: `edin render plano.json` (sai em `videos/AAAA-MM-DD_formato.mp4`).
5. **Crítica independente:** chame o agente **`critico-de-edicao`** com o plano e o `final.mp4` (ele roda `check`, `verify`, folha de quadros e devolve PODE PUBLICAR ou MAIS UMA PASSADA com o pior trecho). Sem o agente, rode você mesmo `edin check plano.json final.mp4` e `edin verify plano.json final.mp4`.
6. Se o veredito for MAIS UMA PASSADA, corrija **só o trecho apontado**, renderize de novo e repita no máximo 2 vezes.
7. Entregue com 2 ou 3 linhas: duração final, o que foi cortado, as escolhas criativas principais e o que foi conferido. Ofereça uma variação (outro gancho, outro estilo de legenda) se fizer sentido.

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
