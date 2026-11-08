# Referência profissional: como se editam talking heads de Reels, TikTok e Shorts

Pesquisa de nov/2026 sobre como os talking heads profissionais e virais de 2025 e 2026 são editados (Alex Hormozi, Ali Abdaal, Iman Gadzhi, criadores brasileiros de negócios e educação, guias de Submagic, Opus, Captions e de editores). Serve de régua para o `edin` e para o agente `critico-de-edicao`. Complementa `docs/REGRAS.md`: lá está o que nunca fazer; aqui está o padrão a alcançar.

**Sobre as fontes:** quase tudo vem de blogs de ferramentas, tutoriais de editores e guias de safe zone. Não há norma oficial nem estudo independente. Os números abaixo são o consenso entre as fontes ou o meio-termo quando elas divergem. Quando o número é convenção nossa (não está em nenhuma fonte), aparece marcado como **(edin)**. Medidas em px valem para 1080x1920.

## 1. Enquadramento

| Regra | Valor | Como medir no quadro |
|---|---|---|
| Olhos na linha do terço superior | linha dos olhos em 30% a 38% da altura (y ≈ 580 a 730 px); alvo 33% (640 px) | y médio dos olhos / 1920 |
| Headroom (topo da cabeça até a borda) | 5% a 12% da altura (≈ 100 a 230 px). Menos que isso corta a cabeça no punch-in; mais que ~15% "afunda" a pessoa | y do topo do cabelo / 1920 |
| Plano base | plano médio fechado: do peito para cima, rosto ocupando 30% a 45% da largura (edin) | largura do rosto / 1080 |
| Pessoa centralizada | centro do rosto entre 40% e 60% da largura. Exceção: estilo Ali Abdaal, pessoa levemente deslocada para abrir espaço para texto ao lado | x do rosto / 1080 |
| Punch-in de corte | alterna 1.00 e 1.10 a 1.18 a cada jump cut (disfarça o corte) | escala entre segmentos |
| Zoom de ênfase | 1.15 a 1.30 na palavra-chave, rápido (100% a 115% em ~4 quadros) ou push-in lento (~1,5% a 2% por segundo) | escala e duração da rampa |
| Frequência de ênfase | zoom de ênfase forte só em momentos de impacto (2 a 4 por vídeo de 30 a 60 s); punch-in de corte pode ser em todo corte | contagem |
| Teto de zoom | ~1.30 (acima de ~1.45 perde nitidez e corta a cabeça) | escala máxima |
| Depois do zoom | olhos continuam entre 25% e 40% da altura e a cabeça não sai do quadro | quadro no zoom máximo |

## 2. Legenda

| Regra | Valor | Como medir |
|---|---|---|
| Posição vertical | centro do bloco entre 55% e 75% da altura (y ≈ 1050 a 1440 px). Nunca nos últimos 25% (UI do app: base livre de 450 a 480 px) nem nos 220 px do topo | y do centro do texto / 1920 |
| Margem lateral | ≥ 90 px à esquerda e ≥ 120 px à direita (coluna de botões) | x mínimo e máximo do texto |
| Tamanho da fonte | 65 a 90 px de altura de corpo (3,4% a 4,7% da altura). Negócios e motivacional: 75 a 90 px. Nunca abaixo de 55 px na legenda principal; teto 100 px | altura das maiúsculas em px |
| Peso | bold a black (700 a 900), sans-serif condensada: Anton, Montserrat Black, The Bold Font, Poppins ExtraBold | inspeção |
| Caixa | maiúsculas no estilo Hormozi; frase normal no estilo Ali Abdaal | inspeção |
| Palavras por tela | 1 a 4 (karaokê palavra a palavra: 1 a 3), no máximo 2 linhas e ~15 caracteres por linha | contagem por quadro |
| Contorno ou sombra | sempre um dos dois: contorno preto 6 a 10 px (edin) ou sombra forte (opacidade 100%, desfoque curto). Sem isso o texto some em fundo claro | inspeção ampliada |
| Caixa de fundo | o padrão viral não usa caixa; usa contorno/sombra. Caixa semiopaca só como seguro de leitura em fundo muito poluído | inspeção |
| Palavra ativa | destacada por cor (amarelo, verde ou a cor da marca) e/ou escala 1.1 a 1.2; uma cor de destaque só | inspeção de 2 quadros seguidos |
| Animação de entrada | pop (escala 0,8 para 1,0 em 3 a 6 quadros) ou subida de baixo para cima; sincronizada com a palavra falada | quadros consecutivos |
| Emoji na legenda | opcional, 1 a cada 2 a 4 frases, animado, ao lado ou acima da palavra (estilo Submagic/Hormozi) | contagem |
| Nunca cobre | olhos e boca, em nenhum nível de zoom | sobreposição com o rosto |

