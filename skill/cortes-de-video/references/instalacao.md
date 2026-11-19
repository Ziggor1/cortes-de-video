# Assistente de instalação, canais e manutenção

Use este roteiro quando `~/.cortes-de-video.json` não existir, quando o usuário pedir para instalar, criar um canal, verificar ou atualizar o sistema.
Regras do assistente:
- **Pergunte antes de instalar qualquer programa** e mostre o comando exato. Os comandos do `instalar.py` sem `--executar` só mostram o plano.
- Faça as perguntas em **poucas rodadas** (use a ferramenta de perguntas de múltipla escolha quando houver; senão, pergunte em texto, numerado). Cada pergunta deve se sustentar sozinha e trazer a opção recomendada.
- Nunca peça nem receba chaves de API na conversa: o usuário as coloca sozinho (instruções na Etapa 6).
- Ao final de cada etapa, diga em uma linha o que foi feito; ao final de tudo, resuma o que ficou instalado e como usar.

Repositório: https://github.com/Ziggor1/cortes-de-video (licença MIT).

---

## Etapa 1 — Reconhecer o computador (sem perguntar nada)
- Windows (PowerShell):
  `[Environment]::OSVersion.VersionString; $PSVersionTable.PSVersion.ToString(); Get-Command py,python,git,winget -ErrorAction SilentlyContinue | Select-Object Name,Source; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>$null; Get-PSDrive C | Select-Object Free`
- macOS/Linux:
  `uname -sm; for c in python3 git brew curl; do command -v $c; done; python3 --version; nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null; df -h ~ | tail -1`
- Python precisa ser **3.12 ou mais novo** (Windows: teste também `py -3.12 --version`). Anote: sistema, Python, git, winget/brew, placa NVIDIA e espaço livre (recomendado: 30 GB+).

## Etapa 2 — Primeira rodada de perguntas
1. **Onde criar o cofre?** Recomendado: Windows `Documentos\Cortes`; macOS/Linux `~/Cortes`. (Pasta nova ou vazia; pode ser num disco externo com espaço.)
2. **Transcrição** (o que mais pesa no tempo):
   - placa NVIDIA detectada → recomendado **turbo na GPU** (rápido e preciso);
   - sem NVIDIA (ou Mac) → recomendado **small na CPU** (mais rápido); **medium** é mais preciso e bem mais lento.
3. **Idioma falado nos vídeos** (padrão: português, `pt`).
4. **Os vídeos vêm do YouTube?** Se sim, a análise usa dados públicos de audiência (momentos mais repetidos, comentários com tempo, chat da live) com o yt-dlp, que precisa do Deno (recomendado instalar).

