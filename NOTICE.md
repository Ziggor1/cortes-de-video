# Créditos e licenças de terceiros

## Código e ideias adaptados
- **EverythingAI-Pro/ai-video-editor** — licença MIT, © 2026 EveryThingAi / EverythingAI-Pro.
  Ideias adaptadas em `sistema/momentos.py`, `sistema/juiz_llm.py` e `sistema/validar_cortes.py`: entrega da fala
  (pico e variação de energia, pausa antes da frase), tipos de gancho (traduzidos para o português), índice de gaguejada
  e juiz final dos Shorts por LLM. https://github.com/EverythingAI-Pro/ai-video-editor

## Fontes incluídas (`sistema/fontes/`)
- **Anton** — SIL Open Font License 1.1, © 2020 The Anton Project Authors. Texto da licença em `sistema/fontes/OFL-Anton.txt`.
- **Archivo Black** — SIL Open Font License 1.1, © 2017 The Archivo Black Project Authors. Texto da licença em `sistema/fontes/OFL-ArchivoBlack.txt`.

## Programas e pacotes usados (não incluídos; instalados pelo usuário)
- LibreHardwareMonitor (MPL-2.0), usado pelo vigia de temperatura no Windows; baixado do GitHub do projeto pelo `instalar_vigia.ps1`.
  .NET Desktop Runtime (licença da Microsoft), exigido pelo LibreHardwareMonitor.
- FFmpeg (LGPL/GPL, conforme o build), faster-whisper (MIT), CTranslate2 (MIT), modelos Whisper (MIT), yt-dlp (Unlicense),
  Deno (MIT), openpyxl (MIT), NumPy (BSD), Pillow (MIT-CMU), bibliotecas NVIDIA cuBLAS/cuDNN (licença da NVIDIA).
