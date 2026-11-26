# Cria/atualiza as notas do Obsidian: uma por episódio, uma por canal e o Painel.
# Só reescreve o trecho entre os marcadores AUTO; o resto da nota (suas anotações) é preservado,
# assim como as caixas de "publicado" que você marcar.
# Uso: python atualizar_notas.py
import os, re, json, glob
import openpyxl
from comum import COFRE, episodios, video_de, planilha_de, duracao, hms, secs

INI, FIM = '%% AUTO: início — gerado por _sistema/atualizar_notas.py; edite fora deste bloco %%', '%% AUTO: fim %%'
ROTULO = {'aguardando-analise': '1 · aguardando análise', 'analisado': '2 · analisado', 'reeditar': '2 · planilha nova, reeditar',
          'editado': '3 · editado', 'finalizado': '3 · pronto para publicar', 'publicado': '4 · publicado'}
PROXIMO = {'aguardando-analise': 'analisar', 'analisado': 'editar', 'reeditar': 'editar (planilha mudou)',
           'editado': 'finalizar (intro, capa, legenda)', 'finalizado': 'revisar e publicar', 'publicado': '—'}

def ler_nota(caminho):
    if not os.path.exists(caminho): return '', '', {}
    txt = open(caminho, encoding='utf-8').read()
    marcados = {m.group(2): m.group(1) == 'x' for m in re.finditer(r'- \[( |x)\].*?%%id:([^%]+)%%', txt)}
    corpo = re.sub(r'^---\n.*?\n---\n', '', txt, count=1, flags=re.S)
    antes, depois = corpo, ''
    if INI in corpo and FIM in corpo:
        antes = corpo.split(INI)[0]; depois = corpo.split(FIM, 1)[1]
    else:
        antes = ''; depois = '\n' + corpo if corpo.strip() else ''
    return antes, depois, marcados

AJ = re.compile(r'ajuste \(s\): início `?([+-]?\d+(?:[.,]\d+)?)`? · fim `?([+-]?\d+(?:[.,]\d+)?)`?.*?%%aj:([^%]+)%%')
def ler_ajustes(caminho):
    if not os.path.exists(caminho): return {}
    num = lambda x: float(x.replace(',', '.'))
    return {m.group(3): [num(m.group(1)), num(m.group(2))] for m in AJ.finditer(open(caminho, encoding='utf-8').read())}

def fmt(x): return ('%+g' % x) if x else '0'

def gravar(caminho, fm, antes, auto, depois, padrao_depois):
    linhas = ['---']
    for k, v in fm.items():
        if isinstance(v, list): linhas.append(f'{k}:' + ''.join(f'\n  - {json.dumps(x, ensure_ascii=False)}' for x in v) if v else f'{k}: []')
        elif isinstance(v, (int, float)) or v is None: linhas.append(f'{k}: {"" if v is None else v}')
        else: linhas.append(f'{k}: {json.dumps(v, ensure_ascii=False)}')
    linhas.append('---')
    if not depois.strip(): depois = padrao_depois
    open(caminho, 'w', encoding='utf-8').write('\n'.join(linhas) + '\n' + antes + INI + '\n' + auto.strip() + '\n' + FIM + depois)

def cortes_do_relatorio(rel):
    """Cortes feitos antes deste sistema (sem _edicao.json): lê o Relatorio_Edicao.xlsx."""
    ws = openpyxl.load_workbook(rel)['Edição']; cab = [c.value for c in ws[1]]; out = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(cab, r)); gerado = d.get('Duração final') not in (None, 'NÃO GERADO')
        out.append(dict(n=d['Nº'], tipo=d['Tipo'], tit=d['Título'], ini=secs(d['Início planilha']), fim=secs(d['Fim planilha']),
                        nota=d.get('Nota'), t1=d.get('Título 1 – citação'), capa=d.get('Texto da capa'),
                        alertas=[x for x in str(d.get('Alertas mantidos (Nº)') or '').split(', ') if x],
                        arquivo=os.path.join('Cortes', d['Tipo'], d['Arquivo']) if gerado else None,
                        dur=secs(d['Duração final']) if gerado else 0, bipes=[]))
    return out

