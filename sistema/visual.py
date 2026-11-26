# Identidade visual de cada canal (pasta "Conteudo Visual" dentro de <Pasta de Trabalho>/<Canal>/).
# O arquivo visual.json da pasta visual define tudo; sem ele, os arquivos são descobertos pelo nome.
# Uso: python visual.py   -> mostra o que será usado em cada canal
#
# visual.json:
# {
#   "intro": "arquivo.mp4", "final": "arquivo.mp4",
#   "finais_verticais": {"YouTube": "a.mp4", "Instagram": "b.mp4", "TikTok": "c.mp4"},
#   "camadas":          [ {camada}, ... ],     # marca d'água dos longos, aplicadas em ordem
#   "camadas_vertical": [ {camada}, ... ],     # marca d'água dos Shorts
#   "capa_logo": "logo.png", "capa_modelo": "", "fonte": "",
#   "capa_cor_texto": "FFD400", "capa_cor_contorno": "000000", "legenda_cor": "FFFFFF", "legenda_destaque": "FFD400",
#   "censura": [[x, y, largura, altura]]   # regiões (px de 1920x1080 do vídeo original) desfocadas/apagadas (QR do patrocinador)
# }
# camada = {"arquivo": "x.png", "modo": "tela"}                      -> estica para o quadro inteiro (PNG do tamanho do vídeo)
#        | {"arquivo": "x.png", "largura": 180, "x": "W-w-30", "y": "30", "opacidade": 1}
#          (x e y aceitam expressões do ffmpeg com t = segundos do corte, W/H = vídeo, w/h = camada)
import os, json, glob, struct
from comum import TRABALHO, FP, sp, pasta_visual, _sem_acento

VID = ('.mp4', '.mov', '.mkv', '.webm', '.avi')
IMG = ('.png', '.webp', '.jpg', '.jpeg')
PLATAFORMAS = {'YouTube': ('youtube', 'shorts'), 'Instagram': ('instagram', 'reels', 'insta'), 'TikTok': ('tiktok', 'tik tok')}
PADRAO = {"intro": "", "final": "", "finais_verticais": {}, "camadas": [], "camadas_vertical": [], "capa_logo": "", "capa_modelo": "",
          "fonte": "", "imagem_duracao_s": 3, "capa_cor_texto": "FFD400", "capa_cor_contorno": "000000",
          "legenda_cor": "FFFFFF", "legenda_destaque": "FFD400", "censura": []}

