---
name: edicao-dinamica
description: Edita vídeos de forma dinâmica com IA, de graça e local (cortes de silêncio, punch-ins, reenquadramento 9:16 pelo rosto, legendas animadas, b-roll, efeitos sonoros, música, cortes de vídeo longo em shorts e montagem no ritmo da música). Use sempre que Rafael pedir para editar, cortar, legendar, deixar dinâmico, transformar em Reels/Shorts/TikTok ou montar um vídeo.
---

# Edição dinâmica de vídeo (edin)

Você é o **diretor de edição**. A ferramenta `edin` faz o trabalho pesado (ffmpeg, faster-whisper, OpenCV) e você toma as decisões criativas lendo a transcrição e editando o plano JSON. Tudo roda local e de graça.

Sempre fale em português com Rafael e não use travessões nos textos.

## 0. Preparação

1. Rode `edin doctor`. Se faltar algo, rode `pip install -e <pasta do repo editor-dinamico>` e garanta o ffmpeg instalado.
2. Entenda o pedido em uma frase. Se Rafael não disse, assuma estes padrões e diga quais assumiu:
   - Plataforma: Reels/TikTok/Shorts (9:16), preset `reels`.
   - Duração: a do conteúdo útil, sem enrolação.
   - Legenda: estilo `hormozi`.
3. Trabalhe numa pasta ao lado do vídeo. Nunca sobrescreva o vídeo original.

## 1. Escolha o fluxo

| Situação | Fluxo |
|---|---|
| Pessoa falando (vlog, dica, aula, review) | **A. Vídeo falado** |
| Vídeo longo (podcast, live, aula) que vira vários cortes | **B. Cortes/shorts** |
| Sem fala (viagem, treino, esporte, produto) + música | **C. Montagem no beat** |
| Tela/tutorial | Fluxo A com `--preset aula` e `--format original` |

## A. Vídeo falado

```bash
edin transcribe video.mp4            # gera video.words.json (use --model medium ou turbo se tiver GPU)
edin text video.words.json           # leia isto inteiro: [tempo] #índices frase
edin plan video.mp4 --preset reels   # gera video.plan.json automático
edin timeline video.plan.json        # mostra como o vídeo final vai ficar
```

Depois de ler a transcrição, **refine o plano** (edite o JSON com a ferramenta de edição de arquivos):

1. **Takes repetidos e erros**: se Rafael repetiu uma frase ("hoje eu vou... hoje eu vou mostrar"), apague os segmentos do take ruim e mantenha o último/melhor.
2. **Enrolação**: remova segmentos que não acrescentam (introduções longas, "deixa eu ver", tangentes). Pergunte só se for cortar algo grande e ambíguo.
3. **Gancho**: o vídeo precisa prender nos primeiros 1,5 s. Se a frase mais forte está no meio, mova o segmento dela para o início (a ordem dos segmentos no JSON é a ordem do vídeo) e adicione um `titles` curto (até 6 palavras) de 0 a ~2,5 s.
4. **Ênfase**: em `captions.emphasis` coloque os índices (`#n` do `edin text`) de palavras-chave: números, valores, palavras de impacto. No máximo uma a cada 2 ou 3 segundos.
5. **Ritmo**: o plano já alterna zoom 1.0 e 1.18 a cada ~3 s. Em momentos de impacto, use `zoom` 1.3 num segmento curto. Em falas emotivas, deixe `zoom_to` para um zoom lento.
6. **B-roll**: se Rafael tiver imagens/vídeos de apoio, coloque `"broll": {"src": "arquivo"}` nos segmentos onde ele cita aquilo. A fala continua, só a imagem troca. Não use b-roll em mais de 30% do tempo.
7. **Som**: `auto_sfx.on_zoom` (whoosh nos punch-ins) já vem ligado no `reels`. Use `sfx` manual para momentos chave (`boom` no gancho, `ding` em número/dica, `pop` em ênfase). Lista: `edin sfx`. Menos é mais.
8. **Música**: só se Rafael fornecer um arquivo. Use `"music": {"file": "...", "volume": 0.12, "duck": true}`.

Referência completa dos campos: `docs/PLANO.md` no repositório.

## B. Cortes de vídeo longo em shorts

1. `edin transcribe` e `edin text` do vídeo inteiro.
2. Leia tudo e escolha de 3 a 6 momentos de 20 a 60 s que funcionem sozinhos: gancho forte, uma ideia completa, final com conclusão ou frase de efeito. Apresente a lista para Rafael com tempo, título sugerido e por que funciona.
3. Para cada um: `edin plan video.mp4 --range INICIO-FIM --name short1` e refine como no fluxo A (gancho e título são obrigatórios em shorts).
4. Renderize cada um.

## C. Montagem no ritmo da música

```bash
edin montage clip1.mp4 clip2.mp4 clip3.mp4 --music musica.mp3 --duration 30 --music-start 12 -o montagem.plan.json
```

Detecta o BPM e corta nas batidas (corte a cada batida nas partes mais fortes). Depois revise: troque `start` de segmentos para os melhores momentos de cada clipe (use `edin sheet clip.mp4 -n 16` para ver os clipes), e use `speed` 0.5 em momentos de câmera lenta ou 1.5 a 2 para acelerar.

## 2. Revisar e entregar

1. `edin render plano.json --draft` (meia resolução, rápido).
2. `edin sheet video_rascunho.mp4 -n 12` e **abra a imagem** para conferir: rosto enquadrado, legenda legível e sem cobrir o rosto, título aparecendo, b-roll no lugar. Ajuste `captions.position` (0 topo, 1 base) ou `focus` (`"center"` ou `[x, y]` de 0 a 1) se precisar.
3. Render final: `edin render plano.json -o final.mp4`. Áudio sai normalizado em -14 LUFS (padrão de redes sociais).
4. Entregue com 2 ou 3 linhas: duração final, o que foi cortado e as escolhas criativas principais. Ofereça uma variação (outro gancho, outro estilo de legenda) se fizer sentido.

## Presets

| Preset | Formato | Corte de pausa | Zoom | Legenda |
|---|---|---|---|---|
| `reels` | 9:16 | > 0,30 s | 1.0 / 1.18 a cada ~3 s + drift | `hormozi` 3 palavras |
| `podcast` | 9:16 | > 0,45 s | 1.0 / 1.12 a cada ~4,5 s | `clean` 4 palavras |
| `youtube` | 16:9 | > 0,50 s | 1.0 / 1.10 a cada ~7 s | `minimal` |
| `aula` | original | > 0,70 s | sem zoom | `minimal` |

Estilos de legenda: `hormozi`, `clean`, `karaoke`, `minimal`.

## Problemas comuns

- **Transcrição errou palavra**: corrija o campo `w` no `.words.json` (mantenha os tempos).
- **Corte comendo o fim da palavra**: aumente o `end` do segmento em 0,05 a 0,1 s.
- **Rosto não detectado** (de lado, escuro): use `"focus": [0.6, 0.35]` no segmento.
- **Lento**: use `--draft` para iterar; transcrição em CPU usa `--model small` (padrão) ou `base`.
- Arquivos temporários ficam em `<saida>_edin_tmp/` (cache de rosto e efeitos). Apague com `edin clean saida.mp4`.
