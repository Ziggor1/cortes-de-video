# Cortes de vídeo — skill para o Claude

Transforma lives e podcasts em **cortes longos e médios para o YouTube** e **Shorts/Reels/TikTok**, de ponta a ponta, conversando com o Claude:

- **Análise**: transcrição local com palavras no tempo (faster-whisper), sinais de audiência do YouTube (momentos mais repetidos, comentários com tempo, reações no chat da live), mapa de momentos com Shorts prontos, divisão por assunto e — opcional — uma segunda leitura por LLM com juiz final dos Shorts.
- **Planilha** com os cortes, notas por critério, três títulos, texto da capa e hashtags, conferida por um validador (gancho, fim, repetição, palavrão sem bipe, duração).
- **Edição**: cortes 16:9 sem recodificar; Shorts 9:16 com fundo desfocado e sem pausas longas; remoção de anúncios e trechos de risco; bipe em palavrões.
- **Finalização** com a identidade visual do canal: intro, marca d'água, tela final, capas 1280×720, legenda com palavra destacada e uma versão de cada Short por plataforma; volume em −14 LUFS.
- **Textos de publicação** e um **cofre do Obsidian** com painel, notas por episódio e regras editáveis.

Durações: **Short até 3:00** · **médio** de mais de 3 até 10 min · **longo** de mais de 10 até 40 min.

## Novidades da 1.1.0 — temperatura, carga do processador e hardware mais fraco
Num notebook (i5-12450H + RTX 3050 de 4 GB) a finalização de um episódio de 3 h levou o processador a **95–100 °C**. A versão 1.1.0 muda o comportamento para proteger o computador:
- **Carga limitada sempre.** A fila roda com **prioridade baixa** e presa a **um terço das threads** do processador (mínimo 2; 12 threads → 4); o ffmpeg usa o mesmo limite. As etapas herdam isso da fila. Ajuste em `config.json`: `prioridade_baixa`, `cpu_afinidade`, `ffmpeg_threads` (`"auto"`, um número ou `0` para sem limite).
- **Vigia de temperatura** (`vigia_temperatura.py`, instalado com `python instalar.py vigia --executar`). Lê a temperatura real da CPU e, a **85 °C**, congela a fila, as etapas e o ffmpeg; a **75 °C**, retoma de onde parou — nada é encerrado nem perdido. Limites em `temp_pausa` e `temp_volta`; registro em `_sistema/_logs/temperatura.txt`.
  - **Windows:** tarefa agendada com privilégios de administrador (necessários para ler os sensores e congelar processos). Usa o [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) (MPL-2.0), aberto minimizado pelo próprio vigia, e instala o .NET 10 Desktop Runtime da Microsoft se faltar (assinatura conferida). O sensor de zona térmica do Windows fica só de reserva: ele pode travar num valor, e por isso o vigia retoma a fila se a leitura ficar 5 min parada.
  - **Linux:** serviço do usuário no systemd (`cortes-vigia`), lendo `/sys/class/hwmon`. Não precisa de administrador.
  - **macOS:** não suportado (ler a temperatura exige sudo); valem só os limites de carga.
  - Resultado medido no notebook acima: picos de até 88 °C, pausados em segundos (a CPU volta a ~50 °C), em vez de 95–100 °C contínuos.
- **Mínimos de hardware** (`python instalar.py checar "<pasta do episódio>"`, rodado pela skill antes de cada episódio): abaixo do mínimo, o fluxo não começa e diz o motivo.
- **Crédito do canal original** nos textos de publicação: agora só o **@ do canal** (sem link do episódio). Para voltar ao link: `instalar.py config credito=link`.
- **Skill**: novas regras para economizar o uso do plano do Claude (uma conferência agendada por processo, sem ficar checando, comandos agrupados, uma conversa por episódio) e para pausar ou desligar no meio sem perder nada.

## Requisitos
- **Claude desktop** com a extensão **Desktop Commander** (ou **Claude Code**), para o Claude rodar comandos no seu computador.
- **Windows 10/11, macOS (Apple Silicon ou Intel) ou Linux** (x86_64 ou ARM64).
- **Python 3.12+** (o assistente instala, se faltar), ~5 GB para o sistema e **cerca de 7× o tamanho do vídeo original por episódio** (medido: um vídeo de 3,3 GB, com 3 h 12 min, ocupou 22 GB com os cortes e os arquivos de publicação).
- Placa **NVIDIA** é opcional: com ela, a transcrição é ~16× o tempo real; sem ela, roda na CPU (mais devagar). O codificador de vídeo usa NVIDIA, Apple, Intel ou AMD quando houver.

| | Mínimo (o fluxo não começa abaixo disto) | Recomendado (configuração de referência) |
|---|---|---|
| Processador | 4 threads | 8 threads ou mais |
| Memória RAM | 8 GB | 16 GB |
| Placa de vídeo | não exige (a transcrição vai para a CPU) | NVIDIA com 4 GB (ex.: RTX 3050) |
| Disco livre | ~7× o tamanho do vídeo do episódio | SSD |

