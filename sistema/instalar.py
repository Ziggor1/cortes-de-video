# Instalador e verificador da skill /cortes-de-video (Windows, Linux e macOS). Só usa a biblioteca padrão do Python.
#
# Uso (o Claude roda estes comandos pela skill, sempre perguntando antes de instalar algo):
#   python instalar.py verificar [--json]            confere tudo e diz o que falta e como resolver
#   python instalar.py criar-cofre "<pasta>"         cria o cofre (modelo + scripts em <pasta>/_sistema) — roda a partir do repositório
#   python instalar.py pacotes [--gpu]               cria o ambiente Python do cofre (_sistema/.venv) e instala os pacotes travados
#   python instalar.py ffmpeg [--executar] [--estatico]   instala o ffmpeg (sem --executar só mostra o comando)
#   python instalar.py deno [--executar]             instala o Deno (runtime JavaScript que o yt-dlp usa no YouTube)
#   python instalar.py modelo [turbo|small|medium]   baixa o modelo do Whisper (~0,8 a 1,6 GB)
#   python instalar.py config chave=valor ...        grava escolhas desta máquina em _sistema/config.json (ex.: llm.ativado=true)
#   python instalar.py autoteste [--sem-whisper]     testa codificador, fontes, legenda, capa e Whisper com um vídeo sintético
#   python instalar.py atualizar [--ref main]        baixa a versão nova dos scripts do GitHub (guarda a anterior em _sistema/_backup_*)
#
# Nada é apagado: atualizações guardam a versão anterior. config.json, .env (chaves), calibracao.json e desempenho.json
# são desta máquina e nunca vão para o GitHub.
import os, sys, json, shutil, platform, subprocess, tempfile, zipfile, tarfile, urllib.request, datetime, time, glob

REPO = 'Ziggor1/cortes-de-video'
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_REPO = os.path.dirname(AQUI) if os.path.isdir(os.path.join(os.path.dirname(AQUI), 'modelo_cofre')) else None
NO_COFRE = os.path.basename(AQUI) == '_sistema'
COFRE = os.path.dirname(AQUI) if NO_COFRE else None
PONTEIRO = os.path.join(os.path.expanduser('~'), '.cortes-de-video.json')
SO = platform.system()                      # Windows | Linux | Darwin
ARQ = platform.machine().lower()            # amd64/x86_64 | arm64/aarch64
LOCAIS = {'config.json', '.env', 'calibracao.json', 'desempenho.json'}   # desta máquina: nunca substituídos
PYMIN = (3, 12)

def p(*a): print(*a, flush=True)

# ------------------------------------------------------------------ config desta máquina
def cfg_caminho(sistema_dir=None): return os.path.join(sistema_dir or AQUI, 'config.json')

def cfg_ler(sistema_dir=None):
    c = {}
    for nome in ('config_padrao.json', 'config.json'):
        f = os.path.join(sistema_dir or AQUI, nome)
        if os.path.exists(f):
            for k, v in json.load(open(f, encoding='utf-8')).items():
                c[k] = dict(c.get(k) or {}, **v) if isinstance(v, dict) and isinstance(c.get(k), dict) else v
    return c

