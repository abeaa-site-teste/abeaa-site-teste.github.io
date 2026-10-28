"""Registro da divulgação no site para a prestação de contas da ABEAA.

Roda no GitHub depois de cada publicação do site e no dia 1º de cada mês
(arquivo .github/workflows/prints.yml). Gera um PDF de cada página abaixo, com o endereço,
a data e a hora da captura (horário de Brasília) em todas as folhas:
  - Atualizações (todas as notícias)
  - Espaço CREA-SP
e salva no Google Drive em: Prestação de contas / AAAA / MM-mês / "AAAA-MM-DD · Página.pdf".

Quando gera:
  - se as notícias mudaram desde o último PDF daquela página (no máximo um por dia: no mesmo dia, o novo substitui o anterior);
  - se o mês ainda não tem nenhum PDF daquela página (garante pelo menos um por mês).

Precisa de dois segredos no GitHub (Settings > Secrets and variables > Actions):
  PRINTS_URL   = endereço do "app da web" do Google Apps Script (recebe os arquivos e grava no Drive)
  PRINTS_TOKEN = senha combinada entre o GitHub e o Apps Script
Sem os segredos, não faz nada (só avisa).

Teste local, sem enviar nada:  python3 prints.py --teste   (grava os PDFs na pasta prints_teste/)
"""
import base64
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

SITE = os.environ.get("SITE_URL", "https://abeaa-site-teste.github.io").rstrip("/")
EXIBE = os.environ.get("SITE_EXIBIDO", "").rstrip("/")  # só para prévias: endereço mostrado no cabeçalho
ROTULO = os.environ.get("PRINTS_ROTULO", "")  # texto extra no cabeçalho (ex.: "PRÉVIA")
PASTA_RAIZ = "Prestação de contas"
MESES = ["01-janeiro", "02-fevereiro", "03-março", "04-abril", "05-maio", "06-junho", "07-julho",
         "08-agosto", "09-setembro", "10-outubro", "11-novembro", "12-dezembro"]
PAGINAS = [("/atualizacoes/", "Atualizações (todas as notícias)"),
           ("/espaco-crea-sp/", "Espaço CREA-SP")]
TESTE = "--teste" in sys.argv
URL, TOKEN = os.environ.get("PRINTS_URL", ""), os.environ.get("PRINTS_TOKEN", "")


def chama(dados):
    req = urllib.request.Request(URL, data=json.dumps(dados).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    if not TESTE and not (URL and TOKEN):
        print("AVISO: segredos PRINTS_URL e PRINTS_TOKEN não configurados; nenhum PDF foi feito.")
        return
    agora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))
    hoje = agora.date().isoformat()
    pastas = [PASTA_RAIZ, str(agora.year), MESES[agora.month - 1]]
    # "impressão digital" das notícias: muda sempre que alguma notícia entra, sai ou é editada
    marca = hashlib.sha256(Path("conteudo/destaques.json").read_bytes()).hexdigest()[:16]

    existentes = []
    if not TESTE:
        r = chama({"token": TOKEN, "acao": "listar", "pastas": pastas})
        if not r.get("ok"):
            sys.exit(f"ERRO do Apps Script: {r}")
        existentes = r.get("arquivos", [])

    fazer = []
    for caminho, titulo in PAGINAS:
        nome = f"{hoje} · {titulo}.pdf"
        desta = [a for a in existentes if a["nome"].endswith(f" · {titulo}.pdf")]
        ultima = max(desta, key=lambda a: a["nome"]) if desta else None
        if TESTE or not ultima or ultima.get("descricao") != marca:
            fazer.append((caminho, titulo, nome))
        else:
            print(f"Sem mudança desde o último PDF: {titulo}")
    if not fazer:
        return

    from playwright.sync_api import sync_playwright
    carimbo = agora.strftime("%d/%m/%Y às %H:%M")
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pag = nav.new_page(viewport={"width": 1280, "height": 900})
        for caminho, titulo, nome in fazer:
            url = SITE + caminho
            pag.goto(url, wait_until="networkidle")
            pag.emulate_media(media="screen")
            # carrega as fotos que só aparecem ao rolar a página
            pag.evaluate("""async () => {
                for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); }
                document.querySelectorAll('img[loading="lazy"]').forEach(i => i.loading = 'eager');
                window.scrollTo(0, 0);
                const s = document.createElement('style');
                s.textContent = '.top{position:static!important} .zoom-count,.zoom-wrap::after{display:none!important}';
                document.head.appendChild(s);
            }""")
            pag.wait_for_load_state("networkidle")
            extra = f"{ROTULO} · " if ROTULO else ""
            cab = (f'<div style="font:9px Arial,sans-serif;width:100%;padding:0 10mm;display:flex;justify-content:space-between;color:#333">'
                   f'<span>{extra}Site da ABEAA · {(EXIBE + caminho) if EXIBE else url}</span><span>Capturado em {carimbo} (horário de Brasília)</span></div>')
            rod = ('<div style="font:9px Arial,sans-serif;width:100%;padding:0 10mm;text-align:right;color:#333">'
                   'Folha <span class="pageNumber"></span> de <span class="totalPages"></span></div>')
            pdf = pag.pdf(format="A4", print_background=True, display_header_footer=True,
                          header_template=cab, footer_template=rod,
                          margin={"top": "14mm", "bottom": "12mm", "left": "6mm", "right": "6mm"}, scale=0.62)
            if TESTE:
                Path("prints_teste").mkdir(exist_ok=True)
                (Path("prints_teste") / nome).write_bytes(pdf)
                print(f"[TESTE] {'/'.join(pastas)}/{nome}")
            else:
                r = chama({"token": TOKEN, "acao": "salvar", "pastas": pastas, "nome": nome,
                           "tipo": "application/pdf", "descricao": marca, "substituir": True,
                           "arquivo": base64.b64encode(pdf).decode("ascii")})
                print(("Salvo: " if r.get("ok") else "ERRO ao salvar: ") + f"{'/'.join(pastas)}/{nome}")
        nav.close()


if __name__ == "__main__":
    main()
