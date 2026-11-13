from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

import threading
import time

from apps.dashboard.acesso import admin_requerido
from apps.dashboard.metricas import calcular_indicadores

from . import miro
from .servico import gerar_analise


# "Gerar nova análise" chama o Gemini (cota/custo): no máximo uma vez a cada INTERVALO_FORCAR segundos
INTERVALO_FORCAR = 15
_ultima_forcada = {"momento": 0.0}
_trava = threading.Lock()


def _pode_forcar():
    with _trava:
        if time.monotonic() - _ultima_forcada["momento"] < INTERVALO_FORCAR:
            return False
        _ultima_forcada["momento"] = time.monotonic()
        return True


@admin_requerido
def analise(request):
    """Análise da IA em JSON (o painel chama via fetch). ?forcar=1 ignora o cache (com intervalo mínimo)."""
    forcar = request.GET.get("forcar") == "1" and _pode_forcar()
    resultado = gerar_analise(calcular_indicadores(), forcar=forcar)
    return JsonResponse(resultado, json_dumps_params={"ensure_ascii": False})


def _analise_atual():
    indicadores = calcular_indicadores()
    return gerar_analise(indicadores), indicadores  # usa o cache: exporta o que está na tela


@admin_requerido
@require_POST
def exportar_miro(request):
    """Cria no quadro do Miro um frame com a análise atual."""
    try:
        resultado = miro.exportar(*_analise_atual())
    except miro.ErroMiro as erro:
        return JsonResponse({"ok": False, "erro": str(erro)}, status=502)
    return JsonResponse({"ok": True, **resultado})


@admin_requerido
def csv_miro(request):
    """Plano B (sem token): CSV para importar no Miro como sticky notes."""
    conteudo = miro.gerar_csv(*_analise_atual())
    resposta = HttpResponse(conteudo, content_type="text/csv; charset=utf-8")
    nome = f"planejamento-{timezone.localtime():%Y%m%d-%H%M}.csv"
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resposta