def cfg_gravar(mudancas, sistema_dir=None):
    f = cfg_caminho(sistema_dir); c = json.load(open(f, encoding='utf-8')) if os.path.exists(f) else {}
    for chave, valor in mudancas.items():
        alvo = c; partes = chave.split('.')
        for k in partes[:-1]: alvo = alvo.setdefault(k, {})
        alvo[partes[-1]] = valor
    json.dump(c, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return c

def valor(txt):
    try: return json.loads(txt)
    except ValueError: return txt

def ponteiro_gravar(cofre, py):
    json.dump(dict(cofre=os.path.abspath(cofre), python=py, sistema=os.path.join(os.path.abspath(cofre), '_sistema'),
                   atualizado_em=datetime.datetime.now().isoformat(timespec='minutes')),
              open(PONTEIRO, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# ------------------------------------------------------------------ utilidades
def rodar(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)

def baixar(url, destino):
    p('baixando', url)
    req = urllib.request.Request(url, headers={'User-Agent': 'cortes-de-video-instalador'})
    with urllib.request.urlopen(req, timeout=600) as r, open(destino, 'wb') as f: shutil.copyfileobj(r, f)
    return destino

def py_venv(sistema_dir=None):
    v = os.path.join(sistema_dir or AQUI, '.venv')
    return os.path.join(v, 'Scripts', 'python.exe') if SO == 'Windows' else os.path.join(v, 'bin', 'python')

def py_do_sistema():
    c = cfg_ler(); py = c.get('python')
    return py if py and os.path.exists(py) else (py_venv() if os.path.exists(py_venv()) else sys.executable)

def achar_bin(nome):
    cfg = cfg_ler().get('ffmpeg_dir') or ''
    for c in [os.path.join(cfg, nome + '.exe'), os.path.join(cfg, nome), os.path.join(AQUI, 'bin', nome + '.exe'), os.path.join(AQUI, 'bin', nome)]:
        if os.path.exists(c) and (cfg or 'bin' in c): return c
    a = shutil.which(nome)
    if a: return a
    cand = glob.glob(os.path.expandvars(rf'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\{nome}.exe')) if SO == 'Windows' else \
           [f'/opt/homebrew/bin/{nome}', f'/usr/local/bin/{nome}', f'/usr/bin/{nome}', os.path.expanduser(f'~/.local/bin/{nome}')]
    return next((c for c in cand if os.path.exists(c)), None)

def arq_bin():
    return 'arm64' if ARQ in ('arm64', 'aarch64') else 'amd64'

# ------------------------------------------------------------------ verificar
def verificar(saida_json=False):
    itens = []   # (item, ok|falta|aviso|info, detalhe, como resolver)
    add = lambda *x: itens.append(x)
    add('Sistema', 'info', f'{SO} {platform.release()} ({ARQ})', '')
    v = sys.version_info
    add('Python (instalador)', 'ok' if v >= PYMIN else 'falta', f'{v.major}.{v.minor}.{v.micro} em {sys.executable}',
        '' if v >= PYMIN else f'Instale o Python {PYMIN[0]}.{PYMIN[1]} ou mais novo (Windows: winget install Python.Python.3.12; macOS: brew install python@3.12)')
    if NO_COFRE: add('Cofre', 'ok', COFRE, '')
    elif RAIZ_REPO: add('Cofre', 'aviso', 'rodando do repositório (cofre ainda não criado)', 'python instalar.py criar-cofre "<pasta>"')
    # pacotes Python do ambiente do cofre
    py = py_do_sistema()
    r = rodar([py, '-c', 'import faster_whisper, ctranslate2, numpy, openpyxl, PIL, yt_dlp; '
                         'print(faster_whisper.__version__, ctranslate2.__version__, numpy.__version__, yt_dlp.version.__version__); '
                         'print(ctranslate2.get_cuda_device_count())'])
    if r.returncode == 0:
        linhas = r.stdout.strip().splitlines()
        add('Pacotes Python', 'ok', f'faster-whisper/ctranslate2/numpy/yt-dlp = {linhas[0]} ({py})', '')
        cuda = int(linhas[1]) if len(linhas) > 1 and linhas[1].isdigit() else 0
    else:
        add('Pacotes Python', 'falta', f'não importam em {py}', 'python instalar.py pacotes' + (' --gpu' if shutil.which('nvidia-smi') else '')); cuda = 0
    # GPU
    smi = shutil.which('nvidia-smi')
    if smi:
        g = rodar([smi, '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader']).stdout.strip()
        add('Placa NVIDIA', 'ok', g or 'detectada', '')
        tem_libs = rodar([py, '-c', 'import nvidia.cublas, nvidia.cudnn']).returncode == 0
        add('Bibliotecas CUDA do Whisper', 'ok' if tem_libs else 'aviso', 'cuBLAS/cuDNN instaladas' if tem_libs else 'não instaladas: o Whisper vai rodar na CPU (mais lento)',
            '' if tem_libs else 'python instalar.py pacotes --gpu')
    else:
        add('Placa NVIDIA', 'info', 'não encontrada: transcrição na CPU' + (' (Mac: normal)' if SO == 'Darwin' else ''), 'use whisper_modelo_analise=small para ficar mais rápido')
    # ffmpeg
    ff, fp = achar_bin('ffmpeg'), achar_bin('ffprobe')
    if ff and fp:
        ver = rodar([ff, '-version']).stdout.split('\n')[0][:60]
        filtros = rodar([ff, '-hide_banner', '-filters']).stdout
        precisa = ['drawtext', 'ass', 'loudnorm', 'boxblur', 'xstack', 'silencedetect']
        faltam = [f for f in precisa if f' {f} ' not in filtros]
        add('ffmpeg', 'ok' if not faltam else 'falta', f'{ver} ({ff})' + (f' — sem os filtros: {", ".join(faltam)}' if faltam else ''),
            '' if not faltam else 'Instale um ffmpeg completo: python instalar.py ffmpeg --estatico --executar')
        encs = []
        for nome in ('h264_nvenc', 'h264_videotoolbox', 'h264_qsv', 'h264_amf'):
            if rodar([ff, '-v', 'error', '-f', 'lavfi', '-i', 'color=s=256x256:d=0.2', '-c:v', nome, '-f', 'null', '-']).returncode == 0: encs.append(nome)
        add('Codificador de vídeo', 'ok', ', '.join(encs) + ' (placa de vídeo)' if encs else 'libx264 (CPU; funciona, mais lento)', '')
    else:
        add('ffmpeg', 'falta', 'ffmpeg/ffprobe não encontrados', 'python instalar.py ffmpeg  (mostra o comando; depois --executar)')
    # yt-dlp precisa de runtime JS
    js = shutil.which('deno') or shutil.which('node') or next((c for c in glob.glob(os.path.join(AQUI, 'bin', 'deno*'))), None)
    add('Runtime JavaScript (yt-dlp)', 'ok' if js else 'aviso', js or 'nem Deno nem Node: dados do YouTube podem falhar',
        '' if js else 'python instalar.py deno  (mostra o comando; depois --executar)')
    # fontes
    fontes = [os.path.join(AQUI, 'fontes', f) for f in ('Anton-Regular.ttf', 'ArchivoBlack-Regular.ttf')]
    add('Fontes (capa e legenda)', 'ok' if all(map(os.path.exists, fontes)) else 'falta', 'Anton e Archivo Black', '' if all(map(os.path.exists, fontes)) else 'python instalar.py atualizar')
    # modelo do Whisper
    c = cfg_ler(); modelo = c.get('whisper_modelo_analise', 'turbo')
    cache = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
    tem_modelo = bool(glob.glob(os.path.join(cache, f'models--*faster-whisper-*{modelo}*'))) or bool(glob.glob(os.path.join(cache, f'models--*{modelo}*')))
    add(f'Modelo do Whisper ({modelo})', 'ok' if tem_modelo else 'aviso', 'baixado' if tem_modelo else 'ainda não baixado (baixa sozinho na 1ª transcrição)',
        '' if tem_modelo else f'python instalar.py modelo {modelo}')
    # LLM opcional
    llm = c.get('llm') or {}
    if llm.get('ativado'):
        url = (llm.get('base_url') or 'http://127.0.0.1:31415/v1').rstrip('/') + '/models'
        k = os.environ.get(llm.get('chave_env') or 'CORTES_LLM_KEY') or ler_env(llm.get('chave_env') or 'CORTES_LLM_KEY')
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Bearer {k}'} if k else {})
            urllib.request.urlopen(req, timeout=15).read(); add('API de LLM (triagem)', 'ok', url.rsplit('/models', 1)[0], '')
        except Exception as e:
            add('API de LLM (triagem)', 'aviso', f'{url}: {str(e)[:80]}', 'confira llm.base_url, a chave (llm.chave_env) e se o serviço está aberto')
    else:
        add('API de LLM (triagem)', 'info', 'desligada (opcional)', 'python instalar.py config llm.ativado=true llm.base_url=... llm.modelos=[...]')
    # disco
    alvo = COFRE or os.path.expanduser('~')
    livre = shutil.disk_usage(alvo).free / 1e9
    add('Espaço em disco', 'ok' if livre > 30 else 'aviso', f'{livre:.0f} GB livres em {alvo}', '' if livre > 30 else 'cada episódio de 2–3 h ocupa ~5–15 GB com os cortes')
    if saida_json:
        print(json.dumps([dict(item=a, status=b, detalhe=c_, resolver=d) for a, b, c_, d in itens], ensure_ascii=False, indent=1)); return 0
    simb = {'ok': 'OK   ', 'falta': 'FALTA', 'aviso': 'AVISO', 'info': 'info '}
    for a, b, c_, d in itens: p(f'[{simb[b]}] {a}: {c_}' + (f'\n         → {d}' if d and b != 'ok' else ''))
    faltas = sum(b == 'falta' for _, b, _, _ in itens)
    p(f'\n{faltas} itens faltando.' if faltas else '\nTudo o que é obrigatório está instalado.')
    return 1 if faltas else 0

def ler_env(nome):
    f = os.path.join(AQUI, '.env')
    if os.path.exists(f):
        for l in open(f, encoding='utf-8'):
            if l.strip().startswith(nome + '='): return l.split('=', 1)[1].strip().strip('"\'')
    return ''

# ------------------------------------------------------------------ criar o cofre
def criar_cofre(pasta):
    if not RAIZ_REPO: p('Rode criar-cofre a partir do repositório baixado (pasta com modelo_cofre/ e sistema/).'); return 1
    pasta = os.path.abspath(os.path.expanduser(pasta)); os.makedirs(pasta, exist_ok=True)
    novos = 0
    for raiz, dirs, arqs in os.walk(os.path.join(RAIZ_REPO, 'modelo_cofre')):   # modelo: nunca sobrescreve notas que já existem
        rel = os.path.relpath(raiz, os.path.join(RAIZ_REPO, 'modelo_cofre')); dest = os.path.join(pasta, rel); os.makedirs(dest, exist_ok=True)
        for a in arqs:
            d = os.path.join(dest, a)
            if not os.path.exists(d): shutil.copy2(os.path.join(raiz, a), d); novos += 1
    sis = os.path.join(pasta, '_sistema')
    n = copiar_sistema(os.path.join(RAIZ_REPO, 'sistema'), sis)
    for extra in ('requirements.txt', 'requirements-gpu-nvidia.txt', 'VERSAO', 'LICENSE', 'NOTICE.md'):
        if os.path.exists(os.path.join(RAIZ_REPO, extra)): shutil.copy2(os.path.join(RAIZ_REPO, extra), os.path.join(sis, extra))
    if not os.path.exists(cfg_caminho(sis)): cfg_gravar({'criado_em': datetime.date.today().isoformat()}, sis)
    ponteiro_gravar(pasta, sys.executable)
    p(f'Cofre pronto em {pasta}: {novos} arquivos do modelo, {n} scripts em _sistema.')
    p(f'Próximo passo: python "{os.path.join(sis, "instalar.py")}" pacotes' + (' --gpu' if shutil.which('nvidia-smi') else ''))
    return 0

def copiar_sistema(origem, destino, backup=None):
    """Copia os scripts para o cofre. Arquivos desta máquina (config.json, .env…) e pastas locais nunca são substituídos."""
    os.makedirs(destino, exist_ok=True); n = 0
    for raiz, dirs, arqs in os.walk(origem):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'bin', '_logs') and not d.startswith('_backup')]
        rel = os.path.relpath(raiz, origem); dest = os.path.join(destino, rel); os.makedirs(dest, exist_ok=True)
        for a in arqs:
            if a in LOCAIS or a.endswith('.pyc'): continue
            d = os.path.join(dest, a)
            if backup and os.path.exists(d):
                b = os.path.join(backup, rel, a); os.makedirs(os.path.dirname(b), exist_ok=True); shutil.copy2(d, b)
            shutil.copy2(os.path.join(raiz, a), d); n += 1
    return n

# ------------------------------------------------------------------ pacotes Python (ambiente do cofre)
def pacotes(gpu=False):
    if sys.version_info < PYMIN: p(f'Precisa do Python {PYMIN[0]}.{PYMIN[1]}+ para criar o ambiente (este é {sys.version.split()[0]}).'); return 1
    venv = os.path.join(AQUI, '.venv'); py = py_venv()
    if not os.path.exists(py):
        p('criando o ambiente Python em', venv)
        r = rodar([sys.executable, '-m', 'venv', venv])
        if r.returncode:
            p('Não consegui criar o ambiente:', r.stderr[-400:])
            if SO == 'Linux': p('No Debian/Ubuntu: sudo apt install python3-venv  — depois rode de novo.')
            return 1
    req = next((f for f in (os.path.join(AQUI, 'requirements.txt'), os.path.join(os.path.dirname(AQUI), 'requirements.txt')) if os.path.exists(f)), None)
    if not req: p('requirements.txt não encontrado (rode atualizar).'); return 1
    arqs = [req]
    if gpu:
        if SO == 'Darwin': p('Mac não usa CUDA: ignorando --gpu (o Whisper roda na CPU).')
        else: arqs.append(os.path.join(os.path.dirname(req), 'requirements-gpu-nvidia.txt'))
    rodar([py, '-m', 'pip', 'install', '--upgrade', 'pip'])
    for a in arqs:
        p('instalando', os.path.basename(a), '(pode levar alguns minutos)…')
        r = subprocess.run([py, '-m', 'pip', 'install', '-r', a])
        if r.returncode: p('ERRO ao instalar', os.path.basename(a)); return 1
    cfg_gravar({'python': py})
    if COFRE: ponteiro_gravar(COFRE, py)
    p('Pacotes instalados. Python do cofre:', py); return 0

# ------------------------------------------------------------------ ffmpeg e Deno
def _extrair_binarios(arquivo, nomes, destino):
    os.makedirs(destino, exist_ok=True); achados = []
    if arquivo.endswith('.zip'):
        with zipfile.ZipFile(arquivo) as z:
            for m in z.namelist():
                base = os.path.basename(m)
                if base in nomes:
                    with z.open(m) as o, open(os.path.join(destino, base), 'wb') as f: shutil.copyfileobj(o, f)
                    achados.append(base)
    else:
        with tarfile.open(arquivo) as t:
            for m in t.getmembers():
                base = os.path.basename(m.name)
                if base in nomes and m.isfile():
                    with t.extractfile(m) as o, open(os.path.join(destino, base), 'wb') as f: shutil.copyfileobj(o, f)
                    achados.append(base)
    for b in achados:
        if SO != 'Windows': os.chmod(os.path.join(destino, b), 0o755)
    return achados

def ffmpeg(executar=False, estatico=False):
    bin_ = os.path.join(AQUI, 'bin')
    if SO == 'Windows' and shutil.which('winget') and not estatico:
        cmd = ['winget', 'install', '--id', 'Gyan.FFmpeg', '-e', '--accept-source-agreements', '--accept-package-agreements']
    elif SO == 'Darwin' and not estatico:
        if not shutil.which('brew'): p('Instale o Homebrew (https://brew.sh) e rode de novo, ou instale o ffmpeg por conta própria.'); return 1
        cmd = ['brew', 'install', 'ffmpeg']
    else:   # Linux (padrão: binário estático, sem sudo) ou --estatico
        url = {'Windows': 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
               'Linux': f'https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-{arq_bin()}-static.tar.xz'}.get(SO)
        if not url: p('Sem binário estático para este sistema; use o gerenciador de pacotes.'); return 1
        p(f'Plano: baixar o ffmpeg estático de {url} para {bin_} (não precisa de administrador).')
        if not executar: p('Rode de novo com --executar para fazer.'); return 0
        arq = baixar(url, os.path.join(tempfile.gettempdir(), os.path.basename(url)))
        nomes = ('ffmpeg.exe', 'ffprobe.exe') if SO == 'Windows' else ('ffmpeg', 'ffprobe')
        ok = _extrair_binarios(arq, nomes, bin_); os.remove(arq)
        if len(ok) < 2: p('Não achei ffmpeg e ffprobe no pacote baixado.'); return 1
        cfg_gravar({'ffmpeg_dir': bin_}); p('ffmpeg instalado em', bin_); return 0
    p('Plano:', ' '.join(cmd))
    if not executar: p('Rode de novo com --executar para fazer.'); return 0
    r = subprocess.run(cmd); p('Feito. Rode "verificar" de novo (no Windows, abra um terminal novo se o ffmpeg não aparecer).' if r.returncode == 0 else 'Falhou.')
    return r.returncode

def deno(executar=False):
    if SO == 'Windows' and shutil.which('winget'): cmd = ['winget', 'install', '--id', 'DenoLand.Deno', '-e', '--accept-source-agreements', '--accept-package-agreements']
    elif SO == 'Darwin' and shutil.which('brew'): cmd = ['brew', 'install', 'deno']
    else:
        alvo = {('Linux', 'amd64'): 'x86_64-unknown-linux-gnu', ('Linux', 'arm64'): 'aarch64-unknown-linux-gnu',
                ('Windows', 'amd64'): 'x86_64-pc-windows-msvc', ('Darwin', 'arm64'): 'aarch64-apple-darwin', ('Darwin', 'amd64'): 'x86_64-apple-darwin'}.get((SO, arq_bin()))
        url = f'https://github.com/denoland/deno/releases/latest/download/deno-{alvo}.zip'
        p(f'Plano: baixar o Deno de {url} para {os.path.join(AQUI, "bin")}.')
        if not executar: p('Rode de novo com --executar para fazer.'); return 0
        arq = baixar(url, os.path.join(tempfile.gettempdir(), 'deno.zip'))
        ok = _extrair_binarios(arq, ('deno.exe',) if SO == 'Windows' else ('deno',), os.path.join(AQUI, 'bin')); os.remove(arq)
        p('Deno instalado.' if ok else 'Falhou.'); return 0 if ok else 1
    p('Plano:', ' '.join(cmd))
    if not executar: p('Rode de novo com --executar para fazer.'); return 0
    return subprocess.run(cmd).returncode

# ------------------------------------------------------------------ modelo do Whisper
def modelo(nome=None):
    nome = nome or cfg_ler().get('whisper_modelo_analise', 'turbo'); py = py_do_sistema()
    p(f'baixando o modelo "{nome}" do Whisper (uma vez só)…')
    r = subprocess.run([py, '-c', f'from faster_whisper import download_model; print(download_model({nome!r}))'])
    return r.returncode

# ------------------------------------------------------------------ autoteste
def autoteste(sem_whisper=False):
    try:
        import numpy, openpyxl   # noqa: F401  (precisa do ambiente do cofre)
    except ImportError:
        py = py_do_sistema()
        if os.path.abspath(py) != os.path.abspath(sys.executable):
            return subprocess.run([py, os.path.abspath(__file__), 'autoteste'] + (['--sem-whisper'] if sem_whisper else [])).returncode
        p('Os pacotes Python não estão instalados: rode "pacotes" antes.'); return 1
    sys.path.insert(0, AQUI)
    import comum, finalizar, legenda, visual, editar
    t = tempfile.mkdtemp(prefix='autoteste_cortes_'); res = []
    def passo(nome, fn):
        t0 = time.time()
        try: det = fn(); res.append((nome, 'OK', det, time.time() - t0))
        except Exception as e: res.append((nome, 'FALHOU', str(e)[:300], time.time() - t0))
    src, logo, v_src = os.path.join(t, 'teste.mp4'), os.path.join(t, 'logo.png'), os.path.join(t, 'vertical.mp4')
    def sintetico():
        r = comum.sp([comum.FF, '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=1920x1080:r=30:d=12', '-f', 'lavfi', '-i', 'sine=frequency=440:d=12',
                      '-shortest', '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', src])
        if r.returncode: raise RuntimeError(r.stderr[-300:])
        comum.sp([comum.FF, '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=300x300', '-frames:v', '1', logo])
        return f'{comum.duracao(src):.1f} s em 1920x1080'
    passo('vídeo de teste (ffmpeg)', sintetico)
    passo('codificador', lambda: (comum.encoder(), comum._ENC['nome'])[1])
    def longo():
        d = os.path.join(t, 'longo.mp4')
        if not finalizar.montar(src, d, 1920, 1080, '30', None, None, [{'arquivo': logo, 'largura': 150, 'x': 'W-w-30', 'y': '30', 'opacidade': 0.85}]):
            raise RuntimeError('montar() falhou (veja o log acima)')
        return f'16:9 com marca d\'água e -14 LUFS: {comum.duracao(d):.1f} s'
    passo('finalização 16:9', longo)
    def capa():
        vis = dict(visual.PADRAO, capa_logo=logo, pasta=None)
        d = os.path.join(t, 'capa.jpg'); finalizar.capa(src, 'TESTE DA CAPA FUNCIONANDO', d, vis)
        if not os.path.exists(d): raise RuntimeError('capa não gerada')
        return 'capa 1280x720 com a fonte Anton'
    passo('capa', capa)
    def short():
        r = comum.sp([comum.FF, '-y', '-v', 'error', '-i', src, '-filter_complex', editar.vf_vert(1.5), '-map', '[v]', '-map', '0:a',
                      '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', v_src])
        if r.returncode: raise RuntimeError(r.stderr[-300:])
        trab = os.path.join(t, 'short'); os.makedirs(trab)
        nome = comum.preparar_fonte_legenda(dict(visual.PADRAO), trab)
        palavras = [[0.5, 0.9, 'TESTE'], [0.9, 1.4, 'DA'], [1.4, 2.0, 'LEGENDA'], [2.2, 2.8, 'FUNCIONANDO']]
        legenda.gerar_ass(palavras, os.path.join(trab, 'leg.ass'), nome)
        d = os.path.join(t, 'short.mp4')
        if not finalizar.montar(v_src, d, 1080, 1920, '30', None, None, [], ass='leg.ass', cwd=trab): raise RuntimeError('montar() com legenda falhou')
        comum.sp([comum.FF, '-y', '-v', 'error', '-ss', '1.6', '-i', d, '-frames:v', '1', os.path.join(t, 'short_quadro.jpg')])
        return f'Short 9:16 com legenda ({nome}): {comum.duracao(d):.1f} s'
    passo('Short com legenda (libass)', short)
    if not sem_whisper:
        def whisper():
            import transcrever
            m = transcrever.modelo('tiny')
            list(m.transcribe(numpy.zeros(32000, numpy.float32), language=transcrever.IDIOMA)[0])
            return 'CPU' if transcrever._SO_CPU else 'GPU (CUDA)'
        passo('Whisper (modelo tiny)', whisper)
    for nome, st, det, dt in res: p(f'[{st:6}] {nome}: {det}  ({dt:.1f} s)')
    p(f'\nArquivos do teste (para olhar a capa e o quadro do Short): {t}')
    return 1 if any(st != 'OK' for _, st, _, _ in res) else 0

# ------------------------------------------------------------------ atualizar a partir do GitHub
def atualizar(ref='main'):
    if not NO_COFRE: p('Rode "atualizar" a partir do _sistema do cofre.'); return 1
    url = f'https://codeload.github.com/{REPO}/zip/refs/heads/{ref}'
    arq = baixar(url, os.path.join(tempfile.gettempdir(), 'cortes-de-video.zip'))
    tmp = tempfile.mkdtemp(prefix='cortes_atualizar_')
    with zipfile.ZipFile(arq) as z: z.extractall(tmp)
    os.remove(arq)
    raiz = next(os.path.join(tmp, d) for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d, 'sistema')))
    antes = open(os.path.join(AQUI, 'VERSAO'), encoding='utf-8').read().strip() if os.path.exists(os.path.join(AQUI, 'VERSAO')) else '?'
    req_antes = open(os.path.join(AQUI, 'requirements.txt'), encoding='utf-8').read() if os.path.exists(os.path.join(AQUI, 'requirements.txt')) else ''
    backup = os.path.join(AQUI, '_backup_' + datetime.datetime.now().strftime('%Y%m%d_%H%M'))
    n = copiar_sistema(os.path.join(raiz, 'sistema'), AQUI, backup)
    for extra in ('requirements.txt', 'requirements-gpu-nvidia.txt', 'VERSAO', 'LICENSE', 'NOTICE.md'):
        f = os.path.join(raiz, extra)
        if os.path.exists(f):
            if os.path.exists(os.path.join(AQUI, extra)):
                os.makedirs(backup, exist_ok=True); shutil.copy2(os.path.join(AQUI, extra), os.path.join(backup, extra))
            shutil.copy2(f, os.path.join(AQUI, extra))
    # notas novas do modelo entram só se ainda não existirem (as suas Regras nunca são substituídas)
    novas = 0
    for r_, ds, fs in os.walk(os.path.join(raiz, 'modelo_cofre')):
        rel = os.path.relpath(r_, os.path.join(raiz, 'modelo_cofre'))
        for a in fs:
            d = os.path.join(COFRE, rel, a)
            if not os.path.exists(d): os.makedirs(os.path.dirname(d), exist_ok=True); shutil.copy2(os.path.join(r_, a), d); novas += 1
    depois = open(os.path.join(AQUI, 'VERSAO'), encoding='utf-8').read().strip() if os.path.exists(os.path.join(AQUI, 'VERSAO')) else '?'
    shutil.rmtree(tmp, ignore_errors=True)
    p(f'Atualizado: versão {antes} → {depois}; {n} arquivos; {novas} notas novas. Versão anterior guardada em {backup}.')
    if req_antes != open(os.path.join(AQUI, 'requirements.txt'), encoding='utf-8').read():
        p('Os pacotes mudaram: rode "python instalar.py pacotes" (com --gpu se usar placa NVIDIA).')
    p('A skill do Claude (SKILL.md) não se atualiza sozinha: veja no README se ela mudou e envie a nova versão.')
    return 0

