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
- `broll: {"query": "estudante cansado"}` (sem `src`): b-roll grátis do Pexels. No render o edin busca na orientação do vídeo, baixa o melhor clipe que cubra o segmento para `broll/` ao lado do plano (com cache) e grava autor e URL em `broll/CREDITOS.txt`. `"pick": 1` usa o 2º resultado. Para revisar antes, `edin broll --plan plano.json` grava o `src` escolhido no plano. Avulso: `edin broll "consulta" --orientation portrait --n 3`. Precisa da chave grátis em `PEXELS_API_KEY` (sem ela o edin explica como pegar).

**Legendas** (`captions`, ou `null` para desligar)
- `style`: `hormozi`, `clean`, `karaoke`, `minimal`.
- Animação padrão Submagic: cada palavra tem posição fixa (medida pela fonte), o grupo entra subindo com fade e a palavra falada sobe um pouco e cresce (pop 92% → 113% → 110%) sem empurrar as vizinhas, então nada treme.
- `letter_px`: altura das maiúsculas em px numa saída de 1080 de largura (padrão `hormozi` 80, `clean` 70; padrão pro 65 a 90). `scale` multiplica.
- `words_per_group`: 1 a 4 nos estilos animados. Grupo largo demais quebra em 2 linhas.
- `emphasis`: índices das palavras (o `#n` mostrado por `edin text` e `edin timeline`).
- `categories`: segunda cor por categoria, além da cor principal da palavra ativa. `true` liga todas; `["numero"]` só uma; ou `{"numero": "#39FF14", "alerta": {"color": "#FF3B30", "words": ["prova"]}}`. `numero`: algarismos, R$, %, números por extenso, mil, milhões, reais. `alerta`: não, nunca, nada, nenhum, cuidado, erro, pior. Use no máximo 2 cores de categoria.
- `emoji`: `[{"word": 41, "emoji": "🔥"}, {"at": 3.2, "emoji": "💡", "duration": 1.2}]`. PNG do Twemoji animado (pop de entrada, flutuação leve, saída), 150 px em 1080. Fica acima da palavra; se cobrir rosto (detectado no vídeo montado) ou legenda, tenta menor, ao lado da legenda, ao lado da cabeça e abaixo da legenda. `"x"`/`"y"` (0 a 1) forçam a posição; `"size"` muda o tamanho. No máximo 1 emoji a cada 3 s (o render e o `edin captions` avisam).
- `position`: altura do centro da legenda (0 topo, 1 base). No 9:16 a legenda respeita 90 px à esquerda e 120 px à direita.
- `edin captions plano.json` confere sem renderizar: altura da letra, palavras de cada categoria e avisos (tamanho, zona segura, emojis seguidos).
- Cores no formato ASS `&H00BBGGRR&` (azul, verde, vermelho invertidos) ou `#RRGGBB`.

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

**Fonte ruim** (`enhance`, opcional): `{"mode": "fast|esrgan", "scale": 2}` na raiz. Antes de renderizar, troca a fonte principal (e os segmentos com o mesmo arquivo) pela versão ampliada e com nitidez; mesmo fps e duração, então nenhum tempo do plano muda. Fica em cache (`~/.local/share/edin/cache/enhance`, por arquivo + modo): só o primeiro render paga. O `--draft` ignora e usa a fonte original.
- `fast`: ffmpeg `hqdn3d` leve + `scale` lanczos + `cas=0.5`. ~0,5 a 1 s por segundo de vídeo. Ganho pequeno (um pouco mais de nitidez), mas nunca estraga.
- `esrgan`: Real-ESRGAN ncnn/Vulkan, modelo `realesr-animevideov3` (baixado no 1º uso, 47 MB). É o que mais se aproxima do original em 1080, inclusive em rosto; texto e telas de app ficam mais nítidos que o próprio original. Efeitos: pele fica lisa e desfoque intencional (texto "fora de foco" de motion) volta nítido. ~7 s por segundo de vídeo numa RTX 4050 (usa a GPU dedicada sozinho; `EDIN_GPU=n` força outra). Sem GPU Vulkan dedicada cai para `fast` com aviso. `"model": "realesrgan-x4plus"` existe, mas é ~26x mais lento e ficou pior que o padrão; `"tile": 200` se faltar VRAM.
- O `edin check` dá a dica quando a fonte tem menos de 1080 no lado menor e o plano não tem `enhance`.
- Avulso: `edin enhance video.mp4 [--mode fast|esrgan] [--scale 2] [-o saida.mp4] [--ref original_1080.mp4]` (o `--ref` mede SSIM/PSNR contra uma versão em alta).

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

## Cenas (`edin scenes`)

`edin scenes video.mp4` detecta as trocas de plano com o PySceneDetect (`AdaptiveDetector`) e grava `video.scenes.json` ao lado (com cache em `~/.cache/edin/scenes`): `cuts` (todos os cortes), `hard_cuts` (trocas de plano de verdade), `detail` (nota de cada corte: correlação de cor e bordas mantidas) e `scenes` (`start`/`end`). Corte com mesma paleta e mesmas bordas dos dois lados (`hard: false`) é conteúdo mudando no mesmo enquadramento (banner, rolagem, texto do motion).

- `--segments` imprime um segmento por cena, pronto para colar no plano; `--hard-only` separa só nas trocas de plano de verdade; `--min-len` junta cenas curtas com a anterior.
- O render usa os cortes sozinho (câmera virtual e `pan` recomeçam por plano). Se não houver `video.scenes.json`, detecta só a janela de cada segmento.
- `edin montage` encaixa cada pedaço num plano só do clipe (sem 2 ou 3 quadros do plano vizinho no começo ou no fim) e usa `focus: "auto"`.

## Como os cortes são feitos

1. As palavras do Whisper decidem **o que** fica (pausas maiores que o limite do preset e fillers como "ahn" viram corte).
2. A energia do áudio decide **onde** cortar: cada borda é estendida até o som da palavra acabar (ou começar), sem engolir a palavra vizinha nem o filler removido. Desligue com `edin plan --no-snap`.
3. Depois do render, `edin verify plano.json final.mp4` retranscreve o resultado e acusa palavras comidas.
