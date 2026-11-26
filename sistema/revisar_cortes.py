# Abre no navegador a revisão visual dos cortes de um episódio (desde a 1.2.0).
# Uso: python revisar_cortes.py "<pasta do episódio>" [--fase longos|curtos] [--sem-navegador]
#   Fase 1 (longos): o episódio inteiro com os cortes longos propostos e os trechos sem corte; você aprova, recusa,
#   aumenta, diminui ou propõe cortes. Fase 2 (curtos): os cortes curtos dentro dos longos aprovados.
#   A revisão fica em _analise/revisao_cortes.json; depois: python aplicar_revisao.py "<pasta>" --aplicar
#   (ou o botão "Aplicar" da própria página).
import os, sys
from comum import CONFIG, FF, FP, log


def main():
    if len(sys.argv) < 2:
        print('uso: python revisar_cortes.py "<pasta do episódio>" [--fase longos|curtos] [--sem-navegador]'); return 2
    pasta = os.path.abspath(sys.argv[1])
    fase = sys.argv[sys.argv.index('--fase') + 1] if '--fase' in sys.argv else None
    if fase not in (None, 'longos', 'curtos'): log('fase deve ser "longos" ou "curtos"'); return 2
    from revisao_servidor import revisar_cortes
    try:
        revisar_cortes(pasta, fase=fase, porta=int(CONFIG.get('revisao_porta', 8766)),
                       abrir='--sem-navegador' not in sys.argv, ffmpeg=FF, ffprobe=FP)
    except FileNotFoundError as e:
        log(str(e)); return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
