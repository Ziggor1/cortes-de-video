# Gera os cortes de um episódio a partir da planilha Cortes_*.xlsx.
# Uso: python editar.py "<pasta do episódio>" [--plano]
#   --plano  só mostra o que seria feito, sem gerar arquivos.
import os, re, sys, json, datetime, unicodedata
import openpyxl
from comum import FF, CONFIG, sp, duracao, secs, hms, limpar, video_de, planilha_de, log, encoder

def vf_vert(zoom=1.0):
    """Vertical 1080x1920: fundo desfocado + o vídeo no meio. zoom > 1 corta as laterais e o vídeo ocupa mais a tela
    (1.0 = faixa 16:9 inteira; 1.5 ≈ 47% da altura; 1.78 = quadrado)."""
    fg = f"crop=iw/{zoom:.3f}:ih," if zoom and zoom > 1.0 else ""
    return ("[0:v]split[a][b];[a]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=10,"
            f"scale=1080:1920,setsar=1[bg];[b]{fg}scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
VF_VERT = vf_vert()
AUD = ['-c:a', 'aac', '-b:a', '160k', '-ar', '48000']

def enc_vertical():
    """Codificador H.264 detectado na máquina (NVIDIA, Apple, Intel, AMD ou CPU) — ver comum.encoder()."""
    return encoder() + ['-r', '30']

def run(cmd):
    r = sp(cmd)
    if r.returncode: log('ERRO', r.stderr[-800:])
    return r.returncode == 0

def silencio_perto(video, t, D, janela=3.0):
    a = max(0, t-janela); d = min(2*janela, D-a)
    r = sp([FF, '-hide_banner', '-nostats', '-ss', f'{a:.3f}', '-i', video, '-t', f'{d:.3f}', '-vn',
            '-af', 'silencedetect=n=-32dB:d=0.25', '-f', 'null', '-']).stderr
    st = [float(x) for x in re.findall(r'silence_start: (-?[\d.]+)', r)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r)]
    mids = [a + (max(s, 0) + (en[i] if i < len(en) else d))/2 for i, s in enumerate(st)]
    return min(mids, key=lambda m: abs(m-t)) if mids else t

def ler_planilha(xl, D):
    wb = openpyxl.load_workbook(xl, data_only=True); ws = wb['Cortes']
    cab = [str(c or '') for c in next(r for r in ws.iter_rows(min_row=1, max_row=6, values_only=True) if r and r[0] == 'Nº')]
    col = {n: i for i, n in enumerate(cab)}
    def g(r, nome):
        for k, i in col.items():
            if k.lower().startswith(nome.lower()): return r[i] if i < len(r) else None
    texto_topo = ' '.join(str(r[0] or '') for r in ws.iter_rows(min_row=1, max_row=2, values_only=True))
    v2 = 'Nota (0–10)' in col or 'limite das falas' in texto_topo
    itens = []
    for r in ws.iter_rows(min_row=3, values_only=True):
        if not isinstance(r[0], (int, float)) or g(r, 'Início') is None: continue
        itens.append(dict(n=int(r[0]), cat=str(g(r, 'Categoria')), ini=secs(g(r, 'Início')), fim=min(secs(g(r, 'Fim')), D),
                          tit=g(r, 'Título / Tema'), obs=str(g(r, 'Observação') or ''), nota=g(r, 'Nota'),
                          t1=g(r, 'Título 1'), t2=g(r, 'Título 2'), t3=g(r, 'Título 3'), capa=g(r, 'Texto da capa'),
                          primeira=g(r, 'Primeira frase')))
        if itens[-1]['nota'] is None and g(r, 'Gancho') is not None:   # planilha nova, ainda sem valores calculados pelo Excel
            itens[-1]['nota'] = sum(int(g(r, k) or 0) for k in ('Gancho', 'Autossuf', 'Emoção', 'Frase', 'Tema em alta'))
    return itens, v2

