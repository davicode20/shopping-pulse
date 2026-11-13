"""Área do visitante (mobile first)."""
from collections import Counter

from django.http import Http404
from django.shortcuts import render

from apps.participacao.views import dados_visitante, estado_visitante, obter_visitante

from . import repositorio as repo

PROXIMOS = ["proposta", "confirmado"]  # eventos que ainda vão acontecer


def _contagem_interessados():
    contagem = Counter()
    vistos = set()
    for i in repo.listar_interacoes(repo.INTERESSE):
        chave = (i["evento_id"], i["visitante"])
        if chave not in vistos:
            vistos.add(chave)
            contagem[i["evento_id"]] += 1
    return contagem


def _preparar(eventos, estado, contagem):
    """Evento + campos de exibição + situação do visitante atual."""
    return [{
        **repo.enriquecer(e),
        "interessado": e["id"] in estado[repo.INTERESSE],
        "vou": e["id"] in estado[repo.PRESENCA],
        "fez_checkin": e["id"] in estado[repo.CHECKIN],
        "avaliou": e["id"] in estado[repo.AVALIACAO],
        "total_interessados": contagem.get(e["id"], 0),
    } for e in eventos]


def recomendar(estado, contagem, limite=4):
    """Recomendação simples e explicável: categorias que o visitante curtiu + popularidade."""
    eventos = {e["id"]: e for e in repo.listar_eventos()}
    pontos = Counter()
    pesos = {repo.INTERESSE: 2, repo.PRESENCA: 3, repo.CHECKIN: 1, repo.SEM_INTERESSE: -1.5}
    for tipo, peso in pesos.items():
        for eid in estado[tipo]:
            if eid in eventos:
                pontos[eventos[eid]["categoria"]] += peso

    ja_vistos = estado[repo.INTERESSE] | estado[repo.SEM_INTERESSE]
    candidatos = [e for e in repo.listar_eventos(status=PROXIMOS) if e["id"] not in ja_vistos]
    maximo = max(contagem.values(), default=1)
    candidatos.sort(key=lambda e: pontos[e["categoria"]] + contagem.get(e["id"], 0) / maximo, reverse=True)

    saida = []
    for e in candidatos[:limite]:
        item = _preparar([e], estado, contagem)[0]
        if pontos[e["categoria"]] > 0:
            item["motivo"] = f"Porque você curtiu {item['categoria_nome']}"
        else:
            item["motivo"] = "Em alta no shopping"
        saida.append(item)
    return saida


def inicio(request):
    visitante = obter_visitante(request)
    estado = estado_visitante(visitante)
    contagem = _contagem_interessados()
    categoria = request.GET.get("categoria")
    if categoria not in repo.CATEGORIAS:
        categoria = None

    eventos = repo.listar_eventos(categoria, status=PROXIMOS)
    eventos.sort(key=lambda e: e["data"])
    personalizado = bool(estado[repo.INTERESSE] or estado[repo.SEM_INTERESSE])

    contexto = {
        "eventos": _preparar(eventos, estado, contagem),
        "recomendados": recomendar(estado, contagem, 6) if not categoria else [],
        "personalizado": personalizado,
        "categorias": {k: {"nome": v, "icone": repo.ICONES[k]} for k, v in repo.CATEGORIAS.items()},
        "categoria_atual": categoria,
        "perguntar_faixa": "faixa_etaria" not in request.session,
        "faixas": repo.FAIXAS_ETARIAS,
        "total_propostas": len(repo.listar_eventos(status="proposta")),
        "aba": "inicio",
    }
    return render(request, "visitante/inicio.html", contexto)


def descobrir(request):
    """Cartões no estilo "swipe": direita = interesse, esquerda = sem interesse."""
    visitante = obter_visitante(request)
    estado = estado_visitante(visitante)
    contagem = _contagem_interessados()
    ja_vistos = estado[repo.INTERESSE] | estado[repo.SEM_INTERESSE]
    eventos = [e for e in repo.listar_eventos(status=PROXIMOS) if e["id"] not in ja_vistos]
    eventos.sort(key=lambda e: (e.get("status") != "proposta", e["data"]))
    return render(request, "visitante/descobrir.html", {
        "eventos": _preparar(eventos, estado, contagem),
        "perguntar_faixa": "faixa_etaria" not in request.session,
        "faixas": repo.FAIXAS_ETARIAS,
        "aba": "descobrir",
    })


def detalhe(request, evento_id):
    evento = repo.obter_evento(evento_id)
    if not evento:
        raise Http404("Evento não encontrado")
    visitante = obter_visitante(request)
    repo.registrar_unica(repo.VISUALIZACAO, evento["id"], visitante, dados_visitante(request))
    estado = estado_visitante(visitante)
    contagem = _contagem_interessados()
    relacionados = [e for e in repo.listar_eventos(evento["categoria"], status=PROXIMOS) if e["id"] != evento["id"]]
    return render(request, "visitante/detalhe.html", {
        "evento": _preparar([evento], estado, contagem)[0],
        "relacionados": _preparar(relacionados[:3], estado, contagem),
        "aba": "propostas" if evento.get("status") == "proposta" else "inicio",
    })


def propostas(request):
    """Validação de demanda: o shopping pergunta antes de investir."""
    visitante = obter_visitante(request)
    estado = estado_visitante(visitante)
    contagem = _contagem_interessados()
    eventos = sorted(repo.listar_eventos(status="proposta"), key=lambda e: -contagem.get(e["id"], 0))
    return render(request, "visitante/propostas.html", {
        "eventos": _preparar(eventos, estado, contagem),
        "perguntar_faixa": "faixa_etaria" not in request.session,
        "faixas": repo.FAIXAS_ETARIAS,
        "aba": "propostas",
    })


def agenda(request):
    visitante = obter_visitante(request)
    estado = estado_visitante(visitante)
    contagem = _contagem_interessados()
    todos = {e["id"]: e for e in repo.listar_eventos()}
    interesses = sorted((todos[i] for i in estado[repo.INTERESSE] if i in todos), key=lambda e: e["data"])
    participados = [todos[i] for i in estado[repo.CHECKIN] if i in todos]

    cats = Counter(todos[i]["categoria"] for i in estado[repo.INTERESSE] if i in todos)
    perfil = [{"nome": repo.CATEGORIAS[c], "icone": repo.ICONES[c], "qtd": q} for c, q in cats.most_common(3)]

    return render(request, "visitante/agenda.html", {
        "interesses": _preparar(interesses, estado, contagem),
        "participados": _preparar(participados, estado, contagem),
        "recomendados": recomendar(estado, contagem, 4),
        "perfil": perfil,
        "aba": "agenda",
    })
