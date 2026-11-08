# Regras de edição (o que nunca fazer)

Regras tiradas de edições reais. Muitas vêm da skill `cinematic-motion-director` (MIT, Fabio Fernandes), adaptadas ao `edin`. Leia antes do plano e de novo antes do render final. O `edin check` confere boa parte delas automaticamente.

## Corte e fala

- **Nunca confie só nos tempos do Whisper para cortar.** Eles erram nas bordas das frases e já apagaram palavra inteira. O `edin plan` decide o que manter pelas palavras e ajusta a borda do corte pela energia do áudio. Depois do render, rode `edin verify plano.json final.mp4`: 2 ou mais palavras seguidas faltando é corte real; uma palavra solta diferente é ruído do Whisper.
- **Nunca acelere antes de cortar.** Primeiro tira pausa e respiração, depois acelera (`--speed 1.05` a `1.10` soa natural). Pergunte uma vez a velocidade preferida de Rafael e lembre.
- **Nunca deixe corte seco sem disfarce.** Todo jump cut ganha punch-in (alternar zoom 1.0 / 1.12 a 1.18) ou b-roll.
- **Nunca abra no preto ou em silêncio.** A primeira palavra entra em até 0,5 s e o primeiro som em até 0,15 s.
- **Nunca invente número, dado ou depoimento** em título ou legenda. Confira nomes, marcas e números da transcrição (o `edin check` lista palavras com baixa confiança).

## Ritmo e enquadramento

- **Nunca segure o mesmo plano por mais de ~3 s** em Reels/Shorts (algo muda a cada 1,5 a 3 s: corte, punch-in, b-roll, título).
- **Nunca empilhe zoom demais:** até 1.3 nos momentos de impacto. Acima de ~1.45 perde nitidez e corta a cabeça.
- **Nunca corte a cabeça.** Confira na folha de quadros. Rosto de lado ou escuro: use `focus: [x, y]`.
- **Rosto na tela pelo menos 60 a 70% do tempo** em vídeo de pessoa falando. B-roll no máximo 30%.
- **Nunca segmentos menores que 0,25 s** (piscam).
- **O vídeo da pessoa ocupa a tela inteira o tempo todo.** Nunca encolha a filmagem numa janela, moldura, split ou letterbox com faixas sólidas fixas em cima ou embaixo para abrir espaço para cards e legenda.
- **Vertical usa a tela inteira, inclusive ao converter vídeo horizontal.** Nada de quadro 16:9 no meio com faixas (nem da cor do fundo). Tela de app: altura cheia + `pan`. Texto/logo: ampliar e `fit: "extend"`. Pessoa: recorte pelo rosto.
- **Tela de app em vertical: nunca ampliar e recortar.** Tela inteira na largura do celular (`fit: "card"`), título acima, frase abaixo, fundo desenhado na cor da marca. Zoom de 1,8x numa fonte 720p corta a tela e borra o texto.
- **Tela de app no horizontal também fica sem zoom** (`zoom_to: 1.0`), inteira e vinda da fonte melhorada no Real-ESRGAN. Zoom lento (Ken Burns) só em tela de texto/logo. Guarde sempre a fonte original crua junto do projeto (`original.mp4` de verdade, não link para Downloads): sem ela não dá para refazer nada sem o zoom já embutido.
- **Fonte já editada** (legenda ou cards gravados na imagem): avise Rafael que não dá para apagar isso dos pixels e peça a gravação crua. Se ele quiser seguir com aquele arquivo, mantenha a tela cheia e esconda só as zonas dos elementos antigos com uma cópia desfocada e escurecida do próprio vídeo, com borda suave. Os elementos novos entram por cima dessas zonas. Nunca resolva encolhendo o vídeo.

## Texto na tela

