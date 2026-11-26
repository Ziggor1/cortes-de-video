# Confere a finalização de um ou mais episódios: duração de cada final (corte + intro/final), 3 plataformas, legendas,
# capas e o limite de 3 min dos Shorts. Uma linha por episódio e um TOTAL no fim (o Claude só afirma o que leu aqui).
# Uso: python conferir.py "<pasta 1>" ["<pasta 2>" ...]
import os, sys, json
from comum import duracao, final_vertical_cabe
import visual

LIMITE_SHORT = 180   # YouTube Shorts e Instagram Reels

def conferir(pasta):
    pasta = os.path.abspath(pasta); canal = os.path.basename(os.path.dirname(pasta)); vis = visual.carregar(canal)
    extra16 = (duracao(vis['intro']) if vis['intro'] else 0) + (duracao(vis['final']) if vis['final'] else 0)
    fv = {p: duracao(f) for p, f in vis['finais_verticais'].items()}
    pj = os.path.join(pasta, 'Publicar', '_publicar.json')
    if not os.path.exists(pj): return 0, ['ainda não finalizado (sem Publicar/_publicar.json)']
    E = {(c['tipo'], c['n']): c for c in json.load(open(os.path.join(pasta, 'Cortes', '_edicao.json'), encoding='utf-8'))['cortes']}
    P = json.load(open(pj, encoding='utf-8'))['cortes']
    prob = []; n = 0
    for r in P:
        c = E.get((r['tipo'], r['n']))
        if not c or not c.get('arquivo'): prob.append(f"{r['tipo']} {r['n']}: sem corte bruto registrado"); continue
        bruto = duracao(os.path.join(pasta, c['arquivo']))
        if r['tipo'] == 'Shorts':
            if len(r['arquivos']) != len(fv): prob.append(f"Curto {r['n']}: {len(r['arquivos'])} plataformas")
            if not r.get('legenda'): prob.append(f"Curto {r['n']}: SEM legenda")
            for p, a in r['arquivos'].items():
                n += 1; d = duracao(os.path.join(pasta, a))
                esp = bruto + (fv.get(p, 0) if final_vertical_cabe(bruto, fv.get(p, 0), p) else 0)
                if abs(d - esp) > 1: prob.append(f"Curto {r['n']} {p}: {d:.1f}s, esperado {esp:.1f}s")
                if p in ('YouTube', 'Instagram') and d > LIMITE_SHORT: prob.append(f"Curto {r['n']} {p}: {d:.0f}s passa do limite de {LIMITE_SHORT}s")
        elif r.get('arquivo'):
            n += 1; d = duracao(os.path.join(pasta, r['arquivo']))
            if abs(d - bruto - extra16) > 1: prob.append(f"{r['tipo']} {r['n']}: {d:.1f}s, esperado {bruto + extra16:.1f}s")
            if not r.get('capa') or len(r.get('capas_extras') or []) != 2: prob.append(f"{r['tipo']} {r['n']}: capas incompletas")
    return n, prob

if __name__ == '__main__':
    com = 0
    for pasta in sys.argv[1:]:
        n, prob = conferir(pasta); com += bool(prob)
        print(f'{os.path.basename(os.path.abspath(pasta))}: {n} vídeos conferidos · problemas: {prob or "nenhum"}')
    print(f'TOTAL: {len(sys.argv) - 1} episódios conferidos · {com} com problemas')
