from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.dashboard.metricas import calcular_indicadores

from . import miro
from .servico import gerar_analise


def analise(request):
    """Análise da IA em JSON (o painel chama via fetch). ?forcar=1 ignora o cache."""
    resultado = gerar_analise(calcular_indicadores(), forcar=request.GET.get("forcar") == "1")
    return JsonResponse(resultado, json_dumps_params={"ensure_ascii": False})


def _analise_atual():
    indicadores = calcular_indicadores()
    return gerar_analise(indicadores), indicadores  # usa o cache: exporta o que está na tela


@require_POST
def exportar_miro(request):
    """Cria no quadro do Miro um frame com a análise atual."""
    try:
        resultado = miro.exportar(*_analise_atual())
    except miro.ErroMiro as erro:
        return JsonResponse({"ok": False, "erro": str(erro)}, status=502)
    return JsonResponse({"ok": True, **resultado})


def csv_miro(request):
    """Plano B (sem token): CSV para importar no Miro como sticky notes."""
    conteudo = miro.gerar_csv(*_analise_atual())
    resposta = HttpResponse(conteudo, content_type="text/csv; charset=utf-8")
    nome = f"planejamento-{timezone.localtime():%Y%m%d-%H%M}.csv"
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resposta
