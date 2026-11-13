from django.http import JsonResponse

from apps.dashboard.metricas import calcular_indicadores

from .servico import gerar_analise


def analise(request):
    """Análise da IA em JSON (o painel chama via fetch). ?forcar=1 ignora o cache."""
    resultado = gerar_analise(calcular_indicadores(), forcar=request.GET.get("forcar") == "1")
    return JsonResponse(resultado, json_dumps_params={"ensure_ascii": False})
