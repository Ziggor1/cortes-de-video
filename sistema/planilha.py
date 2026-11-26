# Gera a planilha da análise no formato v2 a partir de _analise/cortes.json (escrito pelo Claude).
# Uso: python planilha.py "<pasta do episódio>"
# cortes.json = {"titulo": "...", "arquivo": "Cortes_Tema.xlsx",
#                "cortes": [{"categoria": "Corte longo", "inicio": "0:01:02", "fim": "0:15:40", "tema": "...",
#                            "gancho": 2, "autossuf": 1, "emocao": 2, "frase": 1, "em_alta": 2,
#                            "titulo1": "...", "titulo2": "...", "titulo3": "...", "capa": "...",
#                            "primeira_frase": "...", "obs": "..."}, ...]}
# Categorias: Corte longo (mais de 3 até 40 min), Corte curto (até 3:00; antes "Short/Reels"), Remover (anúncio), Remover (outros),
#             Atenção (políticas), Atenção (direitos), Atenção (monetização)
import os, sys, json, csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo
from comum import secs, hms, duracao, video_de, log, CONFIG

ORDEM = ['Corte longo', 'Corte médio', 'Corte curto',   # 'Corte médio': planilhas feitas antes da 1.2.0
         'Remover (anúncio)', 'Remover (outros)']
COR = {'Corte longo': 'DDEBF7', 'Corte médio': 'E2EFDA', 'Corte curto': 'FFF2CC', 'Short/Reels': 'FFF2CC', 'Remover': 'F8CBAD', 'Atenção': 'FCE4D6'}
CAB = ['Nº', 'Categoria', 'Início', 'Fim', 'Duração', 'Título / Tema', 'Nota (0–10)', 'Gancho', 'Autossuf.', 'Emoção', 'Frase',
       'Tema em alta', 'Intensidade do áudio', 'Título 1 – citação', 'Título 2 – pergunta', 'Título 3 – busca', 'Texto da capa',
       'Primeira frase', 'Observação']
F = 'Arial'

def intensidade_media(pasta, ini, fim):
    p = os.path.join(pasta, '_analise', 'intensidade.csv')
    if not os.path.exists(p): return None
    v = [float(r['intensidade']) for r in csv.DictReader(open(p, encoding='utf-8')) if ini <= secs(r['inicio']) < fim]
    return round(sum(v)/len(v), 2) if v else None