def estado(pasta):
    xl = planilha_de(pasta); saida = os.path.join(pasta, 'Cortes')
    info, rel = os.path.join(saida, '_edicao.json'), os.path.join(saida, 'Relatorio_Edicao.xlsx')
    if not xl: return 'aguardando-analise', None, [], []
    if os.path.exists(info):
        j = json.load(open(info, encoding='utf-8'))
        st = 'editado' if j.get('planilha_mtime') == os.path.getmtime(xl) else 'reeditar'
        return st, xl, j['cortes'], j.get('mantidos', [])
    if os.path.exists(rel):
        st = 'editado' if os.path.getmtime(rel) >= os.path.getmtime(xl) else 'reeditar'
        return st, xl, cortes_do_relatorio(rel), []
    return 'analisado', xl, [], []

def nota_episodio(pasta):
    canal, ep = os.path.basename(os.path.dirname(pasta)), os.path.basename(pasta)
    caminho = os.path.join(pasta, ep + '.md')
    antes, depois, marcados = ler_nota(caminho); ajustes = ler_ajustes(caminho)
    st, xl, cortes, mantidos = estado(pasta)
    if os.path.isdir(os.path.join(pasta, 'Cortes')):
        json.dump({k: v for k, v in ajustes.items() if any(v)}, open(os.path.join(pasta, 'Cortes', '_ajustes.json'), 'w', encoding='utf-8'))
    v = video_de(pasta); D = duracao(v)
    gerados = [c for c in cortes if c.get('arquivo')]
    pub = sum(1 for c in gerados if marcados.get(f"{c['tipo']}-{c['n']}"))
    if any(c.get('erro') for c in cortes): st = 'reeditar'
    pj = os.path.join(pasta, 'Publicar', '_publicar.json')
    fin = {(x['tipo'], x['n']): x for x in json.load(open(pj, encoding='utf-8'))['cortes']} if os.path.exists(pj) else {}
    if st == 'editado' and gerados and all(fin.get((c['tipo'], c['n']), {}).get('arquivo') for c in gerados): st = 'finalizado'
    if st in ('editado', 'finalizado') and gerados and pub == len(gerados): st = 'publicado'
    notas = [c['nota'] for c in cortes if isinstance(c.get('nota'), (int, float))]
    fm = dict(tipo='episodio', canal=canal, status=ROTULO[st], proximo_passo=PROXIMO[st], duracao=hms(D),
              video=os.path.basename(v), planilha=os.path.basename(xl) if xl else '',
              longos=sum(c['tipo'] in ('Longos', 'Medios') for c in gerados),   # Medios: episódios feitos antes da 1.2.0
              shorts=sum(c['tipo'] == 'Shorts' for c in gerados), nota_max=max(notas) if notas else None,
              publicados=f'{pub}/{len(gerados)}', alertas=len(mantidos), tags=['episodio', canal.lower().replace(' ', '-')])
    L = [f'# {ep}', '', f'**Canal:** [[{canal}]] · **Status:** {ROTULO[st]} · **Próximo passo:** {PROXIMO[st]}', '',
         f'- Vídeo: `{os.path.basename(v)}` ({hms(D)})']
    cof = lambda p: os.path.relpath(p, COFRE).replace(os.sep, '/')   # links com caminho do cofre (nomes de arquivo se repetem)
    if xl: L.append(f'- Planilha da análise: [[{cof(xl)}|{os.path.basename(xl)}]]')
    if os.path.exists(os.path.join(pasta, 'Cortes', 'Relatorio_Edicao.xlsx')):
        L.append(f"- Relatório da edição: [[{cof(os.path.join(pasta, 'Cortes', 'Relatorio_Edicao.xlsx'))}|Relatorio_Edicao.xlsx]]")
    if os.path.exists(os.path.join(pasta, '_analise', 'transcricao.txt')): L.append(f'- Transcrição: `_analise/transcricao.txt`')
    if st == 'reeditar': L += ['', '> [!warning] A planilha foi alterada depois da edição. Os cortes abaixo são da versão anterior.']
    for tipo, titulo in (('Longos', 'Cortes longos (YouTube)'), ('Medios', 'Cortes médios (formato antigo, YouTube)'), ('Shorts', 'Cortes curtos (YouTube Shorts · Reels · TikTok)')):
        grupo = [c for c in cortes if c['tipo'] == tipo]
        if not grupo: continue
        L += ['', f'## {titulo}', '']
        for c in sorted(grupo, key=lambda c: c['n']):
            cid = f"{c['tipo']}-{c['n']}"
            nota = f" · nota **{c['nota']}**" if c.get('nota') is not None else ''
            if not c.get('arquivo'):
                motivo = 'FALHOU na edição — rodar de novo' if c.get('erro') else 'não gerado (trecho inteiro marcado para remoção)'
                L.append(f"- ~~{c['n']:02d} · {c['tit']}~~ · {motivo}"); continue
            extra = []
            if c.get('t1'): extra.append(f"título: {c['t1']}")
            if c.get('capa'): extra.append(f"capa: **{c['capa']}**")
            if c.get('alertas'): extra.append(f"⚠ alerta nº {', '.join(map(str, c['alertas']))}")
            if isinstance(c.get('bipes'), list) and c['bipes']: extra.append(f"🔇 {len(c['bipes'])} bipes")
            elif c.get('bipes') == 'falhou': extra.append('⚠ bipe pedido mas não aplicado')
            link = cof(os.path.join(pasta, c['arquivo'])); f = fin.get((c['tipo'], c['n']), {})
            abrir = f"[[{link}|bruto]]"
            if f.get('arquivos'):
                abrir = ' · '.join(f"[[{cof(os.path.join(pasta, x))}|▶ {p}]]" for p, x in f['arquivos'].items()) + ' · ' + abrir
            elif f.get('arquivo'): abrir = f"[[{cof(os.path.join(pasta, f['arquivo']))}|▶ final]] · " + abrir
            if f.get('legenda'): extra.append('legendado')
            elif c['tipo'] == 'Shorts' and f.get('arquivo'): extra.append('⚠ finalizado SEM legenda (rodar finalizar com --so-shorts --refazer)')
            L.append(f"- [{'x' if marcados.get(cid) else ' '}] **{c['n']:02d} · {c['tit']}** · {hms(c['dur'])}{nota} · {abrir} %%id:{cid}%%")
            if extra: L.append('    - ' + ' · '.join(extra))
            a = ajustes.get(cid, [0, 0]); aplicado = (c.get('ajuste') or [0, 0]) == a
            sit = '' if not any(a) else (' — aplicado' if aplicado else " — **pendente**: diga \"aplicar ajustes de " + ep + "\"")
            L.append(f"    - ajuste (s): início `{fmt(a[0])}` · fim `{fmt(a[1])}`{sit} %%aj:{cid}%%")
            if f.get('capa'):
                L.append(f"    - ![[{cof(os.path.join(pasta, f['capa']))}|320]]")
                if f.get('capas_extras'): L.append('    - outras opções: ' + ' · '.join(f"[[{cof(os.path.join(pasta, x))}|opção {i + 2}]]" for i, x in enumerate(f['capas_extras'])))
    if mantidos:
        L += ['', '## Alertas mantidos nos cortes', '']
        for m in mantidos: L.append(f"- **{m['n']}** · {hms(m['ini'])}–{hms(m['fim'])} · {m['tit']}: {m['obs']}")
    if gerados: L += ['', '*Corte começou cedo ou tarde? Troque os números de "ajuste (s)": início `-2` = começa 2 s antes, `+1` = 1 s depois; fim `+3` = termina 3 s depois. Depois diga "aplicar ajustes".*']
    if st in ('editado', 'finalizado', 'publicado'): L += ['', '*Marque a caixa de cada corte quando publicar. Publique os arquivos **final** (pasta Publicar).*']
    gravar(caminho, fm, antes, '\n'.join(L), depois, '\n\n## Anotações\n\n')
    return dict(canal=canal, ep=ep, st=st, fm=fm)

