---
tipo: regra
tags: [regra]
---
# Finalização e identidade visual

Aplicada por `_sistema/finalizar.py`, depois da edição. Os cortes brutos (`Cortes/`) não são alterados; o resultado vai para `Publicar/`.

## O que entra em cada formato
| Formato | Intro | Marca d'água | Final | Legenda | Capa |
|---|---|---|---|---|---|
| Longos e médios (16:9) | sim | camadas 16:9 do canal | final 16:9 | não | 1280×720 + 2 opções |
| Shorts (9:16, cortes de até 3:00) | não | camadas verticais do canal | uma versão por plataforma (YouTube, Instagram, TikTok), sempre com a finalização vertical | palavra destacada | não |

## Configuração de cada canal
Fica em `Pasta de Trabalho/<Canal>/Conteudo Visual/visual.json` (criado pelo `novo_canal.py` na instalação). Para conferir: `python visual.py` em `_sistema`.
Sem intro, final ou logo, o canal funciona: aquela parte só não entra.

<!-- O instalador acrescenta aqui uma seção por canal (### <Canal>) com o que foi configurado. -->

### Formato das camadas no `visual.json`
```json
{"arquivo": "x.png", "modo": "tela"}
{"arquivo": "x.png", "largura": 180, "x": "W-w-30", "y": "30", "opacidade": 0.8}
```
`x`/`y` aceitam expressões do ffmpeg (`t` = segundos do corte; `W`/`H` = vídeo; `w`/`h` = camada).
Dica: logo escuro sobre fundo escuro some; nos Shorts, o logo fica na faixa desfocada e pode ser maior e opaco. Compare opções com `python previa_marca.py "<pasta do episódio>"` antes de mudar.

### Anúncios do vídeo original
- Vídeos de origem podem trazer anúncios na imagem (QR codes no canto, painel do patrocinador). Eles vão para os cortes como estão; nos Shorts, o zoom do vertical costuma cortá-los das laterais.
- O `finalizar.py` aceita `"censura": [[x, y, largura, altura]]` no `visual.json` para desfocar uma região fixa, mas costuma falhar quando o anúncio muda de lugar: prefira não usar.

## Capa
- Foco no texto: frase em 2 linhas, letra pesada (Anton, ou a fonte do canal no `visual.json`) com contorno preto; 1ª linha branca, 2ª vermelha. Borda amarela grossa.
- Um quadro do corte, com uma pessoa (zoom de 25%, cores fortes). Três versões com quadros de momentos diferentes.
- A frase vem da planilha: "Texto da capa" se tiver 3 palavras ou mais; senão, a citação do "Título 1" (até 7 palavras); senão, o "Texto da capa" curto. Sem exagero e sem inventar.
- Canto superior esquerdo desfocado (onde costuma estar o QR do patrocinador). Logo do canal pequeno no canto superior direito.
- Confira se a pessoa do quadro é quem disse a frase antes de publicar.

## Legenda dos Shorts
- Transcrição do próprio Short, 2–3 palavras por vez, em maiúsculas, com a palavra falada em amarelo (fonte Archivo Black, ou a do canal).
- Na faixa desfocada abaixo do vídeo, longe dos botões das plataformas.
- Palavrões censurados (P****); trechos com bipe mostram a palavra censurada.
- Cache em `_analise/legendas/` para refazer sem transcrever de novo.

## Amostras e canais aprovados
- Toda mudança visual (marca, legenda, capa) passa por amostra em vídeo real: `python amostra_trecho.py "<pasta>"` gera trechos de um longo (em 3 pontos do corte) e de um Short em `_previas/amostras/`, sem tocar em `Publicar/`.
- Amostras aprovadas: (anote aqui o canal, o episódio e a data quando aprovar).

## Tempos de referência
Medidos num PC com RTX 3050 (NVIDIA): transcrição ~16× o tempo real; longo de ~21 min finalizado em ~2 min 50 s; episódio de 2 h com 11 cortes 16:9 + 4 Shorts em 3 plataformas + capas em ~19 min. Sem placa NVIDIA, a transcrição e a exportação demoram bem mais. Anote aqui os tempos medidos na sua máquina.
