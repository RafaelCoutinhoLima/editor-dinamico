# Referência do plano de edição (`*.plan.json`)

O plano é a "linha do tempo" do vídeo. A ordem de `segments` é a ordem do vídeo final. Caminhos relativos são resolvidos a partir da pasta do plano.

```json
{
  "source": "video.mp4",
  "words": "video.words.json",
  "format": "9:16",
  "fps": 30,
  "preset": "reels",
  "audio": "source",
  "segments": [
    {"start": 12.40, "end": 15.10, "zoom": 1.0, "zoom_to": 1.035, "focus": "face"},
    {"start": 15.10, "end": 18.00, "zoom": 1.18, "speed": 1.0},
    {"start": 21.30, "end": 24.00, "zoom": 1.0, "broll": {"src": "praia.jpg", "zoom_to": 1.1}},
    {"src": "outro_clipe.mp4", "start": 3.0, "end": 5.0, "zoom": 1.1}
  ],
  "captions": {
    "style": "hormozi",
    "words_per_group": 3,
    "position": 0.68,
    "emphasis": [41, 57],
    "uppercase": true,
    "scale": 1.0,
    "max_chars": 22,
    "active_color": "&H0000E5FF&",
    "emphasis_color": "&H0014FF39&"
  },
  "titles": [{"text": "3 erros que custam caro", "start": 0, "end": 2.5}],
  "sfx": [{"at": 0.0, "type": "boom", "volume": 0.6}],
  "auto_sfx": {"on_zoom": "softclick"},
  "music": {"file": "musica.mp3", "volume": 0.12, "start": 0, "duck": true},
  "loudness": -14,
  "voice": {"clean": "dfn", "strength": 24, "chain": "broadcast"}
}
```

## Campos

**Raiz**
- `source`: vídeo principal (as legendas usam a transcrição dele).
- `words`: transcrição gerada por `edin transcribe` (ou `null` para vídeo sem fala).
- `format`: `9:16` (1080x1920), `16:9` (1920x1080), `1:1`, `4:5` ou `original`.
- `audio`: `source` usa o áudio do vídeo; `music` usa só a música (montagens).
- `loudness`: alvo em LUFS (-14 para redes sociais, -16 para YouTube mais calmo).

**Segmento**
- `start`, `end`: tempos em segundos **no arquivo de origem**.
- `src`: outro arquivo de vídeo/imagem para este segmento (padrão: `source`).
- `zoom`: 1.0 = quadro inteiro no formato de saída; 1.18 = punch-in. Valores menores que 1 viram 1.
- `zoom_to`: se diferente de `zoom`, faz zoom suave ao longo do segmento (in ou out).
- `fit`: `"blur"` mostra o quadro inteiro com fundo desfocado nas laterais (automático quando a fonte é vertical e a saída horizontal; assim não corta testa e queixo). `"crop"` força o recorte. `"pad"` faz o mesmo com fundo de cor sólida (`pad_color` na raiz do plano ou no segmento, ex. `"#0B0716"`), melhor quando a fonte tem fundo liso (o desfoque escurecido deixa branco cinza). `blur_dim` (0 a 1, padrão 0.22) diz quanto escurecer o fundo do `blur`; use 0 em fundos com degradê para emendar sem faixa.
- `fit: "extend"`: quadro inteiro (com `zoom` para ampliar) e as bordas da própria cena esticadas e suavizadas até o topo, a base e as laterais. Emenda sem faixa em fundos lisos ou com degradê; é o modo certo para cenas de texto, logo e motion ao passar de 16:9 para 9:16.
- `pan`: `"auto"` ou `[x_inicio, x_fim]` normalizados. Nunca atravessa uma troca de plano: com corte no meio do segmento, `"auto"` mede e move cada plano separado, e o manual faz o movimento no plano mais longo (parado em `x_inicio` antes dele e em `x_fim` depois). Banner que entra ou rolagem na mesma tela não contam como corte. `"auto"` propõe a câmera pelas bordas do texto (mantém o início da leitura, centraliza conteúdo estreito); confira e troque por manual onde errar. A câmera anda de lado dentro do segmento, com easing. É o jeito de passar tela de computador/app 16:9 para 9:16 em tela cheia: altura inteira e a câmera percorre a tela.
- `hide`: `[[x0, y0, x1, y1], ...]` normalizados na fonte. Esconde regiões (rótulo, legenda ou marca gravada) com uma cópia desfocada e escurecida do próprio vídeo, para pôr o elemento novo por cima.
- `focus`: `"face"` (padrão, segue o rosto com a câmera virtual), `"auto"` (rosto quando houver; sem rosto, segue o que se mexe de verdade e, parado, o ponto mais saliente), `"center"` ou `[x, y]` normalizado de 0 a 1 (fixo).
- `reframe`: como a câmera virtual de `focus: "face"`/`"auto"` se comporta (estilo Premiere Auto Reframe). Opcional; o padrão é `{"mode": "auto", "deadzone": 0.15, "smooth": 1.0, "max_speed": 1.0}`. Também aceita só o modo, ex. `"reframe": "static"`.
  - `mode`: `"auto"` fica parada quando o alvo varia pouco no plano e segue quando ele anda; `"static"` sempre parada (mediana do plano); `"track"` sempre segue.
  - `deadzone`: zona morta, em fração da largura (e da altura) do recorte. A câmera só sai do lugar quando o alvo passa disso e volta a travar quando o alcança. 0.15 = 15%.
  - `smooth`: segundos para a câmera assentar depois de começar a andar (mola criticamente amortecida). Maior = mais calma.
  - `max_speed`: velocidade máxima em larguras de recorte por segundo.
  - Como funciona: por plano (a câmera recomeça a cada troca de plano detectada pelo `edin scenes` e salta junto com o corte, nunca desliza de um plano para o outro), rosto amostrado a 6 fps seguindo a mesma pessoa (semente = rosto mais persistente x maior), filtro One Euro de ida e volta, antecipação de 0,25 s, zona morta com histerese, mola com velocidade máxima. Rosto em menos de 25% das amostras do plano (de perfil, no escuro) não guia a câmera: ela segue o mapa de atividade com compensação do movimento da câmera original (ORB + RANSAC), e no `"face"` sem atividade fica parada como antes. Aplicado como `crop` com x(t)/y(t) por expressão (`exact=1`, passos de 1 px); `zoom`/`zoom_to` continuam funcionando por cima.
  - Medido (palestra TED 16:9 → 9:16, 2 min, 12 segmentos): rosto dentro do quadro 78,6% → 99,9%; tremor (desvio padrão da derivada de x, px/quadro) 24,6 no rastreio cru quadro a quadro → 6,2, e da 2ª derivada 33,7 → 0,75; nenhuma inversão de direção.
