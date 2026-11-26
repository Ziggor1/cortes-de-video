---
tipo: workflow
tags: [workflow]
---
# Workflow de cortes

Tudo acontece numa conversa com o Claude usando a skill **/cortes-de-video**. Este cofre é a memória do processo: regras, estado de cada episódio e o que já foi publicado. Pode ser aberto no Obsidian (recomendado), mas funciona como pastas comuns.

## Etapas

| # | Etapa | Quem faz | Resultado | Status da nota |
|---|---|---|---|---|
| 0 | Colocar o vídeo em `Pasta de Trabalho/<Canal>/<Episódio>/` | você | pasta com o `.mp4` | 1 · aguardando análise |
| 1 | Análise: transcrição, grade de quadros, intensidade do áudio, mapa de momentos, cortes, notas e títulos | Claude | `Cortes_<tema>.xlsx` + `_analise/` | 2 · analisado |
| 2 | Revisão da análise (opcional) | você | ajustes na planilha | — |
| 3 | Edição: cortes longos 16:9, cortes curtos 9:16, remoções, bipes | Claude | `Cortes/` + `Relatorio_Edicao.xlsx` | 3 · editado |
| 4 | Finalização: intro + final + marca d'água (longos), capa 1280×720, cortes curtos com legenda + marca + final vertical | Claude | `Publicar/` | 3 · pronto para publicar |
| 5 | Atualização das notas e do [[00 Painel]] | Claude (automático) | notas do episódio e do canal | — |
| 6 | Publicação: subir os arquivos de `Publicar/` e marcar a caixa de cada corte | você | caixas marcadas | 4 · publicado |
| 7 | Desempenho: preencher a aba "Desempenho" da planilha | você | calibra a nota dos próximos | — |

## O que dizer ao Claude

| Você diz | O Claude faz |
|---|---|
| **processar pendentes** | Analisa, edita e finaliza os episódios novos; mostra o plano e o tempo estimado antes de começar. Episódios já finalizados não são refeitos |
| **analisar Episódio 01** | Só a etapa 1 desse episódio |
| **editar Episódio 01** | Só a etapa 3 (usa a planilha que estiver na pasta) |
| **finalizar Episódio 01** | Só a etapa 4 (intro, final, marca d'água, capas, legendas) |
| **refazer as capas de Episódio 01** | Gera as capas de novo (ex.: depois de mudar o "Texto da capa") |
| **analisar e me mostrar antes de editar** | Para na etapa 2 para você revisar |
| **status** | Atualiza as notas e resume o [[00 Painel]] |
| **textos de publicação de Episódio 01** | Gera `Publicar/Textos de publicação.md`: título, descrição, hashtags e crédito por corte e por plataforma |
| **desempenho** | Lê a aba "Desempenho" das planilhas e mostra quais critérios da nota acertaram (a partir de 5 cortes publicados por grupo) |
| **limpeza** | Lista temporários e versões antigas com o tamanho; só apaga o que você autorizar |
| **amostra de Episódio 01** | Trechos curtos em vídeo real com o visual atual, para aprovar mudanças antes de finalizar |
| **novo canal** | Cria a pasta e o `visual.json` de mais um canal |
| **verificar a instalação** / **atualizar o sistema** | Confere as dependências / baixa a versão mais nova dos scripts do GitHub |

## Estrutura de pastas

```
<cofre>/
├─ 00 Painel.md             ← gerado automaticamente
├─ 01 Workflow.md
├─ Canais/                  ← uma nota por canal (perfil editável + lista automática)
├─ Regras/                  ← regras que o Claude segue; edite aqui para mudar o comportamento
├─ Episódios.base           ← tabela filtrável (Obsidian Bases)
├─ _sistema/                ← scripts (não precisa abrir); config.json = escolhas desta máquina
├─ Pasta de Trabalho/<Canal>/Conteudo Visual/ ← intro, finais, marcas d'água, logos + visual.json
└─ Pasta de Trabalho/<Canal>/<Episódio>/
   ├─ <Episódio>.md         ← nota do episódio (bloco AUTO + suas anotações)
   ├─ video.mp4
   ├─ Cortes_<tema>.xlsx    ← planilha da análise
   ├─ _analise/             ← transcrição, grade de quadros, mapa de momentos
   ├─ Cortes/{Longos,Cortes Curtos}/ + Relatorio_Edicao.xlsx   ← cortes brutos
   └─ Publicar/{Longos,Capas,Cortes Curtos/{YouTube,Instagram,TikTok}}/   ← o que vai para as plataformas
```

## Regras
- [[Padrões de análise]]
- [[Critérios de nota]]
- [[Padrões de edição]]
- [[Políticas e alertas]]
- [[Finalização e identidade visual]]
- [[Decisões]] — o que foi decidido e o que foi recusado
- [[Nomes]] — grafias confirmadas de pessoas e marcas

## Comandos manuais (se precisar rodar sem o Claude)
Dentro de `<cofre>/_sistema`, com o Python do sistema (o caminho está em `config.json` → `python`):
```
python instalar.py verificar                 # confere dependências, GPU, ffmpeg, fontes
python editar.py "<pasta>" --plano           # mostra o que seria feito
python editar.py "<pasta>"                   # gera os cortes
python finalizar.py "<pasta>"                # intro, final, marca, capas, legendas
python finalizar.py "<pasta>" --so-capas --refazer   # só refaz as capas
python visual.py                             # arquivos visuais de cada canal
python atualizar_notas.py                    # atualiza notas e painel
python amostra_trecho.py "<pasta>"           # amostra em vídeo real (_previas/amostras)
python previa_marca.py "<pasta>"             # compara opções de logo/marca d'água
python publicacao.py "<pasta>"               # textos de publicação
python momentos.py "<pasta>"                 # mapa de momentos (_analise/momentos.md)
python conferir.py "<pasta 1>" "<pasta 2>"   # confere episódios finalizados
python fila.py criar finalizar "<pasta>" + conferir "<pasta>"   # fila retomável
python fila.py rodar | status
```
