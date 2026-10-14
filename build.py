"""Gera a pasta dist/ pronta para hospedar o site da ABEAA.

O arquivo index.html é a fonte (prévia de página única). Este script separa cada
seção em uma página própria, com título, descrição e endereço amigável:
  /  /a-abeaa/  /agenda/  /atualizacoes/  /associe-se/  /reservas/  /vitrine/  /transparencia/  /contato/  /privacidade/

Uso:  python3 build.py            -> versão de TESTE (não aparece no Google)
      python3 build.py --oficial  -> versão OFICIAL (só depois da aprovação)
"""
import base64, hashlib, html, json, re, shutil, sys
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
          ("Profissão e região", "regiao", "", ""),
          ("Legislação", ("Senado Federal", "Câmara dos Deputados"), "", ""), ("Outras fontes", (), "", "")]

REDES = {
    "CREA-SP": [("Instagram", "https://www.instagram.com/creasaopaulo/"), ("Facebook", "https://www.facebook.com/creasaopaulo"),
                ("LinkedIn", "https://www.linkedin.com/company/creasaopaulo/"), ("YouTube", "https://www.youtube.com/tvcreasp"),
                ("X", "https://x.com/creasp")],
    "Confea": [("Instagram", "https://www.instagram.com/confea_"), ("Facebook", "https://www.facebook.com/Confea/"),
               ("YouTube", "https://www.youtube.com/user/Confea10"), ("X", "https://twitter.com/confeacrea")],
    "Mútua": [("Instagram", "https://www.instagram.com/mutua_sp/")],
}

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
            prot = " data-protegida" if i.get("foto_protegida") is True else ""
            foto = f'<img src="{esc(f)}" alt="{esc(i.get("foto_descricao"))}" loading="lazy"{prot}>'
            cls = ' class="has-photo"'
        elif f:
            print(f"AVISO: foto não encontrada: {f}")
        fonte = esc(i.get("veiculo")) or esc(i.get("fonte")) or "ABEAA"
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
        if fontes == "regiao":
            grupo = [i for i in bons if i.get("regiao") is True]
        elif fontes:
            grupo = [i for i in bons if str(i.get("fonte", "")).strip() in fontes and i.get("regiao") is not True]
        else:
            grupo = [i for i in bons if id(i) not in usados]
        usados.update(id(i) for i in grupo)
        if grupo:
            if fontes == "regiao":
                titulo = ('<span class="hl-pin" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" '
                          'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                          '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg></span>' + nome)
            elif logo == "img/logo.png":
                titulo = f'<span class="hl-logo seal"><img src="{logo}" alt=""></span>{nome}'
            elif logo:
                titulo = f'<span class="hl-logo"><img src="{logo}" alt="{nome}"></span>'
            else:
                titulo = nome
            ver = (f'<a class="more" href="{mais}" target="_blank" rel="noopener">Todas as notícias {"da" if nome=="Mútua" else "do"} {nome} →</a>'
                   if mais else "")
            if nome in REDES:
                ver += ('<span class="hl-social" aria-label="Redes sociais do ' + nome + '">' + "".join(
                    f'<a href="{u}" target="_blank" rel="noopener">{rede}</a>' for rede, u in REDES[nome]) + '</span>')
            if fontes == "regiao":
                ver = '<span class="hl-sub">Santana de Parnaíba e Pirapora do Bom Jesus</span>'
                if any(i.get("exemplo") is True for i in grupo):
                    ver += ' <span class="pend">exemplo para aprovação da diretoria</span>'
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

# Fontes: se o baixar_fontes.py rodou (no GitHub), o site usa as fontes hospedadas nele mesmo
# e o visitante não se conecta ao Google. Senão, continua com o Google Fonts.
FONTES_LOCAIS = (root / "fonts" / "fontes.css").exists()
_google = re.compile(r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*'
                     r'<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*'
                     r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2[^"]*">')
if FONTES_LOCAIS:
    before, _n = _google.subn('<link rel="stylesheet" href="/fonts/fontes.css">', before)
    if _n != 1:
        print("AVISO: links do Google Fonts não encontrados; fontes locais não aplicadas")
        FONTES_LOCAIS = False
print("Fontes:", "hospedadas no site" if FONTES_LOCAIS else "Google Fonts")

# Regras de segurança da página (Content-Security-Policy): só roda o código do próprio site
# e os formulários só podem ser enviados ao FormSubmit.
def politica(page):
    hashes = " ".join("'sha256-" + base64.b64encode(hashlib.sha256(m.encode("utf-8")).digest()).decode() + "'"
                      for m in re.findall(r"<script>(.*?)</script>", page, re.S))
    fontes = "'self'" if FONTES_LOCAIS else "'self' https://fonts.gstatic.com"
    estilos = "'self' 'unsafe-inline'" + ("" if FONTES_LOCAIS else " https://fonts.googleapis.com")
    return (f"default-src 'self'; script-src 'self' {hashes}; style-src {estilos}; font-src {fontes}; "
            "img-src 'self' data:; connect-src 'self' https://formsubmit.co; "
            "form-action 'self' https://formsubmit.co; base-uri 'self'; object-src 'none'; upgrade-insecure-requests")
dist = root / "dist"
if dist.exists():
    shutil.rmtree(dist)
(dist / "img").mkdir(parents=True)

for r in routes:
    title, desc = PAGES[r]
    url = SITE_URL + path_of(r)
    ld = [ORG] + ([EVENT] if r in ("inicio", "agenda") else [])
    view = views[r].replace('class="view"', 'class="view on"', 1)
    page = links(before, r) + links(view, r) + links(after, r)
    page = page.replace(f'<a href="{path_of(r)}"', f'<a aria-current="page" href="{path_of(r)}"')
    head = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{politica(page)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
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
    out = dist / ("index.html" if r == "inicio" else f"{r}/index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(head + page + "\n</body>\n</html>\n", encoding="utf-8")

(dist / "404.html").write_text((dist / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
shutil.copytree(root / "img", dist / "img", dirs_exist_ok=True)

# Proteção das fotos da ABEAA: as imagens marcadas com data-protegida no index.html
# saem no site com no máximo 1600 px e uma marca d'água discreta "ABEAA".
# Os arquivos originais na pasta img/ não são alterados.
def _proteger_fotos():
    alvos = sorted(set(re.findall(r'<img[^>]*src="img/([^"]+)"[^>]*data-protegida', _idx.read_text(encoding="utf-8"))))
    if not alvos:
        return
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("AVISO: Pillow não instalado; fotos publicadas sem marca d'água")
        return
    for rel in alvos:
        orig, dest = root / "img" / rel, dist / "img" / rel
        if not orig.exists():
            print(f"AVISO: foto protegida não encontrada: img/{rel}")
            continue
        im = Image.open(orig).convert("RGB")
        im.thumbnail((1600, 1600))
        camada = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(camada)
        tam = max(14, im.width // 28)
        try:
            fonte = ImageFont.load_default(size=tam)
        except TypeError:
            fonte = ImageFont.load_default()
        texto = "ABEAA"
        x0, y0, x1, y1 = d.textbbox((0, 0), texto, font=fonte)
        m = max(8, im.width // 60)
        x, y = im.width - (x1 - x0) - m, im.height - (y1 - y0) - m - y0
        d.text((x + 1, y + 1), texto, font=fonte, fill=(0, 0, 0, 90))
        d.text((x, y), texto, font=fonte, fill=(255, 255, 255, 150))
        Image.alpha_composite(im.convert("RGBA"), camada).convert("RGB").save(dest, "JPEG", quality=85, optimize=True)
    print(f"Fotos protegidas: {len(alvos)}")

_proteger_fotos()

# Calendário de avisos (avisos.ics): datas de vencimento dos destaques.
# Assine o endereço /avisos.ics no Google Agenda para ver os vencimentos.
def _avisos_ics():
    import datetime as _dt
    arq = root / "conteudo" / "destaques.json"
    try:
        itens = json.loads(arq.read_text(encoding="utf-8"))
    except Exception:
        itens = []
    def esc(t):
        return str(t).replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", " ")
    agora = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ABEAA//Avisos do site//PT-BR",
              "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Avisos do site da ABEAA",
              "X-WR-TIMEZONE:America/Sao_Paulo"]
    for n, i in enumerate(itens if isinstance(itens, list) else []):
        v = str(i.get("vence_em") or "").strip()[:10]
        try:
            dia = _dt.date.fromisoformat(v)
        except ValueError:
            if v:
                print(f"AVISO: data de vencimento inválida: {v}")
            continue
        for antes, rotulo in ((3, "Vence em 3 dias"), (0, "Vence hoje")):
            d0 = dia - _dt.timedelta(days=antes)
            linhas += ["BEGIN:VEVENT", f"UID:abeaa-{hashlib.sha1(str(i.get('link', n)).encode()).hexdigest()[:12]}-{antes}@abeaa.com.br", f"DTSTAMP:{agora}",
                       f"DTSTART;VALUE=DATE:{d0:%Y%m%d}", f"DTEND;VALUE=DATE:{d0 + _dt.timedelta(days=1):%Y%m%d}",
                       f"SUMMARY:{esc(rotulo + ': ' + str(i.get('titulo', '')))}",
                       f"DESCRIPTION:{esc('Destaque do site com vencimento em ' + dia.strftime('%d/%m/%Y') + '. Trocar ou manter conforme a regra da quinzena. ' + str(i.get('link', '')))}",
                       "TRANSP:TRANSPARENT", "END:VEVENT"]
    linhas.append("END:VCALENDAR")
    def dobra(l):  # linhas longas quebradas a cada 74 bytes, como pede o padrão do calendário
        b, partes = l.encode("utf-8"), []
        while len(b) > 74:
            corte = 74
            while (b[corte] & 0xC0) == 0x80:
                corte -= 1
            partes.append(b[:corte].decode("utf-8")); b = b[corte:]
        partes.append(b.decode("utf-8"))
        return "\r\n ".join(partes)
    (dist / "avisos.ics").write_text("\r\n".join(dobra(l) for l in linhas) + "\r\n", encoding="utf-8")
_avisos_ics()
if FONTES_LOCAIS:
    shutil.copytree(root / "fonts", dist / "fonts", dirs_exist_ok=True)
(dist / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n" if OFICIAL else "User-agent: *\nDisallow: /\n",
    encoding="utf-8")
urls = "\n".join(f"  <url><loc>{SITE_URL}{path_of(r)}</loc></url>" for r in routes)
(dist / "sitemap.xml").write_text(
    f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n',
    encoding="utf-8")
print("Pronto:", dist, "|", len(routes), "páginas | versão", "OFICIAL" if OFICIAL else "de TESTE")
