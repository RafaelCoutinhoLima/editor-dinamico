# Reel tutorial de app a partir de gravação de tela

Referência do fluxo G da skill `edicao-dinamica`. Primeiro vem o roteiro passo a passo; no fim, o briefing original de Rafael (2026-11-10), que é a fonte das regras. Na dúvida, vale o briefing.

## Passo a passo

1. **Material:** gravação de tela (.mp4, normalmente horizontal e baixa, ex. 1362x596), logo oficial (`logo.jpeg`, nunca o `icone-512.png` do app), fontes Sora 600/700 e Inter. Copie tudo para a pasta do vídeo (cópia de verdade). Narração: a de Rafael, se ele mandou; senão o agente `roteirista` escreve e gera.
2. **Cenas:** `edin scenes gravacao.mp4 --hard-only` e folhas de contato a cada 3 a 4 s. Liste as cenas úteis na ordem do app (matéria, assuntos, ementa, períodos, dias, horário, semana, Lupe, tutor, questões, ajuda, correção, resumo, revisões, mapa, evolução, insígnias). Corte cadastro e qualquer dado pessoal.
3. **Roteiro e voz:** dispare o agente `roteirista` com o objetivo, a lista de cenas (ou as folhas) e a duração alvo (abaixo de 2 min). Ele devolve `narracao/roteiro.txt`, `narracao/voz.mp3`, o alinhamento e a tabela fala x tempo. Voz padrão: "Yuri - Natural Brazilian Narrator" (Voice Library do ElevenLabs), Stability 0.50, Similarity 0.75, modelo `eleven_v4` (o `edin tts` cai para `eleven_v3` se o v4 não existir e avisa).
4. **Montagem quadro a quadro** (Python com OpenCV + PIL mandando rawvideo para o ffmpeg), 1080x1920, 30 fps, H.264 yuv420p, AAC, abaixo de 2 min:
   - fundo `linear-gradient(160deg, #1e1b4b 0%, #191a3f 45%, #0f172a 100%)` com halos índigo rgb(79,70,229);
   - cartão do vídeo com 1000 px de largura, centro em y=960, cantos de 32 px, sombra;
   - legenda em pílula de vidro (branco 13%, borda 24%), Sora 600 46 px, 40 px acima do cartão, no imperativo falando com o aluno (nunca primeira pessoa), trocando junto com a câmera com fade de 0,3 s;
   - rodapé fixo: ícone de 60 px + "LoopEdu" em Sora 700, y ≈ 1610;
   - degradê de destaque #818cf8 → #a855f7 → #ff6b4a só em "LoopEdu" da intro e em "Viva por inteiro." do fechamento.
5. **Câmera dentro do cartão:** quadros-chave (t, cx, cy, w, h) com smoothstep e empurrão contínuo de ~3,5%. Zoom certeiro, conferido numa grade de coordenadas, sem cortar o que importa. Telas grandes abertas; detalhe fechado. Dissolver entre cenas em 0,3 s.
6. **Sincronia com a narração** (tabela do `roteirista`, ou `edin falas voz.mp3 roteiro.txt`): uma fala por cena, cortada no meio do silêncio (`corte_sugerido`); a fala entra 0,15 s depois do início da cena (0,3 s na intro), fades de 20 ms; cena = fala + 0,3 a 0,6 s (ajustando velocidade e escalando quadros-chave e legendas); ajuda e correção sem mudar velocidade; o fechamento cobre a última fala. **Nenhum silêncio maior que 1 s** no vídeo (o primeiro foi reprovado por pausas de 3 s).
7. **Conferência:** folha de contato a cada 3 a 4 s (legenda certa, nada cortado, nenhuma insígnia bloqueada no zoom final, nenhum dado pessoal), quadros únicos dos momentos críticos, tabela de silêncio do vídeo final (`silencedetect=noise=-35dB:d=0.35`), duração abaixo de 2 min, textos em português com "LoopEdu" e sem travessão. Depois, o agente `critico-de-edicao` com o vídeo final.

## Lições do primeiro Reel (2026-11-10), aplicar sempre

Cada item é uma correção de Rafael ou do `critico-de-edicao`.

