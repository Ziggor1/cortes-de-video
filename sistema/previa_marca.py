# Prévia de marca d'água/logo: compara, em quadros reais de um episódio, a marca atual do canal com alternativas.
# Uso: python previa_marca.py "<pasta do episódio>" [--opcoes opcoes.json] [--t16 120] [--tv 8]
#   -> <cofre>/_previas/marca/<canal>_<episódio>/GRADE_16x9.jpg e GRADE_vertical.jpg (+ um .jpg por opção). Não altera nada publicado.
# Sem --opcoes, monta 3 opções a partir do visual.json do canal:
#   A = atual; B = logo maior e mais forte; C (16:9) = logo no canto oposto · C (vertical) = logo grande no centro do topo.
# opcoes.json (opcional): {"16x9": [["rótulo", [camadas...]], ...], "vertical": [["rótulo", [camadas...]], ...]}
#   camada = {"arquivo": "logo.png", "largura": 150, "x": "W-w-30", "y": "30", "opacidade": 0.85}  (arquivo relativo à pasta visual do canal)
# Depois de escolher, a mudança vai para o visual.json e passa pela amostra em vídeo (amostra_trecho.py) antes de valer.
import os, sys, glob, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import COFRE, FF, fonte, caminho_ff, log
from finalizar import filtros_camadas
import visual

def quadro(video, t, camadas, W, H, destino):
    e, fl, ult = filtros_camadas('[b]', camadas, W, H, 1)
    filtro = f'[0:v]scale={W}:{H},setsar=1[b];' + ';'.join(fl) + (f';{ult}null[o]' if fl else ';[b]null[o]')
    cmd = [FF, '-y', '-v', 'error', '-ss', str(t), '-i', video] + e + ['-filter_complex', filtro, '-map', '[o]', '-frames:v', '1', '-q:v', '3', destino]
    subprocess.run(cmd, check=True)

def grade(imgs, rotulos, destino, W, H):
    s = 0.5 if W > H else 0.36
    w, h = int(W * s) // 2 * 2, int(H * s) // 2 * 2
    ent, fil, ft = [], [], caminho_ff(fonte('ui'))
    for i, (im, r) in enumerate(zip(imgs, rotulos)):
        r = r.replace('%', ' por cento').replace(':', ' ').replace("'", '')
        ent += ['-i', im]
        fil.append(f"[{i}:v]scale={w}:{h},drawbox=0:0:iw:52:black@0.75:fill,drawtext=fontfile={ft}:text='{r}':x=14:y=12:fontsize=26:fontcolor=yellow[g{i}]")
    n = len(imgs)
    lay = '|'.join([f'{(i % 2) * w}_{(i // 2) * h}' for i in range(n)]) if W > H else '|'.join([f'{i * w}_0' for i in range(n)])
    fil.append(''.join(f'[g{i}]' for i in range(n)) + f'xstack=inputs={n}:layout={lay}:fill=white[o]')
    subprocess.run([FF, '-y', '-v', 'error'] + ent + ['-filter_complex', ';'.join(fil), '-map', '[o]', '-frames:v', '1', '-q:v', '3', destino], check=True)

def _logo(cam):
    """Primeira camada com logo (não 'tela inteira'), para montar as alternativas."""
    return next((c for c in cam if c.get('modo') != 'tela'), None)

def opcoes_padrao(vis):
    op = {}
    c16, cv = vis['camadas'], vis['camadas_vertical']
    logo = _logo(c16) or _logo(cv) or ({'arquivo': vis['capa_logo']} if vis.get('capa_logo') else None)
    if logo:
        larg = int(logo.get('largura') or 150)
        op['16x9'] = [('A - ATUAL', c16),
                      ('B - LOGO MAIOR E MAIS FORTE', [dict(logo, largura=int(larg * 1.4), opacidade=0.85, x='W-w-30', y='30')]),
                      ('C - LOGO NO CANTO SUPERIOR ESQUERDO', [dict(logo, largura=int(larg * 1.25), opacidade=0.85, x='30', y='30')])]
        lv = _logo(cv) or logo; largv = int(lv.get('largura') or 110)
        op['vertical'] = [('A - ATUAL', cv),
                          ('B - CENTRO DO TOPO, GRANDE', [dict(lv, largura=max(200, int(largv * 2)), opacidade=1.0, x='(W-w)/2', y='250')]),
                          ('C - DIREITA, MAIOR', [dict(lv, largura=max(160, int(largv * 1.5)), opacidade=0.9, x='W-w-50', y='300')])]
    return op

def main():
    a = sys.argv[1:]
    pasta = os.path.abspath(a[0]); canal = os.path.basename(os.path.dirname(pasta)); vis = visual.carregar(canal)
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d
    if '--opcoes' in a:
        bruto = json.load(open(arg('--opcoes', ''), encoding='utf-8')); pv = vis['pasta'] or ''
        absol = lambda cams: [dict(c, arquivo=c['arquivo'] if os.path.isabs(c['arquivo']) else os.path.join(pv, c['arquivo'])) for c in cams]
        ops = {fmt: [(r, absol(c)) for r, c in lst] for fmt, lst in bruto.items()}
    else:
        ops = opcoes_padrao(vis)
    if not ops: log('O canal não tem logo no visual.json nem na pasta visual: nada a comparar.'); return 1
    longo = sorted(glob.glob(os.path.join(pasta, 'Cortes', 'Longos', '*.mp4')) + glob.glob(os.path.join(pasta, 'Cortes', 'Medios', '*.mp4')))
    short = sorted(glob.glob(os.path.join(pasta, 'Cortes', 'Shorts', '*.mp4')))
    out = os.path.join(COFRE, '_previas', 'marca', f'{canal}_{os.path.basename(pasta)}'); os.makedirs(out, exist_ok=True)
    for fmt, video, t, W, H in (('16x9', longo[0] if longo else None, float(arg('--t16', 120)), 1920, 1080),
                                ('vertical', short[0] if short else None, float(arg('--tv', 8)), 1080, 1920)):
        if fmt not in ops: continue
        if not video: log(f'sem corte {fmt} editado neste episódio (rode editar.py antes)'); continue
        imgs = []
        for k, (rot, cam) in enumerate(ops[fmt]):
            d = os.path.join(out, f'{fmt}_{"ABCDEF"[k]}.jpg'); quadro(video, t, cam, W, H, d); imgs.append(d)
        g = os.path.join(out, f'GRADE_{fmt}.jpg'); grade(imgs, [r for r, _ in ops[fmt]], g, W, H); log('grade:', g)
    return 0

if __name__ == '__main__':
    sys.exit(main())
