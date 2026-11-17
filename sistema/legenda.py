# Legenda com palavra destacada (formato ASS) para Shorts 1080x1920.
import re, unicodedata
from comum import CONFIG

def _norm(w): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', w.lower()).encode('ascii', 'ignore').decode())

def censurar(w):
    if _norm(w) in set(CONFIG['palavroes']):
        letras = re.sub(r'[^\wÀ-ÿ]', '', w)
        return letras[:1] + '*' * max(2, len(letras) - 1)
    return w

def preparar(palavras, bipes=None):
    """palavras = [[ini, fim, texto], ...] no tempo do Short. Os trechos com bipe viram palavra censurada."""
    bipes = [b for b in (bipes or []) if isinstance(b, (list, tuple)) and b[1] is not None]
    fora = [p for p in palavras if not any(p[0] < b[1] and p[1] > b[0] for b in bipes)]
    fora += [[b[0], b[1], str(b[2])] for b in bipes]
    return [[a, b, censurar(t.strip())] for a, b, t in sorted(fora) if t.strip()]

def grupos(ws, max_pal=3, max_chars=16, pausa=0.5):
    out, g = [], []
    for w in ws:
        if g and (len(g) >= max_pal or len(' '.join(x[2] for x in g + [w])) > max_chars or w[0] - g[-1][1] > pausa):
            out.append(g); g = []
        g.append(w)
        if re.search(r'[.!?…]$', w[2]): out.append(g); g = []
    if g: out.append(g)
    return out

def _t(s):
    s = max(0, s); h = int(s // 3600); m = int(s % 3600 // 60); return f'{h}:{m:02d}:{s % 60:05.2f}'

def _cor(hexrgb): h = hexrgb.lstrip('#'); return f'&H00{h[4:6]}{h[2:4]}{h[0:2]}&'.upper()

def gerar_ass(palavras, destino, fonte='Archivo Black', cor='FFFFFF', destaque='FFD400', y_base=1480, bipes=None):
    ws = preparar(palavras, bipes)
    L = ['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1080', 'PlayResY: 1920', 'WrapStyle: 2', 'ScaledBorderAndShadow: yes', '',
         '[V4+ Styles]',
         'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, '
         'ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
         f'Style: Leg,{fonte},88,{_cor(cor)},{_cor(cor)},&H00000000&,&H80000000&,-1,0,0,0,100,100,1,0,1,7,3,2,60,60,{1920 - y_base},1',
         '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    gs = grupos(ws)
    for gi, g in enumerate(gs):
        fim_grupo = g[-1][1] + 0.15
        if gi + 1 < len(gs): fim_grupo = min(fim_grupo, gs[gi + 1][0][0])
        for i, w in enumerate(g):
            ini = w[0]; fim = g[i + 1][0] if i + 1 < len(g) else fim_grupo
            if fim <= ini: fim = ini + 0.05
            partes = []
            for j, x in enumerate(g):
                t = x[2].upper().replace('{', '(').replace('}', ')')
                partes.append(f'{{\\c{_cor(destaque)}\\fscx108\\fscy108}}{t}{{\\c{_cor(cor)}\\fscx100\\fscy100}}' if j == i else t)
            L.append(f'Dialogue: 0,{_t(ini)},{_t(fim)},Leg,,0,0,0,,' + ' '.join(partes))
    open(destino, 'w', encoding='utf-8-sig').write('\n'.join(L) + '\n')
    return len(gs)
