# Fila retomável das etapas longas. Se o computador desligar, "rodar" continua de onde parou.
# Uso (em _sistema):
#   python fila.py criar finalizar "<pasta>" [--refazer] + finalizar "<pasta 2>" + conferir "<pasta>"
#   python fila.py rodar      -> executa os itens que faltam, em ordem (use em segundo plano)
#   python fila.py status     -> mostra cada item e se a fila está rodando, interrompida ou concluída
# Etapas: transcrever, sinais, youtube, momentos, triagem (LLM; chama momentos e juiz no fim), juiz (só o juiz dos Shorts), planilha,
#         editar, finalizar, conferir, publicacao,
#         notas (sem pasta).
# "criar" acrescenta "notas" no fim. Uma fila com itens pendentes só é trocada com --substituir.
# Em "finalizar --refazer" a fila usa --refazer-desde <criação da fila>: o que já foi refeito não é refeito de novo.
import os, sys, json, time, subprocess, datetime
from comum import AQUI, CONFIG, PY, processo_vivo, manter_acordado, aplicar_limites

EST = os.path.join(AQUI, '_logs', 'fila_estado.json'); LOG = os.path.join(AQUI, '_logs', 'fila.txt')
ETAPAS = {'transcrever': 'transcrever.py', 'sinais': 'sinais.py', 'youtube': 'youtube.py', 'momentos': 'momentos.py', 'triagem': 'triagem_llm.py', 'juiz': 'juiz_llm.py',
          'planilha': 'planilha.py', 'editar': 'editar.py',
          'finalizar': 'finalizar.py', 'conferir': 'conferir.py', 'publicacao': 'publicacao.py', 'notas': 'atualizar_notas.py'}
agora = lambda: datetime.datetime.now().strftime('%d/%m %H:%M:%S')

def ler(): return json.load(open(EST, encoding='utf-8')) if os.path.exists(EST) else None

def gravar(e):
    os.makedirs(os.path.dirname(EST), exist_ok=True); tmp = EST + '.tmp'
    json.dump(e, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, EST)

def marca(t):
    s = agora() + ' ' + t; print(s, flush=True); open(LOG, 'a', encoding='utf-8').write(s + '\n')

def vivo(pid): return processo_vivo(pid)

def nome(i): return i['etapa'] + (' · ' + os.path.basename(i['pasta']) if i['pasta'] else '') + (' ' + ' '.join(i['flags']) if i['flags'] else '')

def status():
    e = ler()
    if not e: print('Não há fila.'); return 0
    falta = [i for i in e['itens'] if i['status'] != 'feito']; rodando = vivo(e.get('pid'))
    estado = 'RODANDO' if rodando else 'CONCLUÍDA' if not falta else 'INTERROMPIDA' if any(i['status'] in ('rodando', 'feito') for i in e['itens']) else 'CRIADA (não iniciada)'
    print(f"Fila de {e['criada_em']}: {estado} — {len(e['itens']) - len(falta)}/{len(e['itens'])} itens feitos")
    for i in e['itens']:
        print(f"  [{i['status']:8}] {nome(i)}" + (f"  ({i.get('inicio', '')} → {i.get('fim', '…')})" if i.get('inicio') else ''))
    return 0

def criar(args):
    ant = ler()
    if ant and any(i['status'] != 'feito' for i in ant['itens']) and '--substituir' not in args:
        print('Já existe uma fila com itens pendentes: use "rodar" para retomar, ou "criar … --substituir" para trocar.'); status(); return 1
    grupos = [[]]
    for a in [a for a in args if a != '--substituir']:
        if a == '+': grupos.append([])
        else: grupos[-1].append(a)
    itens = []
    for g in [g for g in grupos if g]:
        et = g[0]
        if et not in ETAPAS: print('Etapa desconhecida:', et, '| válidas:', ', '.join(ETAPAS)); return 1
        pasta = os.path.abspath(g[1]) if len(g) > 1 and not g[1].startswith('--') else None
        if et != 'notas' and not (pasta and os.path.isdir(pasta)): print('Pasta não encontrada para', et + ':', pasta); return 1
        itens.append(dict(etapa=et, pasta=pasta, flags=g[(2 if pasta else 1):], status='pendente'))
    if not itens: print('Nenhum item. Veja o uso no topo de fila.py.'); return 1
    if itens[-1]['etapa'] != 'notas': itens.append(dict(etapa='notas', pasta=None, flags=[], status='pendente'))
    gravar(dict(criada=time.time(), criada_em=agora(), pid=None, itens=itens)); return status()

def rodar():
    e = ler()
    if not e: print('Não há fila. Use "criar".'); return 1
    if vivo(e.get('pid')): print('A fila já está rodando (PID', str(e['pid']) + ').'); return 1
    retomada = any(i['status'] in ('rodando', 'feito', 'erro') for i in e['itens'])
    e['pid'] = os.getpid(); gravar(e); marca('FILA RETOMADA' if retomada else 'FILA INICIADA')
    liberar = manter_acordado()   # impede a suspensão por inatividade enquanto a fila roda (Windows, macOS e Linux)
    lim = aplicar_limites()       # prioridade baixa e parte dos núcleos (temperatura); as etapas herdam
    if lim: marca('limites de carga: ' + ', '.join(lim))
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    for i in e['itens']:
        if i['status'] == 'feito': continue
        flags = list(i['flags'])
        if i['etapa'] == 'finalizar' and '--refazer' in flags:
            flags.remove('--refazer'); flags += ['--refazer-desde', str(e['criada'])]
        cmd = [PY, '-u', os.path.join(AQUI, ETAPAS[i['etapa']])] + ([i['pasta']] if i['pasta'] else []) + flags
        destino = os.path.join(i['pasta'], '_analise', f"log_{i['etapa']}.txt") if i['pasta'] else os.path.join(AQUI, '_logs', f"log_{i['etapa']}.txt")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        i.update(status='rodando', inicio=agora(), log=destino); i.pop('fim', None); gravar(e); marca('iniciando ' + nome(i))
        with open(destino, 'a', encoding='utf-8') as f:
            f.write(f'\n===== {agora()} · fila =====\n'); f.flush()
            r = subprocess.run(cmd, cwd=AQUI, stdout=f, stderr=subprocess.STDOUT, env=env)
        i.update(status='feito' if r.returncode == 0 else 'erro', codigo=r.returncode, fim=agora()); gravar(e)
        marca(('terminou ' if r.returncode == 0 else f'ERRO (código {r.returncode}) em ') + nome(i))
    erros = [nome(i) for i in e['itens'] if i['status'] == 'erro']
    e['pid'] = None; gravar(e); marca('FILA CONCLUIDA' + (' COM ERROS: ' + '; '.join(erros) if erros else ''))
    liberar()
    return 1 if erros else 0

if __name__ == '__main__':
    acao = sys.argv[1] if len(sys.argv) > 1 else 'status'
    sys.exit(criar(sys.argv[2:]) if acao == 'criar' else rodar() if acao == 'rodar' else status())
