# Funções comuns do fluxo de cortes (análise -> edição -> notas).
import os, re, sys, glob, json, shutil, platform, subprocess, datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
COFRE = os.path.dirname(AQUI)                      # raiz do cofre (pasta que contém _sistema)
FONTES = os.path.join(AQUI, 'fontes')              # fontes livres (OFL) que acompanham o sistema

def _ler_config():
    """config_padrao.json (vem com o sistema) + config.json (desta máquina, criado pelo instalar.py; nunca vai para o GitHub)."""
    cfg = {}
    for nome in ('config_padrao.json', 'config.json'):
        p = os.path.join(AQUI, nome)
        if os.path.exists(p):
            local = json.load(open(p, encoding='utf-8'))
            for k, v in local.items():
                cfg[k] = dict(cfg.get(k) or {}, **v) if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    return cfg
CONFIG = _ler_config()
SISTEMA = platform.system()                        # 'Windows', 'Linux' ou 'Darwin' (macOS)
PY = CONFIG.get('python') if os.path.exists(CONFIG.get('python') or '') else sys.executable
# Onde ficam os canais e episódios: subpasta do cofre (ex.: "Pasta de Trabalho") ou "" para a própria raiz
TRABALHO = os.path.join(COFRE, CONFIG.get('pasta_trabalho', '')) if CONFIG.get('pasta_trabalho') else COFRE

def _achar_bin(nome):
    cfg = CONFIG.get('ffmpeg_dir') or ''
    for c in [os.path.join(cfg, nome + '.exe'), os.path.join(cfg, nome)]:
        if cfg and os.path.exists(c): return c
    achado = shutil.which(nome)
    if achado: return achado
    candidatos = []
    if os.name == 'nt':
        base = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages')
        candidatos += glob.glob(os.path.join(base, 'Gyan.FFmpeg*', '*', 'bin', nome + '.exe'))
        candidatos += glob.glob(os.path.expandvars(rf'%ProgramFiles%\ffmpeg*\bin\{nome}.exe'))
    else:
        candidatos += [f'/opt/homebrew/bin/{nome}', f'/usr/local/bin/{nome}', f'/usr/bin/{nome}', os.path.expanduser(f'~/.local/bin/{nome}')]
    return next((c for c in candidatos if os.path.exists(c)), nome)
FF, FP = _achar_bin('ffmpeg'), _achar_bin('ffprobe')

def fonte(tipo='legenda'):
    """Arquivo de fonte padrão: 'titulo' = Anton (capas, no lugar da Impact); 'legenda'/'ui' = Archivo Black."""
    arq = {'titulo': 'Anton-Regular.ttf'}.get(tipo, 'ArchivoBlack-Regular.ttf')
    return os.path.join(FONTES, arq)
NOME_FONTE_LEGENDA = 'Archivo Black'

def preparar_fonte_legenda(vis, trab):
    """Copia para <trab>/fontes a fonte da legenda (a do canal, se houver; senão a Archivo Black que vem com o sistema)
    e devolve o nome da família para o arquivo .ass. Com fontsdir=fontes, o libass usa essa fonte em qualquer sistema."""
    os.makedirs(os.path.join(trab, 'fontes'), exist_ok=True)
    if vis.get('fonte') and vis.get('fonte_nome') and os.path.exists(vis['fonte']):
        shutil.copy(vis['fonte'], os.path.join(trab, 'fontes')); return vis['fonte_nome']
    shutil.copy(fonte('legenda'), os.path.join(trab, 'fontes')); return NOME_FONTE_LEGENDA

def caminho_ff(p):
    """Caminho de arquivo para usar dentro de um filtro do ffmpeg (fontfile=...): barras normais e ':' escapado."""
    return "'" + p.replace('\\', '/').replace(':', '\\:').replace("'", "\\'") + "'"

