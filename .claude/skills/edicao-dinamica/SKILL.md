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
3. Trabalhe numa pasta ao lado do vídeo. Nunca sobrescreva o original.
4. Leia `docs/REGRAS.md` do repositório (o que nunca fazer). O `edin check` confere boa parte.

## 1. Escolha o fluxo

| Situação | Fluxo |
|---|---|
| Pessoa falando (vlog, dica, aula, review) | **A. Vídeo falado** |
| Vídeo longo (podcast, live, aula) que vira vários cortes | **B. Cortes/shorts** |
| Sem fala (viagem, treino, esporte, produto) + música | **C. Montagem no beat** |
| Tela/tutorial | Fluxo A com `--preset aula` e `--format original` |
| Quer efeitos de motion (palavra atrás da cabeça, cards, checklist, título cinético) | Fluxo A + **D. Motion** |
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
5. **Ênfase:** em `captions.emphasis` coloque os `#n` de palavras-chave (números, valores, impacto). No máximo uma a cada 2 ou 3 s.
6. **Ritmo:** o plano alterna zoom 1.0 e 1.18 a cada ~3 s. Impacto: `zoom` 1.3 num segmento curto. Fala emotiva: `zoom_to` para um zoom lento. Nada parado por mais de ~3 s em 9:16.
7. **B-roll:** se Rafael tiver imagens/vídeos de apoio, `"broll": {"src": "arquivo"}` onde ele cita aquilo. A fala continua. No máximo 30% do tempo.
8. **Som:** o `reels` já põe `softclick` nas trocas de zoom. Acentos manuais só nos momentos chave: `boom` no gancho, `ding` em número/dica, `whoosh` numa transição grande. `boom`/`riser` no máximo 2 por vídeo. Lista: `edin sfx`. Menos é mais.
9. **Música:** só se Rafael mandar o arquivo. `"music": {"file": "...", "volume": 0.12, "duck": true}`. Se ele vai pôr música no app, entregue sem.

Referência dos campos: `docs/PLANO.md`.

## B. Cortes de vídeo longo em shorts

1. `edin transcribe` do vídeo inteiro.
2. Delegue a escolha ao agente **`cacador-de-cortes`** (passe o `.words.json`, quantos cortes e a duração alvo). Se o agente não estiver disponível, faça você: leia tudo e escolha de 3 a 6 trechos de 20 a 60 s que funcionem sozinhos, com gancho forte, ideia completa e final de efeito.
3. Apresente a lista para Rafael (tempo, título, por que funciona) e siga com os aprovados.
4. Para cada um: `edin plan video.mp4 --range INICIO-FIM --name short1` e refine como no fluxo A (gancho e título obrigatórios).
5. Renderize e revise cada um (seção 2). Os cortes são independentes: pode renderizar em paralelo.

## C. Montagem no ritmo da música

```bash
edin montage clip1.mp4 clip2.mp4 clip3.mp4 --music musica.mp3 --duration 30 --music-start 12 -o montagem.plan.json
```

Detecta o BPM e corta nas batidas (a cada batida nas partes mais fortes). Revise: troque `start` dos segmentos para os melhores momentos de cada clipe (`edin sheet clip.mp4 -n 16` para ver), `speed` 0.5 para câmera lenta e 1.5 a 2 para acelerar. Duração ideal: múltiplo de compassos (4 batidas).

## D. Motion por cima (Remotion)

Para efeitos que o ffmpeg não faz bem (palavra gigante atrás da cabeça, cards, checklist, lower-third, título cinético): primeiro edite e renderize com o edin (fluxo A), depois adicione a chave `"motion"` no plano e rode `edin motion plano.json video_editado.mp4 -o final.mp4`. Campos e exemplos em `docs/MOTION.md`. Para direção de arte, regras de movimento e receitas de cena, consulte a skill `cinematic-motion-director` (referências `talking-head-effects.md`, `motion-principles.md`, `never-do.md`). Remotion é grátis para pessoa física e empresas de até 3 pessoas.

Use motion com parcimônia: um efeito assinatura a cada 5 a 10 s, sempre ilustrando exatamente o que está sendo dito naquele momento, nunca cobrindo o rosto.

## 2. Revisar e entregar

1. `edin check plano.json` e corrija erros e avisos que fizerem sentido.
2. `edin render plano.json --draft` (meia resolução, rápido).
3. `edin sheet video_rascunho.mp4 -n 12` e **abra a imagem**: rosto enquadrado e cabeça inteira, legenda legível sem cobrir o rosto, título aparecendo, b-roll no lugar. Ajuste `captions.position` (0 topo, 1 base, zona segura 0.55 a 0.78) ou `focus` (`"center"` ou `[x, y]`).
4. Render final: `edin render plano.json -o final.mp4`.
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
- Temporários ficam em `<saida>_edin_tmp/` (cache de rosto e efeitos). Apague com `edin clean saida.mp4`.