- **"Tá muito acelerado":** cenas a 1,5x a 1,8x foram reprovadas. Teto de 1,15x (digitação até 1,5x). Se a fala é curta, corte o tempo parado da gravação; não acelere.
- **"As imagens tão com um lagzinho":** veio de juntar quadros quase iguais para poupar ESRGAN (o cursor andava de 4 em 4 quadros). Amplie todos os quadros usados.
- **"Ajuste o cursor, tá meio travado":** o próprio gravador de tela entrega o cursor parando e saltando. Solução aprovada: `cursor_modelos.py` (modelos de seta e mão por diferença entre dois quadros, miolo preenchido por flood fill), `cursor_detectar.py` (matchTemplate com máscara; score < 1500 é cursor, acima é cursor de texto ou escondido, e aí fica o original), `cursor_limpar.py` (tapa com o mesmo lugar de um quadro vizinho com o fundo igual, senão inpaint; trajetória com gaussiana de 2,5 quadros) e o desenho em `montar.py` (`cursor_pos`/`draw_cursor`).
- **Tempo de fala:** `edin falas` errou quando a narração tinha mais pausas internas do que trocas de fala (juntou "Primeiro, você digita..." com a fala seguinte). Confira as falas com `edin transcribe` num trecho antes de montar.
- **Silêncio:** respiro de 0,75 s entre falas (0,15 s de entrada + 0,6 s de cauda) ficou bom; o limite é 1 s.
- **Dados pessoais:** a conta de teste ("Theo Montenegro") aparece na barra lateral, na saudação e no cartão de nível. Tape (lista `HIDE`).
- **"Cuidado com esses zooms, perde partes das imagens":** zooms que cortavam o campo do nome, a lista de assuntos, as linhas dos períodos, as colunas da semana, o resumo e o cartão de nível foram reprovados. Regra: a borda do enquadramento cai no vão entre blocos; tela de duas colunas fica na largura inteira do conteúdo (sem a barra lateral); o movimento é só o empurrão leve. Ao abrir mais o quadro, confira se apareceu dado pessoal que antes ficava fora ("Boa noite, Theo" voltou na Lupe).
- **Zoom:** confira as bordas do cartão em cada quadro-chave. Título ou enunciado cortado ao meio foi apontado pelo crítico. No zoom final das insígnias, feche na conquistada (cerca de 420 px da fonte) e escureça o resto.
- **Legenda × fala:** a troca de legenda e de tela tem que esperar a palavra. "Ganhe insígnias" entrou 1,4 s antes da voz; resolvido congelando o painel anterior.
- **Áudio:** -14 LUFS, estéreo.
- **Scripts reaproveitáveis** em [reel-tutorial/](reel-tutorial/): copie a pasta para `scripts/` do vídeo novo e troque só `cenas.py` (trechos, câmera, legendas, `HIDE`, `PATCH`). Ordem: `extrair.py` → ESRGAN de `rascunhos/src_raw` para `rascunhos/src_x2` (`realesr-animevideov3 -s 2`) → `cursor_modelos.py` (ajuste os dois instantes dos modelos) → `cursor_detectar.py` → `cursor_limpar.py` → `montar.py`.

## Roteiro modelo (aprovado)

```
Vou te mostrar como usar o LoopEdu em menos de dois minutos.

Primeiro, você digita a sua matéria.

Na hora, ele já sugere os assuntos. E se você tiver a ementa do professor, cola aqui ou manda o PDF, que o plano fica do jeito que o seu professor cobra.

Depois, você escolhe o período do dia e os dias que quer estudar.

Se preferir, dá pra montar o horário hora por hora, do seu jeito.

Pronto, ele monta a sua semana sozinho. E se não der pra fazer um bloco, é só remarcar.

Aqui é a Lupe. Ela sabe o que você tem pra estudar e responde tudo em cima do seu plano.

Na hora de estudar, o tutor explica o assunto com você, passo a passo, no seu ritmo.

Depois, você revisa com questões.

Se travar em alguma, pede ajuda ali mesmo, sem sair da questão.

E quando responde, ele mostra a correção e explica o porquê.

No final, você ganha um resumo do que importa, as revisões já entram na sua semana, e ainda tem um mapa do que você estudou.

E aqui você acompanha a sua evolução: o seu nível, o que falta pro próximo e as insígnias que vai desbloqueando enquanto estuda.

LoopEdu. Estude melhor, viva por inteiro.
```

## Briefing original de Rafael

### Briefing de Rafael: Reel tutorial do LoopEdu a partir de gravação de tela (2026-11-10)

