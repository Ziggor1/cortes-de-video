---
tipo: regra
tags: [regra]
---
# Padrões de edição

Aplicados por `_sistema/editar.py`. As opções ajustáveis ficam em `_sistema/config.json`.

## Formatos
| Tipo | Formato | Como |
|---|---|---|
| Cortes longos | 16:9, resolução original | Recorte sem recodificar (qualidade idêntica ao original; borda pode variar 1–2 s pelo quadro-chave) |
| Cortes curtos (Shorts, Reels, TikTok) | 9:16, 1080×1920 | Vídeo inteiro no centro com fundo desfocado; codificador da placa de vídeo quando disponível (NVIDIA, Apple, Intel ou AMD), senão CPU |

## Remoções dentro dos cortes
- Tudo que está em **Remover** sai do corte e as partes são emendadas.
- **Atenção** sai do corte, **exceto**:
  - trechos com mais de 5 min (ex.: reacts inteiros; removê-los esvaziaria o corte);
  - trechos cuja observação pede só conferir, verificar, atribuir ou manter a linguagem.
  Esses ficam e aparecem como alerta na nota do episódio.
- Se um corte inteiro estiver marcado para remoção, ele não é gerado.

## Bordas
- Planilha v2 (tempos no limite das falas): usa os tempos exatos.
- Planilha v1 (±30 s) e emendas de remoção: ajusta para a pausa de fala mais próxima (até 3 s).

## Bipes
Cortes curtos com "bipar" na observação são transcritos e recebem bipe de 1 kHz sobre os palavrões da lista em `config.json`. Os segundos ficam na aba "Bipes" do relatório.

## Versões
Se a planilha mudar depois da edição, a próxima edição guarda os cortes anteriores em `Cortes_vN_antigo` (nada é apagado).

## Arquivos de saída
`Cortes/Longos` (`Longo NN - tema.mp4`), `Cortes/Cortes Curtos` (`Curto NN - tema.mp4`), `Cortes/Relatorio_Edicao.xlsx` (abas Edição, Alertas mantidos, Bipes).

## Cortes de até 3 minutos são cortes curtos
- Todo corte de até **3:00** de duração final (depois das remoções) vira corte curto (YouTube Shorts, Reels e TikTok). Um longo que, depois das remoções, ficar com até 3:00 ganha também a versão vertical.
- Todo corte curto ganha a **finalização vertical** nas 3 plataformas; os longos ganham **intro + final 16:9**. Se o Short passar de 2:53, o `validar_cortes.py` avisa: com os 7 s da finalização ele passa de 3:00 e o YouTube/Instagram o tratam como vídeo comum. Configurável em `_sistema/config.json`: `limite_short_s` (180) e `plataformas_com_limite` (vazio = nenhuma perde a finalização).
- Ajuste de início/fim marcado no longo vale também para a versão vertical, se ela não tiver ajuste próprio.

## Enquadramento, pausas e volume
- **Enquadramento dos Shorts:** zoom 1.5 sobre o 16:9 (corta as laterais; o vídeo ocupa ~47% da altura) e fundo desfocado. `config.json`: `vertical_zoom`; por canal, `vertical_zoom` no `visual.json`.
- **Pausas nos Shorts:** silêncios acima de 0,6 s entre palavras são cortados (folga de 0,15 s de cada lado e fade de áudio de 20–30 ms). `config.json`: `short_cortar_pausas_acima_s`, `short_folga_pausa_s`.
- **Volume:** `loudnorm` em -14 LUFS (pico -1,5 dBTP) na saída de longos e curtos. `config.json`: `loudnorm`.
- **Pedidos de like:** frases como "dá like na live" dentro de um corte viram linhas "Remover (outros) · Pedido de like (automático)" na planilha. Apague a linha para manter o trecho. `config.json`: `remover_pedidos_de_like`.
