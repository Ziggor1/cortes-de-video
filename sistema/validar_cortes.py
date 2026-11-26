# Confere o _analise\cortes.json antes de gerar a planilha. Não altera nada: só lista avisos.
# Uso: python validar_cortes.py "<pasta do episódio>"   (o planilha.py também chama sozinho)
# Confere: categoria válida; início < fim e dentro do vídeo; duração por categoria; títulos até 100 caracteres;
# texto da capa com 3 a 7 palavras; 3 a 5 hashtags; os 5 critérios entre 0 e 2; cortes repetidos;
# longo que passa pouco de 3:00 (apertando, vira Short); Short curto demais; Short com palavrão sem "bipar";
# GAGUEJADA: Short com mais de 5% de palavras repetidas em sequência (ideia do ve_virality.py, ai-video-editor, MIT);
# SEM CORTE: trecho de 3 min ou mais sem nenhum corte nem remoção (assunto que pode ter ficado de fora).
# 1.2.0: não existe mais "Corte médio" — tudo acima de 3:00 é Corte longo (de mais de 3 até 40 min).
import json, os, sys, re, unicodedata
from comum import CONFIG, secs, hms, duracao, video_de

CATS = ['Corte longo', 'Corte curto', 'Remover (anúncio)', 'Remover (outros)',
        'Atenção (políticas)', 'Atenção (direitos)', 'Atenção (monetização)']
FAIXA = {'Corte longo': (180, 2400), 'Corte curto': (30, 180)}   # 17/11/2026: Short até 3:00; longo de mais de 3 até 40 min
SHORT_ALVO = (60, 150)      # Short completo: 1:00 a 2:30 (até 2:53 se a história pedir); abaixo de 45 s, só frase de efeito
SHORT_CURTO = 45
SEM_CORTE_S = 180           # trecho sem corte a partir do qual o validador pergunta o motivo
DEPENDE = ['como eu falei', 'como eu disse', 'como falei', 'como eu tinha falado', 'voltando', 'isso aqui', 'isso aí', 'isso', 'esse', 'essa',
           'esses', 'essas', 'ele', 'ela', 'eles', 'elas', 'e aí', 'então', 'também', 'daí', 'aí', 'mas', 'e', 'porque', 'que', 'o outro', 'a outra']
CONECTIVO = {'mas', 'e', 'porque', 'então', 'que', 'tipo', 'ou', 'pra', 'para', 'de', 'do', 'da', 'o', 'a', 'com', 'se', 'é'}
acento = lambda w: re.sub(r'[^\wà-úç ]', '', w.lower()).strip()
norm = lambda w: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', w.lower()).encode('ascii', 'ignore').decode())

