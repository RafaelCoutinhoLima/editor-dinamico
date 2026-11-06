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
  "auto_sfx": {"on_zoom": "whoosh", "on_emphasis": "pop", "on_cut": "click"},
  "music": {"file": "musica.mp3", "volume": 0.12, "start": 0, "duck": true},
  "loudness": -14
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
- `focus`: `"face"` (padrão, segue o rosto), `"center"` ou `[x, y]` normalizado de 0 a 1.
- `speed`: 0.5 câmera lenta, 2.0 acelerado (o áudio acompanha).
- `broll`: troca só a imagem e mantém a fala. `{"src", "start", "zoom", "zoom_to", "focus"}`. Imagens ganham zoom lento automático.

**Legendas** (`captions`, ou `null` para desligar)
- `style`: `hormozi`, `clean`, `karaoke`, `minimal`.
- `emphasis`: índices das palavras (o `#n` mostrado por `edin text` e `edin timeline`).
- `position`: altura do centro da legenda (0 topo, 1 base).
- Cores no formato ASS `&H00BBGGRR&` (azul, verde, vermelho invertidos).

**Efeitos sonoros**
- `sfx[].at` é o tempo **no vídeo final** (veja `edin timeline`).
- Tipos: `whoosh`, `swoosh`, `pop`, `click`, `ding`, `boom`, `riser`, `glitch` (sintetizados, sem direitos autorais).
- `auto_sfx`: `on_zoom` (troca de zoom), `on_emphasis` (palavras de ênfase), `on_cut` (todo corte).

**Música**
- `duck: true` abaixa a música automaticamente quando há fala (sidechain).
- Use músicas livres de direitos (Biblioteca de Áudio do YouTube, Pixabay Music, ou as do próprio Instagram/TikTok adicionadas no app).