def tirar_pausas(pasta, pecas):
    """Shorts: corta silêncios longos entre palavras (config short_cortar_pausas_acima_s; None = desligado)."""
    lim = CONFIG.get('short_cortar_pausas_acima_s')
    tj = os.path.join(pasta, '_analise', 'transcricao.json')
    if not lim or not os.path.exists(tj): return pecas
    ws = json.load(open(tj, encoding='utf-8')); folga = CONFIG.get('short_folga_pausa_s', 0.15); out = []
    for a, b, sa, sb in pecas:
        p = [w for w in ws if a <= w[0] and w[1] <= b]; ini = a; s_ini = sa
        for w1, w2 in zip(p, p[1:]):
            if w2[0] - w1[1] > lim:
                out.append([ini, w1[1] + folga, s_ini, False]); ini = w2[0] - folga; s_ini = False
        out.append([ini, b, s_ini, sb])
    return [x for x in out if x[1] - x[0] > 0.3]

def planejar(pasta):
    video = video_de(pasta); xl = planilha_de(pasta); D = duracao(video)
    itens, v2 = ler_planilha(xl, D)
    lim = CONFIG['atencao_manter_se_maior_que_s']; dicas = CONFIG['atencao_manter_se_obs_contem']
    remov, mantidos = [], []
    for i in itens:
        c = i['cat'].lower()
        if c.startswith('remover'): remov.append(i)
        elif c.startswith('aten'):
            (mantidos if (i['fim']-i['ini']) > lim or any(k in i['obs'].lower() for k in dicas) else remov).append(i)
    plano = []
    for i in itens:
        c = i['cat'].lower()
        if not (c.startswith('corte') or c.startswith('short')): continue
        tipo = 'Longos' if 'longo' in c else 'Medios' if ('médio' in c or 'medio' in c) else 'Shorts'
        # cada peça: [início, fim, ajustar_início, ajustar_fim]; na v1 (±30 s) todas as bordas são ajustadas em pausas
        pecas = [[i['ini'], i['fim'], not v2, not v2]]; tirados = []
        for rm in remov:
            nov = []
            for a, b, sa, sb in pecas:
                if rm['fim'] <= a or rm['ini'] >= b: nov.append([a, b, sa, sb]); continue
                tirados.append(rm['n'])
                if rm['ini'] > a: nov.append([a, rm['ini'], sa, True])
                if rm['fim'] < b: nov.append([rm['fim'], b, True, sb])
            pecas = nov
        pecas = [p for p in pecas if p[1]-p[0] >= (5 if tipo == 'Shorts' else 15)]
        alertas = [m['n'] for m in mantidos if not (m['fim'] <= i['ini'] or m['ini'] >= i['fim'])]
        bipe = tipo == 'Shorts' and any(k in i['obs'].lower() for k in CONFIG['bipe_quando_obs_contem'])
        if tipo == 'Shorts': pecas = tirar_pausas(pasta, pecas)
        plano.append(dict(i, tipo=tipo, pecas=pecas, removidos=sorted(set(tirados)), alertas=alertas, bipe=bipe))
        # corte de até 3:00 também vira Short/Reels/TikTok (17/11/2026). Se corte + finalização vertical passar de 3:00,
        # o finalizar.py tira a finalização das versões do YouTube e do Instagram (ver comum.final_vertical_cabe).
        lim_short = CONFIG.get('limite_short_s', 180)
        if tipo == 'Medios' and pecas and sum(b - a for a, b, *_ in pecas) <= lim_short:
            plano.append(dict(i, tipo='Shorts', pecas=tirar_pausas(pasta, [list(x) for x in pecas]), removidos=sorted(set(tirados)), alertas=alertas,
                              bipe=True, do_medio=True))   # bipe: só age se a transcrição achar palavrão
    return dict(video=video, planilha=xl, D=D, v2=v2, plano=plano, mantidos=mantidos, remov=remov)

def norm(w): return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', w.lower()).encode('ascii', 'ignore').decode())