def validar(pasta):
    j = json.load(open(os.path.join(pasta, '_analise', 'cortes.json'), encoding='utf-8'))
    for c in j['cortes']:   # 1.2.0: "Short/Reels" passou a se chamar "Corte curto"
        if c.get('categoria') == 'Short/Reels': c['categoria'] = 'Corte curto'
    D = duracao(video_de(pasta)); av = []; vistos = {}
    lim_short = CONFIG.get('limite_short_s', 180)
    ws = None
    tj = os.path.join(pasta, '_analise', 'transcricao.json')
    if os.path.exists(tj): ws = json.load(open(tj, encoding='utf-8'))
    for k, c in enumerate(j['cortes'], 1):
        r = f"#{k} {c.get('categoria')} · {c.get('tema')}"; cat = c.get('categoria')
        if cat == 'Corte médio': av.append(f'{r}: a categoria "Corte médio" não existe mais (1.2.0) — use "Corte longo" ou "Corte curto"'); continue
        if cat not in CATS: av.append(f'{r}: categoria desconhecida'); continue
        a, b = secs(c['inicio']), secs(c['fim'])
        if not (0 <= a < b <= D + 1): av.append(f'{r}: tempo fora do vídeo ou início depois do fim ({c["inicio"]}–{c["fim"]})'); continue
        if cat not in FAIXA: continue
        d = b - a; lo, hi = FAIXA[cat]
        if not (lo * 0.9 if cat == 'Corte curto' else lo) < d <= hi * (1.0 if cat == 'Corte curto' else 1.1):   # 3:00 é o teto do Short
            av.append(f'{r}: duração {hms(d)} fora da faixa da categoria ({hms(lo)}–{hms(hi)})')
        fv = CONFIG.get('final_vertical_s', 7)
        if cat == 'Corte curto' and lim_short - fv < d <= lim_short:
            av.append(f'{r}: Short de {hms(d)} + {fv} s de finalização vertical = {hms(d + fv)}, passa de 3:00 — o YouTube e o Instagram '
                      f'o tratam como vídeo comum. Apertar para até {hms(lim_short - fv)}?')
        if cat == 'Corte longo' and lim_short < d <= lim_short + 45:
            av.append(f'{r}: {hms(d)}, só {d - lim_short:.0f} s acima de 3:00 — apertando, vira Short também. Vale apertar?')
        if cat == 'Corte curto' and d < SHORT_CURTO:
            av.append(f'{r}: SHORT CURTO — {hms(d)}; o alvo é {hms(SHORT_ALVO[0])} a {hms(SHORT_ALVO[1])} com a história completa '
                      f'(gancho → desenvolvimento → conclusão). Só fica abaixo de {SHORT_CURTO} s se for uma frase de efeito que se sustenta sozinha.')
        chave = (cat, round(a), round(b))
        if chave in vistos: av.append(f'{r}: mesmo trecho que #{vistos[chave]}')
        vistos[chave] = k
        for t in ('titulo1', 'titulo2', 'titulo3'):
            if not c.get(t): av.append(f'{r}: falta {t}')
            elif len(c[t]) > 100: av.append(f'{r}: {t} com {len(c[t])} caracteres (máx. 100)')
        if cat != 'Corte curto' and not 3 <= len((c.get('capa') or '').split()) <= 7: av.append(f'{r}: texto da capa fora de 3–7 palavras')
        if not 3 <= len(c.get('hashtags') or []) <= 5: av.append(f'{r}: {len(c.get("hashtags") or [])} hashtags (pede 3–5)')
        for x in ('gancho', 'autossuf', 'emocao', 'frase', 'em_alta'):
            if c.get(x) not in (0, 1, 2): av.append(f'{r}: critério {x} = {c.get(x)!r} (pede 0, 1 ou 2)')
        if cat == 'Corte curto' and ws and 'bipar' not in (c.get('obs') or '').lower():
            pal = [w[2] for w in ws if a <= w[0] < b and norm(w[2]) in set(CONFIG['palavroes'])]
            if pal: av.append(f'{r}: tem palavrão ({", ".join(sorted(set(pal)))}) e a observação não diz "bipar"')
        if cat == 'Corte curto' and ws:
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
            if cat not in ('Corte longo', 'Corte curto'): continue
            r = f"#{k} {cat} · {c.get('tema')}"; a, b = secs(c['inicio']), secs(c['fim'])
            m = depende(a)
            if m:
                alt = next((ws[i] for i in frase_ini if a < ws[i][0] <= a + 25 and not depende(ws[i][0])), None)
                av.append(f'{r}: GANCHO — começa com "{m}…", que depende do que veio antes'
                          + (f'; início alternativo em {hms(alt[0])}: "{" ".join(x[2] for x in ws if alt[0] <= x[0])[:70]}…"' if alt else
                             '; sem frase independente nos 25 s seguintes: use legenda de contexto'))
            fim = [w for w in ws if w[1] <= b + 0.5][-3:]
            if fim:
                ult = fim[-1][2].strip()
                if ult.endswith('?'): av.append(f'{r}: FIM — termina numa pergunta ("…{" ".join(w[2] for w in fim)}"): a resposta ficou fora?')
                elif acento(ult) in CONECTIVO: av.append(f'{r}: FIM — termina em "{ult}", a ideia ficou pela metade')
        # repetição: longos que dividem mais de 20% do menor (cada assunto entra em UM longo) ou Shorts que dividem mais de 30%.
        # Short de dentro de um longo é permitido: vai para outras plataformas e atrai público novo.
        cs = [(k, c, secs(c['inicio']), secs(c['fim'])) for k, c in enumerate(j['cortes'], 1)
              if c.get('categoria') in ('Corte longo', 'Corte curto')]
        for x in range(len(cs)):
            for y in range(x + 1, len(cs)):
                (k1, c1, a1, b1), (k2, c2, a2, b2) = cs[x], cs[y]
                sob = min(b1, b2) - max(a1, a2)
                if sob <= 0: continue
                menor = min(b1 - a1, b2 - a2)
                lim_rep = 0.2 if c1['categoria'] == 'Corte longo' else 0.3
                if c1['categoria'] == c2['categoria'] and sob > lim_rep * menor:
                    av.append(f"REPETIÇÃO — #{k1} e #{k2} ({c1['categoria']}) dividem {hms(sob)}: {c1['tema'][:35]} / {c2['tema'][:35]}"
                              + (' — cada assunto entra em um longo só' if c1['categoria'] == 'Corte longo' else ''))
    av += sem_corte(pasta, j['cortes'], D)
    for k, c in enumerate(j['cortes'], 1):
        if c.get('em_alta') == 2 and not c.get('fonte_em_alta'):
            av.append(f"#{k} {c.get('categoria')} · {c.get('tema')}: \"Tema em alta\" = 2 sem fonte (chave fonte_em_alta com o link da notícia)")
    return av

def sem_corte(pasta, cortes, D, minimo=SEM_CORTE_S):
    """Trechos de `minimo` s ou mais sem nenhum corte, remoção ou alerta: assunto que pode ter ficado de fora.
    Traz a nota média dos sinais (mapa de momentos) e o assunto mais próximo, quando existirem."""
    iv = []
    for c in cortes:
        try: iv.append((secs(c['inicio']), secs(c['fim'])))
        except (KeyError, ValueError, TypeError): pass
    iv.sort(); buracos = []; ant = 0.0
    for a, b in iv:
        if a - ant >= minimo: buracos.append((ant, a))
        ant = max(ant, b)
    if D - ant >= minimo: buracos.append((ant, D))
    if not buracos: return []
    mp = os.path.join(pasta, '_analise', 'momentos.json'); assuntos = []
    if os.path.exists(mp):
        try: assuntos = json.load(open(mp, encoding='utf-8')).get('assuntos') or []
        except (ValueError, OSError): pass
    av = []
    for a, b in buracos:
        info = ''
        sob = [s for s in assuntos if min(b, s['fim']) - max(a, s['inicio']) > 0.5 * min(b - a, s['fim'] - s['inicio'])]
        if sob:
            s = max(sob, key=lambda s: s.get('nota', 0))
            info = f"; sinais {s.get('nota', 0):+.2f}, palavras-chave: {', '.join(s.get('chave', [])[:4])}"
        av.append(f'SEM CORTE — {hms(a)}–{hms(b)} ({hms(b - a)}) sem corte nem remoção{info}. '
                  'Vira corte, ou diga ao usuário por que fica de fora (abertura, conversa fraca, repetição, risco).')
    return av

if __name__ == '__main__':
    av = validar(os.path.abspath(sys.argv[1]))
    print('\n'.join(av) if av else 'cortes.json sem avisos'); print(f'{len(av)} avisos')
