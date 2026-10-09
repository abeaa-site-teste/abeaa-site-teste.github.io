"""Gera a pasta dist/ pronta para hospedar o site da ABEAA.

O arquivo index.html é a fonte (prévia de página única). Este script separa cada
seção em uma página própria, com título, descrição e endereço amigável:
  /  /a-abeaa/  /agenda/  /atualizacoes/  /associe-se/  /reservas/  /vitrine/  /transparencia/  /contato/  /privacidade/

Uso:  python3 build.py            -> versão de TESTE (não aparece no Google)
      python3 build.py --oficial  -> versão OFICIAL (só depois da aprovação)
"""
import html, json, re, shutil, sys
from pathlib import Path

SITE_URL = "https://www.abeaa.com.br"   # endereço definitivo
OFICIAL = "--oficial" in sys.argv

# título (até 60 caracteres) e descrição (até 155) de cada página
PAGES = {
    "inicio": ("ABEAA · Associação Bandeirante de Santana de Parnaíba",
               "Associação de engenheiros, arquitetos e agrônomos de Santana de Parnaíba: cursos, estrutura para associados e representação profissional."),
    "a-abeaa": ("A ABEAA · história, atuação e diretoria",
                "Desde 1993 em Santana de Parnaíba: a história da ABEAA, a Inspetoria do CREA-SP, a fundação da UNARO, a sede e a diretoria."),
    "agenda": ("Agenda de cursos e eventos · ABEAA",
               "Cursos, palestras e encontros da ABEAA em Santana de Parnaíba e online, com datas, horários e link de inscrição."),
    "atualizacoes": ("Atualizações profissionais · ABEAA",
                     "Notícias da ABEAA e links para as notícias oficiais do CREA-SP, do Confea e da Mútua."),
    "associe-se": ("Associe-se à ABEAA · R$ 250 por ano",
                   "Benefícios para associados da ABEAA: auditório, sala do profissional com plotter, área de lazer, cursos e convênios. Saiba como se associar."),
    "reservas": ("Reserva de espaços para associados · ABEAA",
                 "Associados da ABEAA podem solicitar o auditório, a área de lazer ou a sala do profissional. A secretaria confirma a disponibilidade."),
    "vitrine": ("Vitrine Profissional: vagas e serviços · ABEAA",
                "Vagas, parcerias e serviços entre profissionais de engenharia, arquitetura e agronomia, com publicações analisadas pela diretoria da ABEAA."),
    "transparencia": ("Transparência: estatuto, documentos e parcerias · ABEAA",
                      "Estatuto, documentos para os associados e parcerias da ABEAA com a administração pública, conforme a Lei 13.019/2014."),
    "contato": ("Contato · ABEAA Santana de Parnaíba",
                "Endereço, telefone, e-mail e horário de atendimento da ABEAA, na Rua Santa Edwiges, 118, Jardim Rubi, Santana de Parnaíba/SP."),
    "privacidade": ("Política de Privacidade · ABEAA",
                    "Como a ABEAA trata os dados enviados pelos formulários do site, conforme a LGPD."),
}

def path_of(r):
    return "/" if r == "inicio" else f"/{r}/"

ORG = {
    "@context": "https://schema.org", "@type": "Organization",
    "name": "Associação Bandeirante de Engenheiros, Arquitetos e Agrônomos",
    "alternateName": "ABEAA", "url": SITE_URL + "/", "logo": SITE_URL + "/img/logo.png",
    "email": "abeaaaparnaiba@gmail.com", "telephone": "+55 11 4154-3546",
    "address": {"@type": "PostalAddress", "streetAddress": "Rua Santa Edwiges, 118 - Jardim Rubi",
                "addressLocality": "Santana de Parnaíba", "addressRegion": "SP",
                "postalCode": "06502-135", "addressCountry": "BR"},
    "sameAs": ["https://www.instagram.com/abeaasp", "https://www.facebook.com/abeaa.associacaobandeirante"],
}
EVENT = {
    "@context": "https://schema.org", "@type": "Event",
    "name": "Patologias e Impermeabilização na Construção Civil",
    "startDate": "2026-11-17T18:30-03:00", "endDate": "2026-11-18T22:30-03:00",
    "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
    "eventStatus": "https://schema.org/EventScheduled", "isAccessibleForFree": True,
    "location": {"@type": "VirtualLocation", "url": "https://santanadeparnaiba.portalsca.com.br"},
    "organizer": {"@type": "Organization", "name": "ABEAA", "url": SITE_URL + "/"},
    "performer": {"@type": "Person", "name": "Paulo Afonso dos Santos Júnior"},
    "image": SITE_URL + "/img/curso-patologias-2026.jpg",
}

