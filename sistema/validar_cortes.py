# Confere o _analise\cortes.json antes de gerar a planilha. Não altera nada: só lista avisos.
# Uso: python validar_cortes.py "<pasta do episódio>"   (o planilha.py também chama sozinho)
# Confere: categoria válida; início < fim e dentro do vídeo; duração por categoria; títulos até 100 caracteres;
# texto da capa com 3 a 7 palavras; 3 a 5 hashtags; os 5 critérios entre 0 e 2; cortes repetidos;
# médio que passa pouco do limite para virar Short; Short com palavrão sem "bipar" na observação;
# GAGUEJADA: Short com mais de 5% de palavras repetidas em sequência (ideia do ve_virality.py, ai-video-editor, MIT).
import json, os, sys, re, unicodedata
from comum import CONFIG, secs, hms, duracao, video_de

CATS = ['Corte longo', 'Corte médio', 'Short/Reels', 'Remover (anúncio)', 'Remover (outros)',
        'Atenção (políticas)', 'Atenção (direitos)', 'Atenção (monetização)']
FAIXA = {'Corte longo': (600, 2400), 'Corte médio': (180, 600), 'Short/Reels': (30, 180)}   # 17/11/2026: Short ≤3:00, médio ≤10, longo ≤40 min
DEPENDE = ['como eu falei', 'como eu disse', 'como falei', 'como eu tinha falado', 'voltando', 'isso aqui', 'isso aí', 'isso', 'esse', 'essa',
           'esses', 'essas', 'ele', 'ela', 'eles', 'elas', 'e aí', 'então', 'também', 'daí', 'aí', 'mas', 'e', 'porque', 'que', 'o outro', 'a outra']
CONECTIVO = {'mas', 'e', 'porque', 'então', 'que', 'tipo', 'ou', 'pra', 'para', 'de', 'do', 'da', 'o', 'a', 'com', 'se', 'é'}
acento = lambda w: re.sub(r'[^\wà-úç ]', '', w.lower()).strip()
norm = lambda w: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', w.lower()).encode('ascii', 'ignore').decode())