def bipar(arquivo):
    """Transcreve o Short, acha palavrões e sobrepõe um bipe de 1 kHz. Devolve a lista de bipes."""
    from transcrever import palavras
    ws = palavras(arquivo, CONFIG.get('whisper_modelo_bipe', 'medium'))
    pal = set(CONFIG['palavroes']); iv = []
    for k, (a, b, t) in enumerate(ws):
        if norm(t) in pal:
            if norm(t) == 'puta' and k >= 2 and norm(ws[k-2][2]) == 'filho': a = ws[k-2][0]
            iv.append([round(max(0, a-0.08), 2), round(b+0.08, 2), t.strip(',.?!')])
    if not iv: return []
    cond = '+'.join(f'between(t,{a:.2f},{b:.2f})' for a, b, _ in iv); dur = duracao(arquivo)
    fc = (f"[0:a]volume=volume='if({cond},0,1)':eval=frame[m];"
          f"sine=frequency=1000:sample_rate=48000:duration={dur:.2f},volume=volume='if({cond},0.3,0)':eval=frame[s];"
          f"[m][s]amix=inputs=2:normalize=0:duration=first[a]")
    tmp = arquivo[:-4] + '_bipe.mp4'
    if run([FF, '-y', '-v', 'error', '-i', arquivo, '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', *AUD, '-movflags', '+faststart', tmp]):
        os.replace(tmp, arquivo)
    return iv

