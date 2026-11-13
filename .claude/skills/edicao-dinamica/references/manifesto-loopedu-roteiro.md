# Manifesto LoopEdu: "onde você trava" (roteiro, 41 s)

Regras gerais em [manifesto.md](manifesto.md). Construção no fluxo I (kit `html-video/`, `edin html --fps 60 --motion-blur 8`, 1080x1920), pessoas do `edin-pessoas.js`, câmera de [higgsfield-camera.md](higgsfield-camera.md). Os ids de estilo e pose abaixo são os do rig; os closes aparecem como `close-maos`, `close-olho-perfil` e `close-pes` (troque pelos ids reais do `edin-pessoas.js` se forem outros).

## Ideia em uma linha

Estudar mais horas não resolve; saber onde você trava resolve, e o tempo que sobra é vida. A imagem conta isso pela luz: a noite fria de tela acesa vira manhã quente ao ar livre. O **ponto laranja** é o fio: o ponto fraco que o LoopEdu acha é o mesmo ponto que vira o sol e depois o anel da logo.

## Elenco e set (defina uma vez, reuse em todos os planos)

- **Protagonista**: estilo `silhueta` com rim light; coque alto, moletom com capuz baixado, mochila de uma alça no ombro direito; 7,5 cabeças de altura. Rosto nunca detalhado. Único que muda de pose ao longo do filme.
- **Multidão** (planos 5, 6, 16, 17): 30 a 60 pessoas em 3 profundidades (`data-z` 0,4 / 0,7 / 1; desfoque 6 / 3 / 0 px). Variar altura (±12%), cabelo (crespo, tranças, liso, raspado, coque), boné, óculos, mochila. Na tensão todos na mesma pose; no convite cada um numa pose diferente.
- **Sets**: (A) quarto à noite: mesa, luminária, janela com prédios e janelas acesas; (B) sala de estudo enorme, fileiras de mesas; (C) rua/ladeira e escadaria abrindo para o céu, sol nascendo à direita; (D) gramado/praça aberta de manhã. Luz sempre atrás do sujeito, acima e à direita.
- **Estilos**: `silhueta` em todos os planos; `traco` só no traço da caneta (plano 2) e nas linhas do caderno. Nada de `ilustracao`.
- **Paleta e grade**: planos 1 a 8 frios (fundo #0f0c2e a #1d2470, rim #8ea2ff, sem laranja exceto o ponto do plano 7); a partir do plano 9 quente (rim #F97316, céu de #4F46E5 a #7C3AED subindo para #ffb68a no horizonte). Grão 5%, vinheta 0,38, constantes. Fonte Sora 700.
- **Sentido de tela**: na tensão, nada anda para a direita (P2 vai para a esquerda); do plano 9 em diante, tudo que anda vai para a direita.

## Tabela de planos

Tempos em segundos. "Texto (sem narração)" é a versão só com texto na tela; "Narração" é o rascunho para o agente `roteirista` (ElevenLabs), e "Texto (com narração)" é a cartela que acompanha a fala. Palavra laranja entre `*asteriscos*`.

| # | tempo | imagem (estilo / pose / enquadramento) | câmera e transição de entrada | texto (sem narração) | narração | texto (com narração) | som |
|---|---|---|---|---|---|---|---|
| 1 | 0,0 a 2,4 | Set A. Protagonista `sentado-estudando`, médio de perfil olhando para a esquerda, luminária fria; mesa e caneca em primeiro plano desfocadas (k 1,5). Pela janela, as luzes dos prédios apagam uma a uma (o tempo passa, sem relógio) | `super-dolly-in` com `intensidade` 0,5 + `handheld` x0,5; `deriva` com `zeroNoInicio` (quadro 0 = capa, câmera neutra) | mais uma hora. (visível desde o quadro 0) | Mais uma hora. | mais uma hora. | pulso grave começa no quadro 0 |
| 2 | 2,4 a 4,6 | `close-maos`: mão em silhueta escrevendo, o traço (`traco`) aparece na página e risca, reescreve | `truck-left` lento (sentido da tensão); corte seco na batida | mais um resumo. | Mais um resumo. | mais um resumo. | batida do pulso no corte |
| 3 | 4,6 a 6,8 | `olhando-celular`, close do perfil iluminado só pela tela; na tela, uma barra de vídeo em "2x" (decorativa) | `rack-focus` do celular (frente) para o perfil; corte seco | mais um vídeo no 2x. | Mais um vídeo no 2x. | mais um vídeo no 2x. | |
| 4 | 6,8 a 9,0 | `close-pes` embaixo da mesa: um pé batendo devagar no chão (um gesto, ansiedade), o outro parado | `static` + `deriva`; corte seco | e a nota não mexe. | E a nota não sai do lugar. | não sai do lugar. | |
| 5 | 9,0 a 11,8 | Set B. Multidão `sentado-estudando` / `cabeca-baixa`, todos iguais, telas frias acesas, fileiras até o fundo | `crane-up` lento (revela a escala); entra por `dissolve` 0,3 | todo mundo estudando tudo. | Todo mundo estudando tudo, | estudando tudo. | pad frio sobe 2 dB |
| 6 | 11,8 a 14,0 | Mesma sala: a câmera encontra o protagonista na fileira do meio (`data-z` 0,7), `cabeca-baixa` mais funda que os outros; a multidão desfoca até 10 px e escurece 30% | `dolly-in` + `foco` com `focoPara` no protagonista (receita "multidão para um"); corte no movimento com a velocidade do crane | do mesmo jeito. | do mesmo jeito. | do mesmo jeito. | o pulso para em 13,8 |
| 7 | 14,0 a 15,0 | Respiro. Quase preto. Protagonista pequeno (≤ 20% da altura) `em-pe` diante da janela, de costas. No horizonte, um ponto laranja mínimo (≤ 1% do quadro) | `static` + `deriva` intensidade 0,3; entra por `dissolve` 0,4 | (sem texto) | (silêncio) | (sem texto) | **silêncio total 1,0 s** |
| 8 | 15,0 a 19,2 | `close-olho-perfil` em silhueta, o ponto laranja refletido na íris crescendo devagar | `dolly-in` muito lento (S 1 a 1,05); entra por `dissolve` 0,3 | 15,15 a 16,95: não é falta de esforço. / 17,05 a 18,8: é não saber onde *trava*. | Não é falta de esforço. [pausa 0,4] É não saber onde você trava. | não é esforço. / é onde você *trava*. | nota única (piano) em 15,0; nada mais |
| 9 | 19,2 a 22,4 | Set C, alvorada. Protagonista de costas, médio, `cabeca-baixa` que ergue para `olhando-horizonte` (transição de pose de 1,0 s entre 19,8 e 20,8, sem corte). Sol nasce à direita; o rim light passa de azul a laranja em 1,5 s | entra por `zoom-through` com `alvo` e `raio` no reflexo do olho (curva cúbica, véu escuro saindo em 0,5 s); dentro, `dolly-in` + `rack-focus` para o horizonte | o *LoopEdu* acha esse ponto. (20,3 a 22,2) | O LoopEdu acha esse ponto | acha esse *ponto*. | segunda nota; respiração de pad quente |
| 10 | 22,4 a 25,0 | Tela do app em `data-tela` (plano da semana): o card "ponto de atenção" com o ponto laranja, e blocos de revisão pousando nos dias (3 dias, texto ≥ 66 px) | `match-cut` `data-match="ponto"`: o disco do sol vira o ponto laranja do card (`dissolve` 0,17, `escalaMax` 1,2 para não clarear); câmera `crane-down` (tela só translada) | e monta sua *revisão* da semana. | e monta a sua revisão da semana. | revisão da *semana*. | **batida entra em 22,4** |
| 11 | 25,0 a 26,8 | `close-pes` andando na calçada para a direita, primeiro passo na batida (rima com o plano 4) | `action-run` (câmera baixa, balanço); corte seco na batida | menos horas no *escuro*. | Menos horas no escuro. | menos horas no *escuro*. | |
| 12 | 26,8 a 28,4 | Protagonista `andando` que vira `correndo`, médio lateral, para a direita; poste e grade passam desfocados na frente | `truck-right` com parallax; corte no meio do passo, velocidade de tela igual ±20% | (sem texto) | (sem fala) | (sem texto) | corte na batida |
| 13 | 28,4 a 30,2 | `subindo` a escadaria, contra-plongée, céu ocupa 60% do quadro, sol atrás (contraluz forte) | `hero-cam`; corte seco | mais tempo lá *fora*. | Mais tempo lá fora. | mais tempo lá *fora*. | crescendo começa |
| 14 | 30,2 a 30,8 | Insert `close-maos`: a mão fecha o caderno na mesa ao sol | `static`; corte seco | (sem texto) | (sem fala) | (sem texto) | batida |
| 15 | 30,8 a 31,6 | `close-maos`: a mesma mão, aberta e erguida contra o céu | `match-cut` `data-match="mao"` (mesmo centro ±2%, escala ±10%, gira até 15°); `static` | (sem texto) | (sem fala) | (sem texto) | batida |
| 16 | 31,6 a 34,4 | Set D, manhã. Grupo ao ar livre, ninguém estudando: conversa, um `apontando` para a direita, outros `em-pe` e `olhando-horizonte`; o protagonista no terço direito, rim laranja | `arc-right`; entra por `dissolve` 0,3 no movimento | estude *melhor*. (grande, centralizado, 120 px) | Estude melhor. | estude *melhor*. | crescendo |
| 17 | 34,4 a 37,2 | Protagonista `bracos-abertos` no centro; a câmera recua e revela a multidão variada em volta, cada um numa pose (receita "um para multidão") | `aerial-pullback`; corte no movimento | viva por *inteiro*. (grande, 120 px) | Viva por inteiro. | viva por *inteiro*. | **pico da música em 34,4** |
| 18 | 37,2 a 41,0 | O sol encolhe e vira o anel laranja da logo LoopEdu, que fecha (37,4 a 38,6); "LoopEdu" embaixo. Nos últimos 0,8 s o anel encolhe até virar a luz da luminária do plano 1 e o quarto noturno volta (emenda de loop) | pullback que volta ao neutro + `deriva` com `saida` 1,2; `match-cut` sol para anel; dissolve final de 0,8 s para o quadro 0 | *LoopEdu* (37,6 a 40,0) | LoopEdu. | *LoopEdu* | nota final com reverb de 1,8 s; o pulso grave volta nos últimos 0,3 s |

Conferência dos números:
- Duração 41,0 s (2.460 quadros a 60 fps). 18 planos, média 2,3 s. Virada (frase-chave) em 15,0 s = 37% do filme; marca em 20,3 s; pico da música em 34,4 s (84%).
- Sem narração: 58 palavras na tela; maior cartela 6 palavras ("e monta sua revisão da semana.", 30 caracteres em 2,4 s = 12,5 c/s). Todas ≤ 13 c/s.
- Com narração: 62 palavras faladas em ~33 s de fala = 1,9 palavra/s; cartelas de 1 a 4 palavras.
- Planos sem texto: 7, 12, 14, 15. Laranja: nenhum até o plano 7; uma palavra laranja por cartela do plano 8 em diante.
- Contrário do óbvio: "estude melhor" sobre gente que não está estudando (16); "mais uma hora" sem relógio, com janelas apagando (1); "não sai do lugar" sobre um pé que bate e não anda (4).
- Contraponto (sugere, não ilustra): planos 1, 4, 7, 9, 13, 15, 16, 17.

## Narração completa (para o agente `roteirista`)

Tom: voz baixa e próxima, sem locutor de anúncio, sem animação forçada. Stability 0,55 a 0,60. Pausas: `...` = 0,3 s; `[pausa X]` em segundos. Durações finais dos planos saem da tabela fala x tempo do `roteirista`; se a fala do plano 8 passar de 4,2 s, alongue o plano 8, nunca o respiro.

```
Mais uma hora.
Mais um resumo.
Mais um vídeo no 2x.
E a nota não sai do lugar.
Todo mundo estudando tudo... do mesmo jeito.
[pausa 1,0]
Não é falta de esforço. [pausa 0,4]
É não saber onde você trava.
[pausa 0,4]
O LoopEdu acha esse ponto
e monta a sua revisão da semana.
Menos horas no escuro.
Mais tempo lá fora.
[pausa 1,6]
Estude melhor.
Viva por inteiro.
[pausa 0,6]
LoopEdu.
```

## Versão só texto (sem narração)

Mesma tabela, coluna "texto (sem narração)". Música escolhida no Instagram: exporte com AAC silencioso estéreo (`--silent-audio`) e deixe as marcas de batida desta tabela (22,4 / 25,0 / 26,8 / 28,4 / 30,2 / 30,8 / 34,4) para Rafael alinhar a faixa; o silêncio do plano 7 continua valendo se a faixa tiver pausa, senão a cena funciona só pela imagem.

## Notas para quem constrói

- Funções reusadas: `montarQuarto` (planos 1, 7 e fim do 18, para o loop), `montarSala` (5, 6), `montarRua` (11, 12, 13), `montarPraca` (16, 17). Ângulo novo = mesma cena com câmera nova.
- O ponto laranja é um componente só (`montarPonto`): reflexo no plano 8, sol no 9, ponto do card no 10, anel no 18. Mesma cor (#F97316) e mesmo halo pelo `EdinVideo.halo()`.
- Transição de pose do plano 9 (`cabeca-baixa` para `olhando-horizonte`) é interpolação do rig em função de `t` (`inOutCubic`, 1,0 s), não corte. Respiração dos parados: ±1,2% a 0,25 Hz, fase diferente por pessoa (semente), nada além disso.
- Texto da cena que sai some antes da janela da transição; no `zoom-through` do plano 9, o texto só aparece depois que o portal passa de 60% (20,3 s).
- Plano 10 é a única tela do app: `data-tela`, largura ≤ quadro, sem zoom; o destaque é o ponto laranja pulsando, sem callout.
- Plano 18: a cena clara não pode dar clarão no loop; o dissolve final de 0,8 s escurece primeiro e só então revela o quarto (salto de brilho < 10 por quadro).
- Conferência: folha de quadros a cada 2 s, sobreposição 50% nos match cuts (9 para 10, 14 para 15, sol para anel no 18), quadro 0 contra o último quadro, e o agente `critico-de-edicao` no final.
