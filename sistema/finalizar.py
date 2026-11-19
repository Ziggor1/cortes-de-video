# Finalização para publicar.
#   Longos e médios: intro + corte com marca d'água (camadas do canal) + final 16:9, e capa 1280x720.
#   Shorts: legenda de palavra destacada + marca d'água vertical + finalização vertical de cada plataforma
#           (uma versão por plataforma: Publicar/Shorts/YouTube, /Instagram, /TikTok).
#           Todo Short ganha a finalização vertical (17/11/2026); o validar_cortes.py avisa quando corte + final passa de 3:00.
# Uso: python finalizar.py "<pasta do episódio>" [--so-capas] [--so-shorts] [--refazer] [--refazer-desde <epoch>] [--plano]
# Lê Cortes/_edicao.json (gerado pelo editar.py). Os cortes brutos em Cortes/ não são alterados.
import os, re, sys, json, shutil, tempfile, datetime, textwrap, subprocess
from comum import FF, FP, CONFIG, sp, duracao, log, final_vertical_cabe, encoder, fonte as fonte_padrao, preparar_fonte_legenda, limitar_ff
import visual

def enc():
    """Codificador H.264 detectado na máquina (NVIDIA, Apple, Intel, AMD ou CPU) — ver comum.encoder()."""
    return encoder()
AUD = ['-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2']

def run(cmd, cwd=None):
    r = subprocess.run(limitar_ff(cmd), capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=cwd)
    if r.returncode: log('ERRO', r.stderr[-900:])
    return r.returncode == 0

def tem_audio(f): return 'audio' in sp([FP, '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', f]).stdout
def e_imagem(f): return f.lower().endswith(visual.IMG)
def fps_de(f):
    return sp([FP, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'csv=p=0', f]).stdout.strip() or '30'

def filtros_camadas(base, camadas, W, H, k0):
    """Aplica as camadas de marca d'água sobre o rótulo `base`. Devolve (entradas, filtros, rótulo final)."""
    ent, fil, ult = [], [], base
    for i, c in enumerate(camadas):
        k = k0 + i; ent += ['-i', c['arquivo']]
        op = c.get('opacidade', 1)
        aj = f',format=rgba,colorchannelmixer=aa={op}' if op < 1 else ',format=rgba'
        if c.get('modo') == 'tela':
            fil.append(f'[{k}:v]scale={W}:{H}{aj}[cm{i}]'); pos = '0:0'
        else:
            larg = c.get('largura'); fil.append(f"[{k}:v]{'scale=' + str(larg) + ':-1' if larg else 'null'}{aj}[cm{i}]")
            pos = f"x='{c.get('x', 'W-w-30')}':y='{c.get('y', '30')}'"
        fil.append(f'{ult}[cm{i}]overlay={pos}:eval=frame[mk{i}]'); ult = f'[mk{i}]'
    return ent, fil, ult

