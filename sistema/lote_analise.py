# Roda transcrição + sinais + YouTube em vários episódios, um após o outro.
# Uso: python lote_analise.py "<pasta 1>" "<pasta 2>" ...
import os, sys, time, traceback
from comum import log
import transcrever, sinais, youtube

for p in sys.argv[1:]:
    p = os.path.abspath(p); nome = os.path.basename(p); t0 = time.time()
    try:
        log('==== ', nome)
        transcrever.transcrever_episodio(p)
        sinais.grade(p); sinais.intensidade(p)
        vid = youtube.id_do_video(p)
        if vid: youtube.baixar(p, vid); youtube.analisar(p, vid)
        else: log('sem id do YouTube no nome do arquivo')
        log('==== ', nome, 'pronto em', f'{(time.time() - t0) / 60:.1f} min')
    except Exception:
        log('ERRO em', nome); traceback.print_exc()
log('LOTE CONCLUÍDO')
