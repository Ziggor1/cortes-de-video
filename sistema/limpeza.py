# Lista o que está acumulado no cofre e pode ser apagado. Sem opções, SÓ LISTA.
# Apagar exige a permissão do usuário no chat e a categoria escrita por extenso:
#   python limpeza.py                      -> lista por categoria, com tamanho
#   python limpeza.py --apagar tmp,previas -> apaga só essas categorias
# Categorias:
#   tmp           arquivos *_tmp.mp4 e *.completo deixados por processos interrompidos (ignora os mexidos há menos de 15 min)
#   antigos       pastas Cortes_vN_antigo (cortes de planilhas anteriores)
#   substituidos  _analise\substituidos (cortes trocados por ajuste de borda)
#   planilhas     _analise\planilhas_antigas
#   previas       <cofre>\_previas (grades e amostras de teste)
import os, sys, glob, time, shutil
from comum import COFRE, TRABALHO, episodios, log

def tamanho(p):
    if os.path.isfile(p): return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(p) for f in fs)

def achar():
    c = {k: [] for k in ('tmp', 'antigos', 'substituidos', 'planilhas', 'previas')}
    for r, _, fs in os.walk(TRABALHO):
        for f in fs:
            p = os.path.join(r, f)
            if (f.endswith('_tmp.mp4') or f.endswith('.completo')) and time.time() - os.path.getmtime(p) > 900: c['tmp'].append(p)
    for ep in episodios():
        c['antigos'] += [d for d in glob.glob(os.path.join(ep, 'Cortes_v*_antigo')) if os.path.isdir(d)]
        for k, sub in (('substituidos', 'substituidos'), ('planilhas', 'planilhas_antigas')):
            d = os.path.join(ep, '_analise', sub)
            if os.path.isdir(d) and os.listdir(d): c[k].append(d)
    pv = os.path.join(COFRE, '_previas')
    if os.path.isdir(pv): c['previas'] += [os.path.join(pv, x) for x in sorted(os.listdir(pv))]
    return c

if __name__ == '__main__':
    c = achar(); apagar = sys.argv[sys.argv.index('--apagar') + 1].split(',') if '--apagar' in sys.argv else []
    desconhecidas = [k for k in apagar if k not in c]
    if desconhecidas: print('Categoria desconhecida:', ', '.join(desconhecidas)); sys.exit(1)
    total = 0
    for k, itens in c.items():
        t = sum(tamanho(p) for p in itens); total += t
        print(f'\n[{k}] {len(itens)} itens · {t / 1e6:,.0f} MB' + ('  → APAGANDO' if k in apagar else ''))
        for p in itens:
            print(f'   {tamanho(p) / 1e6:8,.1f} MB  {os.path.relpath(p, COFRE)}')
            if k in apagar:
                shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
    print(f'\nTotal listado: {total / 1e6:,.0f} MB.' + (' Nada foi apagado.' if not apagar else ' Apagado: ' + ', '.join(apagar) + '.'))
