"""Robô de notícias do site da ABEAA.

Roda uma vez por dia no GitHub (gratuito). Lê as páginas oficiais de notícias
do CREA-SP e do Confea e grava em atualizacoes.json só TÍTULO, DATA e LINK
de cada notícia. O site mostra essa lista e manda o visitante ler no site
oficial. Nenhum resumo ou texto das notícias é copiado (direito autoral).

Se uma fonte falhar (site fora do ar ou mudou de formato), o robô mantém as
notícias anteriores dessa fonte e avisa no registro (log) do GitHub.

Uso: python3 robo/atualizar_noticias.py [caminho/do/atualizacoes.json]
"""
import json, re, sys, html, datetime, urllib.request
from html.parser import HTMLParser
from pathlib import Path

POR_FONTE = 5          # quantas notícias de cada entidade
TOTAL = 15             # máximo na lista
AGENTE = "ABEAA-site-noticias/1.0 (+https://www.abeaa.com.br)"

FONTES = [
    {"fonte": "CREA-SP",
     "lista": "https://www.creasp.org.br/noticias/",
     "link": r"^https://www\.creasp\.org\.br/noticia/[a-z0-9-]+/?$"},
    {"fonte": "Confea",
     "lista": "https://www.confea.org.br/noticias",
     "link": r"^https://www\.confea\.org\.br/[a-z0-9-]{12,}/?$"},
    # Mútua: o site não permitiu leitura automática no teste de 05/10/2026.
    # Para incluir, acrescente aqui a página de notícias e o padrão dos links.
]

def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")

class Titulos(HTMLParser):
    """Pega links que estão dentro de títulos (h2, h3, h4) da página de lista."""
    def __init__(self, base):
        super().__init__(); self.base = base; self.nivel = 0; self.href = None; self.txt = []; self.itens = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("h2", "h3", "h4"): self.nivel += 1
        if tag == "a" and self.nivel:
            self.href = urllib.parse.urljoin(self.base, a.get("href") or ""); self.txt = []
    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4") and self.nivel: self.nivel -= 1
        if tag == "a" and self.href is not None:
            t = re.sub(r"\s+", " ", "".join(self.txt)).strip()
            if t: self.itens.append((self.href, t))
            self.href = None
    def handle_data(self, d):
        if self.href is not None: self.txt.append(d)

import urllib.parse

def data_da_noticia(pagina):
    """Procura a data de publicação: primeiro nas marcações padrão, depois dd/mm/aaaa."""
    for pad in (r'property="article:published_time"\s+content="(\d{4})-(\d{2})-(\d{2})',
                r'content="(\d{4})-(\d{2})-(\d{2})[^"]*"\s+property="article:published_time"',
                r'"datePublished"\s*:\s*"(\d{4})-(\d{2})-(\d{2})',
                r'<time[^>]+datetime="(\d{4})-(\d{2})-(\d{2})'):
        m = re.search(pad, pagina)
        if m: return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    m = re.search(r"\b(\d{2})/(\d{2})/(20\d{2})\b", pagina)
    return f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else ""

def ler_fonte(f, baixar=baixar):
    p = Titulos(f["lista"]); p.feed(baixar(f["lista"]))
    vistos, itens = set(), []
    for href, titulo in p.itens:
        if not re.match(f["link"], href) or href in vistos or len(titulo) < 15: continue
        vistos.add(href)
        try: data = data_da_noticia(baixar(href))
        except Exception: data = ""
        itens.append({"fonte": f["fonte"], "titulo": html.unescape(titulo), "link": href, "data": data})
        if len(itens) >= POR_FONTE: break
    if not itens: raise ValueError("nenhuma notícia reconhecida (a página pode ter mudado de formato)")
    return itens

def ordem(item):
    try: return datetime.datetime.strptime(item["data"], "%d/%m/%Y")
    except ValueError: return datetime.datetime.min

def main(destino="atualizacoes.json", baixar=baixar):
    arq = Path(destino)
    anterior = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {"itens": []}
    todos, problemas = [], []
    for f in FONTES:
        try:
            novos = ler_fonte(f, baixar); print(f"OK  {f['fonte']}: {len(novos)} notícias")
        except Exception as e:
            novos = [i for i in anterior.get("itens", []) if i.get("fonte") == f["fonte"]]
            problemas.append(f["fonte"]); print(f"ERRO {f['fonte']}: {e} (mantidas {len(novos)} anteriores)")
        todos += novos
    aviso = Path("robo_problemas.txt")
    if problemas: aviso.write_text("Fontes com problema: " + ", ".join(problemas) + "\n", encoding="utf-8")
    elif aviso.exists(): aviso.unlink()
    todos.sort(key=ordem, reverse=True)
    saida = {"atualizado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
             "itens": todos[:TOTAL]}
    if [i["link"] for i in saida["itens"]] == [i["link"] for i in anterior.get("itens", [])]:
        print("Sem notícias novas."); return 0
    arq.write_text(json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Gravado {destino} com {len(saida['itens'])} notícias.")
    return 1 if problemas and not todos else 0

if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:2] or [])))
