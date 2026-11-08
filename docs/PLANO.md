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
- `pan`: `"auto"` ou `[x_inicio, x_fim]` normalizados. `"auto"` propõe a câmera pelas bordas do texto (mantém o início da leitura, centraliza conteúdo estreito); confira e troque por manual onde errar. A câmera anda de lado dentro do segmento, com easing. É o jeito de passar tela de computador/app 16:9 para 9:16 em tela cheia: altura inteira e a câmera percorre a tela.
- `hide`: `[[x0, y0, x1, y1], ...]` normalizados na fonte. Esconde regiões (rótulo, legenda ou marca gravada) com uma cópia desfocada e escurecida do próprio vídeo, para pôr o elemento novo por cima.
- `focus`: `"face"` (padrão, segue o rosto), `"center"` ou `[x, y]` normalizado de 0 a 1.
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

## Cortes de vídeo longo: `edin hunt` e cold open

`edin hunt video.words.json [--top 5] [--min 20 --max 60] [--video video.mp4]` acha trechos que começam e terminam em frase inteira e grava `video.candidates.json`:

```json
{"start": 348.11, "end": 381.23, "duracao": 33.1, "range": "348.11-381.24",
 "texto": "...", "gancho_texto": "Um dos discursos sobre a tecnologia...",
 "sinais": {"inicio": "limpo", "fim": "pontuação", "palavras_por_s": 2.3, "silencio_morto_s": 0,
            "perguntas": 0, "numeros": 0, "ganchos": [], "ganchos_no_inicio": [], "tensao": 1,
            "depende_de_contexto": ["como o sérgio já colocou"], "energia_z": 0.1, "energia_inicio_z": 0.3,
            "tom_var_st": 3.0, "picos": 2,
            "pontos": {"gancho": 4, "completude": 12, "ritmo": 14, "voz": 12, "conteudo": 2}},
 "nota_objetiva": 44.0,
 "frase_forte": {"i0": 598, "i1": 602, "texto": "a tecnologia como território neutro,", "nota": 40},
 "rubrica": {"hook": null, "flow": null, "value": null, "trend": null, "total": null},
 "comando": "edin plan video.mp4 --range 348.11-381.24 --name short1 --cold-open 598-602"}
```

- `nota_objetiva` (0 a 100) = gancho nos 3 primeiros s (0 a 30) + bordas completas e sem depender de contexto (0 a 20) + ritmo de fala (0 a 15) + energia e variação de tom da voz em relação ao resto do vídeo (0 a 20, librosa) + densidade de perguntas, números e ganchos (0 a 15). Só ordena o que vale ler.
- `rubrica` (Hook, Flow, Value, Trend, 0 a 25 cada) é preenchida pelo agente `cacador-de-cortes`, que lê a transcrição inteira e reordena o arquivo pelo total.
- Palavras de gancho, conectivos e expressões que dependem de contexto ficam em listas no topo de `edin/hunt.py`.

**Cold open:** `edin plan video.mp4 --range A-B --cold-open` põe no início um segmento de 1 a 3 s com a frase mais forte do trecho (pela nota da frase: gancho, pergunta, número, frase inteira, energia e tom; ignora os 4 primeiros s, que já abrem o vídeo). `--cold-open 598-602` usa os índices de palavra do `edin text`. A frase continua no lugar dela depois (é repetida). O segmento fica marcado com `"cold_open": true`, com punch-in (`zoom` 1.25) para o contexto voltar visivelmente a 1.0, e o plano ganha `"cold_open": {"words": [598, 602], "texto": "..."}`. As bordas seguem a energia do áudio sem pegar a palavra vizinha. As legendas não se misturam porque o segmento fora de ordem abre um bloco novo em `remap_words`. Para trocar a frase à mão num plano pronto, edite `start`/`end` do primeiro segmento (ou rode o `plan` de novo com outros índices).

## Como os cortes são feitos

1. As palavras do Whisper decidem **o que** fica (pausas maiores que o limite do preset e fillers como "ahn" viram corte).
2. A energia do áudio decide **onde** cortar: cada borda é estendida até o som da palavra acabar (ou começar), sem engolir a palavra vizinha nem o filler removido. Desligue com `edin plan --no-snap`.
3. Depois do render, `edin verify plano.json final.mp4` retranscreve o resultado e acusa palavras comidas.
