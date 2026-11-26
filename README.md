# Cortes de vídeo — skill para o Claude

Transforma lives e podcasts em **cortes longos para o YouTube** e **cortes curtos para YouTube Shorts, Reels e TikTok**, de ponta a ponta, conversando com o Claude. Tudo roda no seu computador; os arquivos ficam numa pasta comum que também abre no Obsidian.

**Versão atual: 1.2.0** — o que mudou está em [Novidades](#novidades-da-120) e, em detalhe, no [`CHANGELOG.md`](CHANGELOG.md).

## Sumário
- [O que a skill faz](#o-que-a-skill-faz)
- [Novidades da 1.2.0](#novidades-da-120)
- [Requisitos](#requisitos)
- [Tempo de processamento](#tempo-de-processamento)
- [Instalação](#instalação)
- [Uso](#uso)
- [Atualizar](#atualizar)
- [Privacidade e segurança](#privacidade-e-segurança)
- [Direitos autorais](#direitos-autorais)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Licença](#licença)

## O que a skill faz
| Etapa | O que acontece | Resultado |
|---|---|---|
| 1. Análise | Transcrição local com o tempo de cada palavra (faster-whisper); sinais de audiência do YouTube (momentos mais repetidos, comentários com tempo, reações no chat da live); mapa de momentos; divisão do episódio por assunto; segunda leitura por LLM, opcional | Planilha `Cortes_<tema>.xlsx` com os cortes, notas por critério, três títulos, texto da capa e hashtags, conferida por um validador |
| 2. Revisão visual | Página no navegador, em duas fases: primeiro os cortes longos sobre o episódio inteiro (inclusive o que ficou sem corte), depois os cortes curtos dentro dos longos aprovados | Cortes aprovados, recusados ou ajustados por você |
| 3. Edição | Longos em 16:9 sem recodificar; curtos em 9:16 com fundo desfocado e sem pausas longas; remoção de anúncios e trechos de risco; bipe em palavrões | `Cortes/Longos` e `Cortes/Cortes Curtos` |
| 4. Finalização | Identidade visual do canal: intro, marca d'água, tela final, capas 1280×720, legenda com palavra destacada e uma versão de cada corte curto por plataforma; volume em −14 LUFS | `Publicar/Longos`, `Publicar/Capas` e `Publicar/Cortes Curtos/{YouTube, Instagram, TikTok}` |
| 5. Publicação e notas | Textos de publicação (títulos, descrição, hashtags, crédito ao canal original) e notas do Obsidian com painel, estado de cada episódio e regras editáveis | `Publicar/Textos de publicação.md` e notas do cofre |

Durações: **corte curto** até 3:00 (o ideal é de 1:00 a 2:30, com começo, meio e fim) · **corte longo** de mais de 3 até 40 min, um assunto por corte.

## Novidades da 1.2.0
- **Revisão visual dos cortes em duas fases** (`revisar_cortes.py`). Abre no navegador uma linha do tempo do episódio, no estilo de um editor de vídeo: assuntos, cortes longos, trechos sem corte, remoções, miniaturas, forma de onda e reação do público. Para cada corte você aprova, recusa, arrasta as bordas ou usa os botões de ajuste fino; pode propor um corte num trecho vazio, marcar pontos e escrever pedidos. A revisão é gravada no `cortes.json` com `aplicar_revisao.py` ou pelo botão **Aplicar** da página. As bordas que você ajustou não são movidas depois pelo ajuste automático.
- **Fim do corte médio.** O conteúdo dele já estava nos longos. Agora há só dois tipos: longo (mais de 3 até 40 min) e curto (até 3:00).
- **"Shorts" passou a se chamar "Cortes Curtos"** nas pastas, nos arquivos (`Curto NN - tema.mp4`) e na planilha ("Corte curto"). Dentro de `Publicar/Cortes Curtos` continuam as pastas YouTube, Instagram e TikTok.
- **Cortes curtos mais completos** e **aviso de trecho sem corte**: o validador avisa sobre curto abaixo de 45 s, sobre assunto repetido em dois longos e sobre trechos de 3 min ou mais sem nenhum corte nem remoção.
- Planilhas e episódios feitos antes da 1.2.0 continuam funcionando.

## Requisitos
- **Claude desktop** com a extensão **Desktop Commander** (ou **Claude Code**), para o Claude rodar comandos no seu computador.
- **Windows 10/11, macOS (Apple Silicon ou Intel) ou Linux** (x86_64 ou ARM64).
- **Python 3.12+** (o assistente instala, se faltar).
- **Disco:** cerca de 5 GB para o sistema e cerca de **7 vezes o tamanho do vídeo original** por episódio.
- Navegador comum, para a revisão visual (a página fica só no seu computador).

| | Mínimo (o fluxo não começa abaixo disto) | Recomendado |
|---|---|---|
| Processador | 4 threads | 8 threads ou mais |
| Memória RAM | 8 GB | 16 GB |
| Placa de vídeo | não exige (a transcrição vai para o processador) | NVIDIA com 4 GB ou mais |
| Disco livre | ~7× o tamanho do vídeo do episódio | SSD |

O codificador de vídeo usa a placa quando houver (NVIDIA, Apple, Intel ou AMD); sem ela, usa o processador.

**Proteção do computador:** a fila roda com prioridade baixa e usa só parte dos núcleos. No Windows e no Linux, o **vigia de temperatura** (`instalar.py vigia --executar`) pausa o processamento a 85 °C e retoma a 75 °C, sem perder nada. No macOS, valem só os limites de carga.

## Tempo de processamento

### Médias medidas
Médias de quatro episódios completos processados por este fluxo, numa máquina com processador de 12 threads, 16 GB de RAM e placa NVIDIA de 4 GB.

| | Média por episódio |
|---|---|
| Duração do vídeo original | 2 h 28 min |
| Cortes gerados | cerca de 18 (entre longos e curtos) |
| Transcrição | 8 min 56 s |
| Sinais de áudio | menos de 1 min |
| Triagem por LLM (opcional; depende do provedor e da fila dele)¹ | 23 min 51 s |
| Edição | 4 min 56 s |
| Finalização (vídeos, capas e versões por plataforma) | 31 min 46 s |
| **Total no computador, sem a triagem por LLM** | **cerca de 46 min** |
| **Total no computador, com a triagem por LLM** | **cerca de 1 h 10 min** |

¹ Média de três episódios; no quarto, a triagem foi refeita em partes e o tempo não ficou registrado inteiro.

Os tempos são de processamento ativo, tirados dos registros de cada etapa (`_analise/log_*.txt`); intervalos de mais de 10 min sem atividade não entram. A coleta dos dados do YouTube não tem tempo registrado e ficou de fora. Parte dos episódios foi processada antes dos limites de carga e do vigia de temperatura; com eles ligados, a finalização tende a demorar um pouco mais. A leitura da transcrição e a escolha dos cortes pelo Claude, e o tempo que você leva na revisão visual, também não entram: dependem da conversa.

### Estimativa em outras máquinas
> **Atenção: a tabela abaixo é uma estimativa, não uma medição.** Ela foi calculada a partir das médias acima, considerando o que mais pesa em cada etapa: a transcrição depende da placa NVIDIA (sem ela, roda no processador com um modelo menor); a finalização depende do codificador de vídeo da placa e do número de núcleos; a edição depende do disco e do processador. Os valores reais variam com a temperatura, o disco, o sistema e os outros programas abertos. Episódio de referência: 2 h 30 min, cerca de 18 cortes, sem a triagem por LLM.

| # | Classe de máquina | Transcrição | Edição | Finalização | Total estimado |
|---|---|---|---|---|---|
| 1 | Mínimo: 4 threads, 8 GB, só vídeo integrado | 50–70 min | 8–12 min | 70–100 min | 2 h 10 min – 3 h |
| 2 | Notebook de entrada: 6–8 threads, 8–16 GB, só vídeo integrado | 35–50 min | 6–9 min | 50–70 min | 1 h 30 min – 2 h 10 min |
| 3 | Desktop sem NVIDIA: 8–12 threads, 16 GB, placa AMD ou Intel | 30–40 min | 5–7 min | 35–50 min | 1 h 10 min – 1 h 40 min |
| 4 | Mac Apple Silicon, 16 GB | 25–35 min | 4–6 min | 30–40 min | 1 h – 1 h 20 min |
| 5 | Notebook intermediário: 12 threads, 16 GB, NVIDIA 4 GB (base das médias) | 8–10 min | 4–6 min | 28–35 min | 40–50 min |
| 6 | Desktop intermediário: 12–16 threads, 16–32 GB, NVIDIA 8 GB | 5–7 min | 3–4 min | 18–25 min | 26–36 min |
| 7 | Desktop avançado: 16–24 threads, 32 GB, NVIDIA 12–16 GB | 3–5 min | 2–3 min | 12–18 min | 17–26 min |
| 8 | Estação de trabalho: 32 threads ou mais, 64 GB, NVIDIA 24 GB | 2–4 min | 2 min | 8–12 min | 12–18 min |

### Em hardware mais fraco
- **Sem placa NVIDIA:** a transcrição usa o modelo `small` no processador. Ele é mais rápido que o `turbo` na CPU, mas um pouco menos preciso nos nomes e nas bordas dos cortes.
- **NVIDIA com menos de 4 GB:** o modelo `turbo` pode não caber, e o sistema passa sozinho para o processador. `instalar.py config whisper_tipo_gpu=int8_float16` usa menos memória de vídeo.
- **Sem codificador de vídeo na placa:** a finalização usa o processador (libx264), que é a etapa que mais esquenta. Com o limite de carga e o vigia, fica segura, mas lenta.
- **4 a 6 threads ou 8 GB de RAM:** funciona, mas o computador fica menos usável enquanto a fila roda. Feche outros programas.
- **HD em vez de SSD:** a leitura do vídeo e a gravação dos cortes ficam mais lentas.
- **Notebook:** use na tomada e com boa ventilação. Se o vigia pausar com frequência, limpe as saídas de ar ou ligue o modo de ventilação máxima do fabricante.
- Os tempos reais da sua máquina ficam nos registros (`_analise/log_*.txt`); vale anotá-los na nota `Regras/Finalização e identidade visual` do cofre.

## Instalação
1. Baixe **`cortes-de-video-skill.zip`** na [última Release](https://github.com/Ziggor1/cortes-de-video/releases/latest) e envie no Claude em **Personalizar → Skills → Enviar skill**. (Ou compacte a pasta [`skill/cortes-de-video`](skill/cortes-de-video), com a pasta `cortes-de-video` na raiz do ZIP.)
2. Numa conversa nova, diga: **"/cortes-de-video instalar"**.
3. O Claude reconhece o computador e faz algumas perguntas: onde criar o cofre, transcrição na placa de vídeo ou no processador, idioma, dados do YouTube, LLM opcional, canais e identidade visual. Ele mostra cada comando antes de instalar algo e termina com um autoteste.

<details>
<summary>Instalação manual, sem o Claude</summary>

```
python sistema/instalar.py criar-cofre "~/Cortes"
python ~/Cortes/_sistema/instalar.py pacotes            # --gpu com placa NVIDIA (Windows/Linux)
python ~/Cortes/_sistema/instalar.py ffmpeg --executar
python ~/Cortes/_sistema/instalar.py deno --executar     # dados do YouTube
python ~/Cortes/_sistema/instalar.py verificar
python ~/Cortes/_sistema/instalar.py checar
python ~/Cortes/_sistema/instalar.py vigia --executar    # vigia de temperatura (Windows: pede administrador; Linux: serviço do usuário)
python ~/Cortes/_sistema/instalar.py autoteste
python ~/Cortes/_sistema/novo_canal.py "Meu Canal" --logo logo.png --intro intro.mp4 --final final.mp4 --final-vertical final_vertical.mp4
```
</details>

## Uso
1. Coloque o vídeo em `Pasta de Trabalho/<Canal>/<Episódio>/`.
2. Diga ao Claude **"processar pendentes"** (ou "analisar <episódio>").
3. Quando a análise terminar, o Claude abre a **revisão dos cortes longos**. Aprove, recuse ou ajuste e clique em **Enviar** (ou **Aplicar**). Depois vem a **revisão dos cortes curtos**, do mesmo jeito.
4. O Claude edita e finaliza. Os arquivos para publicar ficam em `Publicar/`.

Outros pedidos: "revisar os cortes de <episódio>", "editar…", "finalizar…", "amostra de…", "textos de publicação de…", "desempenho", "limpeza", "status", "novo canal", "atualizar o sistema". O passo a passo completo está em `modelo_cofre/01 Workflow.md`.

Para abrir a revisão sem o Claude: `python <cofre>/_sistema/revisar_cortes.py "<pasta do episódio>" --fase longos` (ou `--fase curtos`).

## Atualizar
`python <cofre>/_sistema/instalar.py atualizar` baixa os scripts novos e guarda a versão anterior. Suas configurações, chaves, regras e episódios não são tocados. A skill é atualizada enviando o ZIP novo da Release.

## Privacidade e segurança
- Tudo roda no seu computador. A transcrição é local.
- A página de revisão é servida só em `127.0.0.1` e só lê arquivos de dentro da pasta do episódio.
- A **triagem por LLM é opcional e vem desligada**. Ligada, envia a transcrição (só de vídeos **públicos** no YouTube) à API que você escolher (FreeLLMAPI, OpenRouter, Ollama local ou outra compatível com OpenAI). As chaves ficam em `_sistema/.env` ou em variável de ambiente, nunca no repositório nem na conversa.
- Textos de terceiros (transcrição, comentários, chat, respostas de LLM) são tratados como dados, nunca como instruções.
- Nada é apagado sem sua permissão; versões anteriores são guardadas.
- O instalador mostra cada comando antes de instalar programas e usa versões travadas dos pacotes Python (`requirements.txt`).
- O vigia de temperatura só pausa e retoma os processos do próprio fluxo (os scripts e o ffmpeg).

## Direitos autorais
Fazer cortes de conteúdo de terceiros exige autorização do canal original ou respeito às regras de uso justo e de parceria. A ferramenta não decide isso por você: a responsabilidade pelo que é publicado é de quem publica.

## Estrutura do repositório
```
skill/cortes-de-video/     SKILL.md + references/instalacao.md (o que o Claude segue)
sistema/                   scripts (vão para <cofre>/_sistema), página da revisão, fontes livres e config padrão
modelo_cofre/              notas iniciais do cofre (Regras, Workflow, tabela do Obsidian)
requirements*.txt          pacotes Python com versões travadas
```

## Licença
MIT (veja `LICENSE`). Créditos e licenças de terceiros em `NOTICE.md`.
