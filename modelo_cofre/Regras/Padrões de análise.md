---
tipo: regra
tags: [regra]
---
# Padrões de análise

O Claude lê esta nota antes de cada análise. Edite à vontade: a próxima análise já segue a versão nova.

## Entradas
1. **Transcrição local** (`transcrever.py`): faster-whisper (modelo em `config.json` → `whisper_modelo_analise`; `turbo` com placa NVIDIA, `small` na CPU), com o tempo de cada palavra e pontuação → `_analise/transcricao.json` e `transcricao.txt`. Com GPU NVIDIA (RTX 3050) foi medido ~16× o tempo real (3 h de vídeo ≈ 11 min); na CPU é bem mais lento. Se a GPU falhar, cai para a CPU sozinho.
2. **Grade de quadros** (`sinais.py`): 64 quadros com o tempo → `_analise/grade.jpg`.
3. **Intensidade do áudio** (`sinais.py`): volume e velocidade da fala por trecho (0 = média; acima de 0,5 = bem mais intenso).
4. **Dados do YouTube** (`youtube.py`, com yt-dlp + Deno ou Node.js): "Mais repetidos", comentários que citam um tempo e chat da live, por minuto → `_analise/youtube_resumo.txt`. Nem todo vídeo tem "Mais repetidos" ou chat gravado; os comentários com tempo quase sempre existem.

## Ajuste fino das bordas (automático, em `planilha.py`)
- Depois que o Claude escolhe os cortes, `bordas.py` leva o início para o **começo da frase** e o fim para o **fim da frase**, usando a pontuação e as pausas da transcrição.
- Respiro: 0,2 s antes da primeira palavra e 0,35 s depois da última, sem pegar a fala seguinte. Com 5 ou mais correções marcadas nas notas, o respiro é recalibrado pela média (`_sistema/calibracao.json`).
- Se a frase completa estiver a mais de 8 s, a borda não é movida e a planilha recebe o aviso "começa/termina no meio de um raciocínio".
- Conferência rápida: `_analise/bordas.txt` mostra as palavras de cada lado de cada borda.

## Correções depois da edição
- Na nota do episódio, cada corte tem `ajuste (s): início 0 · fim 0`. Troque os números (início `-2` = começa 2 s antes; fim `+3` = termina 3 s depois) e diga "aplicar ajustes de <episódio>".
- Só os cortes alterados são refeitos (a versão anterior vai para `_analise/substituidos`), e a finalização refaz só os finais correspondentes.

## Categorias
| Categoria | Duração | Para quê |
|---|---|---|
| Corte longo | mais de 3 até 40 min | Um assunto, história ou discussão completa, para o YouTube; cada assunto em um longo só |
| Corte curto | até 3:00 (ideal 1:00 a 2:30) | Uma história curta completa (gancho, desenvolvimento, conclusão) ou uma frase de efeito; YouTube Shorts, Reels e TikTok |

Corte curto não passa de 3:00 (limite do YouTube Shorts e do Instagram Reels) e pode sair de dentro de um longo. Planilhas antigas com "Corte médio" ou "Short/Reels" continuam aceitas (o médio gera só a versão vertical; "Short/Reels" vira "Corte curto").
| Remover (anúncio / outros) | — | Publicidade, abertura e encerramento soltos, bastidores, problema técnico, música |
| Atenção (políticas / direitos / monetização) | — | Ver [[Políticas e alertas]] |

- Início e fim **no limite das falas** (precisão de ~1 s): o corte começa no início de uma frase e termina no fim de outra.
- A primeira frase do corte é registrada para conferir se prende.
- Dentro de cada categoria, os cortes são ordenados da maior para a menor nota.

## Planilha `Cortes_<tema>.xlsx` (formato v2)
**Aba Cortes**, a partir da linha 3:
`Nº | Categoria | Início | Fim | Duração | Título / Tema | Nota (0–10) | Gancho | Autossuf. | Emoção | Frase | Tema em alta | Intensidade do áudio | Título 1 – citação | Título 2 – pergunta | Título 3 – busca | Texto da capa | Primeira frase | Observação`

- Linha 1: título do episódio. Linha 2: nota de precisão ("ajustados ao limite das falas").
- Duração e Nota por fórmula. Cores por categoria e filtro na tabela.
- Abas: **Critérios** (como a nota é calculada), **Desempenho** (preenchida por você), **Resumo** (quantidade, duração e nota média por categoria).

## Títulos
Três por corte, mais o texto da capa:
- **Citação**: "'Frase' – Pessoa".
- **Pergunta/conflito**.
- **Busca**: nome e tema nas primeiras palavras.

Regras: o nome ou o tema principal vem primeiro; toda opinião é atribuída a quem falou; o título não promete o que o corte não mostra.

## Instruções que o Claude deixa para a edição (coluna Observação)
- "bipar" ou "bipe" → os palavrões do Short recebem bipe na edição.
- "conferir", "verificar", "atribuir", "manter a linguagem" em Atenção → o trecho **fica** no corte e vira alerta.

## Seleção dos cortes (12/11/2026)
- **Mapa de momentos** (`momentos.py` → `_analise/momentos.md`): ranking de trechos de 30 s por intensidade do áudio, "Mais repetidos", chat, comentários com tempo, ganchos na fala e nomes citados. Rodar antes de ler a transcrição; depois do `cortes.json`, rodar de novo para ver os momentos fortes que ficaram FORA dos cortes.
- **Validador** (`validar_cortes.py`, chamado pelo `planilha.py`): além do formato, aponta GANCHO (corte que começa com "isso aqui", "ele", "como eu falei"…, com sugestão de início alternativo), FIM (termina em pergunta ou conectivo), REPETIÇÃO entre cortes e "Tema em alta" = 2 sem fonte.
- **Tema em alta com fonte:** o critério só vale 2 com link de notícia na chave `fonte_em_alta` do `cortes.json` (vai para a Observação); sem notícia, vale 1.
- **Tempos exatos:** `tempos.py` acha o tempo de cada frase na transcrição.