- `speed`: 0.5 câmera lenta, 2.0 acelerado (o áudio acompanha, sem mudar o tom). `edin plan --speed 1.08` aplica em todos os segmentos de fala.
- `broll`: troca só a imagem e mantém a fala. `{"src", "start", "zoom", "zoom_to", "focus"}`. Imagens ganham zoom lento automático.

**Legendas** (`captions`, ou `null` para desligar)
- `style`: `hormozi`, `clean`, `karaoke`, `minimal`.
- `emphasis`: índices das palavras (o `#n` mostrado por `edin text` e `edin timeline`).
- `position`: altura do centro da legenda (0 topo, 1 base).
- Cores no formato ASS `&H00BBGGRR&` (azul, verde, vermelho invertidos).

**Efeitos sonoros**
- `sfx[].at` é o momento do evento **no vídeo final** (veja `edin timeline`). O edin alinha o ponto de sincronia do efeito nesse momento: o ataque de cliques e batidas, o pico de whoosh e riser (que começam antes). Não desconte nada à mão.
- `sfx[].volume` é opcional; o padrão de cada efeito já fica abaixo da voz (cliques ~20 dB abaixo).
- Tipos: `softclick`, `click`, `tock`, `pop`, `snap`, `ding`, `whoosh`, `swoosh`, `boom`, `riser`, `glitch` (sintetizados em camadas, sem direitos autorais).
- `auto_sfx`: `on_zoom` (troca de zoom), `on_emphasis` (palavras de ênfase), `on_cut` (todo corte). Prefira `softclick` a `whoosh` nos automáticos; não ligue `on_zoom` e `on_cut` juntos.

**Voz** (`voice`, ou `null` para desligar; o `edin plan` já liga)
- `clean`: `"dfn"` (DeepFilterNet 3, melhor qualidade), `"rnn"` (RNNoise, mais leve) ou `null`.
- `strength`: redução máxima de ruído em dB (padrão 24). Guarda um pouco do som original para a voz não ficar robótica; 100 = redução total.
- `chain`: `"broadcast"` (corta grave de manuseio, tira o "embolado", de-esser, compressor suave e presença) ou `null`.
- Para limpar um arquivo avulso ou comparar: `edin voice video.mp4` (gera `video_voz_limpa.mp4` e mostra ruído antes/depois).

**Motion** (opcional, Remotion): lista `motion` com efeitos por cima do vídeo editado. Ver [MOTION.md](MOTION.md).

**Música**
- `duck: true` abaixa a música automaticamente quando há fala (sidechain).
- Use músicas livres de direitos (Biblioteca de Áudio do YouTube, Pixabay Music, ou as do próprio Instagram/TikTok adicionadas no app).

## Cenas (`edin scenes`)

`edin scenes video.mp4` detecta as trocas de plano com o PySceneDetect (`AdaptiveDetector`) e grava `video.scenes.json` ao lado (com cache em `~/.cache/edin/scenes`): `cuts` (todos os cortes), `hard_cuts` (trocas de plano de verdade), `detail` (nota de cada corte: correlação de cor e bordas mantidas) e `scenes` (`start`/`end`). Corte com mesma paleta e mesmas bordas dos dois lados (`hard: false`) é conteúdo mudando no mesmo enquadramento (banner, rolagem, texto do motion).

- `--segments` imprime um segmento por cena, pronto para colar no plano; `--hard-only` separa só nas trocas de plano de verdade; `--min-len` junta cenas curtas com a anterior.
- O render usa os cortes sozinho (câmera virtual e `pan` recomeçam por plano). Se não houver `video.scenes.json`, detecta só a janela de cada segmento.
- `edin montage` encaixa cada pedaço num plano só do clipe (sem 2 ou 3 quadros do plano vizinho no começo ou no fim) e usa `focus: "auto"`.

## Como os cortes são feitos

1. As palavras do Whisper decidem **o que** fica (pausas maiores que o limite do preset e fillers como "ahn" viram corte).
2. A energia do áudio decide **onde** cortar: cada borda é estendida até o som da palavra acabar (ou começar), sem engolir a palavra vizinha nem o filler removido. Desligue com `edin plan --no-snap`.
3. Depois do render, `edin verify plano.json final.mp4` retranscreve o resultado e acusa palavras comidas.