root = Path(__file__).parent
src = (root / "index.html").read_text(encoding="utf-8")
src = src.replace("var PREVIEW=true;", "var PREVIEW=false;").replace("var ROUTER=true;", "var ROUTER=false;")
src = re.sub(r"<title>.*?</title>\n", "", src, count=1)
src = re.sub(r'<meta name="description"[^>]*>\n', "", src, count=1)
if not OFICIAL:
    src = src.replace("PRÉVIA PARA A DIRETORIA", "VERSÃO DE TESTE")
src = src.replace('src="img/', 'src="/img/').replace("url('img/", "url('/img/")

# Destaques do mês: preenchidos pelo painel (Pages CMS) em conteudo/destaques.json
# Aparecem agrupados por entidade. Também são gravados no index.html (prévia).
GRUPOS = [("ABEAA", ("ABEAA",), "img/logo.png", ""),
          ("CREA-SP", ("CREA-SP",), "img/logo-crea-sp.png", "https://www.creasp.org.br/noticias/"),
          ("Confea", ("Confea",), "img/logo-confea.png", "https://www.confea.org.br/noticias"),
          ("Mútua", ("Mútua",), "img/logo-mutua.png", "https://www.mutua.com.br/category/noticias-mutua/"),
          ("Legislação", ("Senado Federal", "Câmara dos Deputados"), "", ""), ("Outras fontes", (), "", "")]

EM_FOCO = []

def destaques_html():
    arq = Path(__file__).parent / "conteudo" / "destaques.json"
    try:
        itens = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []
    except ValueError:
        print("AVISO: conteudo/destaques.json com erro de formato; destaques não exibidos")
        return None
    bons = []
    for i in itens if isinstance(itens, list) else []:
        tit, link = str(i.get("titulo", "")).strip(), str(i.get("link", "")).strip()
        if not tit or not link.startswith("https://"):
            print(f"AVISO: destaque ignorado (falta título ou link https): {tit or link}")
            continue
        bons.append(i)
    if not bons:
        return None
    bons.sort(key=lambda i: str(i.get("data", "")), reverse=True)

    def esc(x):
        return html.escape(str(x or "").strip())

    def item(i):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(i.get("data") or ""))
        quando = f'<time datetime="{m.group(0)}">{m.group(3)}/{m.group(2)}/{m.group(1)}</time>' if m else ""
        resumo = f"<p>{esc(i.get('resumo'))}</p>" if str(i.get("resumo") or "").strip() else ""
        foto, cls = "", ""
        f = str(i.get("foto") or "").strip().lstrip("/")
        if f.startswith("img/") and (Path(__file__).parent / f).exists():
            foto = f'<img src="{esc(f)}" alt="{esc(i.get("foto_descricao"))}" loading="lazy">'
            cls = ' class="has-photo"'
        elif f:
            print(f"AVISO: foto não encontrada: {f}")
        fonte = esc(i.get("fonte")) or "ABEAA"
        return (f'          <li{cls}>{foto}<div>\n'
                f'            <span class="meta">{fonte}{" · " if quando else ""}{quando}</span>\n'
                f'            <h4><a href="{esc(i.get("link"))}" target="_blank" rel="noopener">{esc(i.get("titulo"))}</a></h4>\n'
                f'            {resumo}\n'
                f'          </div></li>')

    fixos = [i for i in bons if i.get("fixar") is True]
    bons = [i for i in bons if i.get("fixar") is not True]
    blocos = []
    if fixos:
        blocos.append('      <div class="hl-group hl-focus">\n        <div class="hl-head"><h3>Em foco</h3></div>\n        <ul class="highlights">\n'
                      + "\n".join(item(i) for i in fixos[:2]) + "\n        </ul>\n      </div>")
    global EM_FOCO
    EM_FOCO = fixos
    usados = set()
    for nome, fontes, logo, mais in GRUPOS:
        if fontes:
            grupo = [i for i in bons if str(i.get("fonte", "")).strip() in fontes]
        else:
            grupo = [i for i in bons if id(i) not in usados]
        usados.update(id(i) for i in grupo)
        if grupo:
            if logo == "img/logo.png":
                titulo = f'<span class="hl-logo seal"><img src="{logo}" alt=""></span>{nome}'
            elif logo:
                titulo = f'<span class="hl-logo"><img src="{logo}" alt="{nome}"></span>'
            else:
                titulo = nome
            ver = (f'<a class="more" href="{mais}" target="_blank" rel="noopener">Todas as notícias {"da" if nome=="Mútua" else "do"} {nome} →</a>'
                   if mais else "")
            blocos.append(f'      <div class="hl-group">\n        <div class="hl-head"><h3>{titulo}</h3>{ver}</div>\n        <ul class="highlights">\n'
                          + "\n".join(item(i) for i in grupo[:6]) + "\n        </ul>\n      </div>")
    return "\n".join(blocos)

_dest = destaques_html()
_idx = Path(__file__).parent / "index.html"

