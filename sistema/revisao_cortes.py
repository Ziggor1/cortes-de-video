"""Revisão visual dos cortes de um episódio, em duas fases (desde a 1.2.0).

Duas fases:
- ``longos``: o episódio inteiro, com os cortes longos propostos marcados e os trechos sem corte à vista.
  O usuário aprova, recusa, aumenta ou diminui cada longo e pode propor um corte num trecho sem corte.
- ``curtos``: depois dos longos aprovados, os cortes curtos propostos dentro de cada longo, para aprovar ou ajustar.

Lê ``_analise/cortes.json`` (formato do ``planilha.py`` da skill), ``_analise/transcricao.json`` ([[ini, fim, palavra]]),
``_analise/momentos.json`` (assuntos) e ``_analise/intensidade.csv`` (sinais). Grava ``_analise/revisao_cortes.json``.
Miniaturas a cada 30 s e forma de onda em ``_analise/revisao/``.
"""

import concurrent.futures
import csv
import datetime
import json
import os
import re
import subprocess

PASSO_MINI = 30
LONGO = ("corte longo", "corte médio")
CURTO = ("corte curto", "short/reels")


def _ler_json(caminho, padrao=None):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def secs(t):
    if isinstance(t, (int, float)):
        return float(t)
    partes = [float(x) for x in str(t).replace(",", ".").split(":")]
    s = 0.0
    for p in partes:
        s = s * 60 + p
    return s


def video_do_episodio(pasta):
    """Maior .mp4 na raiz do episódio (o vídeo original), ignorando arquivos que começam com '_'."""
    cands = [os.path.join(pasta, a) for a in os.listdir(pasta)
             if a.lower().endswith((".mp4", ".mkv", ".mov", ".webm")) and not a.startswith("_")]
    return max(cands, key=os.path.getsize) if cands else None


def duracao(arq, ffprobe="ffprobe"):
    try:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                           capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def tipo_do_corte(categoria):
    c = (categoria or "").strip().lower()
    if c in LONGO:
        return "longo"
    if c in CURTO:
        return "curto"
    if c.startswith("remover"):
        return "remover"
    if c.startswith("aten"):
        return "atencao"
    return "outro"


def pontos(c):
    return sum(int(c.get(k) or 0) for k in ("gancho", "autossuf", "emocao", "frase", "em_alta"))


def cortes_do_episodio(pasta):
    j = _ler_json(os.path.join(pasta, "_analise", "cortes.json"), {"cortes": []})
    lista = []
    for k, c in enumerate(j.get("cortes", []), 1):
        try:
            ini, fim = secs(c["inicio"]), secs(c["fim"])
        except (KeyError, ValueError):
            continue
        lista.append({"id": f"k{k}", "k": k, "categoria": c.get("categoria"), "tipo": tipo_do_corte(c.get("categoria")),
                      "ini": round(ini, 2), "fim": round(fim, 2), "tema": c.get("tema", ""), "nota": pontos(c),
                      "titulos": [c.get("titulo1", ""), c.get("titulo2", ""), c.get("titulo3", "")],
                      "capa": c.get("capa", ""), "primeira_frase": c.get("primeira_frase", ""), "obs": c.get("obs", ""),
                      "origem": c.get("origem")})
    longos = [c for c in lista if c["tipo"] == "longo"]
    for c in lista:   # corte curto: a que longo pertence (o que mais o cobre)
        if c["tipo"] == "curto" and not c.get("origem"):
            melhor = max(longos, key=lambda l: min(l["fim"], c["fim"]) - max(l["ini"], c["ini"]), default=None)
            if melhor and min(melhor["fim"], c["fim"]) - max(melhor["ini"], c["ini"]) > 0:
                c["origem"] = melhor["id"]
    return j.get("titulo") or os.path.basename(pasta), lista


def fase_padrao(cortes):
    return "curtos" if any(c["tipo"] == "curto" for c in cortes) else "longos"


def assuntos(pasta):
    m = _ler_json(os.path.join(pasta, "_analise", "momentos.json"), {}) or {}
    return [{"ini": a.get("inicio", 0), "fim": a.get("fim", 0), "chave": a.get("chave", [])[:4]} for a in m.get("assuntos", [])]