def dims(f):
    o = sp([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', f]).stdout.strip()
    try:
        w, h = map(int, o.split(',')[:2]); return w, h
    except ValueError: return 0, 0

def nome_fonte(arquivo):
    """Nome da família na tabela 'name' de um TTF/OTF (sem bibliotecas extras)."""
    try:
        d = open(arquivo, 'rb').read(); n = struct.unpack('>H', d[4:6])[0]
        for i in range(n):
            tag, _, off, ln = struct.unpack('>4sIII', d[12+16*i:28+16*i])
            if tag != b'name': continue
            _, cnt, so = struct.unpack('>HHH', d[off:off+6]); nomes = {}
            for k in range(cnt):
                pid, eid, lid, nid, l, o = struct.unpack('>HHHHHH', d[off+6+12*k:off+18+12*k])
                if nid in (1, 16):
                    raw = d[off+so+o:off+so+o+l]
                    nomes[nid] = raw.decode('utf-16-be', 'ignore') if pid in (0, 3) else raw.decode('latin-1', 'ignore')
            return nomes.get(16) or nomes.get(1)
    except Exception:
        return None

def _tem(nome, *chaves): return any(k in _sem_acento(os.path.basename(nome)) for k in chaves)

def carregar(canal):
    pv = pasta_visual(os.path.join(TRABALHO, canal)); cfg = json.loads(json.dumps(PADRAO)); cfg['pasta'] = pv
    if not pv: return cfg
    j = os.path.join(pv, 'visual.json'); explicito = os.path.exists(j)
    if explicito: cfg.update(json.load(open(j, encoding='utf-8')))
    abs_ = lambda f: f if (not f or os.path.isabs(f)) else os.path.join(pv, f)
    arqs = [f for f in glob.glob(os.path.join(pv, '*')) if os.path.isfile(f)]
    k_final = ('final', 'encerr', 'outro', 'endcard', 'fechamento')
    horizontal = lambda f: (lambda w, h: w >= h)(*dims(f))
    primeiro = lambda c: sorted(c, key=lambda f: (len(os.path.basename(f)), f))[0] if c else ''
    if not cfg['intro']:
        cfg['intro'] = primeiro([f for f in arqs if f.lower().endswith(VID + IMG) and _tem(f, 'intro', 'abertura', 'vinheta') and horizontal(f)])
    if not cfg['final']:
        cfg['final'] = primeiro([f for f in arqs if f.lower().endswith(VID + IMG) and _tem(f, *k_final) and horizontal(f)])
    if not cfg['finais_verticais']:
        verts = [f for f in arqs if f.lower().endswith(VID + IMG) and _tem(f, *k_final) and not horizontal(f)]
        for plat, chaves in PLATAFORMAS.items():
            achado = primeiro([f for f in verts if _tem(f, *chaves)])
            if achado: cfg['finais_verticais'][plat] = achado
        if not cfg['finais_verticais'] and verts: cfg['finais_verticais'] = {'Todas': primeiro(verts)}
    if not cfg['camadas'] and not explicito:   # sem visual.json: logo pequeno no canto
        logo = primeiro([f for f in arqs if f.lower().endswith(IMG) and _tem(f, 'marca', 'logo', 'watermark', 'dagua', 'selo', 'emblema')])
        if logo:
            cfg['camadas'] = [{'arquivo': logo, 'largura': 180, 'x': 'W-w-30', 'y': '30', 'opacidade': 0.85}]
            cfg['camadas_vertical'] = [{'arquivo': logo, 'largura': 200, 'x': 'W-w-40', 'y': '60', 'opacidade': 0.85}]
    if not cfg['capa_logo']:
        cfg['capa_logo'] = primeiro([f for f in arqs if f.lower().endswith(IMG) and _tem(f, 'logo', 'emblema', 'selo')])
    if not cfg['fonte']:
        cfg['fonte'] = primeiro([f for f in arqs if f.lower().endswith(('.ttf', '.otf'))])
    for k in ('intro', 'final', 'capa_logo', 'capa_modelo', 'fonte'): cfg[k] = abs_(cfg[k])
    cfg['finais_verticais'] = {p: abs_(f) for p, f in cfg['finais_verticais'].items()}
    for k in ('camadas', 'camadas_vertical'): cfg[k] = [dict(c, arquivo=abs_(c['arquivo'])) for c in cfg[k]]
    cfg['fonte_nome'] = nome_fonte(cfg['fonte']) if cfg['fonte'] else None
    faltando = [f for f in [cfg['intro'], cfg['final'], cfg['capa_logo'], cfg['fonte'], *cfg['finais_verticais'].values(),
                            *[c['arquivo'] for c in cfg['camadas'] + cfg['camadas_vertical']]] if f and not os.path.exists(f)]
    cfg['faltando'] = faltando
    return cfg

def canais():
    return [c for c in sorted(os.listdir(TRABALHO)) if os.path.isdir(os.path.join(TRABALHO, c)) and pasta_visual(os.path.join(TRABALHO, c))]

if __name__ == '__main__':
    for c in canais():
        v = carregar(c); pv = v['pasta']; r = lambda f: os.path.relpath(f, pv) if f else '— não definido'
        print(f"== {c}  ({os.path.basename(pv)}{', visual.json' if os.path.exists(os.path.join(pv, 'visual.json')) else ', sem visual.json'})")
        print(f"  intro            {r(v['intro'])}"); print(f"  final 16:9       {r(v['final'])}")
        for p, f in v['finais_verticais'].items(): print(f"  final vertical   {p}: {r(f)}")
        for k, rot in (('camadas', 'marca 16:9'), ('camadas_vertical', 'marca 9:16')):
            for cm in v[k]: print(f"  {rot:16} {r(cm['arquivo'])}  ({'tela inteira' if cm.get('modo') == 'tela' else 'largura ' + str(cm.get('largura')) + ' px'})")
        print(f"  logo da capa     {r(v['capa_logo'])}"); print(f"  fonte            {r(v['fonte'])}{'  (' + v['fonte_nome'] + ')' if v['fonte_nome'] else '  (padrão: Archivo Black/Anton, que vêm com o sistema)'}")
        if v['faltando']: print('  FALTANDO:', ', '.join(v['faltando']))
