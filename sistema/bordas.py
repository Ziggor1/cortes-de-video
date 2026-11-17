# Ajuste fino das bordas dos cortes usando o tempo de cada palavra da transcrição (_analise/transcricao.json).
#   - início: no começo da frase (nunca no meio), com um pequeno respiro antes da primeira palavra;
#   - fim: no fim da frase, com respiro depois da última palavra, sem pegar o começo da fala seguinte;
#   - se a frase completa estiver a mais de MAX_DESLOC s, não mexe e avisa ("começa/termina no meio de um raciocínio").
# O respiro padrão é calibrado pelas correções que o usuário marca nas notas (_sistema/calibracao.json).
import os, re, json
from comum import AQUI, hms

FIM_FRASE = re.compile(r'[.!?…]["”)]?$')
PAUSA_FRASE = 0.7     # silêncio que também conta como fim de frase (s)
MAX_DESLOC = 8.0      # quanto a borda pode andar para achar a frase completa (s)
DESLOC_AVISO = 3.0    # acima disso a borda andou, mas vai para conferência no bordas.txt e na Observação

def calibracao():
    p = os.path.join(AQUI, 'calibracao.json'); c = {'respiro_inicio': 0.20, 'respiro_fim': 0.35}
    if os.path.exists(p):
        j = json.load(open(p, encoding='utf-8'))
        if j.get('n', 0) >= 5:   # só calibra com pelo menos 5 correções
            c['respiro_inicio'] = round(min(2.0, max(0.0, 0.20 - j.get('inicio_medio', 0))), 2)
            c['respiro_fim'] = round(min(2.5, max(0.1, 0.35 + j.get('fim_medio', 0))), 2)
    return c

def _fim_de_frase(ws, i):
    """A palavra i encerra uma frase? (pontuação ou pausa longa depois dela)"""
    return bool(FIM_FRASE.search(ws[i][2])) or i == len(ws) - 1 or ws[i + 1][0] - ws[i][1] >= PAUSA_FRASE

def ajustar(ws, ini, fim, cal=None):
    """Devolve (novo_ini, novo_fim, avisos). ws = [[início, fim, palavra], ...] em segundos do vídeo."""
    cal = cal or calibracao(); avisos = []
    if not ws: return ini, fim, ['sem transcrição']
    # --- início: primeira palavra que começa perto de `ini`
    i = next((k for k, w in enumerate(ws) if w[0] >= ini - 0.2), None)
    if i is None: return ini, fim, ['início depois do fim da transcrição']
    if i > 0 and not _fim_de_frase(ws, i - 1):          # está no meio de uma frase: volta até o começo dela
        k = i - 1
        while k > 0 and not _fim_de_frase(ws, k - 1) and ws[i][0] - ws[k][0] < MAX_DESLOC: k -= 1
        if k == 0 or _fim_de_frase(ws, k - 1): i = k
        else: avisos.append('começa no meio de um raciocínio (frase completa a mais de %d s)' % MAX_DESLOC)
    novo_ini = ws[i][0] - cal['respiro_inicio']
    if i > 0: novo_ini = min(ws[i][0], max(novo_ini, ws[i - 1][1] + 0.05))   # nunca corta a primeira palavra
    # --- fim: última palavra que termina perto de `fim`
    j = max((k for k, w in enumerate(ws) if w[1] <= fim + 0.2), default=None)
    if j is None or j < i: return round(novo_ini, 2), fim, avisos + ['fim antes do início na transcrição']
    if not _fim_de_frase(ws, j):                          # termina no meio de uma frase: avança até o fim dela
        k = j
        while k < len(ws) - 1 and not _fim_de_frase(ws, k) and ws[k][1] - ws[j][1] < MAX_DESLOC: k += 1
        if _fim_de_frase(ws, k): j = k
        else: avisos.append('termina no meio de um raciocínio (fim da frase a mais de %d s)' % MAX_DESLOC)
    novo_fim = ws[j][1] + cal['respiro_fim']
    if j < len(ws) - 1: novo_fim = max(ws[j][1], min(novo_fim, ws[j + 1][0] - 0.05))   # nunca corta a última palavra
    # deslocamento grande costuma ser fala sem pontuação: o corte pode ter pegado o fim do assunto anterior ou uma frase solta
    if ini - novo_ini > DESLOC_AVISO: avisos.append(f'início recuou {ini - novo_ini:.1f} s: conferir se não pegou o assunto anterior')
    if novo_fim - fim > DESLOC_AVISO: avisos.append(f'fim avançou {novo_fim - fim:.1f} s: conferir se não terminou numa frase solta')
    return round(novo_ini, 2), round(novo_fim, 2), avisos

def contexto(ws, t, antes=True, n=7):
    """Palavras logo antes (ou depois) de um instante, para conferência."""
    if antes: sel = [w[2] for w in ws if w[1] <= t][-n:]
    else: sel = [w[2] for w in ws if w[0] >= t][:n]
    return ' '.join(sel)

def relatorio(ws, linhas, destino):
    """linhas = [(rótulo, ini_original, fim_original, ini_novo, fim_novo, avisos)] -> arquivo de conferência."""
    out = ['Conferência das bordas  (… antes ‖ dentro do corte …)', '']
    for rot, a0, b0, a1, b1, av in linhas:
        out.append(f'== {rot}   {hms(a0)}–{hms(b0)}  →  {hms(a1)}–{hms(b1)}   (início {a1 - a0:+.1f} s, fim {b1 - b0:+.1f} s)')
        out.append(f'   INÍCIO: …{contexto(ws, a1)} ‖ {contexto(ws, a1, False)}…')
        out.append(f'   FIM:    …{contexto(ws, b1)} ‖ {contexto(ws, b1, False)}…')
        for x in av: out.append(f'   ⚠ {x}')
        out.append('')
    open(destino, 'w', encoding='utf-8').write('\n'.join(out))
