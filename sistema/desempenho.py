# Lê a aba "Desempenho" das planilhas (views reais preenchidas por você) e mostra quais critérios da nota acertaram.
# Só usa números digitados na planilha; com menos de 5 cortes publicados num grupo, não calcula nada (nunca estima).
# Correlação de postos (Spearman) entre cada critério e as views de 7 dias, por canal + tipo de corte.
# Uso: python desempenho.py   -> resumo na tela e _sistema\desempenho.json
import os, json
from openpyxl import load_workbook
from comum import AQUI, episodios, planilha_de, log

CRIT = ['gancho', 'autossuf', 'emocao', 'frase', 'em_alta']; MIN = 5

def num(v):
    try: return float(str(v).replace('.', '').replace(',', '.')) if isinstance(v, str) else float(v)
    except (TypeError, ValueError): return None

def postos(v):
    ordem = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and v[ordem[j + 1]] == v[ordem[i]]: j += 1
        for k in range(i, j + 1): r[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return r

def spearman(x, y):
    a, b = postos(x), postos(y); n = len(a); ma, mb = sum(a) / n, sum(b) / n
    sa = sum((p - ma) ** 2 for p in a) ** 0.5; sb = sum((p - mb) ** 2 for p in b) ** 0.5
    return round(sum((p - ma) * (q - mb) for p, q in zip(a, b)) / (sa * sb), 2) if sa and sb else None

def coletar():
    reg = []
    for pasta in episodios():
        x = planilha_de(pasta)
        if not x: continue
        try: wb = load_workbook(x, data_only=False)
        except Exception as e: log('não abriu', x, e); continue
        if 'Cortes' not in wb.sheetnames or 'Desempenho' not in wb.sheetnames: continue
        ws = wb['Cortes']
        if not str(ws.cell(3, 7).value or '').startswith('Nota'): continue      # planilha no formato antigo
        cortes = {}
        for r in range(4, ws.max_row + 1):
            n = ws.cell(r, 1).value
            if n is None: continue
            pts = [num(ws.cell(r, c).value) for c in range(8, 13)]
            if any(p is None for p in pts): continue
            cortes[int(n)] = dict(categoria=ws.cell(r, 2).value, tema=ws.cell(r, 6).value, **dict(zip(CRIT, pts)), nota=sum(pts))
        d = wb['Desempenho']
        for r in range(4, d.max_row + 1):
            n, v7 = num(d.cell(r, 1).value), num(d.cell(r, 8).value)
            if n is None or v7 is None or int(n) not in cortes: continue
            reg.append(dict(canal=os.path.basename(os.path.dirname(pasta)), episodio=os.path.basename(pasta), n=int(n),
                            plataforma=d.cell(r, 4).value, views48=num(d.cell(r, 7).value), views7=v7,
                            ctr=num(d.cell(r, 9).value), retencao=num(d.cell(r, 10).value), **cortes[int(n)]))
    return reg

def resumo():
    reg = coletar(); grupos = {}
    for x in reg: grupos.setdefault((x['canal'], x['categoria']), []).append(x)
    out = dict(total=len(reg), minimo=MIN, grupos=[])
    log(f'{len(reg)} cortes publicados com "Views 7 dias" preenchido.')
    for (canal, cat), g in sorted(grupos.items()):
        item = dict(canal=canal, categoria=cat, n=len(g))
        if len(g) < MIN:
            item['situacao'] = f'dados insuficientes ({len(g)} de {MIN})'; log(f'  {canal} · {cat}: {item["situacao"]}')
        else:
            v = [x['views7'] for x in g]
            item['correlacao'] = {k: spearman([x[k] for x in g], v) for k in CRIT + ['nota']}
            melhor = max(g, key=lambda x: x['views7']); pior = min(g, key=lambda x: x['views7'])
            item['mais_visto'] = dict(tema=melhor['tema'], views7=melhor['views7'], nota=melhor['nota'])
            item['menos_visto'] = dict(tema=pior['tema'], views7=pior['views7'], nota=pior['nota'])
            log(f'  {canal} · {cat} (n={len(g)}): ' + ', '.join(f'{k} {c:+.2f}' if c is not None else f'{k} –' for k, c in item['correlacao'].items()))
            log(f"     mais visto: {melhor['tema']} ({melhor['views7']:.0f} views, nota {melhor['nota']:.0f}); "
                f"menos visto: {pior['tema']} ({pior['views7']:.0f} views, nota {pior['nota']:.0f})")
        out['grupos'].append(item)
    if not reg: log('Nada preenchido ainda: digite o Nº do corte e as views na aba "Desempenho" de cada planilha.')
    json.dump(out, open(os.path.join(AQUI, 'desempenho.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return out

if __name__ == '__main__':
    resumo()
