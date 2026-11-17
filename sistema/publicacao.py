# Pacote de publicação: um texto pronto por corte (título, descrição, hashtags, crédito), por plataforma.
# Tudo vem da planilha/_edicao.json, do cortes.json (hashtags, primeira frase) e do info.json do vídeo original. Nada é inventado:
# o que não existir aparece como "(preencher)".
# Uso: python publicacao.py "<pasta do episódio>"   -> Publicar\Textos de publicação.md
import os, sys, json, glob
from comum import hms, log

def hashtags(lista):
    out = []
    for h in lista or []:
        h = '#' + ''.join(ch for ch in str(h).lstrip('#') if ch.isalnum() or ch == '_')
        if len(h) > 1 and h.lower() not in [x.lower() for x in out]: out.append(h)
    return out

def gerar(pasta):
    pasta = os.path.abspath(pasta)
    E = json.load(open(os.path.join(pasta, 'Cortes', '_edicao.json'), encoding='utf-8'))
    cj = os.path.join(pasta, '_analise', 'cortes.json')
    C = {c.get('tema'): c for c in json.load(open(cj, encoding='utf-8')).get('cortes', [])} if os.path.exists(cj) else {}
    pj = os.path.join(pasta, 'Publicar', '_publicar.json')
    P = {(x['tipo'], x['n']): x for x in json.load(open(pj, encoding='utf-8')).get('cortes', [])} if os.path.exists(pj) else {}
    infos = glob.glob(os.path.join(pasta, '_analise', 'youtube', '*.info.json'))
    info = json.load(open(infos[0], encoding='utf-8')) if infos else {}
    if info.get('title') and info.get('webpage_url'):
        credito = f"Trecho de: {info['title']} — {info.get('channel') or info.get('uploader') or '(canal: preencher)'}. Episódio completo: {info['webpage_url']}"
    else:
        credito = 'Trecho de: (preencher o título, o canal e o link do episódio original — sem dados do YouTube em _analise\\youtube)'
    rot = {'Longos': 'Longo', 'Medios': 'Médio', 'Shorts': 'Short'}
    L = [f'# Textos de publicação — {os.path.basename(pasta)}', '',
         'Gerado por `publicacao.py` a partir da planilha. Confira nomes, citações e alertas antes de publicar; o título 1 é a sugestão principal.', '']
    n = 0
    for c in E['cortes']:
        if not c.get('arquivo'): continue
        n += 1; a = C.get(c.get('tit'), {}); p = P.get((c['tipo'], c['n']), {}); tags = hashtags(a.get('hashtags'))
        tag_txt = ' '.join(tags) if tags else '(preencher — a análise deste episódio não definiu hashtags)'
        L += [f"## {rot.get(c['tipo'], c['tipo'])} {c['n']:02d} — {c.get('tit', '')}", '',
              f"Nota {c.get('nota', '–')} · duração do corte {hms(c.get('dur', 0))}" + (f" · capa: `{p['capa']}`" if p.get('capa') else ''), '']
        for k, nome in (('t1', 'Título'), ('t2', 'Alternativa (pergunta)'), ('t3', 'Alternativa (busca)')):
            if c.get(k): L.append(f"- **{nome}:** {c[k]}" + (f"  ⚠ {len(c[k])} caracteres (o YouTube aceita até 100)" if len(c[k]) > 100 else ''))
        desc = [x for x in (a.get('primeira_frase') and f"\"{a['primeira_frase']}\"", c.get('t2')) if x]
        if c['tipo'] == 'Shorts':
            L += ['', '**YouTube Shorts**', '```', c.get('t1', ''), '', *desc, '', credito, ' '.join(tags + ['#Shorts']), '```',
                  '**Instagram Reels e TikTok** (legenda)', '```', c.get('t1', ''), '', credito, tag_txt, '```']
        else:
            L += ['', '**Descrição (YouTube)**', '```', *desc, '', credito, '', tag_txt, '```']
        avisos = [c['obs']] if c.get('obs') else []
        avisos += [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in c.get('alertas') or []]
        if avisos: L += ['', '**Conferir antes de publicar:**'] + [f'- {x}' for x in avisos]
        L.append('')
    destino = os.path.join(pasta, 'Publicar', 'Textos de publicação.md'); os.makedirs(os.path.dirname(destino), exist_ok=True)
    open(destino, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    log('textos de publicação:', destino, f'({n} cortes' + ('' if info else '; SEM dados do vídeo original para o crédito') + ')')

if __name__ == '__main__':
    gerar(sys.argv[1])
