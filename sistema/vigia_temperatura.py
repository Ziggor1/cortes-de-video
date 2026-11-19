# Vigia de temperatura: congela a fila de cortes (etapas e ffmpeg) quando a CPU esquenta demais e retoma quando esfria.
# Não encerra nada: os processos ficam parados e continuam de onde pararam.
# Instalação: "python instalar.py vigia" (Windows: tarefa agendada com administrador; Linux: serviço do usuário no systemd).
# Uso manual: python vigia_temperatura.py            -> vigia contínuo
#             python vigia_temperatura.py --teste    -> lê a temperatura 3 vezes e grava em _logs/temperatura.txt
# Limites (config): temp_pausa (85 °C), temp_volta (75 °C), temp_intervalo_s (10).
# Sensor:
#   Windows: LibreHardwareMonitor (_sistema/_ferramentas/LibreHardwareMonitor, servidor local 127.0.0.1:8085, "CPU Package"),
#            aberto pelo próprio vigia; reserva: zona térmica do ACPI (imprecisa; pode travar num valor).
#   Linux:   /sys/class/hwmon (coretemp, k10temp, zenpower) ou /sys/class/thermal.
#   macOS:   não suportado (a leitura exige sudo); o vigia avisa e sai. Os limites de carga da fila continuam valendo.
import os, sys, json, time, glob, re, signal, platform, datetime, subprocess, urllib.request
import xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(AQUI, '_logs', 'temperatura.txt')
SO = platform.system()
LHM = os.path.join(AQUI, '_ferramentas', 'LibreHardwareMonitor', 'LibreHardwareMonitor.exe')
LHM_URL = 'http://127.0.0.1:8085/data.json'
LHM_OPCOES = {'runWebServerMenuItem': 'true', 'listenerPort': '8085', 'listenerIp': '127.0.0.1', 'authenticationEnabled': 'false',
              'startMinMenuItem': 'true', 'minTrayMenuItem': 'true', 'minCloseMenuItem': 'true'}
SCRIPTS = {os.path.basename(p).lower() for p in glob.glob(os.path.join(AQUI, '*.py'))} - {'vigia_temperatura.py'}
SEM_JANELA = 0x08000000 if os.name == 'nt' else 0

def cfg():
    c = {}
    for n in ('config_padrao.json', 'config.json'):
        try: c.update(json.load(open(os.path.join(AQUI, n), encoding='utf-8')))
        except Exception: pass
    return c

def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.datetime.now():%d/%m %H:%M:%S} {msg}\n")

# ---------------------------------------------------------------- Windows: LibreHardwareMonitor
def temp_lhm():
    try: d = json.load(urllib.request.urlopen(LHM_URL, timeout=3))
    except Exception: return None
    achados = []
    def andar(n):
        txt, val = n.get('Text', ''), n.get('Value', '')
        if re.search(r'CPU Package|Core Max|Tctl|Tdie', txt) and '°C' in val:
            try: achados.append(float(val.replace('°C', '').replace(',', '.').strip()))
            except ValueError: pass
        for c in n.get('Children', []): andar(c)
    andar(d)
    return max(achados) if achados else None

def configurar_lhm():
    p = os.path.join(os.path.dirname(LHM), 'LibreHardwareMonitor.config')
    try: arv = ET.parse(p); raiz = arv.getroot()
    except Exception: raiz = ET.Element('configuration'); arv = ET.ElementTree(raiz)
    app = raiz.find('appSettings')
    if app is None: app = ET.SubElement(raiz, 'appSettings')
    for k, v in LHM_OPCOES.items():
        e = next((x for x in app.findall('add') if x.get('key') == k), None)
        if e is None: e = ET.SubElement(app, 'add', key=k)
        e.set('value', v)
    arv.write(p, encoding='utf-8', xml_declaration=True)

def garantir_lhm():
    if SO != 'Windows' or temp_lhm() is not None: return
    if not os.path.exists(LHM): log('LibreHardwareMonitor não encontrado em ' + LHM + ' (rode "instalar.py vigia")'); return
    subprocess.run(['taskkill', '/IM', 'LibreHardwareMonitor.exe', '/F'], capture_output=True, creationflags=SEM_JANELA)
    time.sleep(2); configurar_lhm()
    try: subprocess.Popen([LHM], cwd=os.path.dirname(LHM))
    except Exception as e: log(f'LibreHardwareMonitor não abriu: {e}'); return
    for _ in range(12):
        time.sleep(5)
        t = temp_lhm()
        if t is not None: log(f'LibreHardwareMonitor ativo: CPU {t:.0f} °C'); return
    log('LibreHardwareMonitor aberto, mas sem resposta em 127.0.0.1:8085')

PS = r"""
$t = @(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | % { [math]::Round($_.CurrentTemperature/10-273.15,1) })
$p = @(Get-CimInstance Win32_Process -Filter "Name='ffmpeg.exe' OR Name='python.exe' OR Name='pythonw.exe'" | % { @{pid=$_.ProcessId; nome=$_.Name; cmd=[string]$_.CommandLine} })
@{temps=$t; procs=$p} | ConvertTo-Json -Depth 3 -Compress
"""

