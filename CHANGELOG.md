# Histórico de versões

## 1.2.0 — 26/11/2026 (em relação à 1.1.0)

### Adicionado
- `validar_cortes.py`:
  - aviso **SEM CORTE** para trecho de 3 min ou mais sem corte nem remoção;
  - aviso **SHORT CURTO** para corte curto abaixo de 45 s;
  - aviso de assunto repetido em dois longos (mais de 20% em comum).
- `comum.py`: `PASTA_TIPO`, `PREFIXO_TIPO`, `ROTULO_TIPO` e `pasta_tipo()`.

### Alterado
- **Durações:** corte curto até 3:00 (o ideal é de 1:00 a 2:30, com começo, meio e fim); corte longo de mais de 3 até 40 min, com cada assunto em um longo só. Antes: Short até 3:00, médio de mais de 3 até 10 min, longo de mais de 10 até 40 min.
- **Nomes:**
  - pastas `Cortes/Cortes Curtos` e `Publicar/Cortes Curtos/{YouTube, Instagram, TikTok}` (antes `Shorts`);
  - arquivos `Curto NN - tema.mp4` (antes `Short NN - tema.mp4`);
  - categoria da planilha "Corte curto" (antes "Short/Reels", que continua aceita e é convertida).
- **Triagem por LLM** (`triagem_llm.py`): pede só dois tipos, "Short" (45 s a 2 min 50 s, ideia completa) e "Longo" (assunto inteiro). O cache antigo com "Médio" ou "Tema" é lido como "Longo".
- **Mapa de momentos** (`momentos.py`): os assuntos sugerem só longo ou curto. "Corte curto" conta como Short ao marcar o que ficou FORA.
- **Notas do Obsidian** (`atualizar_notas.py`): as colunas "L / M / S" viraram "Longos / Curtos". A tabela `Episódios.base` não tem mais a coluna de médios.
- `conferir.py`, `publicacao.py`, `finalizar.py`, `editar.py`, `amostra_trecho.py`, `previa_marca.py` e `visual.py`: textos e caminhos com os nomes novos.
- Notas do modelo de cofre (Decisões, Padrões de análise, Padrões de edição, Finalização e identidade visual, Workflow): durações e nomes. Os tempos de referência saíram das notas e foram para o README.
- README reescrito: tabela do que a skill faz, médias de tempo por episódio e estimativa para outras classes de máquina.

### Removido
- **Corte médio.** Não é mais gerado nem sugerido.
  - Linha "Corte médio" de planilha antiga gera só a versão vertical (corte curto), quando cabe em 3:00, e o validador avisa que a categoria não existe mais.
  - Episódios já feitos com médios continuam legíveis pelas notas, pela conferência e pelos textos de publicação.
- Chave `medio_tambem_short_ate_s` do `config_padrao.json` (não era usada).
- Episódios já finalizados não são renomeados nem refeitos: as pastas `Shorts` e `Medios` antigas continuam onde estão.

## 1.1.0 — 19/11/2026 (em relação à 1.0.0)

### Adicionado
- `sistema/vigia_temperatura.py`: vigia de temperatura que congela a fila, as etapas e o ffmpeg em `temp_pausa` (85 °C) e retoma em `temp_volta` (75 °C). Windows (LibreHardwareMonitor, com a zona térmica do ACPI como reserva) e Linux (`/sys/class/hwmon`). Registro em `_sistema/_logs/temperatura.txt`.
- `sistema/instalar_vigia.ps1`: instala o vigia no Windows. Extrai ou baixa o LibreHardwareMonitor, instala o .NET 10 Desktop Runtime se faltar (com a assinatura conferida) e cria a tarefa agendada "Vigia de temperatura - cortes".
- `instalar.py checar ["<pasta>"]`: confere os mínimos de hardware (4 threads, 8 GB de RAM) e o espaço em disco do episódio (cerca de 7× o vídeo). Abaixo do mínimo, sai com código 1.
- `instalar.py vigia [--executar]`: instala o vigia (tarefa agendada no Windows ou serviço do usuário `cortes-vigia` no Linux). Sem `--executar`, só mostra o plano.
- `instalar.py verificar`: novas linhas "Hardware" e "Vigia de temperatura".
- `comum.py`: `threads_limite()`, `limitar_ff()` e `aplicar_limites()`, para prioridade baixa e afinidade de núcleos (Windows, Linux; no macOS, só prioridade).
- Novas chaves em `config_padrao.json`: `prioridade_baixa`, `cpu_afinidade`, `ffmpeg_threads`, `temp_pausa`, `temp_volta`, `temp_intervalo_s` e `credito`.
- Skill: seção "Temperatura, carga do processador e uso do plano", checagem de mínimos e do vigia no pré-voo, regra de nunca afrouxar o vigia ou os limites sem pedido. Na instalação, o assistente agora oferece o vigia (Etapa 7).
- README: novidades, tabela de requisitos (mínimo e recomendado) e "Limitações em hardware mais fraco". `NOTICE.md`: LibreHardwareMonitor (MPL-2.0) e .NET Desktop Runtime. `CHANGELOG.md` (este arquivo).

### Alterado
- **Fila** (`fila.py`): roda sempre com prioridade baixa e presa a um terço das threads (mínimo 2). Antes, usava o processador inteiro.
- **ffmpeg**: todas as chamadas por `sp()` e pelo `finalizar.py` recebem `-threads`, `-filter_threads` e `-filter_complex_threads` com o mesmo limite. Antes, não tinham limite.
- **Whisper na CPU** (`transcrever.py`): usa o limite de threads. Antes, usava todas as threads menos 2.
- **Crédito do canal original** (`publicacao.py`): o padrão passou a ser só o **@ do canal**, sem link. O formato anterior (nome do canal + link do episódio) continua disponível com `credito=link`.
- **Estimativa de disco** no README e no `verificar`: de "~5–15 GB por episódio de 2–3 h" para "cerca de 7× o tamanho do vídeo original" (medido: vídeo de 3,3 GB → 22 GB).
- **Pastas não copiadas** na atualização: `_ferramentas` foi acrescentada às que o instalador não copia. Ela fica no `.gitignore`, junto com `hardware.json`.

### Removido
- Nenhum arquivo, comando nem opção foi removido.
- Deixaram de ser o comportamento padrão, mas podem ser restaurados pelo `config.json`:
  - uso do processador inteiro pela fila e pelo ffmpeg: `prioridade_baixa=false`, `cpu_afinidade=0`, `ffmpeg_threads=0`;
  - link do episódio original nos textos de publicação: `credito=link`.

## 1.0.0 — 17/11/2026
Primeira versão pública.
