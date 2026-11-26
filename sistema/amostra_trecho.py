# Amostra em VÍDEO REAL para aprovar mudanças visuais (marca d'água, legenda, etc.) ANTES de finalizar qualquer coisa.
# Não toca em Publicar/: gera trechos curtos em <cofre>\_previas\amostras\<Canal> - <Episódio>\ com o visual.json atual.
#   - 16:9: um trecho em cada ponto do corte (padrão 15%, 50% e 85% — os anúncios do vídeo original mudam ao longo do episódio);
#   - Short: os primeiros segundos, com legenda (se já houver cache em _analise\legendas) e marca vertical.
# Uso: python amostra_trecho.py "<pasta do episódio>" [--dur 18] [--pontos 0.15,0.5,0.85] [--longo N] [--short N]
import os, sys, json, shutil, tempfile, subprocess
import finalizar, visual
from comum import COFRE, FF, duracao, log

def arg(nome, padrao):
    return type(padrao)(sys.argv[sys.argv.index(nome) + 1]) if nome in sys.argv else padrao

pasta = os.path.abspath(sys.argv[1]); canal = os.path.basename(os.path.dirname(pasta))
dur = arg('--dur', 18.0); pontos = [float(x) for x in arg('--pontos', '0.15,0.5,0.85').split(',')]
nl, ns = arg('--longo', 0), arg('--short', 0)
E = json.load(open(os.path.join(pasta, 'Cortes', '_edicao.json'), encoding='utf-8'))
ger = [c for c in E['cortes'] if c.get('arquivo') and os.path.exists(os.path.join(pasta, c['arquivo']))]

def escolher(tipos, n):
    c = [x for x in ger if x['tipo'] in tipos and (not n or x['n'] == n)]
    return min(c, key=lambda x: x['n']) if c else None

def quadro(video, t, jpg):
    subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', '-q:v', '3', jpg])

vis = visual.carregar(canal)
out = os.path.join(COFRE, '_previas', 'amostras', f'{canal} - {os.path.basename(pasta)}'); os.makedirs(out, exist_ok=True)
trab = tempfile.mkdtemp(prefix='amostra_'); feitos = []
try:
    L = escolher(('Longos', 'Medios'), nl)
    if L:
        src = os.path.join(pasta, L['arquivo']); D = duracao(src); W, H = visual.dims(src); dl = max(5.0, dur / len(pontos))
        for k, p in enumerate(pontos, 1):
            t = max(0.0, min(D - dl, D * p)); bruto = os.path.join(trab, f'l{k}.mp4')
            subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{t:.2f}', '-t', f'{dl:.2f}', '-i', src, '-c', 'copy', bruto])
            d = os.path.join(out, f'amostra_16x9_{k}.mp4')
            if finalizar.montar(bruto, d, W or 1920, H or 1080, finalizar.fps_de(src), None, None, vis['camadas'],
                                censura=finalizar.censura_16x9(vis, W or 1920, H or 1080)):
                quadro(d, dl / 2, d[:-4] + '.jpg'); feitos.append(d); log(f'16:9 ponto {p:.0%} ({t:.0f} s do corte):', d)
    else: log('Sem longo editado neste episódio.')
    S = escolher(('Shorts',), ns)
    if S:
        src = os.path.join(pasta, S['arquivo']); base = os.path.basename(src); ds = min(dur, duracao(src)); bruto = os.path.join(trab, 's.mp4')
        subprocess.run([FF, '-y', '-v', 'error', '-t', f'{ds:.2f}', '-i', src, '-c', 'copy', bruto])
        ass = None; cache = os.path.join(pasta, '_analise', 'legendas', base[:-4] + '.json')
        if os.path.exists(cache):
            import legenda
            from comum import preparar_fonte_legenda
            ws = [w for w in json.load(open(cache, encoding='utf-8')) if w[1] <= ds]; fonte_nome = preparar_fonte_legenda(vis, trab)
            if legenda.gerar_ass(ws, os.path.join(trab, 'leg.ass'), fonte_nome, vis['legenda_cor'], vis['legenda_destaque'],
                                 bipes=S.get('bipes') if isinstance(S.get('bipes'), list) else None): ass = 'leg.ass'
        else: log('Short sem cache de legenda: amostra sem legenda (finalize um Short antes, se a legenda for o que está em teste).')
        d = os.path.join(out, 'amostra_short.mp4')
        if finalizar.montar(bruto, d, 1080, 1920, '30', None, None, vis['camadas_vertical'], ass=ass, cwd=trab, censura=finalizar.censura_vertical(vis)):
            quadro(d, min(4.0, ds / 2), d[:-4] + '.jpg'); feitos.append(d); log('Short:', d)
    else: log('Sem Short editado neste episódio.')
finally:
    shutil.rmtree(trab, ignore_errors=True)
log(f'AMOSTRA PRONTA: {len(feitos)} trechos em', out, '— mostre os .jpg no chat e peça ao usuário para assistir aos .mp4 antes de aprovar.')