## Seleção dos cortes v2 (13/11/2026)
Ordem da análise: `youtube.py` → `momentos.py` → `triagem_llm.py` (chama o `momentos.py` de novo no fim) → leitura da transcrição com o mapa aberto → `_analise/candidatos.md` → `cortes.json` → `planilha.py` → `momentos.py` (o que ficou FORA).

**O que o mapa (`_analise/momentos.md`) traz agora**
1. Trechos fortes de 30 s. O chat conta **reações** (risada, choque, aplauso) além do volume, **sem a tendência da live** (o chat cresce sozinho no começo e no fim) e com **20 s de atraso** (o chat reage depois da fala). Abertura e encerramento (3 min) não contam reação do chat; cumprimento, pedido de like e leitura de superchat descontam.
2. **Candidatos de Short prontos**: 25–90 s no limite de frases, sem começo dependente ("isso aqui", "ele", "por isso", "enfim"), sem abertura de navegação ("vamos lá", "põe na tela", "próximo") e sem fim em conectivo, vírgula ou pergunta. Os tempos já vêm em segundos para o `cortes.json`.
3. **Assuntos do episódio**: onde o vocabulário muda, com palavras-chave e sugestão (longo ou curto). É o ponto de partida dos longos.
4. **Triagem por LLM** (`triagem_llm.py`, API de LLM configurada (`config.json` → `llm`)): segunda leitura da transcrição em blocos de 12 min. Os tempos vêm de citação exata conferida na transcrição, nunca do modelo. Envia só a transcrição do vídeo público, o título e comentários públicos.

**Rubrica do bom momento**
- **Corte curto**: uma ideia completa. A 1ª frase prende sozinha (pergunta, afirmação forte, número, conflito), o meio desenvolve e o fim fecha a ideia (conclusão, piada, frase de efeito). Ideal de 1:00 a 2:30; abaixo de 45 s só frase de efeito que se sustenta sozinha; nunca depende do que veio antes.
- **Longo**: um assunto inteiro da seção 3 (história, reação ou discussão completa), do fato ou da pergunta que o dispara até a conclusão; só junte assuntos vizinhos quando forem o mesmo tema.

**Revisão em duas fases** (`revisar_cortes.py`): (1) longos mostrados sobre o episódio inteiro, com os trechos sem corte à vista, para o usuário aprovar, recusar, aumentar, diminuir ou propor; (2) curtos propostos dentro dos longos aprovados, com a mesma revisão. Cada fase é gravada no `cortes.json` por `aplicar_revisao.py --aplicar`; bordas ajustadas na revisão não são movidas pelo ajuste fino.
- **Prioridade**: conteúdo forte **com** sinal da audiência (reação no chat, "Mais repetidos", comentário com tempo) vem antes de conteúdo forte sem sinal, que vem antes de sinal sem conteúdo. Sinal sozinho não basta: cumprimento, nome da live e leitura de superchat inflam o chat.
- **Concordância**: momento apontado por duas fontes (sinais, Short pronto, triagem LLM) entra na lista, salvo motivo; cite a concordância na Observação.
- **Fora dos cortes**: todo candidato de Short com nota ≥ +2,5 e todo candidato da triagem com nota ≥ 8 que ficarem fora precisam de um motivo dito ao usuário (repetido, risco, depende de contexto, fraco na leitura).
- **Descartar**: abertura e cumprimentos, despedida, pedido de like, anúncio, leitura de superchat sem resposta interessante, navegação de tela, conversa técnica da live.

### Acréscimos de 13/11/2026 (tarde) — entrega da fala, gancho e juiz
Ideias adaptadas do repositório EverythingAI-Pro/ai-video-editor (licença MIT); só o que melhora a escolha dos momentos. O que foi recusado está em [[Decisões]].
- **Entrega da fala** (Shorts prontos): energia do áudio 50 vezes por segundo (`_analise/energia_50hz.npy`, refeita só se o vídeo mudar). Soma pontos o **pico** de energia acima da fala normal, a **variação** (animado × monótono) e uma **pausa** curta logo antes do início.
- **Tipo de gancho** nas duas primeiras frases: curiosidade, alvo, número, contrário, confissão, resultado, chamada, proibido. Cada tipo (até 2) soma pontos e aparece na coluna "Gancho" do mapa.
- **Gaguejada**: palavras repetidas em sequência ("é é", "o o cara"). Acima de 5%, o Short perde pontos no mapa e o `validar_cortes.py` avisa. Limite: o Whisper costuma limpar repetições, então o sinal pega só as gaguejadas mais fortes.
- **Juiz final** (`juiz_llm.py`, chamado no fim da triagem ou pela etapa `juiz` da fila): uma chamada ao API de LLM configurada (`config.json` → `llm`) avalia os Shorts prontos e rejeita meio de raciocínio, preparação sem conclusão, fala atropelada ou dependência de contexto. Coluna "Juiz" no mapa: ✔ aprovado ou ✘ rejeitado, com o motivo.
- **Rubrica**: Short rejeitado pelo juiz só entra com motivo dito ao usuário. Short aprovado pelo juiz **e** com sinais fortes é prioridade.