def nota_canal(canal, eps):
    caminho = os.path.join(COFRE, 'Canais', canal + '.md'); os.makedirs(os.path.dirname(caminho), exist_ok=True)
    antes, depois, _ = ler_nota(caminho)
    L = [f'# {canal}', '', '| Episódio | Status | Duração | Longos / Curtos | Publicados |', '|---|---|---|---|---|']
    for e in eps:
        f = e['fm']; L.append(f"| [[{e['ep']}]] | {f['status']} | {f['duracao']} | {f['longos']} / {f['shorts']} | {f['publicados']} |")
    padrao = ('\n\n## Perfil do canal\n\n- Público:\n- Tom e linguagem:\n- Apresentadores e convidados frequentes:\n'
              '- Regras próprias do canal (o que nunca cortar, vinhetas, chamadas):\n')
    gravar(caminho, dict(tipo='canal', tags=['canal']), antes, '\n'.join(L), depois, padrao)

def painel(todos):
    caminho = os.path.join(COFRE, '00 Painel.md'); antes, depois, _ = ler_nota(caminho)
    ordem = ['aguardando-analise', 'reeditar', 'analisado', 'editado', 'finalizado', 'publicado']
    L = ['# Painel de cortes', '', '| Episódio | Canal | Status | Próximo passo | Longos / Curtos | Publicados |', '|---|---|---|---|---|---|']
    for e in sorted(todos, key=lambda e: (ordem.index(e['st']), e['canal'], e['ep'])):
        f = e['fm']; L.append(f"| [[{e['ep']}]] | [[{e['canal']}]] | {f['status']} | {f['proximo_passo']} | {f['longos']} / {f['shorts']} | {f['publicados']} |")
    pend = sum(e['st'] in ('aguardando-analise', 'analisado', 'reeditar', 'editado') for e in todos)
    L += ['', f'**{len(todos)} episódios · {pend} com trabalho pendente.**']
    padrao = ('\n\n## Tabela filtrável\n\n![[Episódios.base]]\n\n## Como usar\n\n1. Coloque o vídeo em `Pasta de Trabalho/<Canal>/<Episódio>/` (ex.: `Pasta de Trabalho/Meu Canal/Episódio 01/`).\n'
              '2. No Claude, use a skill **/cortes-de-video** e diga: **"processar pendentes"** (análise, edição e finalização) ou "analisar Episódio 01".\n'
              '3. Revise a nota do episódio e marque cada corte ao publicar.\n\nDetalhes: [[01 Workflow]].\n')
    gravar(caminho, dict(tipo='painel'), antes, '\n'.join(L), depois, padrao)

if __name__ == '__main__':
    todos = [nota_episodio(p) for p in episodios()]
    for canal in sorted({e['canal'] for e in todos}): nota_canal(canal, [e for e in todos if e['canal'] == canal])
    painel(todos)
    # calibração: média das correções marcadas em todos os episódios (usada pelo ajuste fino de bordas da próxima análise)
    tot = []
    for p in episodios():
        pa = os.path.join(p, 'Cortes', '_ajustes.json')
        if os.path.exists(pa): tot += [v for v in json.load(open(pa, encoding='utf-8')).values() if any(v)]
    from comum import AQUI
    if True:
        json.dump(dict(n=len(tot), inicio_medio=round(sum(v[0] for v in tot) / len(tot), 2) if tot else 0, fim_medio=round(sum(v[1] for v in tot) / len(tot), 2) if tot else 0),
                  open(os.path.join(AQUI, 'calibracao.json'), 'w', encoding='utf-8'))
    for e in todos: print(f"{e['canal']:16} {e['ep']:14} {ROTULO[e['st']]}")