Pontos-chave (resumo fiel do pedido):
- Entradas: gravação de tela .mp4 horizontal (ex. 1362x596), narração .mp3 do ElevenLabs, logo oficial logo.jpeg (símbolo branco sobre degradê índigo→coral, 1600x1600; nunca o icone-512.png do app), fontes Sora 600/700 (+Inter).
- Saída 1080x1920, 30 fps, H.264 yuv420p, AAC, abaixo de 2 min. Montagem quadro a quadro em Python (OpenCV+PIL) → ffmpeg rawvideo.
- Identidade: fundo linear-gradient(160deg,#1e1b4b 0%,#191a3f 45%,#0f172a 100%) + halos índigo rgb(79,70,229); cartão do vídeo 1000 px de largura, centro y=960, cantos 32, sombra; legenda em pílula de vidro (branco 13%, borda 24%), Sora 600 46 px, 40 px acima do cartão; rodapé fixo ícone 60 px + "LoopEdu" Sora 700 em y≈1610; degradê de destaque #818cf8→#a855f7→#ff6b4a só em "LoopEdu" da intro e "Viva por inteiro." do fechamento. Marca sempre "LoopEdu", masculino.
- Intro 4,5 s cheia (ícone 230 px com brilho entrando 0,75→1; pílula TUTORIAL; "Como usar o"/"LoopEdu" degradê; "em menos de 2 minutos"; 3 miniaturas giradas +7/−6/+3 em leque; pílulas "Matéria · Rotina · Estudo · Revisão"; entradas em sequência, sai com fade 0,4 s).
- 12 cenas com legendas no imperativo falando com o aluno (nunca primeira pessoa): Digite sua matéria; Receba os assuntos sugeridos → Ou cole a ementa do professor; Escolha os períodos do dia → E os dias da semana; Se preferir, monte seu horário; Sua semana personalizada; Tire dúvidas com a Lupe; Estude com o tutor de IA; Revise com questões; Travou? Peça ajuda; Veja a correção; Veja o resumo da aula → Revisões já na sua semana → O mapa do que você estudou; Acompanhe sua evolução → Ganhe insígnias estudando. Legenda troca junto com a câmera, fade 0,3 s.
- Fechamento ~3,7 s: ícone com brilho, "LoopEdu", "Estude melhor." branco, "Viva por inteiro." degradê, pílula "Link na bio".
- Câmera por quadros-chave (t, cx, cy, w, h) com smoothstep + empurrão contínuo ~3,5%; zoom certeiro sem cortar o importante (conferir em grade de coordenadas); telas grandes largas; detalhes fechados; Lupe mostra painel inteiro + pedaço do app atrás; pedir ajuda: medir abertura exata da janela e centralizar no mesmo instante; conquistas: passeio visão geral → nível → coleção → zoom só na insígnia conquistada, nunca em bloqueadas; dissolver cenas 0,3 s.
- Ritmo: começar quando o nome certo começa a ser digitado; nada de cadastro/dados pessoais; acelerar navegação até ~2x, nunca o que precisa ser lido; ajuda e correção em velocidade normal (cortar tempo morto antes); congelar correção 2 a 3 s; períodos e evolução ~4 s; semana ~5 s.
- Narração: tom natural, sem perguntas retóricas, frases curtas afirmativas. Roteiro modelo:
  "Vou te mostrar como usar o LoopEdu em menos de dois minutos. / Primeiro, você digita a sua matéria. / Na hora, ele já sugere os assuntos. E se você tiver a ementa do professor, cola aqui ou manda o PDF, que o plano fica do jeito que o seu professor cobra. / Depois, você escolhe o período do dia e os dias que quer estudar. / Se preferir, dá pra montar o horário hora por hora, do seu jeito. / Pronto, ele monta a sua semana sozinho. E se não der pra fazer um bloco, é só remarcar. / Aqui é a Lupe. Ela sabe o que você tem pra estudar e responde tudo em cima do seu plano. / Na hora de estudar, o tutor explica o assunto com você, passo a passo, no seu ritmo. / Depois, você revisa com questões. / Se travar em alguma, pede ajuda ali mesmo, sem sair da questão. / E quando responde, ele mostra a correção e explica o porquê. / No final, você ganha um resumo do que importa, as revisões já entram na sua semana, e ainda tem um mapa do que você estudou. / E aqui você acompanha a sua evolução: o seu nível, o que falta pro próximo e as insígnias que vai desbloqueando enquanto estuda. / LoopEdu. Estude melhor, viva por inteiro."
- Voz: ElevenLabs, "Yuri - Natural Brazilian Narrator" (voz profissional PVC da Voice Library), Stability 50, Similarity 75, modelo v4 (v3/v4 ignoram <break time>; não depender de pausas no texto; sincronia feita na montagem). Gerar com linha em branco entre as falas.
- Sincronia: silencedetect noise=-35dB d=0.35, cortar uma fala por parte no meio de cada silêncio; fala entra 0,15 s após início da cena (0,3 s na intro), fades de 20 ms; cena = fala + 0,3 a 0,6 s (mudando velocidade e escalando quadros-chave/legendas); ajuda e correção sem mudar velocidade; fechamento cobre a última fala; tabela fala × cena com silêncio final, NENHUM silêncio > 1 s (primeiro vídeo foi reprovado por pausas de 3 s).
- Conferência: folha de contato a cada 3 a 4 s (legenda certa, nada cortado, nenhuma insígnia bloqueada no zoom final, nenhum dado pessoal), quadros únicos dos momentos críticos, tabela de silêncio, duração < 2 min, textos em português com "LoopEdu" e sem travessão.
