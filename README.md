# Cortes de vídeo — skill para o Claude

Transforma lives e podcasts em **cortes longos e médios para o YouTube** e **Shorts/Reels/TikTok**, de ponta a ponta, conversando com o Claude:

- **Análise**: transcrição local com palavras no tempo (faster-whisper), sinais de audiência do YouTube (momentos mais repetidos, comentários com tempo, reações no chat da live), mapa de momentos com Shorts prontos, divisão por assunto e — opcional — uma segunda leitura por LLM com juiz final dos Shorts.
- **Planilha** com os cortes, notas por critério, três títulos, texto da capa e hashtags, conferida por um validador (gancho, fim, repetição, palavrão sem bipe, duração).
- **Edição**: cortes 16:9 sem recodificar; Shorts 9:16 com fundo desfocado e sem pausas longas; remoção de anúncios e trechos de risco; bipe em palavrões.
- **Finalização** com a identidade visual do canal: intro, marca d'água, tela final, capas 1280×720, legenda com palavra destacada e uma versão de cada Short por plataforma; volume em −14 LUFS.
- **Textos de publicação** e um **cofre do Obsidian** com painel, notas por episódio e regras editáveis.

Durações: **Short até 3:00** · **médio** de mais de 3 até 10 min · **longo** de mais de 10 até 40 min.

## Requisitos
- **Claude desktop** com a extensão **Desktop Commander** (ou **Claude Code**), para o Claude rodar comandos no seu computador.
- **Windows 10/11, macOS (Apple Silicon ou Intel) ou Linux** (x86_64 ou ARM64).
- **Python 3.12+** (o assistente instala, se faltar), ~5 GB para o sistema e ~5–15 GB por episódio de 2–3 h.
- Placa **NVIDIA** é opcional: com ela, a transcrição é ~16× o tempo real; sem ela, roda na CPU (mais devagar). O codificador de vídeo usa NVIDIA, Apple, Intel ou AMD quando houver.

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