## 3. Elementos gráficos

| Elemento | Duração | Onde fica |
|---|---|---|
| Texto de ênfase / título | 1,5 a 2,5 s; entra 200 a 400 ms depois da fala que o nomeia; até 4 a 6 palavras; ≥ 48 px (na prática 80 a 140 px) | terço superior, acima da cabeça, ou ao lado do rosto; nunca sobre olhos e boca |
| "Text-pop" de 1 palavra | 6 a 8 quadros (0,2 a 0,3 s), grande, até metade da tela | centro, por cima de tudo (impacto) |
| Emoji / ícone | 0,8 a 2 s, animado (pop, bounce) | perto da cabeça, ao lado, nunca na frente do rosto |
| Card (lista, número, dado) | 2 a 5 s, entra na palavra que o nomeia e sai quando a ideia acaba | flutuando sobre o vídeo, acima ou ao lado da cabeça; câmera limpa entre um card e outro |
| B-roll | 1,5 a 3 s por plano (abaixo de 1,2 s não dá para entender; acima de 3 s trava o ritmo); flash de b-roll pode ter 3 quadros | tela cheia ou janela grande sobre o vídeo; rosto continua visível em pelo menos 60% a 70% do tempo |
| Print / manchete de notícia | 2 a 4 s, legível (texto do print ≥ 45 px após ampliar), com zoom lento ou destaque da linha importante | tela cheia ou metade superior com a pessoa embaixo; nunca minúsculo no meio |
| Painel fixo | **não existe** no padrão pro: nada fica parado na tela por mais de ~5 s | (todo elemento tem entrada e saída) |

## 4. Ritmo

- **Mudança visual a cada 1,5 a 3 s** (corte, punch-in, b-roll, texto, emoji, card). Medida: 4 a 7 mudanças a cada 10 s. Menos de 4 em 10 s lê como lento; mais de 8 lê como ruído. Nenhum plano estático passa de ~3 a 4 s.
- **Cortes por minuto:** na prática 20 a 40 (jump cut a cada 2 a 4 s), mais as mudanças sem corte (zoom, texto).
- **Silêncio:** pausa acima de ~0,3 s é cortada.
- **Gancho nos primeiros 3 s:** a primeira palavra em até 0,5 s, a proposta do vídeo dita até 3 s, título de gancho na tela (até 6 palavras) e pelo menos uma interrupção visual (zoom, texto) antes de 3 s. Pelo menos uma interrupção de padrão nos primeiros 10 s.
- **Loop no final:** os últimos ~2 s voltam para o gancho (frase ou imagem que emenda com o início) e o vídeo não termina em fade para preto nem em "tchau".
- **Duração:** talking head de negócios e educação rende melhor entre 20 e 60 s; acima de 90 s a retenção cai muito.

## 5. Som

- **Música de fundo** 12 a 18 dB abaixo da voz, com ducking. Ali Abdaal: lo-fi ou ambiente calmo; Hormozi: muitas vezes sem música ou bem baixa.
- **SFX** de -10 a -20 dB relativo: cliques ~20 dB abaixo da voz, whoosh ~16 dB, impacto ~12 dB. Pop/clique em entrada de texto e emoji; whoosh só em transição grande; impacto (boom/riser) no máximo 2 vezes (gancho e revelação). Whoosh em todo corte soa amador.
- **Master** -14 LUFS, pico ≤ -1 dBTP. Voz limpa, sem eco, com volume constante.

