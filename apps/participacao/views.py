"""Participação do visitante: interesse (swipe/botão), presença provável, check-in e avaliação."""
import uuid

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.dashboard.acesso import destino_seguro
from apps.eventos import repositorio as repo

from .checkin import token_valido


def obter_visitante(request):
    """Identifica o visitante: "conta-<id>" se estiver logado como visitante, senão o id anônimo da sessão.

    O id anônimo continua guardado na sessão, mesmo com login, para que o logout volte a ele.
    Administradores não contam como visitantes: as interações feitas por eles não entram nas métricas.
    """
    if "visitante_id" not in request.session:
        request.session["visitante_id"] = uuid.uuid4().hex[:12]
    usuario = request.user
    if usuario.is_authenticated and not usuario.is_staff:
        return f"conta-{usuario.pk}"
    return request.session["visitante_id"]


def dados_visitante(request, **extra):
    """Dados anônimos anexados a cada interação (ex.: faixa etária, se informada)."""
    dados = {"faixa_etaria": request.session.get("faixa_etaria")} if request.session.get("faixa_etaria") else {}
    return {**dados, **extra}


def estado_visitante(visitante):
    """Conjuntos de ids de eventos por tipo de interação do visitante."""
    estado = {t: set() for t in (repo.INTERESSE, repo.SEM_INTERESSE, repo.PRESENCA, repo.CHECKIN, repo.AVALIACAO)}
    for i in repo.listar_interacoes(visitante=visitante):
        if i["tipo"] in estado:
            estado[i["tipo"]].add(i["evento_id"])
    return estado


def _evento_ou_404(evento_id):
    evento = repo.obter_evento(evento_id)
    if not evento:
        raise Http404("Evento não encontrado")
    return evento


def _total_interessados(evento_id):
    return len({i["visitante"] for i in repo.listar_interacoes(repo.INTERESSE, evento_id)})


@require_POST
def interesse(request):
    """acao = interesse | sem_interesse | remover. Usado pelo swipe e pelo botão de coração."""
    evento = _evento_ou_404(request.POST.get("evento_id"))
    acao = request.POST.get("acao", "interesse")
    visitante = obter_visitante(request)

    repo.remover_interacao(repo.INTERESSE, evento["id"], visitante)
    repo.remover_interacao(repo.SEM_INTERESSE, evento["id"], visitante)
    repo.registrar_unica(repo.VISUALIZACAO, evento["id"], visitante, dados_visitante(request))
    if acao == "interesse":
        repo.registrar_interacao(repo.INTERESSE, evento["id"], visitante, dados_visitante(request))
    elif acao == "sem_interesse":
        repo.registrar_interacao(repo.SEM_INTERESSE, evento["id"], visitante, dados_visitante(request))
        repo.remover_interacao(repo.PRESENCA, evento["id"], visitante)
    else:  # remover interesse também remove a presença provável
        repo.remover_interacao(repo.PRESENCA, evento["id"], visitante)

    return JsonResponse({
        "ok": True,
        "interessado": acao == "interesse",
        "total_interessados": _total_interessados(evento["id"]),
    })


@require_POST
def presenca(request):
    """Alterna "provavelmente vou comparecer" (implica interesse)."""
    evento = _evento_ou_404(request.POST.get("evento_id"))
    visitante = obter_visitante(request)
    if repo.existe_interacao(repo.PRESENCA, evento["id"], visitante):
        repo.remover_interacao(repo.PRESENCA, evento["id"], visitante)
        vou = False
    else:
        repo.registrar_interacao(repo.PRESENCA, evento["id"], visitante, dados_visitante(request))
        repo.remover_interacao(repo.SEM_INTERESSE, evento["id"], visitante)
        repo.registrar_unica(repo.INTERESSE, evento["id"], visitante, dados_visitante(request))
        vou = True
    return JsonResponse({"ok": True, "vou": vou, "total_interessados": _total_interessados(evento["id"])})


@require_POST
def perfil(request):
    """Faixa etária opcional (anônima), usada na validação de demanda."""
    faixa = request.POST.get("faixa_etaria")
    if faixa in repo.FAIXAS_ETARIAS:
        request.session["faixa_etaria"] = faixa
    elif faixa == "pular":
        request.session["faixa_etaria"] = ""
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"ok": True})
    return redirect(destino_seguro(request, request.POST.get("proximo"), reverse("eventos:inicio")))


def checkin(request, evento_id, token):
    """Destino do QR Code exibido no local do evento."""
    evento = _evento_ou_404(evento_id)
    if not token_valido(evento["id"], token):
        return render(request, "visitante/checkin.html", {"evento": repo.enriquecer(evento), "situacao": "invalido"})

    visitante = obter_visitante(request)
    if repo.existe_interacao(repo.CHECKIN, evento["id"], visitante):
        situacao = "repetido"
    else:
        repo.registrar_unica(repo.VISUALIZACAO, evento["id"], visitante, dados_visitante(request))
        repo.registrar_interacao(repo.CHECKIN, evento["id"], visitante, dados_visitante(request))
        situacao = "novo"
    return render(request, "visitante/checkin.html", {
        "evento": repo.enriquecer(evento),
        "situacao": situacao,
        "ja_avaliou": repo.existe_interacao(repo.AVALIACAO, evento["id"], visitante),
    })


def avaliar(request, evento_id):
    evento = _evento_ou_404(evento_id)
    visitante = obter_visitante(request)
    contexto = {"evento": repo.enriquecer(evento), "melhorias": repo.MELHORIAS}

    if not repo.existe_interacao(repo.CHECKIN, evento["id"], visitante):
        contexto["sem_checkin"] = True
        return render(request, "visitante/avaliar.html", contexto)

    if request.method == "POST":
        try:
            nota = int(request.POST.get("nota", 0))
        except ValueError:
            nota = 0
        if not 1 <= nota <= 5:
            contexto["erro"] = "Escolha de 1 a 5 estrelas."
            return render(request, "visitante/avaliar.html", contexto)
        novamente = request.POST.get("novamente")
        dados = dados_visitante(
            request,
            nota=nota,
            novamente=novamente if novamente in ("sim", "talvez", "nao") else None,
            melhorias=[m for m in request.POST.getlist("melhorias") if m in repo.MELHORIAS],
            comentario=request.POST.get("comentario", "").strip()[:280],
        )
        repo.remover_interacao(repo.AVALIACAO, evento["id"], visitante)  # vale a última avaliação
        repo.registrar_interacao(repo.AVALIACAO, evento["id"], visitante, dados)
        contexto["enviado"] = True

    return render(request, "visitante/avaliar.html", contexto)
