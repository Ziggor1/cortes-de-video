# Cria um canal no cofre: Pasta de Trabalho/<Canal>/Conteudo Visual/ com os arquivos da identidade visual e o visual.json,
# e a nota Canais/<Canal>.md com o perfil para preencher.
# Uso: python novo_canal.py "<Nome do canal>" [--intro arq] [--final arq] [--final-vertical arq]
#                           [--final-youtube arq] [--final-instagram arq] [--final-tiktok arq] [--logo arq.png] [--fonte arq.ttf]
# Tudo é opcional: sem intro/final/logo, aquela parte só não entra. Os arquivos são COPIADOS (os originais ficam onde estão).
# Marca d'água padrão (pode mudar depois, pela amostra em vídeo real):
#   16:9 — logo de 150 px, 85% de opacidade, canto superior direito;
#   Shorts — logo de 220 px, 100%, centro do topo (na faixa desfocada, onde não cobre o vídeo).
import os, sys, json, shutil
from comum import COFRE, TRABALHO, log

def main(a):
    if not a or a[0].startswith('--'): print('Uso: python novo_canal.py "<Nome do canal>" [--intro arq] [--final arq] [--logo arq.png] …'); return 1
    nome = a[0].strip(); arg = lambda k: a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None
    if any(c in nome for c in '\\/:*?"<>|'): print('Nome de canal com caractere inválido para pasta.'); return 1
    pv = os.path.join(TRABALHO, nome, 'Conteudo Visual'); os.makedirs(pv, exist_ok=True)
    vj = os.path.join(pv, 'visual.json')
    vis = json.load(open(vj, encoding='utf-8')) if os.path.exists(vj) else {}
    def copiar(chave, destino_nome):
        orig = arg(chave)
        if not orig: return None
        orig = os.path.abspath(os.path.expanduser(orig))
        if not os.path.exists(orig): print('não encontrei', orig); sys.exit(1)
        d = destino_nome + os.path.splitext(orig)[1].lower(); shutil.copy2(orig, os.path.join(pv, d)); return d
    intro = copiar('--intro', 'intro_16x9'); final = copiar('--final', 'final_16x9'); logo = copiar('--logo', 'logo')
    fonte = copiar('--fonte', 'fonte_canal')
    if intro: vis['intro'] = intro
    if final: vis['final'] = final
    if fonte: vis['fonte'] = fonte
    fv = vis.get('finais_verticais') or {}
    todas = copiar('--final-vertical', 'final_vertical')
    if todas: fv = {p: todas for p in ('YouTube', 'Instagram', 'TikTok')}
    for p in ('YouTube', 'Instagram', 'TikTok'):
        f = copiar('--final-' + p.lower(), 'final_vertical_' + p.lower())
        if f: fv[p] = f
    if fv: vis['finais_verticais'] = fv
    if logo:
        vis['camadas'] = [{'arquivo': logo, 'largura': 150, 'opacidade': 0.85, 'x': 'W-w-30', 'y': '30'}]
        vis['camadas_vertical'] = [{'arquivo': logo, 'largura': 220, 'opacidade': 1.0, 'x': '(W-w)/2', 'y': '250'}]
        vis['capa_logo'] = logo
    for k, v in (('intro', ''), ('final', ''), ('finais_verticais', {}), ('camadas', []), ('camadas_vertical', []), ('capa_logo', '')):
        vis.setdefault(k, v)
    json.dump(vis, open(vj, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    nota = os.path.join(COFRE, 'Canais', nome + '.md'); os.makedirs(os.path.dirname(nota), exist_ok=True)
    if not os.path.exists(nota):
        open(nota, 'w', encoding='utf-8', newline='\n').write(
            f'---\ntipo: "canal"\ntags:\n  - "canal"\n---\n%% AUTO: início — gerado por _sistema/atualizar_notas.py; edite fora deste bloco %%\n# {nome}\n%% AUTO: fim %%\n\n'
            '## Perfil do canal\n\n- Público:\n- Tom e linguagem:\n- Apresentadores e convidados frequentes:\n'
            '- Regras próprias do canal (o que nunca cortar, vinhetas, chamadas):\n')
    reg = os.path.join(COFRE, 'Regras', 'Finalização e identidade visual.md')
    if os.path.exists(reg):
        s = open(reg, encoding='utf-8').read(); marca = f'### {nome}\n'
        if marca not in s:
            linhas = [marca, f"- Intro: `{vis['intro'] or '—'}`; final 16:9: `{vis['final'] or '—'}`; finais verticais: "
                             f"{', '.join(f'{p} `{f}`' for p, f in vis['finais_verticais'].items()) or '—'}.\n",
                      f"- Marca d'água: {'logo `' + logo + '` (16:9: 150 px, 85%, canto superior direito; Shorts: 220 px, 100%, centro do topo)' if logo else 'nenhuma'}.\n",
                      '- Amostra aprovada: (ainda não).\n\n']
            ancora = '### Formato das camadas'
            s = s.replace(ancora, ''.join(linhas) + ancora, 1) if ancora in s else s + '\n' + ''.join(linhas)
            open(reg, 'w', encoding='utf-8', newline='\n').write(s)
    log(f'canal "{nome}" pronto em {pv}')
    for k in ('intro', 'final', 'capa_logo'): log(f'  {k:10} {vis[k] or "— (sem)"}')
    for p, f in vis['finais_verticais'].items(): log(f'  final vertical {p}: {f}')
    log('Próximo passo: coloque um episódio em', os.path.join(TRABALHO, nome, '<Episódio>'), 'e peça "analisar <Episódio>" ao Claude.')
    log('Antes de finalizar o 1º episódio, gere a amostra em vídeo real (amostra_trecho.py) para aprovar o visual.')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