## 6. Cor e acabamento

- Correção primária primeiro: balanço de branco neutro, exposição correta no rosto, contraste de meios-tons moderado. Pele natural.
- Imagem nítida: sem perda de definição por zoom acima de ~1.3 nem por upscale de fonte baixa.
- **Sem vinheta, sem glow, sem "névoa" (haze), sem LUT lavado** no padrão limpo de negócios. Vinheta só se for estilo assumido, e muito leve.
- Estilo Iman Gadzhi/Ali Abdaal: imagem levemente dessaturada com uma cor de destaque só (amarelo, por exemplo), repetida nos textos.
- Uma cor de destaque por identidade, a mesma em legenda, cards e ícones.

## 7. O que entrega um vídeo amador

1. **Faixas escuras ou sólidas** (letterbox, quadro 16:9 no meio do 9:16, moldura).
2. **Desfoque largo** (fundo desfocado ocupando faixas grandes, zona borrada visível maior que ~10% da tela).
3. **Névoa, vinheta, glow** ou imagem lavada/escura.
4. **Texto pequeno** (legenda abaixo de 55 px, print ilegível) ou texto sem contorno sumindo no fundo.
5. **Elementos parados:** painel fixo, card que fica 10 s, legenda sem animação, plano igual por mais de 4 s.
6. **Texto na zona da UI** (base 450 px, coluna direita 120 px, topo 220 px) ou sobre olhos e boca.
7. **Cabeça cortada** ou olhos fora do terço superior (pessoa "afundada" no meio da tela ou com testa cortada).
8. **Música mais alta que a voz**, whoosh em todo corte, efeitos em cima da palavra-chave.
9. **Começo lento:** abre em silêncio, "oi, tudo bem", logo ou intro antes do assunto.
10. **Legenda automática sem revisão** (palavra errada, nome errado) e mais de uma cor de destaque disputando atenção.
11. Final em fade para preto ou despedida, sem loop.

## Estilos de referência (resumo)

- **Alex Hormozi:** Anton (antes The Bold Font), maiúsculas, 1 a 4 palavras por tela, palavra ativa em amarelo ou verde, sombra forte e/ou contorno amarelo, pop de baixo para cima, emojis animados, cortes secos sem pausa, zoom em palavras-chave. Legenda no meio inferior da tela, abaixo do queixo.
- **Ali Abdaal:** visual dessaturado com amarelo como única cor, legenda em frase (não palavra a palavra) ao lado da pessoa, sem contorno; pessoa levemente deslocada; planos de 2 a 5 s; música lo-fi baixa; gancho por pergunta.
- **Iman Gadzhi:** cor de destaque tirada da própria filmagem e repetida nos gráficos, look de filme (pretos esmagados, contraste), texto grande de alto contraste, animações minimalistas, zooms e ritmo rápido.
- **Criadores e agências brasileiras:** o que se pede de editor de Reels é corte de pausas e silêncios, legenda sincronizada com palavras-chave destacadas por cor e tamanho, revisão ortográfica em português, zooms para disfarçar corte, cortes secos e exportação em 1080x1920.

## Fontes

