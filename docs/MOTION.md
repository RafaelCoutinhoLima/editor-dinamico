# Motion design com Remotion (`edin motion`)

Fluxo: **o edin corta, o Remotion embeleza.** O `edin render` faz cortes, reenquadramento, zoom, som e
(opcionalmente) legenda. Depois o `edin motion` coloca por cima, com [Remotion](https://www.remotion.dev)
(React), os elementos de motion design: palavra gigante atrás da cabeça, título cinético, cards,
checklist, lower third e legenda em pílula.

```bash
edin render video.plan.json -o video_editado.mp4
edin motion video.plan.json video_editado.mp4 -o video_motion.mp4
```

Requisitos: Node.js 18+ (`npx` no PATH). Na primeira vez o `edin motion` roda `npm install` em
`remotion/` e o Remotion baixa um Chrome headless (uns 100 MB).

## Opções

| Opção | O que faz |
|---|---|
| `-o saida.mp4` | arquivo final (padrão `<video>_motion.mp4`) |
| `--matte auto\|on\|off` | recorte da pessoa para a palavra atrás da cabeça. `auto` (padrão): gera só se houver `behind-head-word`; `off`: usa uma máscara pelo rosto |
| `--guides` | desenha as zonas proibidas (vermelho), a faixa da legenda (ciano), a cabeça (verde) e as caixas dos overlays (amarelo). Só para conferir |
| `--props-only` | só gera `props.json` e a mídia em `remotion/public/edin`, para abrir no Remotion Studio |
| `--concurrency N` | quadros em paralelo (nunca acima do número de núcleos) |

Prévia interativa: `edin motion ... --props-only` e depois
`cd remotion && npx remotion studio --props=<caminho do props.json>`.

## A chave `motion` do plano

Lista de overlays. **Tempos em segundos no vídeo final** (os mesmos de `edin timeline` e de `sfx[].at`)
**ou pelo índice da palavra** (`#n` de `edin text`/`edin timeline`), que é o jeito recomendado: o efeito
começa na palavra que o nomeia e continua certo se você mudar os cortes.

| Campo comum | |
|---|---|
| `type` | `behind-head-word`, `kinetic-title`, `card`, `checklist`, `lower-third`, `caption-pill` |
| `start` / `end` | segundos no vídeo final |
| `word` / `word_end` | alternativa: começa no início da palavra `#word`, termina no fim da palavra `#word_end` |
| `duration` | se não houver `end`/`word_end` (padrões: 2,5 s; card 3 s; checklist 4 s; lower third 3,5 s) |

| Tipo | Campos | Onde aparece |
|---|---|---|
| `behind-head-word` | `text` (1 palavra curta), `color`, `size` (px, padrão 300) | atrás da cabeça, centrada nela; a parte de baixo some atrás do cabelo |
| `kinetic-title` | `text`, `emphasis` (lista de palavras na cor de destaque) | acima da cabeça (ou no topo seguro); palavras sobem uma a uma |
| `card` | `title`, `body`, `kicker` | ao lado do rosto (direita, esquerda, acima ou abaixo) |
| `checklist` | `title`, `items`: textos ou `{"text", "word"}` / `{"text", "at"}` | embaixo do queixo (ou acima da cabeça); cada item gira e ganha o check na sua palavra; contador 1/3 |
| `lower-third` | `name`, `role` | canto inferior esquerdo, acima da zona da interface |
| `caption-pill` | `emphasis` (índices), `words_per_page` (padrão 3), `uppercase` | legenda palavra a palavra numa pílula escura, abaixo do rosto. Sem `start`/`end` vale para o vídeo todo |

Cor de destaque: `"motion_accent": "#FFE500"` na raiz do plano, ou use a forma longa
`"motion": {"accent": "#FFE500", "overlays": [...]}`.

**Legenda:** use `caption-pill` **ou** a legenda do edin (`captions`), não as duas. Com `caption-pill`,
renderize o plano com `"captions": null`; o `edin motion` avisa se as duas estiverem ligadas. Se
`caption-pill` não tiver `emphasis`, ele usa `captions.emphasis` do plano.

### Exemplo

```json
"captions": null,
"motion_accent": "#FFE500",
"motion": [
  {"type": "caption-pill", "emphasis": [9, 27]},
  {"type": "kinetic-title", "text": "3 erros que custam caro", "start": 0, "end": 2.3, "emphasis": ["caro"]},
  {"type": "lower-third", "name": "Rafael Coutinho", "role": "edição dinâmica", "start": 0.4, "duration": 3.2},
  {"type": "behind-head-word", "text": "ERROS", "word": 6, "duration": 2.3},
  {"type": "checklist", "title": "3 erros", "word": 13, "word_end": 22,
   "items": [{"text": "Falta de gancho", "word": 14}, {"text": "Legenda ruim", "word": 18}, {"text": "Ritmo lento", "word": 21}]},
  {"type": "card", "kicker": "resultado", "title": "Seu alcance sobe", "body": "gancho, legenda e ritmo", "word": 23, "duration": 2.6}
]
```

## Regras de layout (automáticas)

O posicionamento é calculado uma vez por overlay (`remotion/src/layout.ts`), não à mão:

- **Zonas seguras 9:16:** nada nos 220 px de cima nem nos 320 px de baixo (em 1080x1920), 60 px nas laterais.
  Em 16:9 e outros formatos: 6 % em cima, 8 % embaixo.
- **Nunca cobre o rosto:** usa a trilha de rosto do próprio vídeo editado (`face_track` do edin, já no
  tempo e no enquadramento finais), juntando todas as posições da cabeça na janela do overlay. Primeiro
  tenta ficar fora da cabeça inteira (cabelo incluso); se não couber, só fora do rosto (olhos, nariz,
  boca, queixo); depois reduz o tamanho até 66 %.
- **Sem sobreposição:** overlays que aparecem ao mesmo tempo nunca se cruzam, nem com a faixa da legenda.
  Se um overlay só couber em cima da faixa da legenda, a legenda some durante ele.
- Se não houver espaço nenhum (quadro muito fechado e vários overlays ao mesmo tempo), o overlay é
  **pulado** e o Remotion registra um aviso. Solução: espaçar os overlays no tempo ou enquadrar mais aberto.

## Recorte da pessoa (palavra atrás da cabeça)

Com `behind-head-word`, o `edin motion` gera `person.webm` (pessoa sobre fundo transparente, VP9 com
alfa) só nas janelas desses overlays. Modelo: **PP-HumanSeg** (opencv_zoo, Apache-2.0, 6 MB), rodando no
`cv2.dnn` que o edin já usa, então não há dependência nova. Ele é baixado uma vez em
`~/.cache/edin/models` (mude com `EDIN_MODELS`). Roda em ladrilhos quadrados (o modelo é 192x192),
uns 10 s por 10 s de vídeo em CPU.

Limites: a borda é suave (resolução baixa do modelo), cabelo muito armado perde fios, e funciona melhor
com uma pessoa só e luz estável. Para recorte de qualidade de cinema, gere o `person.webm` com outra
ferramenta (ex.: `scripts/person-matte.py` da skill cinematic-motion-director, que usa MediaPipe) e
troque o arquivo em `remotion/public/edin/` depois de `--props-only`.

Sem recorte (`--matte off` ou se o modelo não baixar), a palavra é escondida por uma máscara oval na
cabeça e nos ombros, calculada pela trilha de rosto. Funciona, mas a borda não segue o cabelo.

## Estrutura de `remotion/`

```
remotion/
  package.json          versões fixas (remotion 4.0.536, React 19.2.0, TypeScript 5.9.3)
  remotion.config.ts
  src/
    index.ts, Root.tsx  composição EdinOverlay (tamanho, fps e duração vêm das props)
    EdinOverlay.tsx     camadas: vídeo -> palavra atrás -> pessoa recortada -> overlays -> legenda
    layout.ts           zonas seguras, rosto, sem sobreposição
    overlays.tsx        cada tipo de overlay
    Captions.tsx        legenda em pílula
    types.ts            contrato das props (o que o edin/remotion_bridge.py gera)
    fonts.ts            Anton e Montserrat (assets/fonts, SIL OFL)
    motion/             parte do motion-kit da skill cinematic-motion-director (MIT, Fabio Fernandes)
  public/edin/          gerada a cada render (vídeo, recorte, fontes); fora do git
```

Para criar um tipo novo: adicione o tipo em `types.ts`, o tamanho e as posições preferidas em
`layout.ts` (`sizeOf` e `candidates`), o componente em `overlays.tsx`, o caso em `EdinOverlay.tsx` e o
nome em `TYPES` (`edin/remotion_bridge.py`).

## Problemas

- **Chrome não abre** (`error while loading shared libraries`): o chrome-headless-shell do Remotion
  precisa de bibliotecas do sistema. No Ubuntu/Debian:
  `sudo apt install libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2`
  (no Ubuntu 24.04+ o último é `libasound2t64`). Ou aponte para um Chrome já instalado:
  `EDIN_BROWSER=/usr/bin/google-chrome edin motion ...`.
- **Disco enchendo:** o Remotion deixa bundles em `/tmp` (`remotion-webpack-bundle-*`); pode apagar.

## Licenças

- **Remotion** não é open source no sentido usual: é **grátis para pessoas físicas e empresas com até
  3 funcionários** (inclusive uso comercial). Empresas maiores precisam de uma
  [licença de empresa](https://www.remotion.dev/license).
- `remotion/src/motion/`: motion-kit da skill cinematic-motion-director, MIT, Copyright (c) 2026 Fabio
  Fernandes (`remotion/src/motion/LICENSE-motion-kit.txt`).
- PP-HumanSeg: Apache-2.0 (opencv_zoo). Fontes Anton e Montserrat: SIL OFL.