def gerar(pasta):
    j = json.load(open(os.path.join(pasta, '_analise', 'cortes.json'), encoding='utf-8'))
    for c in j['cortes']:   # 1.2.0: "Short/Reels" passou a se chamar "Corte curto"
        if c.get('categoria') == 'Short/Reels': c['categoria'] = 'Corte curto'
    D = duracao(video_de(pasta))
    import validar_cortes   # avisos não bloqueiam: o Claude lê e decide
    for a in validar_cortes.validar(pasta): log('AVISO', a)
    pontos = lambda c: sum(int(c.get(k, 0) or 0) for k in ('gancho', 'autossuf', 'emocao', 'frase', 'em_alta'))
    chave = lambda c: (ORDEM.index(c['categoria']) if c['categoria'] in ORDEM else 9, -pontos(c) if c['categoria'] in ORDEM[:3] else secs(c['inicio']))
    cortes = sorted(j['cortes'], key=chave)
    # ajuste fino das bordas pela transcrição (frase completa + respiro calibrado); --sem-ajuste desliga
    tj = os.path.join(pasta, '_analise', 'transcricao.json')
    if os.path.exists(tj) and '--sem-ajuste' not in sys.argv:
        import bordas
        wsx = json.load(open(tj, encoding='utf-8')); cal = bordas.calibracao(); linhas = []
        hmsf = lambda t: f'{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}'
        for c in cortes:
            if c['categoria'] not in ORDEM[:3]: continue
            a0, b0 = secs(c['inicio']), secs(c['fim'])
            a1, b1, av = bordas.ajustar(wsx, a0, b0, cal)
            c['inicio'], c['fim'] = hmsf(a1), hmsf(b1)
            if av: c['obs'] = ((c.get('obs') or '') + ' ⚠ ' + '; '.join(av)).strip()
            linhas.append((f"{c['categoria']} · {c['tema']}", a0, b0, a1, b1, av))
        bordas.relatorio(wsx, linhas, os.path.join(pasta, '_analise', 'bordas.txt'))
        if CONFIG.get('remover_pedidos_de_like', True):
            import re as _re
            cta = _re.compile(r'\b(d[aáê] (o )?like|like na live|se inscrev|ativa o sininho)', _re.I)
            janelas = [(secs(c['inicio']), secs(c['fim'])) for c in cortes if c['categoria'] in ORDEM[:3]]
            ja = [(secs(c['inicio']), secs(c['fim'])) for c in cortes if c['categoria'].startswith('Remover')]
            ini_fr = [k for k in range(len(wsx)) if k == 0 or bordas._fim_de_frase(wsx, k - 1)]
            novos = 0
            for k in range(len(wsx)):
                if not cta.match(' '.join(w[2].lower().strip(',.?!') for w in wsx[k:k + 4])): continue
                i = max((x for x in ini_fr if x <= k), default=k); f = k
                while f < len(wsx) - 1 and not bordas._fim_de_frase(wsx, f) and wsx[f][1] - wsx[i][0] < 12: f += 1
                a, b = wsx[i][0] - 0.1, wsx[f][1] + 0.15
                if b - a > 12 or not any(x <= a and b <= y for x, y in janelas) or any(x <= a + 0.5 and b - 0.5 <= y for x, y in ja): continue
                cortes.append(dict(categoria='Remover (outros)', tema='Pedido de like (automático)', inicio=hmsf(a), fim=hmsf(b),
                                   obs='Detectado na transcrição: "' + ' '.join(w[2] for w in wsx[i:f + 1])[:90] + '". Apague a linha para manter.'))
                ja.append((a, b)); novos += 1
            if novos: log('pedidos de like dentro dos cortes:', novos, '(linhas "Pedido de like (automático)")')
            cortes = sorted(cortes, key=chave)
        log('bordas ajustadas em', len(linhas), 'cortes; conferência em _analise/bordas.txt',
            f"(respiro {cal['respiro_inicio']} s antes / {cal['respiro_fim']} s depois)")
    wb = Workbook(); ws = wb.active; ws.title = 'Cortes'
    ws['A1'] = f"Pontos de corte — {j['titulo']}"; ws['A1'].font = Font(name=F, bold=True, size=13)
    ws['A2'] = (f'Vídeo de origem: {hms(D)}. Cortes longos e curtos: início e fim ajustados ao limite das falas (precisão de ~1 s). '
                'Remover/Atenção: ±30 s. Nota = soma dos 5 critérios (aba Critérios); é estimativa, não dado de audiência.')
    ws['A2'].font = Font(name=F, italic=True, size=9)
    ws.append([]); ws.delete_rows(3)
    for i, h in enumerate(CAB, 1):
        c = ws.cell(3, i, h); c.font = Font(name=F, bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='404040')
        c.alignment = Alignment(wrap_text=True, vertical='center')
    for k, c in enumerate(cortes, 1):
        r = 3 + k; cat = c['categoria']; corte = cat in ORDEM[:3]
        ini, fim = secs(c['inicio']), secs(c['fim'])
        vals = [k, cat, ini/86400, fim/86400, f'=D{r}-C{r}', c['tema']]
        vals += [f'=SUM(H{r}:L{r})' if corte else None] + ([int(c.get(x, 0) or 0) for x in ('gancho', 'autossuf', 'emocao', 'frase', 'em_alta')] if corte else [None]*5)
        vals += [intensidade_media(pasta, ini, fim) if corte else None, c.get('titulo1'), c.get('titulo2'), c.get('titulo3'), c.get('capa'), c.get('primeira_frase'), c.get('obs')]
        for i, v in enumerate(vals, 1):
            cel = ws.cell(r, i, v); cel.font = Font(name=F, size=10); cel.alignment = Alignment(vertical='top', wrap_text=i in (6, 14, 15, 16, 18, 19))
            if i in (3, 4, 5): cel.number_format = 'h:mm:ss'
            cor = next((v2 for k2, v2 in COR.items() if cat.startswith(k2)), None)
            if cor: cel.fill = PatternFill('solid', fgColor=cor)
    ult = 3 + len(cortes)
    ws.add_table(Table(displayName='Cortes', ref=f'A3:S{ult}', tableStyleInfo=TableStyleInfo(name='TableStyleLight1', showRowStripes=False)))
    for col, w in zip('ABCDEFGHIJKLMNOPQRS', [5, 18, 9, 9, 9, 40, 8, 7, 8, 7, 6, 8, 10, 40, 36, 36, 16, 40, 40]): ws.column_dimensions[col].width = w
    ws.freeze_panes = 'C4'
    # Critérios
    c2 = wb.create_sheet('Critérios')
    for linha in [['Como a nota é calculada'], ['Critério', '0 ponto', '1 ponto', '2 pontos'],
                  ['Gancho', 'Começa no meio de um raciocínio', 'Abre com contexto, mas sem impacto', 'A primeira frase prende sozinha'],
                  ['Autossuficiência', 'Depende do resto do episódio', 'Precisa de uma legenda de contexto', 'Entende-se sem ter visto o episódio'],
                  ['Emoção', 'Tom neutro, expositivo', 'Alguma tensão ou humor', 'Conflito, indignação, humor ou surpresa claros'],
                  ['Frase de efeito', 'Nenhuma frase citável', 'Frase razoável', 'Frase pronta para título ou legenda'],
                  ['Tema em alta', 'Assunto atemporal', 'Assunto de interesse geral', 'Assunto ou nome no centro do noticiário'], [],
                  ['Intensidade do áudio: volume e velocidade da fala no trecho comparados com o episódio (0 = média; acima de 0,5 = bem mais intenso).'],
                  ['Os critérios aceitam 0, 1 ou 2 e a nota recalcula sozinha.']]:
        c2.append(linha)
    c2['A1'].font = Font(name=F, bold=True, size=12)
    for col, w in zip('ABCD', [18, 34, 34, 44]): c2.column_dimensions[col].width = w
    # Desempenho
    d = wb.create_sheet('Desempenho')
    d.append(['Desempenho dos cortes publicados (preencher)']); d.append(['Digite o Nº do corte (aba Cortes); tema e nota aparecem sozinhos.'])
    d.append(['Nº do corte', 'Tema (automático)', 'Nota prevista', 'Plataforma', 'Data de publicação', 'Título usado', 'Views 48 h',
              'Views 7 dias', 'CTR (%)', 'Retenção média (%)', 'Curtidas', 'Comentários', None, 'Correlação nota × views 7 dias'])
    for r in range(4, 104):
        d.cell(r, 2, f'=IF(A{r}="","",IFERROR(INDEX(Cortes!F:F,MATCH(A{r},Cortes!A:A,0)),""))')
        d.cell(r, 3, f'=IF(A{r}="","",IFERROR(INDEX(Cortes!G:G,MATCH(A{r},Cortes!A:A,0)),""))')
    d['N4'] = '=IF(COUNT(H4:H103)<5,"Precisa de 5+ cortes",CORREL(C4:C103,H4:H103))'
    d['A1'].font = Font(name=F, bold=True, size=12)
    # Resumo
    s = wb.create_sheet('Resumo'); s.append(['Resumo por categoria']); s.append(['Categoria', 'Quantidade', 'Duração total', 'Nota média'])
    cats = list(dict.fromkeys(ORDEM + [c['categoria'] for c in cortes]))
    for k, cat in enumerate([c for c in cats if any(x['categoria'] == c for x in cortes)], 3):
        s.append([cat, f'=COUNTIF(Cortes!B:B,A{k})', f'=SUMIF(Cortes!B:B,A{k},Cortes!E:E)',
                  f'=IFERROR(AVERAGEIF(Cortes!B:B,A{k},Cortes!G:G),"–")' if cat in ORDEM[:3] else '–'])
        s.cell(k, 3).number_format = '[h]:mm:ss'
    s['A1'].font = Font(name=F, bold=True, size=12); s.column_dimensions['A'].width = 24
    nome = j.get('arquivo') or 'Cortes_' + os.path.basename(pasta).replace(' ', '_') + '.xlsx'
    destino = os.path.join(pasta, nome); wb.save(destino); log('planilha:', destino, f'({len(cortes)} linhas)')

if __name__ == '__main__':
    gerar(sys.argv[1])