- Submagic, legendas estilo Hormozi: https://submagic.co/blog/how-to-make-alex-hormozi-captions
- Submagic, legendas estilo Ali Abdaal: https://www.submagic.co/blog/make-captions-like-ali-abdaal
- Submagic, gerador de legendas e estilos: https://www.submagic.co/ai-caption
- Vidpros, legendas Hormozi: https://vidpros.com/learn-secrets-hormozi-style-video-captions/
- Vidpros, enquadramento de talking head: https://vidpros.com/framing-talking-head-videos-best-practices/
- SendShort, legendas Hormozi: https://sendshort.ai/guides/hormozi-captions/
- SendShort, estilo Iman Gadzhi: https://sendshort.ai/guides/iman-gadzhi-style/ e https://sendshort.ai/guides/captions-iman-gadzhi
- Choppity, estilo Ali Abdaal: https://www.choppity.com/tools/recreate-video-editing-style/ali-abdaal/
- Choppity, mixagem de música e SFX: https://help.choppity.com/articles/0057970-background-music-sfx-and-volume-mixing
- Adobe, caso Ali Abdaal (tempo gasto em b-roll, motion e som): https://blog.adobe.com/en/publish/2024/09/05/how-ai-helps-ali-abdaal-save-hours-every-week
- Resumo "Editing like Iman Gadzhi in 2025": https://recapio.com/digest/the-complete-guide-to-editing-like-iman-gadzhi-in-2025-masterclass-by-joseph-video-editing
- SozAI, análise do estilo Iman Gadzhi: https://sozai.app/transcript/ai-edit-iman-gadzhi-videos/
- BlitzCut, tamanho de legenda em Reels: https://blitzcutai.com/blog/best-caption-size-instagram-reels-2026
- ClipSpeed, legendas e safe zones de Reels: https://www.clipspeed.ai/blog/instagram-reels-captions.html
- Hopper HQ, dimensões e safe zones de Reels: https://www.hopperhq.com/blog/instagram-reel-size/
- TryMyPost, safe zones de Reels: https://www.trymypost.com/blog/instagram-reels-safe-zones-text-placement-2026
- Playbook de retenção vertical (cadência, zoom progressivo, texto): https://strategia-x-v2.pages.dev/blog/2026-07-01-vertical-video-retention-editing-playbook
- Aibrify, legendas e b-roll em vídeo curto: https://aibrify.com/en/blog/short-form-video-editing-captions-b-roll-guide
- Faceless, edição focada em retenção: https://faceless.so/blog/retention-first-editing-boost-short-form-watch-time
- TokCount, microtransições (zoom 115%, plano estático ≤ 4 s): https://tokcount.com/blog/14-micro-cut-transitions-that-keep-completion-rates-above-60-percent
- CapCut, ritmo de b-roll em vídeo educativo: https://www.capcut.com/create/b-roll-pacing-educational-videos
- Joyspace, pattern interrupts: https://joyspace.ai/pattern-interrupt-reset-attention-span
- Opus, efeito de zoom/punch-in: https://www.opus.pro/tools/zoom-in-effect
- Opus, ganchos de TikTok: https://www.opus.pro/blog/tiktok-hook-formulas
- Opus, duração e retenção no TikTok: https://www.opus.pro/blog/tiktok-length-format-retention-data
- Teleprompter.com, regra dos 3 s: https://teleprompter.com/blog/tiktok-3-second-rule
- Vizard, punch-ins rápidos demais: https://agent.vizard.ai/how-to/stop-the-punch-ins-cycling-too-fast-in-a-talking-head-edit.html
- Subscribr, talking head envolvente: https://subscribr.ai/youtube-strategy/editing-talking-head-videos-engaging
- Creator Essentials, headroom: https://www.creatoressentials.com/glossary/headroom/
- Argil, posição da cabeça: https://www.argil.ai/blog/perfect-head-position-setup-for-video-shots-from-manual-basics-to-ai-assistants-2025-modern-filming-guide
- Realoficial, face tracking em vídeo vertical: https://realoficial.com.br/en/blog/face-tracking-for-vertical-video-how-to-use-it-and-why-it-matters-in-2026
- PremiumBeat, cor em talking head: https://www.premiumbeat.com/blog/tips-for-coloring-talking-head-interviews-in-davinci-resolve/
- Spotlark, erros de vídeo vertical (faixas, desfoque): https://spotlarkai.netlify.app/blog/vertical-video-mistakes
- BookingAgency, erros de produção em redes sociais: https://bookingagency.io/blog/common-social-media-mistakes-to-avoid-photo-video-audio-production
- Workana, briefings de editores de Reels no Brasil: https://www.workana.com/job/profissional-de-edicao-de-videos-para-reels-com-foco-em-conteudo e https://www.workana.com/job/editor-de-videos-para-legendar-30-reels-com-padrao-visual-estilo-dramaririesemberg