def validar(pasta):
    j = json.load(open(os.path.join(pasta, '_analise', 'cortes.json'), encoding='utf-8'))
    D = duracao(video_de(pasta)); av = []; vistos = {}
    lim_short = CONFIG.get('limite_short_s', 180)
    ws = None
    tj = os.path.join(pasta, '_analise', 'transcricao.json')
    if os.path.exists(tj): ws = json.load(open(tj, encoding='utf-8'))
    for k, c in enumerate(j['cortes'], 1):
        r = f"#{k} {c.get('categoria')} · {c.get('tema')}"; cat = c.get('categoria')
        if cat not in CATS: av.append(f'{r}: categoria desconhecida'); continue
        a, b = secs(c['inicio']), secs(c['fim'])
        if not (0 <= a < b <= D + 1): av.append(f'{r}: tempo fora do vídeo ou início depois do fim ({c["inicio"]}–{c["fim"]})'); continue
        if cat not in FAIXA: continue
        d = b - a; lo, hi = FAIXA[cat]
        if not lo * 0.9 <= d <= hi * (1.0 if cat == 'Short/Reels' else 1.1):   # Short: 3:00 é teto das plataformas
            av.append(f'{r}: duração {hms(d)} fora da faixa da categoria ({hms(lo)}–{hms(hi)})')
        fv = CONFIG.get('final_vertical_s', 7)
        if cat == 'Short/Reels' and lim_short - fv < d <= lim_short:
            av.append(f'{r}: Short de {hms(d)} + {fv} s de finalização vertical = {hms(d + fv)}, passa de 3:00 — o YouTube e o Instagram '
                      f'o tratam como vídeo comum. Apertar para até {hms(lim_short - fv)}?')
        if cat == 'Corte médio' and lim_short < d <= lim_short + 45:
            av.append(f'{r}: {hms(d)}, só {d - lim_short:.0f} s acima de 3:00 — apertando, vira Short também. Vale apertar?')
        chave = (cat, round(a), round(b))
        if chave in vistos: av.append(f'{r}: mesmo trecho que #{vistos[chave]}')
        vistos[chave] = k
        for t in ('titulo1', 'titulo2', 'titulo3'):
            if not c.get(t): av.append(f'{r}: falta {t}')
            elif len(c[t]) > 100: av.append(f'{r}: {t} com {len(c[t])} caracteres (máx. 100)')
        if cat != 'Short/Reels' and not 3 <= len((c.get('capa') or '').split()) <= 7: av.append(f'{r}: texto da capa fora de 3–7 palavras')
        if not 3 <= len(c.get('hashtags') or []) <= 5: av.append(f'{r}: {len(c.get("hashtags") or [])} hashtags (pede 3–5)')
        for x in ('gancho', 'autossuf', 'emocao', 'frase', 'em_alta'):
            if c.get(x) not in (0, 1, 2): av.append(f'{r}: critério {x} = {c.get(x)!r} (pede 0, 1 ou 2)')
        if cat == 'Short/Reels' and ws and 'bipar' not in (c.get('obs') or '').lower():
            pal = [w[2] for w in ws if a <= w[0] < b and norm(w[2]) in set(CONFIG['palavroes'])]
            if pal: av.append(f'{r}: tem palavrão ({", ".join(sorted(set(pal)))}) e a observação não diz "bipar"')
        if cat == 'Short/Reels' and ws:
            tk = [t for t in (norm(w[2]) for w in ws if a <= w[0] < b) if t]
            rep = sum(tk[i] == tk[i - 1] for i in range(1, len(tk))) / (len(tk) - 1) if len(tk) >= 8 else 0
            if rep > 0.05: av.append(f'{r}: GAGUEJADA — {rep:.0%} das palavras repetem a anterior; confira se a fala não está atropelada')
    # --- gancho, fim e repetição (precisa da transcrição)
    if ws:
        import bordas
        frase_ini = [k for k in range(len(ws)) if k == 0 or bordas._fim_de_frase(ws, k - 1)]
        palavras = lambda a, n: [acento(w[2]) for w in ws if w[0] >= a - 0.3][:n]
        def depende(a):
            p = ' '.join(palavras(a, 4))
            return next((m for m in DEPENDE if p == m or p.startswith(m + ' ')), None)
        for k, c in enumerate(j['cortes'], 1):
            cat = c.get('categoria')
            if cat not in ('Corte longo', 'Corte médio', 'Short/Reels'): continue
            r = f"#{k} {cat} · {c.get('tema')}"; a, b = secs(c['inicio']), secs(c['fim'])
            m = depende(a)
            if m:
                alt = next((ws[i] for i in frase_ini if a < ws[i][0] <= a + 25 and not depende(ws[i][0])), None)
                av.append(f'{r}: GANCHO — começa com "{m}…", que depende do que veio antes'
                          + (f'; início alternativo em {hms(alt[0])}: "{" ".join(x[2] for x in ws if alt[0] <= x[0])[:70]}…"' if alt else
                             '; sem frase independente nos 25 s seguintes: use legenda de contexto'))
            if cat == 'Corte longo': continue
            fim = [w for w in ws if w[1] <= b + 0.5][-3:]
            if fim:
                ult = fim[-1][2].strip()
                if ult.endswith('?'): av.append(f'{r}: FIM — termina numa pergunta ("…{" ".join(w[2] for w in fim)}"): a resposta ficou fora?')
                elif acento(ult) in CONECTIVO: av.append(f'{r}: FIM — termina em "{ult}", a ideia ficou pela metade')
        # repetição: mesmo tipo sobreposto, ou Short que é quase o médio inteiro (fora a versão vertical automática)
        cs = [(k, c, secs(c['inicio']), secs(c['fim'])) for k, c in enumerate(j['cortes'], 1)
              if c.get('categoria') in ('Corte longo', 'Corte médio', 'Short/Reels')]
        for x in range(len(cs)):
            for y in range(x + 1, len(cs)):
                (k1, c1, a1, b1), (k2, c2, a2, b2) = cs[x], cs[y]
                sob = min(b1, b2) - max(a1, a2)
                if sob <= 0: continue
                menor = min(b1 - a1, b2 - a2)
                if c1['categoria'] == c2['categoria'] and sob > 0.3 * menor:
                    av.append(f"REPETIÇÃO — #{k1} e #{k2} ({c1['categoria']}) dividem {hms(sob)}: {c1['tema'][:35]} / {c2['tema'][:35]}")
                elif {c1['categoria'], c2['categoria']} == {'Corte médio', 'Short/Reels'} and sob > 0.8 * max(b1 - a1, b2 - a2):
                    av.append(f"REPETIÇÃO — Short e médio quase iguais: #{k1} e #{k2} ({c1['tema'][:35]})")
    for k, c in enumerate(j['cortes'], 1):
        if c.get('em_alta') == 2 and not c.get('fonte_em_alta'):
            av.append(f"#{k} {c.get('categoria')} · {c.get('tema')}: \"Tema em alta\" = 2 sem fonte (chave fonte_em_alta com o link da notícia)")
    return av

if __name__ == '__main__':
    av = validar(os.path.abspath(sys.argv[1]))
    print('\n'.join(av) if av else 'cortes.json sem avisos'); print(f'{len(av)} avisos')
