"""Avisos automáticos do site da ABEAA, por e-mail (via GitHub).

Roda todo dia às 8h no GitHub (arquivo .github/workflows/avisos.yml) e abre um aviso
(issue) atribuído ao dono da conta; o GitHub manda o aviso por e-mail.
Cada aviso é aberto uma vez só, mesmo que o programa rode vários dias.
Só avisa: não apaga nem esconde nada do site.

  1. Destaque vencendo: notícia com "vence_em" nos próximos 3 dias.
  2. Fotos e participantes: no dia seguinte ao fim de cada evento da Agenda,
     lembra de mandar as fotos e o número de participantes.
  3. Notícias antigas: toda segunda-feira, lista as notícias com mais de 60 dias
     (menos as da ABEAA, que não vencem e ficam na página Notícias da ABEAA).

Uso local, só para conferir, sem abrir avisos:
    python3 avisos.py --teste            (usa a data de hoje)
    python3 avisos.py --teste 2026-10-27 (finge que hoje é outra data)
"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ANTECEDENCIA = 3      # dias antes do vencimento de um destaque
JANELA_FOTOS = 7      # dias depois do evento em que o lembrete ainda pode ser aberto
IDADE_MAXIMA = 60     # dias de uma notícia no site (regra do BRIEFING)
PASTA = Path(__file__).parent
ARQUIVO = PASTA / "conteudo" / "destaques.json"
PAGINA = PASTA / "index.html"


def hoje_sp():
    # horário de Brasília (UTC-3), sem depender de bibliotecas extras
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()


def destaques():
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def data_de(texto_data):
    try:
        return dt.date.fromisoformat(str(texto_data or "").strip()[:10])
    except ValueError:
        return None


# 1. Destaques vencendo ---------------------------------------------------------
def avisos_vencimento(hoje):
    for i in destaques():
        if not str(i.get("vence_em") or "").strip():
            continue
        dia = data_de(i.get("vence_em"))
        if not dia:
            print(f"AVISO: data inválida em '{i.get('titulo')}': {i.get('vence_em')}")
            continue
        faltam = (dia - hoje).days
        if not 0 <= faltam <= ANTECEDENCIA:
            continue
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
        yield titulo, corpo


# 2. Fotos e participantes depois de cada evento ----------------------------------
EVENTO = re.compile(r'<section data-inicio="([^"]+)" data-fim="([^"]+)"[^>]*>.*?<h2>(.*?)</h2>', re.S)


def avisos_fotos(hoje):
    for inicio, fim, nome in EVENTO.findall(PAGINA.read_text(encoding="utf-8")):
        dia_fim = data_de(fim)
        if not dia_fim:
            continue
        passados = (hoje - dia_fim).days
        if not 1 <= passados <= JANELA_FOTOS:
            continue
        nome = html.unescape(re.sub(r"<[^>]+>", "", nome)).strip()
        titulo = f"Fotos e participantes: {nome} ({dia_fim:%d/%m/%Y})"[:240]
        corpo = (f"O evento **{nome}** terminou em {dia_fim:%d/%m/%Y}. Ele já aparece sozinho em "
                 f"Agenda › Atividades realizadas, com o texto no passado.\n\n"
                 f"Para completar, mande ao Especialista em Sites (Claude Cowork):\n"
                 f"- as fotos (de preferência sem rostos de pessoas que não autorizaram o uso);\n"
                 f"- o número de participantes;\n"
                 f"- se quiser, uma frase sobre como foi.\n\n"
                 f"Depois de mandar, feche este aviso.")
        yield titulo, corpo


# 3. Notícias com mais de 60 dias (toda segunda-feira) ---------------------------
def avisos_antigas(hoje):
    if hoje.weekday() != 0:
        return
    antigas = []
    for i in destaques():
        dia = data_de(i.get("data"))
        if dia and (hoje - dia).days > IDADE_MAXIMA and str(i.get("fonte", "")).strip() != "ABEAA":
            fixa = " (fixada em Em foco)" if i.get("fixar") else ""
            antigas.append(f"- {dia:%d/%m/%Y} · {i.get('fonte', '')} · {i.get('titulo', '')}{fixa}")
    if not antigas:
        return
    titulo = f"Notícias com mais de {IDADE_MAXIMA} dias (semana de {hoje:%d/%m/%Y})"
    corpo = (f"Estas notícias estão no site há mais de {IDADE_MAXIMA} dias, o prazo combinado no BRIEFING:\n\n"
             + "\n".join(antigas)
             + "\n\nNada foi apagado. Decida o que sai (ou peça ao Especialista em Sites "
               "na próxima atualização de notícias) e feche este aviso.")
    yield titulo, corpo


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def main():
    teste = "--teste" in sys.argv
    datas = [a for a in sys.argv[1:] if a[:2] == "20"]
    hoje = dt.date.fromisoformat(datas[0]) if datas else hoje_sp()
    dono = os.environ.get("DONO", "")
    avisos = list(avisos_vencimento(hoje)) + list(avisos_fotos(hoje)) + list(avisos_antigas(hoje))
    print(f"Hoje: {hoje:%d/%m/%Y} · avisos a abrir: {len(avisos)}")
    if not avisos:
        return
    if teste:
        for titulo, corpo in avisos:
            print(f"\n[TESTE] {titulo}\n{corpo}")
        return
    ja = {x["title"] for x in json.loads(
        gh("issue", "list", "--state", "all", "--limit", "1000", "--json", "title") or "[]")}
    for titulo, corpo in avisos:
        if titulo in ja:
            print(f"Já avisado: {titulo}")
            continue
        cmd = ["issue", "create", "--title", titulo, "--body", corpo]
        if dono:
            cmd += ["--assignee", dono]
        print(gh(*cmd).strip())


if __name__ == "__main__":
    main()