## Etapa 3 — Python e download do sistema
- Sem Python 3.12+: proponha e, com o "pode", instale — Windows: `winget install -e --id Python.Python.3.12`; macOS: `brew install python@3.12` (sem Homebrew: https://brew.sh); Linux: pelo gerenciador da distribuição (Ubuntu 24.04+, Fedora 39+ e Bazzite já trazem 3.12+). Depois use `py -3.12` (Windows) ou `python3`.
- Baixe o repositório numa pasta temporária:
  - com git: `git clone --depth 1 https://github.com/Ziggor1/cortes-de-video "<TEMP>/cortes-de-video"`;
  - Windows sem git: `Invoke-WebRequest https://codeload.github.com/Ziggor1/cortes-de-video/zip/refs/heads/main -OutFile "$env:TEMP\cortes.zip"; Expand-Archive "$env:TEMP\cortes.zip" "$env:TEMP\cortes" -Force` (pasta `cortes-de-video-main`);
  - macOS/Linux sem git: `curl -L -o /tmp/cortes.zip https://codeload.github.com/Ziggor1/cortes-de-video/zip/refs/heads/main && python3 -m zipfile -e /tmp/cortes.zip /tmp/cortes`.

## Etapa 4 — Criar o cofre e instalar os pacotes
1. `<python> "<repo>/sistema/instalar.py" criar-cofre "<pasta do cofre>"` — copia o modelo de cofre (Regras, Workflow, painel) e os scripts para `<pasta>/_sistema`, e grava `~/.cortes-de-video.json`. Nunca sobrescreve notas que já existam.
2. `<python> "<S>/instalar.py" pacotes` (+ `--gpu` se houver NVIDIA no Windows/Linux) — cria o ambiente isolado `<S>/.venv` e instala as versões testadas (faster-whisper, ctranslate2, numpy, openpyxl, Pillow, yt-dlp; com `--gpu`, cuBLAS 12.8 + cuDNN 9.8). Leva alguns minutos e ~1–3 GB. A partir daqui, `<PY>` é o Python do `.venv` (já gravado no `~/.cortes-de-video.json`).
   - Linux sem `venv`: Debian/Ubuntu pedem `sudo apt install python3-venv` (o usuário roda; você não tem sudo).

## Etapa 5 — ffmpeg e Deno (programas do sistema)
1. `"<PY>" "<S>/instalar.py" verificar` — mostra o que falta.
2. Sem ffmpeg completo (precisa dos filtros drawtext, ass e loudnorm): `"<PY>" "<S>/instalar.py" ffmpeg` mostra o plano — Windows: winget `Gyan.FFmpeg`; macOS: `brew install ffmpeg`; Linux: binário estático em `<S>/bin`, sem sudo (`--estatico` também vale no Windows sem winget). Com o "pode", rode de novo com `--executar`.
3. Se o usuário quer os dados do YouTube: `"<PY>" "<S>/instalar.py" deno` → plano → "pode" → `--executar`.

## Etapa 6 — Configuração desta máquina e LLM opcional
1. Grave as escolhas: `"<PY>" "<S>/instalar.py" config idioma=pt whisper_modelo_analise=<turbo|small|medium> whisper_modelo_bipe=<igual> whisper_dispositivo=<auto|cpu>`.
2. **Segunda rodada de perguntas — triagem por LLM (opcional).** Explique: é uma segunda leitura da transcrição por um modelo de linguagem, que sugere momentos e julga os Shorts; manda a transcrição de vídeos **públicos** a um serviço externo (ou a um modelo local). Opções:
   - **Não usar** (recomendado para começar; a análise funciona só com os sinais);
   - **FreeLLMAPI** local (gratuito, junta provedores): `base_url` `http://127.0.0.1:31415/v1`, chave unificada do painel dele;
   - **OpenRouter**: `https://openrouter.ai/api/v1`, chave da conta; modelos `:free` existem;
   - **Ollama** (modelo local, sem chave, precisa de máquina forte): `http://127.0.0.1:11434/v1`, modelo ex.: `qwen2.5:14b`;
   - **outra API compatível com OpenAI** (o usuário informa a URL e o modelo).
   Para ligar: `"<PY>" "<S>/instalar.py" config llm.ativado=true llm.base_url=<URL> llm.chave_env=CORTES_LLM_KEY llm.modelos=<modelo1>,<modelo2>`.
   **A chave o usuário coloca sozinho, fora da conversa**: crie/edite `<S>/.env` com a linha `CORTES_LLM_KEY=<chave>` (funciona em todos os sistemas e sobrevive a reinícios) — ou, no Windows, no PowerShell dele: `[Environment]::SetEnvironmentVariable('CORTES_LLM_KEY', (Read-Host 'Cole a chave'), 'User')`. Prefira modelos "diretos" (não de raciocínio), que devolvem o JSON pedido.
3. Baixe o modelo do Whisper (pergunte antes; turbo ≈ 1,6 GB, small ≈ 0,5 GB, medium ≈ 1,5 GB): `"<PY>" "<S>/instalar.py" modelo <nome>`.

## Etapa 7 — Verificar e autoteste
1. `"<PY>" "<S>/instalar.py" verificar` — tudo obrigatório tem de sair OK.
2. `"<PY>" "<S>/instalar.py" checar` — mínimos de hardware (4 threads e 8 GB de RAM; recomendado 8 threads, 16 GB e placa NVIDIA de 4 GB). Abaixo do mínimo, diga ao usuário que o fluxo não vai começar neste computador. Abaixo do recomendado, diga que funciona, mas mais devagar, e que os tempos do primeiro episódio serão medidos.
3. **Vigia de temperatura** (Windows e Linux; recomendado sobretudo em notebook): explique em uma linha o que ele faz (congela a fila a 85 °C e retoma a 75 °C) e pergunte se instala. No Windows ele pede administrador, usa o LibreHardwareMonitor (código aberto, MPL-2.0) e pode instalar o .NET 10 Desktop Runtime da Microsoft. Mostre o plano com `"<PY>" "<S>/instalar.py" vigia` e, com o "pode", rode `… vigia --executar`. Confira com `verificar` (linha "Vigia de temperatura"). No macOS, diga que o vigia não roda e que valem só os limites de carga.
4. `"<PY>" "<S>/instalar.py" autoteste` — gera um vídeo sintético e testa o codificador, a finalização 16:9 com marca, a capa, o Short com legenda e o Whisper (modelo tiny, ~75 MB). Mostre ao usuário a `capa.jpg` e o `short_quadro.jpg` da pasta indicada. Anote o codificador e se o Whisper rodou na GPU ou na CPU.

## Canais (instalação e "novo canal")
**Terceira rodada de perguntas**, para cada canal:
1. Nome do canal (vira a pasta `Pasta de Trabalho/<Canal>`).
2. Arquivos da identidade visual — todos opcionais; peça o caminho de cada um (ou que o usuário os coloque numa pasta e diga qual):
   - **intro** 16:9 (vídeo curto ou imagem);
   - **final** 16:9 (tela final dos longos e médios);
   - **final vertical** dos Shorts: um só para as 3 plataformas ou um por plataforma (YouTube, Instagram, TikTok);
   - **logo** em PNG com fundo transparente (vira marca d'água e logo da capa);
   - **fonte** própria (.ttf/.otf; sem ela, usa Anton nas capas e Archivo Black nas legendas).
3. Rode `"<PY>" "<S>/novo_canal.py" "<Canal>" --intro "<arq>" --final "<arq>" --final-vertical "<arq>" --logo "<arq>"` (ou `--final-youtube/--final-instagram/--final-tiktok`; `--fonte "<arq>"`). Os arquivos são copiados para `Conteudo Visual/` e o `visual.json` é criado com a marca padrão (16:9: logo de 150 px a 85% no canto superior direito; Shorts: 220 px a 100% no centro do topo).
4. `"<PY>" "<S>/visual.py"` para conferir. Peça ao usuário para preencher o "Perfil do canal" em `Canais/<Canal>.md` (público, tom, apresentadores, regras próprias).
5. **Antes de finalizar o primeiro episódio do canal**, faça a amostra em vídeo real (regra 3) e registre a aprovação na nota de Finalização.

## Encerramento da instalação
- Diga onde ficou o cofre, o que foi instalado (pacotes, ffmpeg, Deno, modelo), o codificador e se a transcrição será na GPU ou na CPU, se o vigia de temperatura ficou ativo e o resultado do `checar` (se o computador está abaixo do recomendado, avise que será mais lento).
- **Obsidian** (opcional, recomendado): https://obsidian.md → "Abrir pasta como cofre" → a pasta do cofre. O `00 Painel.md` e a tabela `Episódios.base` mostram o estado de tudo.
- Como usar: colocar o `.mp4` em `Pasta de Trabalho/<Canal>/<Episódio>/` e pedir "processar pendentes".
- Lembretes, uma vez: direitos autorais dos cortes de terceiros são de quem publica; a triagem por LLM envia transcrição de vídeo público a um serviço externo; nada é apagado sem permissão.
- A pasta temporária do repositório pode ficar; se o usuário quiser, apague-a (com permissão).

## Manutenção
- **Verificar**: `"<PY>" "<S>/instalar.py" verificar` (e `autoteste` se algo mudou).
- **Atualizar os scripts**: `"<PY>" "<S>/instalar.py" atualizar` — baixa a versão nova do GitHub, guarda a anterior em `<S>/_backup_<data>/`, nunca toca em `config.json`, `.env`, calibração nem nas suas `Regras/` (notas novas do modelo só entram se não existirem). Se avisar que os pacotes mudaram, rode `pacotes` de novo.
- **Atualizar a skill**: a skill do Claude não se atualiza sozinha. Baixe a pasta `skill/cortes-de-video` do repositório, compacte em ZIP e envie de novo em Personalizar → Skills (ou peça a quem compartilhou para atualizar).
- **Mudar escolhas**: `instalar.py config chave=valor` (ex.: trocar o modelo, ligar/desligar o LLM).
- **Desinstalar** (só com pedido explícito): apagar a pasta do cofre e `~/.cortes-de-video.json`. ffmpeg, Deno e Python instalados pelo gerenciador de pacotes ficam; diga como removê-los se o usuário quiser.
