# Transcrição local com faster-whisper (palavras com tempo).
# Uso: python transcrever.py "<pasta do episódio>"   -> grava _analise/transcricao.json e transcricao.txt
# Dispositivo (config "whisper_dispositivo"): "auto" (padrão) tenta a GPU NVIDIA e cai para a CPU; "cuda" ou "cpu" forçam.
# GPU NVIDIA precisa das bibliotecas cuBLAS/cuDNN 9 para CUDA 12:
#   Windows: pacotes pip nvidia-cublas-cu12 e nvidia-cudnn-cu12 (o instalar.py instala) ou a pasta CONFIG["nvidia_dlls"];
#   Linux:   pacotes pip nvidia-cublas-cu12 e nvidia-cudnn-cu12 (carregados aqui, sem mexer no LD_LIBRARY_PATH);
#   macOS:   não há CUDA; roda na CPU (int8), mais devagar — o instalar.py escolhe um modelo menor.
# Idioma da fala: CONFIG["idioma"] (padrão "pt").
import os, sys, glob, json, wave, tempfile, time
import numpy as np
from comum import FF, CONFIG, sp, hms, video_de, log

IDIOMA = CONFIG.get('idioma') or 'pt'
DISPOSITIVO = (CONFIG.get('whisper_dispositivo') or 'auto').lower()

def _bibliotecas_nvidia():
    if os.name == 'nt':
        pastas = [os.path.expandvars(CONFIG.get('nvidia_dlls') or r'%LOCALAPPDATA%\cortes_nvidia')]
        try:   # pacotes pip nvidia-cublas-cu12 / nvidia-cudnn-cu12 (requirements-gpu-nvidia.txt): DLLs em nvidia/<pacote>/bin
            import nvidia.cublas, nvidia.cudnn
            pastas += [os.path.join(list(p.__path__)[0], 'bin') for p in (nvidia.cublas, nvidia.cudnn)]
        except ImportError: pass
        for d in pastas:
            if os.path.isdir(d):
                os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
                try: os.add_dll_directory(d)
                except (AttributeError, OSError): pass
    elif sys.platform.startswith('linux'):
        import ctypes
        try:
            import nvidia.cublas.lib, nvidia.cudnn.lib
            for pac in (nvidia.cublas.lib, nvidia.cudnn.lib):
                for so in sorted(glob.glob(os.path.join(list(pac.__path__)[0], 'lib*.so*'))):
                    try: ctypes.CDLL(so, mode=ctypes.RTLD_GLOBAL)
                    except OSError: pass
        except ImportError: pass
if DISPOSITIVO != 'cpu' and sys.platform != 'darwin': _bibliotecas_nvidia()

_modelos = {}
_SO_CPU = False

def _cpu(nome):
    from faster_whisper import WhisperModel
    log('whisper', nome, 'na CPU')
    from comum import threads_limite   # na CPU, respeita o limite de threads (temperatura)
    return WhisperModel(nome, device='cpu', compute_type='int8', cpu_threads=threads_limite() if CONFIG.get('cpu_afinidade', 'auto') else max(1, (os.cpu_count() or 4) - 2))

def modelo(nome):
    global _SO_CPU
    if nome in _modelos: return _modelos[nome]
    if _SO_CPU or DISPOSITIVO == 'cpu' or sys.platform == 'darwin': _SO_CPU = True; m = _cpu(nome); _modelos[nome] = m; return m
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel(nome, device='cuda', compute_type=CONFIG.get('whisper_tipo_gpu', 'float16'))
        list(m.transcribe(np.zeros(32000, np.float32), language=IDIOMA)[0])   # consome o gerador: testa cuBLAS/cuDNN de verdade
        log('whisper', nome, 'na GPU')
    except Exception as e:
        log('GPU indisponível para o Whisper (' + str(e)[:90] + '); usando a CPU')
        _SO_CPU = True; m = _cpu(nome)
    _modelos[nome] = m
    return m

def audio(arquivo, ini=None, fim=None):
    """Decodifica com ffmpeg (a versão do PyAV instalada não é compatível com o faster-whisper)."""
    wav = os.path.join(tempfile.gettempdir(), f'claude_cortes_audio_{os.getpid()}.wav')
    cmd = [FF, '-y', '-v', 'error']
    if ini is not None: cmd += ['-ss', f'{ini:.3f}']
    cmd += ['-i', arquivo]
    if fim is not None: cmd += ['-t', f'{fim-(ini or 0):.3f}']
    cmd += ['-vn', '-ac', '1', '-ar', '16000', wav]
    r = sp(cmd)
    if r.returncode: raise RuntimeError(r.stderr[-500:])
    w = wave.open(wav); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; w.close()
    return a

def palavras(arquivo, nome_modelo, ini=None, fim=None):
    global _SO_CPU
    a = audio(arquivo, ini, fim)
    try:
        segs = list(modelo(nome_modelo).transcribe(a, language=IDIOMA, word_timestamps=True, vad_filter=True)[0])
    except Exception as e:   # erro de GPU que só aparece na transcrição real
        if not any(k in str(e).lower() for k in ('cublas', 'cudnn', 'cuda')): raise
        log('GPU falhou na transcrição (' + str(e)[:90] + '); usando a CPU')
        _SO_CPU = True; _modelos.clear()
        segs = list(modelo(nome_modelo).transcribe(a, language=IDIOMA, word_timestamps=True, vad_filter=True)[0])
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append([round(w.start + (ini or 0), 2), round(w.end + (ini or 0), 2), w.word.strip()])
    return out

def transcrever_episodio(pasta):
    v = video_de(pasta); dest = os.path.join(pasta, '_analise'); os.makedirs(dest, exist_ok=True)
    nome = CONFIG.get('whisper_modelo_analise', 'small'); t0 = time.time()
    log('transcrevendo', os.path.basename(pasta), 'com', nome)
    ws = palavras(v, nome)
    json.dump(ws, open(os.path.join(dest, 'transcricao.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    linhas, atual, t_ini = [], [], None
    for a, b, t in ws:
        if t_ini is None: t_ini = a
        atual.append(t)
        if a - t_ini >= 20: linhas.append(f'[{hms(t_ini)}] ' + ' '.join(atual)); atual, t_ini = [], None
    if atual: linhas.append(f'[{hms(t_ini)}] ' + ' '.join(atual))
    open(os.path.join(dest, 'transcricao.txt'), 'w', encoding='utf-8').write('\n'.join(linhas))
    log('transcrição pronta:', len(ws), 'palavras em', f'{time.time() - t0:.0f} s')

if __name__ == '__main__':
    transcrever_episodio(sys.argv[1])