def processar(pasta, so_plano=False):
    pasta = os.path.abspath(pasta)
    if not planilha_de(pasta):
        log('Sem planilha Cortes_*.xlsx em', pasta, '— analise o episódio primeiro.'); return
    P = planejar(pasta); video, D = P['video'], P['D']
    if so_plano:
        for p in P['plano']:
            print(f"{p['tipo']:6} {p['n']:>2} {hms(p['ini'])}-{hms(p['fim'])} peças={[(hms(a), hms(b)) for a, b, *_ in p['pecas']]} "
                  f"removidos={p['removidos']} alertas={p['alertas']}{' BIPE' if p['bipe'] else ''}{' (versão vertical do médio)' if p.get('do_medio') else ''}")
        print('mantidos (Atenção):', [m['n'] for m in P['mantidos']]); return
    saida = os.path.join(pasta, 'Cortes')
    # cortes antigos de outra planilha são guardados, não apagados
    info_ant = os.path.join(saida, '_edicao.json'); rel_ant = os.path.join(saida, 'Relatorio_Edicao.xlsx')
    bipes_ant = {}; regs_ant = {}
    if os.path.isdir(saida):
        if os.path.exists(info_ant):
            ja = json.load(open(info_ant, encoding='utf-8'))
            desatualizado = ja.get('planilha_mtime') != os.path.getmtime(P['planilha'])
            if not desatualizado: regs_ant = {(r['tipo'], r['n']): r for r in ja.get('cortes', [])}
        else:   # cortes feitos antes deste sistema: vale a data do relatório
            desatualizado = not os.path.exists(rel_ant) or os.path.getmtime(rel_ant) < os.path.getmtime(P['planilha'])
            if not desatualizado and 'Bipes' in openpyxl.load_workbook(rel_ant).sheetnames:
                for r in openpyxl.load_workbook(rel_ant)['Bipes'].iter_rows(min_row=2, values_only=True):
                    m = re.search(r'\d+', str(r[0] or ''))
                    if m: bipes_ant.setdefault(int(m.group()), []).append([r[1], None, r[2]])
        if desatualizado:
            n = 1
            while os.path.exists(os.path.join(pasta, f'Cortes_v{n}_antigo')): n += 1
            destino_ant = os.path.join(pasta, f'Cortes_v{n}_antigo')
            vazio = not any(fs for _, _, fs in os.walk(saida))
            if vazio:
                log('pasta Cortes vazia; nada a guardar')
            else:
                try:
                    os.rename(saida, destino_ant)
                except PermissionError:   # pasta aberta no Explorer/Obsidian: move os arquivos um a um
                    import shutil
                    for raiz, _, fs in os.walk(saida):
                        for x in fs:
                            d = os.path.join(destino_ant, os.path.relpath(os.path.join(raiz, x), saida))
                            os.makedirs(os.path.dirname(d), exist_ok=True); shutil.move(os.path.join(raiz, x), d)
                log('cortes anteriores guardados em', f'Cortes_v{n}_antigo')
    for t in ('Longos', 'Medios', 'Shorts'): os.makedirs(os.path.join(saida, t), exist_ok=True)
    # correções de início/fim marcadas na nota do episódio (atualizar_notas.py grava em Cortes/_ajustes.json)
    pa = os.path.join(saida, '_ajustes.json'); ajustes = json.load(open(pa, encoding='utf-8')) if os.path.exists(pa) else {}
    ENC = enc_vertical(); trab = os.path.join(pasta, '_analise'); os.makedirs(trab, exist_ok=True)
    import visual
    zoom = visual.carregar(os.path.basename(os.path.dirname(pasta))).get('vertical_zoom') or CONFIG.get('vertical_zoom', 1.0)
    VFV = vf_vert(zoom)
    rel = []
    for p in P['plano']:
        nome = f"{p['tipo'][:-1]} {p['n']:02d} - {limpar(p['tit'])}.mp4"
        out = os.path.join(saida, p['tipo'], nome)
        reg = dict(n=p['n'], tipo=p['tipo'], tit=p['tit'], ini=p['ini'], fim=p['fim'], nota=p['nota'], t1=p['t1'], t2=p['t2'],
                   t3=p['t3'], capa=p['capa'], obs=p['obs'], removidos=p['removidos'], alertas=p['alertas'], arquivo=None,
                   usados=[], dur=0, bipes=[], do_medio=bool(p.get('do_medio')))
        if not p['pecas']:
            log('NÃO GERADO (trecho inteiro marcado para remoção):', nome); rel.append(reg); continue
        di, df = ajustes.get(f"{p['tipo']}-{p['n']}") or (ajustes.get(f"Medios-{p['n']}") if p.get('do_medio') else None) or [0, 0]
        pecas = [list(x) for x in p['pecas']]
        if di or df:   # correção manual: desloca o início da 1ª peça e o fim da última, sem ajuste automático nessas bordas
            pecas[0][0] = max(0, pecas[0][0] + di); pecas[0][2] = False
            pecas[-1][1] = min(D, pecas[-1][1] + df); pecas[-1][3] = False
        reg['ajuste'] = [di, df]; ant = regs_ant.get((p['tipo'], p['n']), {})
        if (ant.get('ajuste') or [0, 0]) != [di, df] and os.path.exists(out):
            sub = os.path.join(trab, 'substituidos'); os.makedirs(sub, exist_ok=True)
            os.replace(out, os.path.join(sub, nome)); log('correção nova; versão anterior em _analise/substituidos:', nome)
        aj = [[silencio_perto(video, a, D) if sa else a, silencio_perto(video, b, D) if sb else b] for a, b, sa, sb in pecas]
        aj = [x for x in aj if x[1]-x[0] > (0.3 if p['tipo'] == 'Shorts' else 3)]; reg['usados'] = aj
        if not (os.path.exists(out) and duracao(out) > 0):
            log('gerando:', p['tipo'], nome)
            tmp = os.path.join(saida, p['tipo'], '_tmp_' + nome)
            def corte(a, b, dest):
                if p['tipo'] == 'Shorts':
                    fade = ['-af', f'afade=t=in:d=0.02,afade=t=out:st={max(0, b-a-0.03):.3f}:d=0.03'] if len(aj) > 1 else []
                    return run([FF, '-y', '-v', 'error', '-ss', f'{a:.3f}', '-i', video, '-t', f'{b-a:.3f}', '-filter_complex', VFV,
                                '-map', '[v]', '-map', '0:a', *fade, *ENC, *AUD, '-movflags', '+faststart', dest])
                return run([FF, '-y', '-v', 'error', '-ss', f'{a:.3f}', '-i', video, '-t', f'{b-a:.3f}', '-map', '0:v', '-map', '0:a',
                            '-c', 'copy', '-avoid_negative_ts', 'make_zero', '-movflags', '+faststart', dest])
            if len(aj) == 1: ok = corte(aj[0][0], aj[0][1], tmp)
            else:
                partes = []
                for k, (a, b) in enumerate(aj):
                    pt = os.path.join(trab, f'_parte{k}.mp4'); corte(a, b, pt); partes.append(pt)
                lst = os.path.join(trab, '_lista.txt')
                open(lst, 'w', encoding='utf-8').write(''.join(f"file '{x.replace(os.sep, '/')}'\n" for x in partes))
                ok = run([FF, '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', tmp])
                for x in partes + [lst]:
                    try: os.remove(x)
                    except OSError: pass
            if not ok:
                reg['erro'] = True; log('FALHOU:', nome); rel.append(reg); continue
            os.replace(tmp, out)
            if p['bipe']:
                try:
                    reg['bipes'] = bipar(out); log('  bipes:', len(reg['bipes']))
                except Exception as e:
                    log('  bipe não aplicado:', e); reg['bipes'] = 'falhou'
        else:
            reg['bipes'] = ant['bipes'] if ant.get('bipes') is not None else bipes_ant.get(p['n'], [])
        reg['arquivo'] = os.path.relpath(out, pasta); reg['dur'] = duracao(out)
        rel.append(reg)
    json.dump(dict(planilha=os.path.basename(P['planilha']), planilha_mtime=os.path.getmtime(P['planilha']), v2=P['v2'],
                   editado_em=datetime.datetime.now().isoformat(timespec='minutes'), cortes=rel,
                   mantidos=[dict(n=m['n'], cat=m['cat'], ini=m['ini'], fim=m['fim'], tit=m['tit'], obs=m['obs']) for m in P['mantidos']]),
              open(info_ant, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    relatorio_xlsx(saida, rel, P['mantidos'])
    log('CONCLUÍDO:', os.path.basename(pasta))

def relatorio_xlsx(saida, rel, mantidos):
    wb = openpyxl.Workbook(); w = wb.active; w.title = 'Edição'
    w.append(['Nº', 'Tipo', 'Título', 'Início planilha', 'Fim planilha', 'Trechos usados', 'Removidos (Nº)', 'Alertas mantidos (Nº)',
              'Duração final', 'Arquivo', 'Nota', 'Título 1 – citação', 'Título 2 – pergunta', 'Título 3 – busca', 'Texto da capa', 'Observação'])
    for r in rel:
        w.append([r['n'], r['tipo'], r['tit'], hms(r['ini']), hms(r['fim']), ' + '.join(f'{hms(a)}–{hms(b)}' for a, b in r['usados']) or '—',
                  ', '.join(map(str, r['removidos'])), ', '.join(map(str, r['alertas'])), hms(r['dur']) if r['arquivo'] else 'NÃO GERADO',
                  os.path.basename(r['arquivo']) if r['arquivo'] else ('FALHOU — rodar de novo' if r.get('erro') else 'Trecho inteiro marcado para remoção'), r['nota'], r['t1'], r['t2'], r['t3'], r['capa'], r['obs']])
    w2 = wb.create_sheet('Alertas mantidos'); w2.append(['Nº', 'Categoria', 'Início', 'Fim', 'Título', 'Observação da análise', 'Por que não foi removido'])
    for m in mantidos:
        w2.append([m['n'], m['cat'], hms(m['ini']), hms(m['fim']), m['tit'], m['obs'],
                   'Trecho longo; removê-lo esvaziaria o corte' if m['fim']-m['ini'] > CONFIG['atencao_manter_se_maior_que_s'] else 'Pede conferência ou atribuição, não remoção'])
    w3 = wb.create_sheet('Bipes'); w3.append(['Nº', 'Segundo no Short', 'Palavra'])
    for r in rel:
        for b in (r['bipes'] if isinstance(r['bipes'], list) else []): w3.append([r['n'], b[0], b[2]])
    for s in (w, w2, w3):
        for c in s.columns: s.column_dimensions[c[0].column_letter].width = min(60, max(8, max(len(str(x.value or '')) for x in c) + 2))
    wb.save(os.path.join(saida, 'Relatorio_Edicao.xlsx'))

if __name__ == '__main__':
    processar(sys.argv[1], '--plano' in sys.argv)
