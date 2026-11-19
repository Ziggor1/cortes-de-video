# Histórico de versões

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