# Página inicial: o destaque "Em foco" aparece no bloco Atualizações profissionais
def _foco_home():
    if not EM_FOCO:
        return ('          <p>Notícias da ABEAA e destaques do CREA-SP, do Confea e da Mútua, selecionados todo mês.</p>\n'
                '          <a class="more" href="#atualizacoes">Ver atualizações →</a>')
    i = EM_FOCO[0]
    e = lambda x: html.escape(str(x or "").strip())
    return (f'          <span class="meta-focus">Em foco</span>\n'
            f'          <h3>{e(i.get("titulo"))}</h3>\n'
            f'          <p>{e(i.get("chamada") or i.get("resumo"))}</p>\n'
            f'          <a class="more" href="{e(i.get("link"))}" target="_blank" rel="noopener">{e(i.get("acao") or "Ler mais")} →</a>\n'
            f'          <a class="more" href="#atualizacoes" style="margin-left:16px">Todas as atualizações</a>')
_foco = _foco_home()
_rfoco = r"(<!--EMFOCO-->)(.*?)(<!--/EMFOCO-->)"
src = re.sub(_rfoco, lambda m: m.group(1) + "\n" + _foco + "\n" + m.group(3), src, count=1, flags=re.S)
_o = _idx.read_text(encoding="utf-8")
_n = re.sub(_rfoco, lambda m: m.group(1) + "\n" + _foco + "\n" + m.group(3), _o, count=1, flags=re.S)
if _n != _o:
    _idx.write_text(_n, encoding="utf-8")
_regiao = r"(<!--DESTAQUES-->)(.*?)(<!--/DESTAQUES-->)"
_vazio = '        <p class="lead">Os destaques escolhidos pela ABEAA aparecem aqui, com resumo e link para a fonte original.</p>'
if True:
    _dest = _dest or _vazio
    src = re.sub(_regiao, lambda m: _dest, src, count=1, flags=re.S)
    src = src.replace('src="img/', 'src="/img/')
    # mantém a prévia (index.html) igual ao site gerado
    _orig = _idx.read_text(encoding="utf-8")
    _novo = re.sub(_regiao, lambda m: m.group(1) + "\n" + _dest + "\n" + m.group(3), _orig, count=1, flags=re.S)
    if _novo != _orig:
        _idx.write_text(_novo, encoding="utf-8")

routes = list(PAGES)
views = {r: re.search(rf'(<div class="view" id="v-{r}">.*?)(?=\n<!-- =+ |\n</main>)', src, re.S).group(1) for r in routes}
start = src.index('<div class="view" id="v-inicio">')
end = src.index("\n</main>")
before, after = src[:start], src[end:]

# âncoras internas (ex.: #historia, #sede) apontam para a página onde estão
anchors = {}
for r in routes:
    for a in re.findall(r'\sid="([a-z0-9-]+)"', views[r]):
        if not a.startswith("v-"):
            anchors.setdefault(a, r)

def links(html, here=None):
    for r in routes:
        html = html.replace(f'href="#{r}"', f'href="{path_of(r)}"')
    for a, r in anchors.items():
        html = html.replace(f'href="#{a}"', f'href="#{a}"' if r == here else f'href="{path_of(r)}#{a}"')
    return html

robots = "index, follow" if OFICIAL else "noindex, nofollow"
dist = root / "dist"
if dist.exists():
    shutil.rmtree(dist)
(dist / "img").mkdir(parents=True)

for r in routes:
    title, desc = PAGES[r]
    url = SITE_URL + path_of(r)
    ld = [ORG] + ([EVENT] if r in ("inicio", "agenda") else [])
    head = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#10237a">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/png" href="/img/favicon.png">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="ABEAA">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}/img/compartilhar.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>[hidden]{{display:none!important}}img{{max-width:100%}}</style>
</head>
<body>
"""
    view = views[r].replace('class="view"', 'class="view on"', 1)
    page = links(before, r) + links(view, r) + links(after, r)
    page = page.replace(f'<a href="{path_of(r)}"', f'<a aria-current="page" href="{path_of(r)}"')
    out = dist / ("index.html" if r == "inicio" else f"{r}/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(head + page + "\n</body>\n</html>\n", encoding="utf-8")

(dist / "404.html").write_text((dist / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
shutil.copytree(root / "img", dist / "img", dirs_exist_ok=True)
(dist / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n" if OFICIAL else "User-agent: *\nDisallow: /\n",
    encoding="utf-8")
urls = "\n".join(f"  <url><loc>{SITE_URL}{path_of(r)}</loc></url>" for r in routes)
(dist / "sitemap.xml").write_text(
    f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
    encoding="utf-8")
print("Pronto:", dist, "|", len(routes), "páginas | versão", "OFICIAL" if OFICIAL else "de TESTE")
