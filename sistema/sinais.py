# Sinais de apoio à análise: grade de quadros e intensidade do áudio.
# Uso: python sinais.py "<pasta do episódio>"
#   -> _analise/grade.jpg (64 quadros com o tempo) e _analise/intensidade.csv (janelas de 10 s)
import os, sys, json, wave, tempfile, csv
import numpy as np
from comum import FF, sp, duracao, hms, video_de, log, fonte, caminho_ff

def grade(pasta):
    v = video_de(pasta); D = duracao(v); passo = max(5, D/64)
    dest = os.path.join(pasta, '_analise', 'grade.jpg')
    def tentar(fonte):
        txt = f"drawtext={'fontfile=' + fonte + ':' if fonte else ''}text='%{{pts\\:hms}}':x=4:y=4:fontsize=18:fontcolor=yellow:box=1:boxcolor=black"
        return sp([FF, '-y', '-v', 'error', '-skip_frame', 'nokey', '-i', v, '-an', '-vf',
                   f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{passo:.0f})',scale=240:-1,{txt},tile=8x8",
                   '-frames:v', '1', '-fps_mode', 'vfr', dest])
    r = tentar(caminho_ff(fonte('ui')))
    if r.returncode: r = tentar('')
    log('grade:', 'ok' if r.returncode == 0 else r.stderr[-300:])

def intensidade(pasta, janela=10):
    v = video_de(pasta); wav = os.path.join(tempfile.gettempdir(), 'claude_cortes_sinais.wav')
    sp([FF, '-y', '-v', 'error', '-i', v, '-vn', '-ac', '1', '-ar', '8000', wav])
    w = wave.open(wav); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; w.close()
    n = len(a) // (8000*janela); x = a[:n*8000*janela].reshape(n, -1)
    db = 20*np.log10(np.sqrt((x**2).mean(1)) + 1e-9)
    # velocidade da fala: palavras por janela, se a transcrição já existir
    wps = np.zeros(n); tj = os.path.join(pasta, '_analise', 'transcricao.json')
    if os.path.exists(tj):
        for a0, b0, t in json.load(open(tj, encoding='utf-8')):
            k = int(a0 // janela)
            if k < n: wps[k] += 1
    z = lambda y: (y - y.mean()) / (y.std() + 1e-9)
    score = (z(db) + (z(wps) if wps.any() else 0)) / (2 if wps.any() else 1)
    dest = os.path.join(pasta, '_analise', 'intensidade.csv')
    with open(dest, 'w', newline='', encoding='utf-8') as f:
        c = csv.writer(f); c.writerow(['inicio', 'volume_db', 'palavras', 'intensidade'])
        for i in range(n): c.writerow([hms(i*janela), round(float(db[i]), 1), int(wps[i]), round(float(score[i]), 2)])
    top = np.argsort(-score)[:15]
    log('picos de intensidade:', ', '.join(hms(i*janela) for i in sorted(top)))

if __name__ == '__main__':
    p = sys.argv[1]; os.makedirs(os.path.join(p, '_analise'), exist_ok=True)
    grade(p); intensidade(p)