def montar(principal, saida, W, H, fps, intro=None, final=None, camadas=(), ass=None, cwd=None, img_dur=3, censura=None):
    """[intro] + principal(+legenda, +camadas) + [final], com tamanho, fps e áudio normalizados."""
    entradas, filtros, segs, k = [], [], [], 0
    norm = f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps={fps},format=yuv420p'
    anorm = 'aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo'
    rot = {}
    partes = [('intro', intro), ('main', principal), ('final', final)]
    for nome, f in partes:
        if not f: continue
        entradas += (['-loop', '1', '-t', str(img_dur), '-i', f] if e_imagem(f) else ['-i', f])
        v = f'[{k}:v]{norm}'
        passo_ass = (f"ass={ass}" + (':fontsdir=fontes' if cwd and os.path.isdir(os.path.join(cwd, 'fontes')) else '')) if nome == 'main' and ass else ''
        if nome == 'main' and censura:   # desfoca e apaga as regiões do QR/anúncio do vídeo original
            filtros.append(v + f'[pc{k}]'); ult = f'[pc{k}]'
            for ci, (cx, cy, cw, ch) in enumerate(censura):
                filtros.append(f'{ult}split[ca{ci}][cb{ci}]')
                filtros.append(f'[cb{ci}]crop={cw}:{ch}:{cx}:{cy},boxblur=22:2,eq=brightness=-0.18:saturation=0.45[cd{ci}]')
                filtros.append(f'[ca{ci}][cd{ci}]overlay={cx}:{cy}[ce{ci}]'); ult = f'[ce{ci}]'
            filtros.append(ult + (passo_ass or 'null') + f'[v{k}]'); rot[k] = f'[v{k}]'
        else:
            if passo_ass: v += ',' + passo_ass
            filtros.append(v + f'[v{k}]'); rot[k] = f'[v{k}]'
        if not e_imagem(f) and tem_audio(f): filtros.append(f'[{k}:a]{anorm}[a{k}]')
        else: filtros.append(f'anullsrc=r=48000:cl=stereo,atrim=0:{(img_dur if e_imagem(f) else duracao(f)):.3f}[a{k}]')
        if nome == 'main': main_k = k
        segs.append(k); k += 1
    if camadas:
        e, fl, ult = filtros_camadas(f'[v{main_k}]', camadas, W, H, k)
        entradas += e; filtros += fl; rot[main_k] = ult
    ln = CONFIG.get('loudnorm')   # ex.: {"I": -14, "TP": -1.5, "LRA": 11}; vazio = desligado
    filtros.append(''.join(f'{rot[s]}[a{s}]' for s in segs) + f'concat=n={len(segs)}:v=1:a=1[vo]' + ('[ac]' if ln else '[ao]'))
    if ln: filtros.append(f"[ac]loudnorm=I={ln['I']}:TP={ln['TP']}:LRA={ln['LRA']},aresample=48000[ao]")
    tmp = saida[:-4] + '_tmp.mp4'
    ok = run([FF, '-y', '-v', 'error', *entradas, '-filter_complex', ';'.join(filtros), '-map', '[vo]', '-map', '[ao]',
              *enc(), *AUD, '-movflags', '+faststart', tmp], cwd=cwd)
    if ok: os.replace(tmp, saida)
    elif os.path.exists(tmp): os.remove(tmp)
    return ok

def _fonte_capa(vis):
    """Fonte da capa: a do canal (visual.json) ou a Anton que vem com o sistema (parecida com a Impact)."""
    return vis['fonte'] if vis.get('fonte') and os.path.exists(vis['fonte']) else fonte_padrao('titulo')

