"""Baixa as fontes do site (DM Sans e IBM Plex Mono) para a pasta fonts/.

Roda no GitHub, antes de gerar as páginas. Assim o site passa a usar as fontes
hospedadas nele mesmo e o visitante não precisa se conectar ao Google (LGPD).
Se o download falhar, nada quebra: o build.py volta a usar o Google Fonts.
"""
import re
import sys
import urllib.request
from pathlib import Path

CSS_URL = ("https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;"
           "9..40,600;9..40,700;9..40,800&family=IBM+Plex+Mono:wght@500&display=swap")
# navegador moderno, para o Google entregar o formato woff2
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SUBSETS = ("latin", "latin-ext")  # português usa só estes


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    pasta = Path(__file__).parent / "fonts"
    pasta.mkdir(exist_ok=True)
    css = baixar(CSS_URL).decode("utf-8")
    blocos = re.findall(r"/\*\s*([a-z-]+)\s*\*/\s*(@font-face\s*{.*?})", css, re.S)
    saida, feitos = [], {}
    for subset, bloco in blocos:
        if subset not in SUBSETS:
            continue
        url = re.search(r"url\((https://[^)]+\.woff2)\)", bloco)
        if not url:
            continue
        familia = re.search(r"font-family:\s*'([^']+)'", bloco).group(1)
        peso = re.search(r"font-weight:\s*([\d ]+);", bloco).group(1).strip().replace(" ", "-")
        nome = feitos.get(url.group(1)) or f"{familia.lower().replace(' ', '-')}-{subset}-{peso}.woff2"
        if url.group(1) not in feitos:  # o mesmo arquivo pode servir a vários pesos
            (pasta / nome).write_bytes(baixar(url.group(1)))
            feitos[url.group(1)] = nome
        saida.append(bloco.replace(url.group(1), f"/fonts/{nome}"))
    if not saida:
        raise RuntimeError("nenhuma fonte encontrada na resposta do Google")
    (pasta / "fontes.css").write_text("\n".join(saida) + "\n", encoding="utf-8")
    print(f"Fontes baixadas: {len(feitos)} arquivos em {pasta}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # nunca impede a publicação
        print(f"AVISO: fontes não baixadas ({e}); o site usará o Google Fonts.")
        sys.exit(0)
