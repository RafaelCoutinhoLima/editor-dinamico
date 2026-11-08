# Prompts prontos (PT-BR)

Cole no agente, dentro da pasta do projeto, e troque o que está entre colchetes. Todos dizem
**estilo, duração, formato, fps, som e cortes nomeados com tempo** — é isso que tira o vídeo da
cara de template. Os estilos citados estão em `references/style-library.md`.

## 1. Reels com a sua voz (ElevenLabs) + avatar na abertura
```text
Use a skill cinematic-motion-director. Narração: [CAMINHO DO MP3]. Avatar: [CAMINHO DO MP4 DO HEYGEN].
Acelere a voz em [1.10]x e corte respiros e pausas (cut-breaths --verify).
Abra com o avatar falando a primeira frase sincronizado com a narração (avatar-sync, sem o áudio dele) e corte para a edição na palavra "[MARCA OU PALAVRA]".
Estilo: [Claude Paper]. 1080x1920, 30 fps. Foto real sempre que citar empresa ou pessoa, com crédito na tela.
Um corte a cada 1,5–3 s. Trilha original sintetizada [ou: sem música, eu coloco], cliques de mouse nas transições.
Antes do render final: storyboard com quadros-chave e a checagem de 3 quadros por tomada.
```

## 2. Vinheta de marca (2 formatos)
```text
Use a skill cinematic-motion-director, estilo Chrome Vignette. Só a Creative seed muda:
marca [NOME], que [O QUE FAZ]; título "[NOME]", subtítulo "[FRASE CURTA]"; cores [HEX 1] e [HEX 2].
Momento principal entre 6,0 e 7,5 s: o título bate na tela junto com o acorde mais forte.
Exatamente 10 s, 30 fps, entregue 1920x1080 E 1080x1920 (re-layout por zonas, não corte).
```

## 3. Lançamento de produto (30 s)
```text
Use a skill cinematic-motion-director, estilo Dark Tech Keynote, para [PRODUTO], que [O QUE FAZ] pra [QUEM USA].
Sem narração; texto na tela em português; trilha eletrônica 120 BPM gerada no código (beat-map antes do storyboard).
Cortes nomeados: 0–4 s o problema em 3 palavras · 4–12 s o produto aparecendo (prints reais: [ARQUIVOS]) · 12–24 s três benefícios, um por batida · 24–30 s logo + [SITE].
1920x1080, depois a versão 1080x1920. Não invente telas: use só os prints que mandei.
```

## 4. Explicativo com dados e fonte
```text
Use a skill cinematic-motion-director, estilo Data Documentary. 60 s explicando [TEMA] pra quem nunca ouviu falar.
Só número com fonte; a fonte fica na tela 2 s quando o número aparece. Antes de começar, me liste os números e de onde vem cada um.
Gancho: o número mais surpreendente nos 3 primeiros segundos; 3 blocos; fecho com a pergunta "[PERGUNTA]".
1080x1920, 30 fps, narração ~150 palavras/min.
```

## 5. Notícia de negócios reagindo a uma manchete
```text
Use a skill cinematic-motion-director, estilo Business News Card. Notícia: [LINK].
Abra com o recorte real da manchete (título, data e veículo) e depois "[A PERGUNTA?]" bem grande com as imagens oficiais das marcas.
Confira os números na matéria antes de usar; o que não tiver fonte entra como "ilustrativo".
Narração: [MP3], acelerada [1.10]x e sem pausas. 1080x1920.
```

## 6. Vídeo de fala (talking head)
```text
Use a skill cinematic-motion-director no modo talking head com [VÍDEO].
Corte respiros e pausas (cut-breaths --verify, nunca por lacuna do Whisper), depois acelere [1.05–1.10]x.
Legendas estilo Pílula, palavra ativa em [COR]; punch-ins só nas frases de impacto; cabeça sempre inteira no quadro.
```

## 7. Clipe com letra sincronizada
```text
Use a skill cinematic-motion-director (references/lyric-and-word-sync.md). Música: [MP3], que é [MINHA / DE UM ARTISTA QUE ME AUTORIZOU POR ESCRITO]. Letra: [TXT].
1) Gere o tempo de cada palavra e me mostre 10 linhas pra eu conferir. 2) Proponha 6–10 cenas, uma por trecho, e espere eu aprovar. 3) 1920x1080, 60 fps; renderize primeiro só o refrão.
```

## 8. Personagem da marca atuando
```text
Use a skill cinematic-motion-director (references/character-animation.md). Personagem: [FORMA, COR HEX, ACESSÓRIO, PERSONALIDADE EM 3 PALAVRAS].
Monte o rig como dados e me mostre a folha de emoções antes de animar.
Cena de 12 s: quer [OBJETIVO] → tenta e falha 2x → consegue de um jeito inesperado → orgulho; termina no logo.
Meu computador [TEM / NÃO TEM] placa de vídeo dedicada.
```

## 9. Checklist / "sinais de que você é…" (pra ganhar seguidor)
```text
Use a skill cinematic-motion-director, estilo Terminal Checklist. Narração: [MP3]; vídeo meu na abertura: [MP4] (com o áudio dele).
Um item por tomada com imagem real, ✓ marcando na palavra exata, contador n/total no topo, resumo final e botão "Seguir" sendo clicado no "me segue".
```

## 10. Revisão: corrigir só o pior trecho
```text
Antes de eu aprovar: monte uma folha de contato com 1 quadro a cada 2 s (shot-pass --every 2) e a checagem de 3 quadros por tomada.
Dê nota de 1 a 10 para: gancho nos primeiros 0,5 s, legibilidade no celular, música x cortes, e se algum quadro parece template de IA.
Aponte o PIOR trecho com o tempo exato, corrija só ele, renderize de novo e pare. Eu reviso e peço o próximo.
```

## 11. Efeitos atrás da cabeça (vídeo falando pra câmera)
```text
Use a skill cinematic-motion-director (references/talking-head-effects.md). Vídeo: [MP4 meu falando].
Rode person-matte.py e me proponha 1 efeito a cada frase de impacto, cada um de 1,5 a 4 s, começando na palavra que dá nome a ele:
palavra gigante atrás da cabeça em "[PALAVRA]", checklist embaixo do queixo nos itens "[A | B | C]", cards orbitando quando eu falar "[...]".
Nada cobre o rosto; zoom no máximo 2x; me mostre um quadro do meio de cada efeito antes do render. Minha identidade: Switzer, laranja #D97757.
```

## 12. Uma cena feita por outra skill dentro do meu Reels
```text
Use a skill cinematic-motion-director como diretora e editora. A cena de [0:12 a 0:20] é [uma prova de matemática / um quadro branco narrado / uma pintura sendo feita]:
faça só essa cena com a skill [manim / whiteboard-video / claude-drawing] (references/animation-skills-ecosystem.md), em 1080x1920 ou normalizada com fundo [#FAF9F5],
e traga o MP4 de volta pra linha do tempo do Remotion com minhas legendas, cliques e espaçamento. Antes de entregar, confira references/never-do.md.
```