- **Nada no topo ~220 px nem na base ~320 px** do 9:16 (interface do app). Legenda com `position` entre 0.55 e 0.78.
- **Legenda nunca cobre olhos ou boca.** Se o rosto está baixo no quadro, suba a legenda; se está alto, desça.
- **Título no gancho:** até 6 palavras, na tela por pelo menos 0,4 s + 0,3 s por palavra.
- **Uma ênfase só:** cor de destaque OU escala, nunca as duas em tudo. No máximo uma palavra de ênfase a cada 2 ou 3 s.
- **Uma cor de destaque por identidade.** Se Rafael tem uma cor de marca, use só ela.
- **Cards, títulos, gráficos e legenda flutuam por cima do vídeo.** Entram quando a fala os nomeia e saem depois. Nada de painel permanente: deixe o vídeo respirar entre um card e outro.
- **Cards com vida curta:** cada card entra na palavra que o nomeia e sai quando a ideia acaba (≈2 a 5 s), com câmera limpa entre um e outro. Cards emendados leem como faixa fixa. Corte os redundantes, que repetem o que a legenda ou a pessoa já mostram.
- **Legenda centralizada na sua faixa e acompanhando o zoom.** Ela fica no centro vertical e horizontal da faixa reservada a ela (inclusive a faixa desfocada que esconde uma legenda antiga) e se move junto com o punch-in: faixa em y0..y1 e zoom `s` em torno de `FACE_Y` dão centro na tela em `FACE_Y + ((y0+y1)/2 - FACE_Y) * s`.
- **Nenhum card cobre cabelo ou rosto em nenhum nível de zoom.** Confira no zoom 1.0 e no máximo: com punch-in a cabeça sobe e cresce, então o card do topo precisa caber acima dela (e dentro da zona desfocada, se houver) no zoom máximo.
- **Tela cheia de texto é exceção:** só por poucos segundos, num momento de impacto.

## Som

- **Whoosh em todo corte soa amador.** Padrão: clique suave (`softclick`) baixinho na troca de zoom. Guarde whoosh para transições grandes e `boom`/`riser` para no máximo 2 momentos (gancho e revelação).
- **Efeitos abaixo da voz:** cliques ~20 dB abaixo, whoosh ~16 dB, impacto ~12 dB. Nunca um impacto em cima de uma palavra-chave.
- **Música só se Rafael mandar ou pedir.** Se ele vai pôr música no app, entregue sem música. Com música: volume 0.08 a 0.15 (≈17 dB abaixo da fala) com `duck`.
- **Master em -14 LUFS, pico ≤ -1 dBTP** (o `edin check plano.json final.mp4` mede).

## Entrega

- **Nunca aprove pelo rascunho.** Confira o arquivo final em resolução cheia: há filtros que só quebram em 1080x1920.
- **Folha de 16 quadros não basta.** Olhe quadros em toda troca de cena e rode `edin check plano.json final.mp4` (varre faixas a 4 quadros/s).

### O que o `edin check plano.json final.mp4` mede no arquivo

Uma passada só do ffmpeg (3 a 5 s para 60 a 100 s de vídeo). `--json` imprime o mesmo relatório em JSON, com as medidas brutas em `medidas` (para os agentes).

- **Tela preta** (`blackdetect`, quadro ≥ 99,8% preto): erro se abrir no preto (≥ 0,3 s) ou se passar de 1 s no meio (0,5 s em vídeo com fala). O último segundo não conta (fade final).
- **Imagem congelada** (`freezedetect`): aviso acima de 1,5 s em vídeo com fala e de 4 s em motion. Quadro final segurado até 2,5 s não conta.
- **Silêncio** (`silencedetect`, -45 dB, só em vídeo com fala): aviso acima de 1,2 s no meio, aviso se abrir com mais de 0,5 s mudo.
- **Áudio** (`ebur128`): loudness, pico real (aviso acima de -0,5 dBTP) e LRA (aviso acima de 15 LU).
- **Técnico** (ffprobe): resolução do formato do plano (rascunho ou proporção errada é erro), yuv420p, fps constante, AAC 48 kHz, `+faststart` (moov antes do mdat), áudio e vídeo com menos de 50 ms de diferença, duração para Reels (aviso acima de 90 s, erro acima de 180 s).
- **Ritmo medido** (`scdet`): cortes por minuto e o maior trecho sem mudança visual. Entrada e saída de título e de overlay de motion contam como mudança. Em 9:16 com fala, mais de 4 s parado é aviso (6,4 s se a câmera estiver em zoom lento).
- **Legibilidade**: corpo da legenda e dos títulos em px no vídeo final; abaixo de 55 px num quadro de 1080 de largura é aviso. **Contraste**: borda grossa ou caixa escura já garantem leitura; quando a cor do texto não contrasta com a própria borda (texto escuro), o fundo é medido na região do texto e abaixo de 3:1 é aviso.

- **Nunca entregue sem conferir o arquivo final** (folha de quadros do vídeo final, não do rascunho) e diga o que foi conferido e o que não foi.
- **Depois de feedback, mexa só no trecho apontado.** Não refaça o vídeo inteiro.
- **Nunca sobrescreva o vídeo original.**