# ------------------------------------------------------------------ entrada
def main(a):
    if not a: p(__doc__ or open(__file__, encoding='utf-8').read().split('import os')[0]); return 0
    cmd, resto = a[0], a[1:]
    flag = lambda f: f in resto
    args = [x for x in resto if not x.startswith('--')]
    if cmd == 'verificar': return verificar(flag('--json'))
    if cmd == 'criar-cofre': return criar_cofre(args[0]) if args else (p('Informe a pasta do cofre.'), 1)[1]
    if cmd == 'pacotes': return pacotes(flag('--gpu'))
    if cmd == 'ffmpeg': return ffmpeg(flag('--executar'), flag('--estatico'))
    if cmd == 'deno': return deno(flag('--executar'))
    if cmd == 'modelo': return modelo(args[0] if args else None)
    if cmd == 'config':
        mud = {k: valor(v) for k, v in (x.split('=', 1) for x in args if '=' in x)}
        for k, v in list(mud.items()):   # listas também em texto simples (o PowerShell 5.1 come as aspas do JSON): a,b,c
            if k.endswith('modelos') and isinstance(v, str): mud[k] = [m.strip() for m in v.split(',') if m.strip()]
        c = cfg_gravar(mud); p('config.json desta máquina:', json.dumps(c, ensure_ascii=False)); return 0
    if cmd == 'autoteste': return autoteste(flag('--sem-whisper'))
    if cmd == 'atualizar': return atualizar(resto[resto.index('--ref') + 1] if '--ref' in resto else 'main')
    p('Comando desconhecido:', cmd); return 1

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        try: sys.stdout.reconfigure(encoding='utf-8')
        except Exception: pass
    sys.exit(main(sys.argv[1:]))
