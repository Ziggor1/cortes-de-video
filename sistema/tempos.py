# Acha o tempo exato de frases na transcrição (para montar o cortes.json sem errar segundos).
# Uso: python tempos.py "<pasta do episódio>" "<arquivo com uma frase por linha>"
#      Uma linha pode terminar com "@h:mm:ss" para buscar só depois desse tempo.
# Saída por frase: tempo, início–fim em segundos, nº de ocorrências e as palavras de cada lado.
import json, os, re, sys, unicodedata
from comum import hms

def norm(s):
    return re.sub(r'[^a-z0-9 ]', '', unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode())

def carregar(pasta):
    ws = json.load(open(os.path.join(pasta, '_analise', 'transcricao.json'), encoding='utf-8'))
    return ws, [norm(w[2]).strip() for w in ws]

def achar(ws, toks, frase, depois=0.0):
    alvo = norm(frase).split(); out = []
    for i in range(len(toks) - len(alvo) + 1):
        if ws[i][0] >= depois and all(toks[i + k] == alvo[k] for k in range(len(alvo))): out.append(i)
    return out, len(alvo)

if __name__ == '__main__':
    ws, toks = carregar(os.path.abspath(sys.argv[1]))
    for linha in [l.strip() for l in open(sys.argv[2], encoding='utf-8-sig') if l.strip()]:
        frase, dep = linha, 0.0
        if '@' in linha:
            frase, d = linha.rsplit('@', 1); dep = sum(float(x) * 60 ** k for k, x in enumerate(reversed(d.strip().split(':'))))
        r, n = achar(ws, toks, frase, dep)
        if not r: print(f'NÃO ACHEI: {frase}'); continue
        i = r[0]; j = i + n - 1
        antes = ' '.join(w[2] for w in ws[max(0, i - 6):i]); depois = ' '.join(w[2] for w in ws[j + 1:j + 7])
        print(f'{hms(ws[i][0])} ({ws[i][0]:.2f}–{ws[j][1]:.2f}) x{len(r)}  [{frase}]  …{antes} ‖ {depois}…')
