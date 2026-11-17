# Reanálise de um episódio que já tem planilha: mantém a seleção, as notas e os títulos da planilha atual,
# e recalcula os tempos pela transcrição nova (ajuste fino das bordas do planilha.py) e a intensidade do áudio.
# Uso: python reanalisar.py "<pasta do episódio>"
# A planilha anterior vai para _analise/planilhas_antigas/; a nova sai com o mesmo nome.
import os, sys, json, shutil, datetime
import openpyxl
from comum import planilha_de, secs, log
import planilha

CAMPOS = {'Categoria': 'categoria', 'Título / Tema': 'tema', 'Gancho': 'gancho', 'Autossuf.': 'autossuf', 'Emoção': 'emocao',
          'Frase': 'frase', 'Tema em alta': 'em_alta', 'Título 1 – citação': 'titulo1', 'Título 2 – pergunta': 'titulo2',
          'Título 3 – busca': 'titulo3', 'Texto da capa': 'capa', 'Primeira frase': 'primeira_frase', 'Observação': 'obs'}

def hmsf(t): return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'

def para_json(xl):
    ws = openpyxl.load_workbook(xl, data_only=True)['Cortes']
    titulo = str(ws['A1'].value or '').split('—', 1)[-1].strip() or os.path.basename(xl)
    linhas = list(ws.iter_rows(values_only=True)); h = next(i for i, r in enumerate(linhas) if r and r[0] == 'Nº')
    cab = [str(c or '') for c in linhas[h]]; cortes = []
    for r in linhas[h + 1:]:
        if not r or not isinstance(r[0], (int, float)) or r[cab.index('Início')] is None: continue
        d = dict(zip(cab, r))
        c = {CAMPOS[k]: d.get(k) for k in CAMPOS if k in d}
        c['inicio'] = hmsf(secs(d['Início'])); c['fim'] = hmsf(secs(d['Fim']))
        for k in ('gancho', 'autossuf', 'emocao', 'frase', 'em_alta'): c[k] = int(c.get(k) or 0)
        cortes.append(c)
    return dict(titulo=titulo, arquivo=os.path.basename(xl), cortes=cortes)

if __name__ == '__main__':
    pasta = os.path.abspath(sys.argv[1]); xl = planilha_de(pasta)
    if not os.path.exists(os.path.join(pasta, '_analise', 'transcricao.json')):
        log('Sem _analise/transcricao.json: rode transcrever.py antes.'); sys.exit(1)
    j = para_json(xl)
    json.dump(j, open(os.path.join(pasta, '_analise', 'cortes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    antigas = os.path.join(pasta, '_analise', 'planilhas_antigas'); os.makedirs(antigas, exist_ok=True)
    selo = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    shutil.move(xl, os.path.join(antigas, os.path.basename(xl)[:-5] + f'_{selo}.xlsx'))
    log('planilha anterior guardada em _analise/planilhas_antigas;', len(j['cortes']), 'linhas reaproveitadas')
    planilha.gerar(pasta)
