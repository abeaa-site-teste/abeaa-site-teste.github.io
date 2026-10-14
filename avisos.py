"""Avisa quando um destaque do site está para vencer.

Roda todo dia no GitHub (arquivo .github/workflows/avisos.yml).
Para cada destaque com "vence_em" nos próximos 3 dias, abre um aviso (issue) no
GitHub e o atribui ao dono da conta. O GitHub manda o aviso por e-mail.
Cada destaque gera um aviso só uma vez, mesmo que o programa rode vários dias.

Uso local, só para conferir, sem abrir avisos:
    python3 avisos.py --teste            (usa a data de hoje)
    python3 avisos.py --teste 2026-10-14 (finge que hoje é outra data)
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ANTECEDENCIA = 3  # dias
ARQUIVO = Path(__file__).parent / "conteudo" / "destaques.json"


def hoje_sp():
    # horário de Brasília (UTC-3), sem depender de bibliotecas extras
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()


def a_vencer(hoje):
    itens = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    for i in itens:
        v = str(i.get("vence_em") or "").strip()[:10]
        if not v:
            continue
        try:
            dia = dt.date.fromisoformat(v)
        except ValueError:
            print(f"AVISO: data inválida em '{i.get('titulo')}': {v}")
            continue
        faltam = (dia - hoje).days
        if 0 <= faltam <= ANTECEDENCIA:
            yield i, dia, faltam


def texto(i, dia, faltam):
    quando = "hoje" if faltam == 0 else f"em {faltam} dia{'s' if faltam > 1 else ''}"
    quinzena = ("1ª quinzena: a combinação é trocar agora." if dia.day <= 15
                else "2ª quinzena: decidir se mantém até a virada do mês ou troca agora.")
    titulo = f"Destaque vence {dia:%d/%m/%Y}: {i.get('titulo', '')}"[:240]
    corpo = (f"O destaque **{i.get('titulo', '')}** ({i.get('fonte', '')}) vence {quando}, "
             f"em {dia:%d/%m/%Y}.\n\n"
             f"- {quinzena}\n"
             f"- Para trocar ou apagar, use o painel de conteúdo (Destaques do mês).\n"
             f"- Notícia original: {i.get('link', '')}\n\n"
             f"Depois de resolver, feche este aviso.")
    return titulo, corpo


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def main():
    teste = "--teste" in sys.argv
    datas = [a for a in sys.argv[1:] if a[:2] == "20"]
    hoje = dt.date.fromisoformat(datas[0]) if datas else hoje_sp()
    dono = os.environ.get("DONO", "")
    encontrados = list(a_vencer(hoje))
    print(f"Hoje: {hoje:%d/%m/%Y} · destaques vencendo em até {ANTECEDENCIA} dias: {len(encontrados)}")
    for i, dia, faltam in encontrados:
        titulo, corpo = texto(i, dia, faltam)
        if teste:
            print(f"\n[TESTE] {titulo}\n{corpo}")
            continue
        ja = gh("issue", "list", "--state", "all", "--limit", "500", "--json", "title")
        if any(x["title"] == titulo for x in json.loads(ja or "[]")):
            print(f"Já avisado: {titulo}")
            continue
        cmd = ["issue", "create", "--title", titulo, "--body", corpo]
        if dono:
            cmd += ["--assignee", dono]
        print(gh(*cmd).strip())


if __name__ == "__main__":
    main()