def sinais(pasta):
    caminho = os.path.join(pasta, "_analise", "intensidade.csv")
    out = []
    try:
        with open(caminho, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out.append([secs(r["inicio"]), float(r.get("intensidade") or 0)])
    except (OSError, ValueError, KeyError):
        pass
    return out


def preparar_midia(pasta, video, dur, ffmpeg="ffmpeg", aviso=print, trabalhadores=4):
    """Miniaturas a cada 30 s e forma de onda do episódio (uma vez; ficam em _analise/revisao)."""
    d = os.path.join(pasta, "_analise", "revisao", "mini")
    os.makedirs(d, exist_ok=True)
    tempos = [t for t in range(0, int(dur), PASSO_MINI)]
    faltam = [t for t in tempos if not os.path.exists(os.path.join(d, f"t{t:06d}.jpg"))]

    def um(t):
        subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", str(t + 2), "-i", video, "-frames:v", "1",
                        "-vf", "scale=192:-2", "-q:v", "5", os.path.join(d, f"t{t:06d}.jpg")], capture_output=True)

    if faltam:
        aviso(f"Gerando {len(faltam)} miniaturas do episódio (só na primeira vez)…")
        with concurrent.futures.ThreadPoolExecutor(trabalhadores) as ex:
            for i, _ in enumerate(ex.map(um, faltam), 1):
                if i % 60 == 0:
                    aviso(f"  {i}/{len(faltam)}")
    onda = os.path.join(pasta, "_analise", "revisao", "onda.png")
    if not os.path.exists(onda):
        aviso("Gerando a forma de onda…")
        subprocess.run([ffmpeg, "-y", "-v", "error", "-i", video, "-filter_complex",
                        "aformat=channel_layouts=mono,showwavespic=s=8000x120:colors=0x4FC3A1", "-frames:v", "1", onda],
                       capture_output=True)
    return [t for t in tempos if os.path.exists(os.path.join(d, f"t{t:06d}.jpg"))]


def revisao_vazia(fase):
    return {"versao": 1, "fase": fase, "estado": "rascunho", "atualizado_em": None, "enviado_em": None,
            "geral": "", "cortes": {}, "novos": [], "marcas": []}


def dados(pasta, fase, video, dur, minis):
    titulo, cortes = cortes_do_episodio(pasta)
    rev = _ler_json(os.path.join(pasta, "_analise", "revisao_cortes.json"))
    if not rev or rev.get("fase") != fase:
        rev = revisao_vazia(fase)
    return {
        "titulo": titulo, "episodio": os.path.basename(pasta), "canal": os.path.basename(os.path.dirname(pasta)),
        "fase": fase, "duracao_s": dur, "video": os.path.relpath(video, pasta).replace("\\", "/") if video else None,
        "cortes": cortes, "assuntos": assuntos(pasta), "sinais": sinais(pasta),
        "miniaturas": {"passo": PASSO_MINI, "tempos": minis},
        "onda": "_analise/revisao/onda.png" if os.path.exists(os.path.join(pasta, "_analise", "revisao", "onda.png")) else None,
        "transcricao": "_analise/transcricao.json" if os.path.exists(os.path.join(pasta, "_analise", "transcricao.json")) else None,
        "revisao": rev,
    }


def salvar_revisao(pasta, fase, recebido, enviar=False):
    caminho = os.path.join(pasta, "_analise", "revisao_cortes.json")
    atual = _ler_json(caminho)
    if not atual or atual.get("fase") != fase:
        if atual:   # revisão de outra fase: guarda antes de começar a nova
            os.replace(caminho, caminho[:-5] + f"_{atual.get('fase', 'antiga')}.json")
        atual = revisao_vazia(fase)
    for chave in ("geral", "cortes", "novos", "marcas"):
        if chave in recebido:
            atual[chave] = recebido[chave]
    agora = datetime.datetime.now().isoformat(timespec="seconds")
    atual["atualizado_em"] = agora
    if enviar:
        atual["estado"], atual["enviado_em"] = "enviado", agora
    elif atual.get("estado") == "enviado":
        atual["estado"] = "rascunho"
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)
    return atual
