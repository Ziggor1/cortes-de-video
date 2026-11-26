# Aplica no _analise/cortes.json a revisão visual dos cortes (revisar_cortes.py; desde a 1.2.0).
# Uso: python aplicar_revisao.py "<pasta do episódio>"            -> só mostra o que mudaria
#      python aplicar_revisao.py "<pasta do episódio>" --aplicar  -> grava (cópia do cortes.json anterior em _analise/)
# Fase "longos": recusado sai; aprovado ou sem decisão fica com os tempos da revisão; corte proposto na revisão entra como
#   "Corte longo" para completar (tema, títulos, capa, critérios). Grava _analise/longos_aprovados.json para a fase 2.
# Fase "curtos": o mesmo para os cortes curtos (proposta entra como "Corte curto").
# Bordas ajustadas na revisão ficam marcadas com "borda_revisada": o planilha.py não as move no ajuste fino.
# Observações, pontos marcados e pedidos gerais são listados para tratar em seguida.
import json, os, sys, shutil, datetime
from comum import secs, hms, log

def hmsf(t): return f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'
LONGO, CURTO = ('Corte longo', 'Corte médio'), ('Corte curto', 'Short/Reels')

def texto(ws, a, b, n=25):
    sel = [w[2] for w in ws if a <= w[0] < b]
    return ' '.join(sel[:n]) + (' …' if len(sel) > n else '')

def aplicar(pasta, gravar=False):
    an = os.path.join(pasta, '_analise'); cj, rj = os.path.join(an, 'cortes.json'), os.path.join(an, 'revisao_cortes.json')
    if not os.path.exists(rj): log('Sem revisão salva (_analise/revisao_cortes.json).'); return 1
    J = json.load(open(cj, encoding='utf-8')); R = json.load(open(rj, encoding='utf-8'))
    fase = R.get('fase', 'longos'); alvo = LONGO if fase == 'longos' else CURTO
    tj = os.path.join(an, 'transcricao.json'); ws = json.load(open(tj, encoding='utf-8')) if os.path.exists(tj) else []
    log(f"Revisão da fase {fase} — estado: {R.get('estado')} (enviada em {R.get('enviado_em') or '—'})")
    novos_cortes, rel = [], []
    for k, c in enumerate(J['cortes'], 1):
        r = R.get('cortes', {}).get(f'k{k}', {})
        if c.get('categoria') not in alvo:
            if r.get('nota'): rel.append(f"  nota em #{k} {c.get('categoria')} ({c.get('tema')}): {r['nota']}")
            novos_cortes.append(c); continue
        rot = f"#{k} {c.get('categoria')} · {c.get('tema')}"
        if r.get('decisao') == 'recusado':
            rel.append(f'  RECUSADO  {rot}' + (f" — {r['nota']}" if r.get('nota') else '')); continue
        a0, b0 = secs(c['inicio']), secs(c['fim'])
        a1 = r['ini'] if r.get('ini') is not None else a0; b1 = r['fim'] if r.get('fim') is not None else b0
        c = dict(c)
        if abs(a1 - a0) > 0.05 or abs(b1 - b0) > 0.05:
            c['inicio'], c['fim'], c['borda_revisada'] = hmsf(a1), hmsf(b1), True
            rel.append(f"  AJUSTADO{' e APROVADO' if r.get('decisao') == 'aprovado' else ''}  {rot}: " + f'{hms(a0)}–{hms(b0)} → {hms(a1)}–{hms(b1)} (início {a1 - a0:+.1f} s, fim {b1 - b0:+.1f} s)')
        else:
            rel.append(f"  {'APROVADO ' if r.get('decisao') == 'aprovado' else 'SEM DECISÃO (fica)'}  {rot}")
        c['revisao'] = r.get('decisao') or 'sem decisão'
        if r.get('nota'):
            c['obs'] = ((c.get('obs') or '') + f" · revisão: {r['nota']}").strip(' ·'); rel.append(f"      pedido: {r['nota']}")
        novos_cortes.append(c)
    for n in R.get('novos', []):
        cat = 'Corte longo' if n.get('tipo') == 'longo' else 'Corte curto'
        novos_cortes.append(dict(categoria=cat, inicio=hmsf(n['ini']), fim=hmsf(n['fim']), tema='(proposto na revisão — completar)',
                                 obs=f"Proposto na revisão: {n.get('nota') or '(sem texto)'}", borda_revisada=True, proposto_na_revisao=True))
        rel.append(f"  NOVO {cat}: {hms(n['ini'])}–{hms(n['fim'])} ({hms(n['fim'] - n['ini'])}) — {n.get('nota') or '(sem texto)'}")
        rel.append(f"      começa: {texto(ws, n['ini'], n['fim'])}")
    for m in R.get('marcas', []):
        rel.append(f"  PONTO {hms(m['t'])}: {m.get('nota') or '(sem texto)'}  ·  fala: {texto(ws, m['t'] - 3, m['t'] + 12, 18)}")
    if (R.get('geral') or '').strip(): rel.append(f"  PEDIDO GERAL: {R['geral'].strip()}")
    print('\n'.join(rel))
    if not gravar: log('Nada foi gravado. Rode com --aplicar.'); return 0
    data = datetime.datetime.now().strftime('%Y-%m-%d_%H%M')
    shutil.copy2(cj, os.path.join(an, f'cortes_antes_revisao_{fase}_{data}.json'))
    J['cortes'] = novos_cortes; J.setdefault('revisoes', []).append(dict(fase=fase, aplicada_em=data, enviado_em=R.get('enviado_em')))
    json.dump(J, open(cj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if fase == 'longos':
        ls = [dict(ini=secs(c['inicio']), fim=secs(c['fim']), tema=c.get('tema')) for c in novos_cortes if c.get('categoria') in LONGO]
        json.dump(ls, open(os.path.join(an, 'longos_aprovados.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    shutil.move(rj, os.path.join(an, f'revisao_cortes_{fase}_aplicada_{data}.json'))
    log(f'cortes.json atualizado ({len(novos_cortes)} linhas); revisão guardada em revisao_cortes_{fase}_aplicada_{data}.json')
    return 0

if __name__ == '__main__':
    sys.exit(aplicar(sys.argv[1], '--aplicar' in sys.argv))
