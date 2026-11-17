# Juiz final dos Shorts (opcional): uma chamada à API de LLM (config.json → llm) avalia os "Shorts prontos" do mapa de momentos
# e rejeita o que é meio de raciocínio, preparação sem conclusão, fala atropelada ou dependente de contexto.
# Ideia adaptada do _llm_rank do ve_virality.py (EverythingAI-Pro/ai-video-editor, licença MIT, © 2026 EveryThingAi):
# lá a chamada vai para a API da Anthropic; aqui vai para a API configurada em llm (a mesma da triagem).
# Uso: python juiz_llm.py "<pasta do episódio>" [--publico]   (precisa do _analise\momentos.json; refaz o momentos.md no fim)
#   Mesma trava da triagem: só roda com vídeo público no YouTube, ou com --publico confirmado pelo usuário.
#   -> _analise\juiz_llm.json
# Envia só o texto dos candidatos (transcrição de vídeo público). O resultado é sugestão: o Claude confere e decide.
import os, sys, re, json, time
from comum import hms, log
import triagem_llm as T

PROMPT = """Você é editor de Shorts/Reels/TikTok de um canal brasileiro que publica cortes de lives e podcasts.
Abaixo estão candidatos a Short tirados de um vídeo longo ("{titulo}"), já filtrados por sinais de audiência e de áudio.
Cada candidato tem: i (índice), duracao_s, gaguejada (fração de palavras repetidas em sequência; acima de 0,05 = fala atropelada),
gancho (tipos de gancho detectados por regra, pode estar vazio) e o texto completo (transcrição automática, pontuação imperfeita).

Julgue cada um como um Short INDEPENDENTE, assistido por quem nunca viu a live.
REJEITE quando: começa no meio de um raciocínio ou depende do que veio antes; é só preparação, sem conclusão; a fala está atropelada;
precisa de contexto de fora para ser entendido; é leitura de chat, navegação de tela ou conversa técnica da live.
APROVE quando a primeira frase prende sozinha e o fim fecha a ideia (conclusão, piada, frase de efeito).

Responda SOMENTE com JSON, um item para CADA candidato, os melhores primeiro e os rejeitados no fim:
{{"avaliacao": [{{"i": 0, "aprovado": true, "motivo": "até 10 palavras, concreto", "nota": 1 a 10}}]}}

CANDIDATOS:
{lista}"""

def objeto_json(txt):
    txt = re.sub(r'<think>.*?</think>', '', txt, flags=re.S)
    a, b = txt.find('{'), txt.rfind('}')
    if a < 0 or b < a: raise ValueError('sem JSON')
    try: return json.loads(txt[a:b + 1])
    except json.JSONDecodeError: return json.loads(re.sub(r',\s*([\]}])', r'\1', txt[a:b + 1]))

def main(pasta, regerar_mapa=True, forcar_publico=False):
    if not T.ativado(): log('juiz por LLM desligado (config.json → llm.ativado = false)'); return 0
    ok, motivo = T.publico(pasta, forcar_publico)
    if not ok: log('juiz NÃO rodou por segurança:', motivo); return 3
    A = os.path.join(pasta, '_analise'); mj = os.path.join(A, 'momentos.json')
    if not os.path.exists(mj): log('sem _analise\\momentos.json: rode momentos.py antes'); return 1
    shorts = json.load(open(mj, encoding='utf-8')).get('shorts', [])
    if not shorts: log('nenhum Short pronto para julgar'); return 0
    k = T.chave()
    if not k and 'localhost' not in T.base_url() and '127.0.0.1' not in T.base_url(): log('API de LLM: sem a chave; juiz não rodou'); return 2
    import glob
    info = next(iter(glob.glob(os.path.join(A, 'youtube', '*.info.json'))), None)
    titulo = json.load(open(info, encoding='utf-8')).get('title') if info else os.path.basename(pasta)
    lista = json.dumps([dict(i=i, duracao_s=round(c['dur']), gaguejada=c.get('gaguejada', 0), gancho=c.get('tipos', []),
                             texto=c.get('texto') or f"{c.get('primeira', '')} … {c.get('ultima', '')}") for i, c in enumerate(shorts)],
                       ensure_ascii=False)
    prompt = PROMPT.format(titulo=titulo, lista=lista)
    aval, via, erros, t0 = None, None, [], time.time()
    for mod in T.MODELOS:
        try: txt, via = T.pedir(prompt, mod, k, tentativas=2)
        except RuntimeError as e:
            erros.append(f'{mod}: {e}')
            if 'HTTP 401' in str(e):
                log('a API de LLM recusou a chave: confira config.json → llm'); return 2
            continue
        try:
            aval = [x for x in objeto_json(txt).get('avaliacao', []) if isinstance(x, dict) and isinstance(x.get('i'), int)]
            if aval: break
        except Exception: pass
        erros.append(f'{mod} ({via}): resposta sem JSON válido'); aval = None
    if not aval: log('juiz não rodou:', '; '.join(erros) or 'sem resposta'); return 1
    itens = []
    for x in aval:
        if 0 <= x['i'] < len(shorts):
            c = shorts[x['i']]
            itens.append(dict(inicio=c['inicio'], fim=c['fim'], aprovado=x.get('aprovado') is True, motivo=T.txt(x.get('motivo'), 120),
                              nota=T.nota_num(x.get('nota')), primeira=c.get('primeira', '')[:120]))
    json.dump(dict(via=via, segundos=round(time.time() - t0), julgados=len(itens), de=len(shorts), itens=itens),
              open(os.path.join(A, 'juiz_llm.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    ok = sum(x['aprovado'] for x in itens)
    log(f'juiz: {ok} aprovados e {len(itens) - ok} rejeitados de {len(shorts)} Shorts prontos, via {via} em {round(time.time() - t0)} s'
        + (f' ({len(shorts) - len(itens)} sem avaliação)' if len(itens) < len(shorts) else ''))
    if regerar_mapa:
        import momentos; momentos.gerar(pasta)
    return 0

if __name__ == '__main__':
    sys.exit(main(os.path.abspath(sys.argv[1]), forcar_publico='--publico' in sys.argv))
