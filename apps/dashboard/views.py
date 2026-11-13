"""Área administrativa: painel de inteligência, eventos e ferramentas da demonstração."""
import io

import qrcode
from django.contrib import messages
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.eventos import repositorio as repo
from apps.eventos import simulacao
from apps.inteligencia import miro
from apps.participacao.checkin import url_checkin

from .forms import EventoForm
from .metricas import detalhe_evento, metricas_por_evento, payload_painel


def painel(request):
    return render(request, "administrativo/painel.html", {
        "dados": payload_painel(), "secao": "painel", "miro_configurado": miro.configurado(),
    })


def dados(request):
    """JSON consultado a cada poucos segundos pelo painel (atualização ao vivo)."""
    return JsonResponse(payload_painel(), json_dumps_params={"ensure_ascii": False})


def eventos(request):
    metricas = metricas_por_evento()
    lista = sorted(metricas.values(), key=lambda m: (m["evento"].get("status") != "proposta", m["evento"]["data"]))
    return render(request, "administrativo/eventos.html", {"metricas": lista, "secao": "eventos"})


def novo_evento(request):
    form = EventoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        evento = repo.adicionar_evento(form.para_evento())
        messages.success(request, f"\"{evento['nome']}\" publicado! Ele já aparece para os visitantes.")
        return redirect("dashboard:evento", evento_id=evento["id"])
    return render(request, "administrativo/evento_form.html", {"form": form, "secao": "eventos"})


def evento(request, evento_id):
    detalhe = detalhe_evento(evento_id)
    if not detalhe:
        raise Http404("Evento não encontrado")
    return render(request, "administrativo/evento_detalhe.html", {
        "m": detalhe,
        "evento": detalhe["evento"],
        "link_checkin": url_checkin(request, evento_id),
        "secao": "eventos",
    })


def qrcode_png(request, evento_id):
    if not repo.obter_evento(evento_id):
        raise Http404("Evento não encontrado")
    imagem = qrcode.make(url_checkin(request, evento_id), box_size=10, border=2)
    buffer = io.BytesIO()
    imagem.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@require_POST
def simular(request, evento_id):
    """Botões da demonstração: gera interações SIMULADAS (identificadas como tal)."""
    evento = repo.obter_evento(evento_id)
    if not evento:
        raise Http404("Evento não encontrado")
    if request.POST.get("tipo") == "realizacao":
        novas = simulacao.simular_realizacao(evento)
        texto = "Simulação: o evento aconteceu, com check-ins e avaliações registrados."
    else:
        novas = simulacao.simular_engajamento(evento)
        texto = "Simulação: novos visitantes viram a proposta e demonstraram interesse."
    for i in novas:
        repo.registrar_interacao(i["tipo"], i["evento_id"], i["visitante"], i["dados"], i["momento"], simulado=True)
    messages.info(request, f"{texto} ({len(novas)} interações simuladas)")
    return redirect("dashboard:evento", evento_id=evento["id"])


@require_POST
def reiniciar(request):
    repo.reiniciar()
    messages.success(request, "Demonstração reiniciada: dados de volta ao estado inicial.")
    return redirect("dashboard:painel")