def capa(corte_mp4, texto, destino, vis, posicoes=(0.25, 0.5, 0.75)):
    """Capa 1280x720: um quadro do corte (uma pessoa, com zoom), borda amarela,
    frase em 2 linhas (branca + vermelha), letra pesada inclinada com contorno preto. Os QR codes do canto ficam fora
    desfocados. 3 versões com quadros de momentos diferentes do corte."""
    D = duracao(corte_mp4); trab = tempfile.mkdtemp(prefix='capa_')
    fonte = _fonte_capa(vis)
    fnome = ''
    if fonte: fnome = 'fonte' + os.path.splitext(fonte)[1]; shutil.copy(fonte, os.path.join(trab, fnome))
    ff = f"fontfile={fnome}:" if fnome else ''
    palavras = (texto or '').upper().split()
    if len(palavras) <= 1: l1, l2 = '', ' '.join(palavras)
    else:   # divide em 2 linhas equilibradas; a 2ª (vermelha) fica com o fim da frase
        corte_i = min(range(1, len(palavras)), key=lambda i: abs(len(' '.join(palavras[:i])) - len(' '.join(palavras[i:]))))
        l1, l2 = ' '.join(palavras[:corte_i]), ' '.join(palavras[corte_i:])
    for nome, t in (('l1.txt', l1), ('l2.txt', l2)):
        open(os.path.join(trab, nome), 'w', encoding='utf-8', newline='\n').write(t)
    maior = max(len(l1), len(l2), 1)
    tam = int(min(165, 1150 / (maior * 0.52)))       # Impact é condensada (~0,52 em por letra)
    borda = max(8, tam // 11)
    y2 = 700 - tam; y1 = y2 - int(tam * 0.98)
    txt = (f"color=c=black@0:s=1280x720,format=rgba"
           + (f",drawtext={ff}expansion=none:textfile=l1.txt:fontsize={tam}:fontcolor=white:borderw={borda}:bordercolor=black:x=(w-tw)/2:y={y1}" if l1 else '')
           + f",drawtext={ff}expansion=none:textfile=l2.txt:fontsize={tam}:fontcolor=0xE10600:borderw={borda}:bordercolor=black:x=(w-tw)/2:y={y2}"
           + ",shear=shx=-0.18:fillcolor=black@0[txt]")
    # um quadro só: desfoca o canto superior esquerdo (QR codes do vídeo original), zoom de 25% no centro, cores fortes
    quadro_f = ("split[a][b];[b]crop=iw*0.20:ih*0.42:0:0,boxblur=30:3[bl];[a][bl]overlay=0:0,"
                "scale=1600:900,crop=1280:720:160:50,eq=contrast=1.12:saturation=1.4:brightness=0.03,unsharp=5:5:0.8")
    feitos = []
    for i, p in enumerate(posicoes):
        q = os.path.join(trab, f'q{i}.png')
        sp([FF, '-y', '-v', 'error', '-ss', f'{max(0, D*p):.2f}', '-i', corte_mp4, '-t', '25', '-vf',
            'thumbnail=200,scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720', '-frames:v', '1', q])
        if not os.path.exists(q): continue
        qs = [q]
        f = [f'[0:v]{quadro_f}[img]']
        f.append(txt if texto else 'color=c=black@0:s=1280x720,format=rgba[txt]')
        f.append('[img][txt]overlay=0:0[c0]'); ult = '[c0]'; ent = ['-i', qs[0]]; k = 1
        if vis.get('capa_modelo'):
            ent += ['-i', vis['capa_modelo']]; f.append(f'[{k}:v]scale=1280:720[mod];{ult}[mod]overlay=0:0[c{k}]'); ult = f'[c{k}]'; k += 1
        if vis.get('capa_logo'):
            ent += ['-i', vis['capa_logo']]; f.append(f'[{k}:v]scale=110:-1[lg];{ult}[lg]overlay=W-w-26:24[c{k}]'); ult = f'[c{k}]'; k += 1
        f.append(f'{ult}drawbox=x=0:y=0:w=iw:h=ih:color=0xFFD400:t=16[fim]')
        out = os.path.join(trab, f'capa{i}.jpg')
        if run([FF, '-y', '-v', 'error', *ent, '-filter_complex', ';'.join(f), '-map', '[fim]', '-frames:v', '1', '-q:v', '2', out], cwd=trab):
            feitos.append(out)
    if not feitos: return []
    os.makedirs(os.path.dirname(destino), exist_ok=True); shutil.copy(feitos[0], destino); extras = []
    if len(feitos) > 1:
        od = os.path.join(os.path.dirname(destino), 'Opções'); os.makedirs(od, exist_ok=True)
        for j, fx in enumerate(feitos[1:], 1):
            e = os.path.join(od, os.path.basename(destino)[:-4] + f' (opção {j + 1}).jpg'); shutil.copy(fx, e); extras.append(e)
    shutil.rmtree(trab, ignore_errors=True)
    return [destino] + extras

def palavras_short(arquivo, cache):
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(arquivo): return json.load(open(cache, encoding='utf-8'))
    from transcrever import palavras
    ws = palavras(arquivo, CONFIG.get('whisper_modelo_bipe', 'medium'))
    os.makedirs(os.path.dirname(cache), exist_ok=True); json.dump(ws, open(cache, 'w', encoding='utf-8'), ensure_ascii=False)
    return ws

def frase_capa(c):
    capa_txt = (c.get('capa') or '').strip()
    if len(capa_txt.split()) >= 3: return capa_txt
    m = re.search(r'["“]([^"”]+)["”]', c.get('t1') or '')
    if m and 2 <= len(m.group(1).split()) <= 7: return m.group(1).strip().rstrip('.')
    return capa_txt

def _regioes_censura(vis):
    c = vis.get('censura') or []
    if c and isinstance(c[0], (int, float)): c = [c]
    return c

def censura_16x9(vis, W, H):
    return [(int(x*W/1920)//2*2, int(y*H/1080)//2*2, int(w*W/1920)//2*2+2, int(h*H/1080)//2*2+2)
            for x, y, w, h in _regioes_censura(vis)] or None

def censura_vertical(vis):
    """O Short já vem composto em 1080x1920 com o vídeo 16:9 na faixa central."""
    s = 1080 / 1920; y0 = (1920 - 1080 * s) / 2
    return [(int(x*s)//2*2, int(y0 + y*s)//2*2, int(w*s)//2*2+2, int(h*s)//2*2+2)
            for x, y, w, h in _regioes_censura(vis)] or None

def processar(pasta, so_capas=False, so_shorts=False, refazer=False, desde=None, plano=False):
    pasta = os.path.abspath(pasta); canal = os.path.basename(os.path.dirname(pasta))
    info = os.path.join(pasta, 'Cortes', '_edicao.json')
    if not os.path.exists(info):
        log('Sem Cortes/_edicao.json — rode editar.py neste episódio antes.'); return
    E = json.load(open(info, encoding='utf-8')); vis = visual.carregar(canal)
    if vis.get('faltando'): log('ERRO — arquivos do visual.json não encontrados:', ', '.join(vis['faltando'])); return
    for k, rot in (('intro', 'intro'), ('final', 'final 16:9'), ('finais_verticais', 'finais verticais'), ('camadas', "marca d'água 16:9"),
                   ('camadas_vertical', "marca d'água 9:16")):
        if not vis.get(k): log('Aviso — sem', rot, 'para', canal, '(segue sem)')
    finais_v = vis['finais_verticais'] or {'Todas': None}
    pub = os.path.join(pasta, 'Publicar'); res = []
    # refaz quando: --refazer, destino não existe, corte bruto mais novo, ou destino anterior a `desde` (fila retomável)
    velho = lambda s, d: (refazer or not os.path.exists(d) or os.path.getmtime(s) > os.path.getmtime(d)
                          or bool(desde and os.path.getmtime(d) < desde))
    if plano:   # só mostra o que seria feito; não altera nada
        nv = nc = 0; total = 0.0
        for c in E['cortes']:
            if not c.get('arquivo'): continue
            src = os.path.join(pasta, c['arquivo']); base = os.path.basename(src)
            if not os.path.exists(src): log('  corte bruto não encontrado:', base); continue
            if c['tipo'] in ('Longos', 'Medios'):
                if not so_capas and not so_shorts and velho(src, os.path.join(pub, c['tipo'], base)):
                    log(f"  vídeo  {c['tipo']:7} {base}  ({c.get('dur', 0) / 60:.1f} min)"); nv += 1; total += c.get('dur', 0)
                if not so_shorts and velho(src, os.path.join(pub, 'Capas', base[:-4] + '.jpg')): log('  capa  ', base); nc += 1
            elif c['tipo'] == 'Shorts' and not so_capas:
                if any(velho(src, os.path.join(pub, 'Shorts', pl, base)) for pl in finais_v):
                    log(f"  Short  ×{len(finais_v)}      {base}  ({c.get('dur', 0):.0f} s)"); nv += 1; total += c.get('dur', 0) * len(finais_v)
        log(f'PLANO: {nv} cortes a finalizar ({total / 60:.0f} min de vídeo) e {nc} capas. Nada foi alterado.')
        return
    for c in E['cortes']:
        if not c.get('arquivo'): continue
        src = os.path.join(pasta, c['arquivo']); base = os.path.basename(src)
        r = dict(n=c['n'], tipo=c['tipo'], arquivo=None, arquivos={}, capa=None, capas_extras=[], legenda=False)
        if c['tipo'] in ('Longos', 'Medios'):
            dest = os.path.join(pub, c['tipo'], base)
            if not so_capas and not so_shorts and velho(src, dest):
                os.makedirs(os.path.dirname(dest), exist_ok=True); log('finalizando:', c['tipo'], base)
                W, H = visual.dims(src)
                montar(src, dest, W or 1920, H or 1080, fps_de(src), vis['intro'] or None, vis['final'] or None, vis['camadas'],
                       img_dur=vis['imagem_duracao_s'], censura=censura_16x9(vis, W or 1920, H or 1080))
            if os.path.exists(dest): r['arquivo'] = os.path.relpath(dest, pasta)
            cp = os.path.join(pub, 'Capas', base[:-4] + '.jpg')
            if not so_shorts and velho(src, cp):
                if not c.get('capa'): log('  sem "Texto da capa" na planilha; capa só com imagem:', base)
                r['capas_extras'] = [os.path.relpath(x, pasta) for x in capa(src, frase_capa(c), cp, vis)[1:]]
            if os.path.exists(cp): r['capa'] = os.path.relpath(cp, pasta)
        elif c['tipo'] == 'Shorts' and not so_capas:
            destinos = {p: os.path.join(pub, 'Shorts', p, base) for p in finais_v}
            if any(velho(src, d) for d in destinos.values()):
                log('finalizando: Shorts', base, '→', ', '.join(destinos))
                trab = tempfile.mkdtemp(prefix='short_'); ass = None
                try:
                    ws = palavras_short(src, os.path.join(pasta, '_analise', 'legendas', base[:-4] + '.json'))
                    fonte_nome = preparar_fonte_legenda(vis, trab)
                    import legenda
                    r['legenda'] = legenda.gerar_ass(ws, os.path.join(trab, 'leg.ass'), fonte_nome, vis['legenda_cor'], vis['legenda_destaque'],
                                                     bipes=c.get('bipes') if isinstance(c.get('bipes'), list) else None)
                    ass = 'leg.ass'
                except Exception as e:
                    log('  legenda não gerada:', e)
                dsrc = duracao(src)
                for p, d in destinos.items():
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    fin = finais_v[p]
                    if fin and not final_vertical_cabe(dsrc, duracao(fin), p):
                        log(f'  {p}: corte de {dsrc:.0f} s + finalização passaria de 3:00 → sai sem a finalização vertical'); fin = None
                    montar(src, d, 1080, 1920, '30', None, fin, vis['camadas_vertical'], ass=ass, cwd=trab,
                           img_dur=vis['imagem_duracao_s'], censura=censura_vertical(vis))
                shutil.rmtree(trab, ignore_errors=True)
            else:
                r['legenda'] = None   # já existia: mantém o registro anterior
            r['arquivos'] = {p: os.path.relpath(d, pasta) for p, d in destinos.items() if os.path.exists(d)}
            if r['arquivos']: r['arquivo'] = next(iter(r['arquivos'].values()))
        res.append(r)
    pj = os.path.join(pub, '_publicar.json')
    ant = {(x['tipo'], x['n']): x for x in json.load(open(pj, encoding='utf-8')).get('cortes', [])} if os.path.exists(pj) else {}
    for r in res:   # mantém o que não foi refeito nesta rodada
        a = ant.get((r['tipo'], r['n']), {})
        for k in ('arquivo', 'arquivos', 'capa', 'capas_extras', 'legenda'):
            if r.get(k) in (None, False, [], {}) and a.get(k): r[k] = a[k]
    os.makedirs(pub, exist_ok=True)
    json.dump(dict(finalizado_em=datetime.datetime.now().isoformat(timespec='minutes'), cortes=res),
              open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('FINALIZADO:', os.path.basename(pasta), '·', sum(len(r['arquivos']) or bool(r['arquivo']) for r in res), 'vídeos ·',
        sum(1 for r in res if r['capa']), 'capas')

if __name__ == '__main__':
    _desde = float(sys.argv[sys.argv.index('--refazer-desde') + 1]) if '--refazer-desde' in sys.argv else None
    processar(sys.argv[1], '--so-capas' in sys.argv, '--so-shorts' in sys.argv, '--refazer' in sys.argv, desde=_desde, plano='--plano' in sys.argv)
