# Finaliza só uma amostra de um episódio (para aprovar o visual de um canal): 1 longo (com capas) + 1 Short (3 plataformas).
# Uso: python amostra.py "<pasta do episódio>" [nº do longo] [nº do Short]
import os, sys, json, shutil
import finalizar

pasta = os.path.abspath(sys.argv[1]); info = os.path.join(pasta, 'Cortes', '_edicao.json')
E = json.load(open(info, encoding='utf-8'))
gerados = [c for c in E['cortes'] if c.get('arquivo')]
nl = int(sys.argv[2]) if len(sys.argv) > 2 else min(c['n'] for c in gerados if c['tipo'] == 'Longos')
ns = int(sys.argv[3]) if len(sys.argv) > 3 else min(c['n'] for c in gerados if c['tipo'] == 'Shorts')
completo = info + '.completo'; shutil.copy(info, completo)
try:
    E['cortes'] = [c for c in E['cortes'] if (c['tipo'], c['n']) in (('Longos', nl), ('Shorts', ns))]
    json.dump(E, open(info, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    finalizar.processar(pasta)
finally:
    os.replace(completo, info)
print('AMOSTRA PRONTA: Longo', nl, '+ Short', ns)