def sp(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

def duracao(f):
    o = sp([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).stdout.strip()
    try: return float(o)
    except ValueError: return 0.0

def secs(t):
    if t is None: return None
    if isinstance(t, datetime.time): return t.hour*3600 + t.minute*60 + t.second + t.microsecond/1e6
    if isinstance(t, datetime.timedelta): return t.total_seconds()
    if isinstance(t, datetime.datetime): return t.hour*3600 + t.minute*60 + t.second + t.microsecond/1e6
    if isinstance(t, (int, float)): return float(t)*86400 if float(t) < 1 else float(t)
    p = [float(x) for x in str(t).split(':')]
    while len(p) < 3: p.insert(0, 0)
    return p[0]*3600 + p[1]*60 + p[2]

def hms(s):
    s = int(round(s or 0)); return f'{s//3600}:{s%3600//60:02d}:{s%60:02d}'

def limpar(t):
    t = re.sub(r'[\\/:*?"<>|“”]', '', str(t)).strip().rstrip('.')
    return re.sub(r'\s+', ' ', t)[:90]

def _sem_acento(s):
    import unicodedata
    return unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()

def e_pasta_visual(nome):
    """Pasta de identidade visual do canal (intro, final, marca d'água, capa): nunca é episódio."""
    n = _sem_acento(nome)
    return any(k in n for k in ('visual', 'identidade', 'marca', 'assets', 'vinheta'))

def pasta_visual(canal_dir):
    for n in sorted(os.listdir(canal_dir)):
        if os.path.isdir(os.path.join(canal_dir, n)) and e_pasta_visual(n): return os.path.join(canal_dir, n)
    return None

def episodios():
    """Pastas de episódio: <Canal>/<Episódio>/ contendo um .mp4."""
    eps = []
    for canal in sorted(os.listdir(TRABALHO)):
        pc = os.path.join(TRABALHO, canal)
        if not os.path.isdir(pc) or canal.startswith(('_', '.', '0', 'Canais', 'Regras', 'Modelos')): continue
        for ep in sorted(os.listdir(pc)):
            pe = os.path.join(pc, ep)
            if e_pasta_visual(ep): continue
            if os.path.isdir(pe) and glob.glob(os.path.join(pe, '*.mp4')):
                eps.append(pe)
    return eps

def video_de(pasta):
    v = sorted(glob.glob(os.path.join(pasta, '*.mp4')), key=os.path.getsize, reverse=True)
    return v[0] if v else None

def planilha_de(pasta):
    x = [f for f in glob.glob(os.path.join(pasta, 'Cortes_*.xlsx')) if not os.path.basename(f).startswith('~$')]
    return max(x, key=os.path.getmtime) if x else None

def log(*a):
    s = datetime.datetime.now().strftime('%H:%M:%S') + ' ' + ' '.join(map(str, a))
    print(s, flush=True)

# Durações (decisão de 17/11/2026): Short até 3:00; médio de mais de 3 até 10 min; longo de mais de 10 até 40 min.
LIMITE_SHORT = CONFIG.get('limite_short_s', 180)
PLATAFORMAS_COM_LIMITE = CONFIG.get('plataformas_com_limite', [])   # 17/11: vazio = todo Short sempre ganha a finalização vertical

def final_vertical_cabe(dur_corte, dur_final, plataforma):
    """Padrão (decisão de 17/11/2026): todo Short ganha a finalização vertical, em todas as plataformas (lista vazia no config).
    Se um dia alguma plataforma entrar em `plataformas_com_limite`, a versão dela sai sem a finalização quando passar de 3:00."""
    return plataforma not in PLATAFORMAS_COM_LIMITE or dur_corte + dur_final <= LIMITE_SHORT


# ---------------------------------------------------------------- vídeo: codificador H.264 da máquina
_ENC = {}
_OPCOES_ENC = {   # do mais rápido ao mais compatível; 'auto' testa nesta ordem e cai no libx264 (CPU) se nenhum funcionar
    'h264_nvenc': ['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '21', '-b:v', '0', '-maxrate', '12M', '-bufsize', '24M'],   # NVIDIA
    'h264_videotoolbox': ['-c:v', 'h264_videotoolbox', '-b:v', '10M', '-maxrate', '12M'],                                                  # macOS
    'h264_qsv': ['-c:v', 'h264_qsv', '-global_quality', '22'],                                                                              # Intel
    'h264_amf': ['-c:v', 'h264_amf', '-rc', 'cqp', '-qp_i', '20', '-qp_p', '22'],                                                           # AMD (Windows)
    'libx264': ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20'],                                                                    # CPU
}

def encoder():
    """Argumentos do codificador H.264. config "encoder": "auto" (padrão) ou um nome de _OPCOES_ENC. Testado uma vez por execução."""
    if 'args' in _ENC: return _ENC['args']
    pedido = CONFIG.get('encoder') or CONFIG.get('encoder_vertical') or 'auto'
    ordem = [pedido] if pedido in _OPCOES_ENC and pedido != 'auto' else list(_OPCOES_ENC)
    for nome in ordem + ['libx264']:
        if nome == 'libx264' or sp([FF, '-v', 'error', '-f', 'lavfi', '-i', 'color=s=256x256:d=0.2', '-c:v', nome, '-f', 'null', '-']).returncode == 0:
            _ENC.update(nome=nome, args=list(_OPCOES_ENC[nome])); break
    return _ENC['args']

# ---------------------------------------------------------------- processos longos: manter o computador acordado
def processo_vivo(pid):
    if not pid: return False
    try:
        if os.name == 'nt':
            return str(pid) in subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout
        os.kill(int(pid), 0); return True
    except (OSError, ValueError): return False

def manter_acordado():
    """Impede a suspensão por inatividade enquanto a fila roda (não impede fechar a tampa nem desligar).
    Windows: SetThreadExecutionState; macOS: caffeinate; Linux: systemd-inhibit, se existir. Devolve a função que libera."""
    try:
        if os.name == 'nt':
            import ctypes
            if ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):
                return lambda: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        elif SISTEMA == 'Darwin' and shutil.which('caffeinate'):
            p = subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())]); return p.terminate
        elif shutil.which('systemd-inhibit'):
            p = subprocess.Popen(['systemd-inhibit', '--what=idle:sleep', '--who=cortes-de-video', '--why=fila de cortes rodando',
                                  'sleep', 'infinity'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return p.terminate
    except Exception: pass
    return lambda: None