# ---------------------------------------------------------------- Linux
def temp_linux():
    vals = []
    for d in glob.glob('/sys/class/hwmon/hwmon*'):
        try: nome = open(os.path.join(d, 'name')).read().strip()
        except OSError: continue
        if nome not in ('coretemp', 'k10temp', 'zenpower', 'cpu_thermal', 'acpitz'): continue
        for f in glob.glob(os.path.join(d, 'temp*_input')):
            try: vals.append(int(open(f).read()) / 1000)
            except (OSError, ValueError): pass
    if not vals:
        for f in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
            try: vals.append(int(open(f).read()) / 1000)
            except (OSError, ValueError): pass
    vals = [v for v in vals if 0 < v < 130]
    return max(vals) if vals else None

# ---------------------------------------------------------------- leitura e controle dos processos
def ler():
    """Devolve (temperatura, fonte, pids da fila)."""
    alvos = []
    if SO == 'Windows':
        r = subprocess.run(['powershell', '-NoProfile', '-Command', PS], capture_output=True, text=True, errors='replace', creationflags=SEM_JANELA)
        d = json.loads(r.stdout or '{}')
        procs = [(int(p['pid']), p['nome'].lower(), (p.get('cmd') or '').lower()) for p in d.get('procs') or []]
        t = temp_lhm(); fonte = 'LHM'
        if t is None:
            zonas = [float(x) for x in (d.get('temps') or []) if 0 < float(x) < 130]
            t = max(zonas) if zonas else None; fonte = 'zona'
    else:
        r = subprocess.run(['ps', '-eo', 'pid=,comm=,args='], capture_output=True, text=True, errors='replace')
        procs = []
        for linha in r.stdout.splitlines():
            partes = linha.strip().split(None, 2)
            if len(partes) == 3: procs.append((int(partes[0]), partes[1].lower(), partes[2].lower()))
        t = temp_linux(); fonte = 'sensor'
    for pid, nome, cmd in procs:
        if pid == os.getpid(): continue
        if nome.startswith('ffmpeg') or ('python' in nome and any(s in cmd for s in SCRIPTS)):
            alvos.append(pid)
    return t, fonte, alvos

def mudar(pids, pausar):
    ok = []
    for pid in pids:
        try:
            if os.name == 'nt':
                import ctypes
                ntdll = ctypes.WinDLL('ntdll'); k = ctypes.windll.kernel32
                h = k.OpenProcess(0x0800, False, pid)   # PROCESS_SUSPEND_RESUME
                if h:
                    if (ntdll.NtSuspendProcess if pausar else ntdll.NtResumeProcess)(h) == 0: ok.append(pid)
                    k.CloseHandle(h)
            else:
                os.kill(pid, signal.SIGSTOP if pausar else signal.SIGCONT); ok.append(pid)
        except Exception: pass
    return ok

def teste():
    garantir_lhm()
    for _ in range(3):
        t, fonte, alvos = ler(); log(f'TESTE temperatura={t} ({fonte}) processos da fila={alvos}'); time.sleep(3)

def vigiar():
    if SO == 'Darwin':
        log('macOS: leitura de temperatura não suportada (exige sudo); o vigia não roda. Os limites de carga da fila continuam valendo.')
        return 2
    pausados = set(); ultimo = 0; ultimo_lhm = 0; repet = 0; ult_t = None
    if os.name != 'nt': signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))   # parar o serviço retoma o que estava pausado
    log('vigia iniciado')
    try:
        while True:
            c = cfg(); alto, baixo = float(c.get('temp_pausa', 85)), float(c.get('temp_volta', 75))
            if time.time() - ultimo_lhm > 120:
                try: garantir_lhm()
                except Exception as e: log(f'erro no LibreHardwareMonitor: {e!r}')
                ultimo_lhm = time.time()
            try: t, fonte, alvos = ler()
            except Exception as e: log(f'erro na leitura: {e!r}'); time.sleep(30); continue
            if t is None: time.sleep(60); continue
            if fonte == 'zona' and pausados:   # zona térmica travada: não deixa a fila presa para sempre
                repet = repet + 1 if t == ult_t else 0
                if repet >= 30:
                    mudar(list(pausados), False); log(f'zona térmica travada em {t:.0f} °C -> RETOMADOS {sorted(pausados)}; instale o LibreHardwareMonitor')
                    pausados.clear(); repet = 0
            ult_t = t
            if time.time() - ultimo > 300:
                log(f'{t:.0f} °C ({fonte})' + (' - fila pausada' if pausados else '')); ultimo = time.time()
            if t >= alto or (pausados and t > baixo):
                novos = [p for p in alvos if p not in pausados]
                if novos:
                    pausados |= set(mudar(novos, True)); log(f'{t:.0f} °C ({fonte}, limite {alto:.0f}) -> PAUSADOS {novos}')
            elif pausados and t <= baixo:
                mudar(list(pausados), False); log(f'{t:.0f} °C ({fonte}, volta em {baixo:.0f}) -> RETOMADOS {sorted(pausados)}'); pausados.clear()
            time.sleep(float(c.get('temp_intervalo_s', 10)))
    finally:
        if pausados: mudar(list(pausados), False); log(f'vigia encerrado -> RETOMADOS {sorted(pausados)}')

if __name__ == '__main__':
    sys.exit(teste() if '--teste' in sys.argv else vigiar())