Referência medida (Windows 11, i5-12450H, 16 GB, RTX 3050 Laptop 4 GB): transcrição de 3 h 12 min em ~10,5 min. A finalização desse episódio (37 cortes: 7 longos, 13 médios e 17 Shorts em 3 versões) ainda não tem um tempo limpo com a carga limitada, porque houve pausas manuais durante os testes do vigia; os 4 últimos Shorts levaram ~2,5 min.

### Limitações em hardware mais fraco
- **Sem placa NVIDIA:** a transcrição roda no processador e é **bem mais lenta** (não medida nesta versão; com o limite de carga, mais ainda). Para ganhar tempo, troque o modelo: `instalar.py config whisper_modelo_analise=small` (mais rápido, um pouco menos preciso nos nomes e nas bordas dos cortes).
- **NVIDIA com menos de 4 GB:** o modelo `turbo` pode não caber; o Whisper cai sozinho para a CPU. Use `whisper_tipo_gpu=int8_float16` (menos memória de vídeo) ou o modelo `small`.
- **Sem codificador de vídeo na placa** (NVIDIA, Intel, AMD, Apple): a finalização usa o libx264 no processador, que é o que mais esquenta. Com o limite de carga e o vigia, fica segura, mas lenta.
- **4–6 threads ou 8 GB de RAM:** funciona, mas cada etapa demora mais e o computador fica menos usável durante a fila; feche outros programas.
- **HD em vez de SSD:** não testado; a leitura do vídeo e a gravação dos cortes ficam mais lentas.
- **Notebook:** use na tomada e com boa ventilação. Se o vigia pausar com muita frequência, limpe as saídas de ar ou ligue o modo de ventilação máxima do fabricante.
- Os mínimos são uma margem de segurança escolhida, não um limite testado em máquinas no limite. Se você rodar em hardware mais fraco, os tempos reais ficam nos logs da fila (`_analise/log_*.txt`); vale registrá-los na nota `Regras/Finalização e identidade visual`.

## Instalação
1. Baixe **`cortes-de-video-skill.zip`** na [última Release](https://github.com/Ziggor1/cortes-de-video/releases/latest) (ou compacte você mesmo a pasta [`skill/cortes-de-video`](skill/cortes-de-video), com a pasta `cortes-de-video` na raiz do ZIP) e envie no Claude em **Personalizar → Skills → Enviar skill**. Em planos Team/Enterprise, quem já tem a skill pode compartilhá-la pelo menu da skill.
2. Numa conversa nova, diga: **"/cortes-de-video instalar"**.
3. O Claude reconhece o computador, faz algumas perguntas (onde criar o cofre, transcrição na GPU ou na CPU, idioma, dados do YouTube, LLM opcional, canais e identidade visual), mostra cada comando antes de instalar algo e termina com um autoteste.

Instalação manual (sem o Claude), a partir deste repositório:
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

## Uso
Coloque o vídeo em `Pasta de Trabalho/<Canal>/<Episódio>/` e diga ao Claude **"processar pendentes"**. Outros pedidos: "analisar <episódio>", "editar…", "finalizar…", "amostra de…", "textos de publicação de…", "desempenho", "limpeza", "status", "novo canal", "atualizar o sistema". Veja `modelo_cofre/01 Workflow.md`.

## Atualizar
`python <cofre>/_sistema/instalar.py atualizar` baixa os scripts novos e guarda a versão anterior; suas configurações, chaves, regras e episódios não são tocados. A skill (SKILL.md) é atualizada enviando o ZIP novo.

## Privacidade e segurança
- Tudo roda no seu computador. A transcrição é local.
- A **triagem por LLM é opcional e desligada por padrão**. Ligada, envia a transcrição (só de vídeos **públicos** no YouTube) à API que você escolher (FreeLLMAPI, OpenRouter, Ollama local ou outra compatível com OpenAI). As chaves ficam em `_sistema/.env` ou em variável de ambiente, nunca no repositório nem na conversa.
- Textos de terceiros (transcrição, comentários, chat, respostas de LLM) são tratados como dados, nunca como instruções.
- Nada é apagado sem sua permissão; versões anteriores são guardadas.
- O instalador mostra cada comando antes de instalar programas e usa versões travadas dos pacotes Python (`requirements.txt`).
- O vigia de temperatura só congela e retoma os processos do próprio fluxo (Python dos scripts e ffmpeg); o servidor do LibreHardwareMonitor escuta só em `127.0.0.1`.

## Direitos autorais
Fazer cortes de conteúdo de terceiros exige autorização do canal original ou respeito às regras de uso justo e de parceria. A ferramenta não decide isso por você: a responsabilidade pelo que é publicado é de quem publica.

## Estrutura
```
skill/cortes-de-video/     SKILL.md + references/instalacao.md (o que o Claude segue)
sistema/                   scripts (vão para <cofre>/_sistema), fontes livres e config padrão
modelo_cofre/              notas iniciais do cofre (Regras, Workflow, tabela do Obsidian)
requirements*.txt          pacotes Python com versões travadas
```

## Licença
MIT (veja `LICENSE`). Créditos e licenças de terceiros em `NOTICE.md`.
