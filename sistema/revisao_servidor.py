# Servidor local da revisão visual dos cortes (desde a 1.2.0). Só a biblioteca padrão do Python.
# Escuta apenas em 127.0.0.1; entrega a página, a mídia do episódio (com Range, para o vídeo andar rápido) e grava a revisão.
# Uso normal: python revisar_cortes.py "<pasta do episódio>" [--fase longos|curtos]
import json, mimetypes, os, re, threading, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import revisao_cortes as RC

PAGINA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pagina', 'revisao_cortes.html')
LIMITE_FAIXA = 8 * 1024 * 1024      # faixa aberta ("bytes=X-") é entregue em pedaços de 8 MB: buscas no vídeo ficam rápidas
LIMITE_CORPO = 5 * 1024 * 1024
TRAVA = threading.Lock()


def _dentro(pasta, rel):
    """Caminho de um arquivo dentro da pasta do episódio; None se tentar sair dela."""
    alvo = os.path.realpath(os.path.join(pasta, rel))
    base = os.path.realpath(pasta)
    return alvo if os.path.commonpath([alvo, base]) == base else None


def criar_servidor(pasta, info, porta=8766):
    pasta = os.path.abspath(pasta)

    class H(BaseHTTPRequestHandler):
        server_version = 'CortesRevisao/1'

        def log_message(self, *a): pass

        def end_headers(self):
            self.send_header('Content-Security-Policy', "frame-ancestors 'self'")
            super().end_headers()

        def _host_ok(self):
            h = (self.headers.get('Host') or '').lower()
            return h in (f'127.0.0.1:{self.server.server_address[1]}', f'localhost:{self.server.server_address[1]}')

        def _origem_ok(self):
            o = self.headers.get('Origin') or self.headers.get('Referer') or ''
            p = self.server.server_address[1]
            return any(o.startswith(f'http://{h}:{p}') for h in ('127.0.0.1', 'localhost'))

        def _json(self, dados, status=200):
            corpo = json.dumps(dados, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(corpo)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(corpo)

        def _arquivo(self, caminho, cache=False):
            if not caminho or not os.path.isfile(caminho): return self._json({'erro': 'não encontrado'}, 404)
            tipo = ('text/html; charset=utf-8' if caminho.endswith('.html') else
                    mimetypes.guess_type(caminho)[0] or 'application/octet-stream')
            tam = os.path.getsize(caminho); ini, fim, status = 0, tam - 1, 200
            m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range') or '')
            if m:
                if m.group(1):
                    ini = int(m.group(1)); fim = int(m.group(2)) if m.group(2) else min(tam - 1, ini + LIMITE_FAIXA - 1)
                elif m.group(2): ini = max(0, tam - int(m.group(2)))
                fim = min(fim, tam - 1)
                if ini > fim:
                    self.send_response(416); self.send_header('Content-Range', f'bytes */{tam}'); self.end_headers(); return
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', tipo); self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(fim - ini + 1))
            if status == 206: self.send_header('Content-Range', f'bytes {ini}-{fim}/{tam}')
            self.send_header('Cache-Control', 'max-age=60' if cache else 'no-store')
            self.end_headers()
            try:
                with open(caminho, 'rb') as f:
                    f.seek(ini); resta = fim - ini + 1
                    while resta > 0:
                        b = f.read(min(1 << 20, resta))
                        if not b: break
                        self.wfile.write(b); resta -= len(b)
            except (ConnectionError, BrokenPipeError):
                pass

        def do_GET(self):
            if not self._host_ok(): return self._json({'erro': 'acesso negado'}, 403)
            url = urllib.parse.urlparse(self.path)
            if url.path in ('/', '/index.html'): return self._arquivo(PAGINA)
            if url.path == '/favicon.ico': self.send_response(204); self.end_headers(); return
            if url.path == '/api/episodio':
                return self._json(RC.dados(pasta, info['fase'], info['video'], info['dur'], info['minis']))
            if url.path.startswith('/midia/'):
                return self._arquivo(_dentro(pasta, urllib.parse.unquote(url.path[7:])), cache=True)
            return self._json({'erro': 'não encontrado'}, 404)

        def do_POST(self):
            n = int(self.headers.get('Content-Length') or 0)
            if not self._host_ok() or not self._origem_ok() or n > LIMITE_CORPO:
                if n <= LIMITE_CORPO: self.rfile.read(n)
                return self._json({'erro': 'acesso negado'}, 403)
            url = urllib.parse.urlparse(self.path)
            try:
                corpo = json.loads(self.rfile.read(n).decode('utf-8') or '{}')
                if url.path in ('/api/revisao', '/api/enviar_revisao'):
                    with TRAVA:
                        r = RC.salvar_revisao(pasta, info['fase'], corpo, enviar=url.path.endswith('enviar_revisao'))
                    return self._json({'ok': True, 'atualizado_em': r['atualizado_em'], 'estado': r['estado']})
                if url.path == '/api/aplicar_revisao':
                    import aplicar_revisao
                    with TRAVA:
                        cod = aplicar_revisao.aplicar(pasta, gravar=True)
                    if cod: return self._json({'ok': False, 'erro': 'Não foi possível aplicar: confira se a análise e a revisão foram salvas.'}, 400)
                    return self._json({'ok': True})
            except (ValueError, KeyError, OSError) as e:
                return self._json({'ok': False, 'erro': str(e)}, 400)
            return self._json({'erro': 'não encontrado'}, 404)

    for p in range(porta, porta + 10):   # porta ocupada: tenta as seguintes
        try: return ThreadingHTTPServer(('127.0.0.1', p), H)
        except OSError: continue
    raise OSError(f'nenhuma porta livre entre {porta} e {porta + 9}')


def revisar_cortes(pasta, fase=None, porta=8766, abrir=True, ffmpeg='ffmpeg', ffprobe='ffprobe'):
    """Revisão dos cortes de um episódio (fase "longos" ou "curtos"; sem fase, decide pelo cortes.json)."""
    pasta = os.path.abspath(pasta)
    if not os.path.exists(os.path.join(pasta, '_analise', 'cortes.json')):
        raise FileNotFoundError('_analise/cortes.json não encontrado: a análise do episódio ainda não foi feita')
    video = RC.video_do_episodio(pasta)
    if not video: raise FileNotFoundError('vídeo do episódio não encontrado na pasta')
    dur = RC.duracao(video, ffprobe)
    _, lista = RC.cortes_do_episodio(pasta)
    fase = fase or RC.fase_padrao(lista)
    minis = RC.preparar_midia(pasta, video, dur, ffmpeg=ffmpeg)
    srv = criar_servidor(pasta, dict(fase=fase, video=video, dur=dur, minis=minis), porta)
    url = f'http://127.0.0.1:{srv.server_address[1]}/'
    print(f'Revisão dos cortes {fase} aberta em {url}  (feche esta janela para encerrar)', flush=True)
    if abrir: webbrowser.open(url)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: srv.server_close()
