"""
Acesso à área administrativa (protótipo sem banco de dados).

- Um único administrador, definido no .env: ADMIN_USUARIO e ADMIN_SENHA_HASH
  (gerado com `python manage.py definir_admin`; a senha nunca fica em texto puro).
- O login fica na sessão, que é um cookie ASSINADO com a SECRET_KEY. Por isso a chave
  precisa ser secreta: com a chave pública, qualquer um forjaria o cookie de admin.
- Limite de tentativas por IP contra força bruta.

Quando o projeto ganhar banco de dados, basta trocar este módulo pelo django.contrib.auth:
as views continuam usando o mesmo decorator @admin_requerido.
"""
import time
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

CHAVE_SESSAO = "admin"
DURACAO_SESSAO = 12 * 3600       # o login vale por 12 horas
MAX_TENTATIVAS = 5               # erros seguidos por IP...
BLOQUEIO = 5 * 60                # ...bloqueiam novas tentativas por 5 minutos


def admin_logado(request):
    dados = request.session.get(CHAVE_SESSAO)
    if not isinstance(dados, dict) or not settings.ADMIN_USUARIO:
        return False
    valido = (constant_time_compare(str(dados.get("usuario", "")), settings.ADMIN_USUARIO)
              and time.time() - dados.get("desde", 0) < DURACAO_SESSAO)
    if not valido:
        request.session.pop(CHAVE_SESSAO, None)
    return valido


def _quer_json(request):
    return (request.headers.get("x-requested-with") == "fetch"
            or "application/json" in request.headers.get("accept", "")
            or request.path.endswith(".json"))


def admin_requerido(view):
    """Protege uma view: páginas redirecionam para o login; chamadas fetch/JSON recebem 401."""
    @wraps(view)
    def protegida(request, *args, **kwargs):
        if admin_logado(request):
            return view(request, *args, **kwargs)
        url_login = reverse("dashboard:login")
        if _quer_json(request):
            return JsonResponse({"ok": False, "erro": "Sessão expirada. Entre novamente.", "login": url_login}, status=401)
        destino = request.get_full_path() if request.method == "GET" else reverse("dashboard:painel")
        return redirect(f"{url_login}?{urlencode({'proximo': destino})}")
    return protegida


def destino_seguro(request, url, padrao):
    """Só aceita redirecionar para o próprio site (evita open redirect)."""
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return url
    return padrao


def _ip(request):
    return request.META.get("REMOTE_ADDR", "desconhecido")


def login(request):
    proximo = destino_seguro(request, request.POST.get("proximo") or request.GET.get("proximo"),
                             reverse("dashboard:painel"))
    if admin_logado(request):
        return redirect(proximo)

    contexto = {"proximo": proximo, "configurado": bool(settings.ADMIN_USUARIO and settings.ADMIN_SENHA_HASH)}
    chave_tentativas = f"login-falhas:{_ip(request)}"

    if request.method == "POST":
        falhas = cache.get(chave_tentativas, 0)
        usuario = request.POST.get("usuario", "").strip()
        senha = request.POST.get("senha", "")
        if falhas >= MAX_TENTATIVAS:
            contexto["erro"] = "Muitas tentativas. Aguarde alguns minutos e tente de novo."
        elif not contexto["configurado"]:
            contexto["erro"] = "Acesso não configurado. Rode: python manage.py definir_admin"
        else:
            # confere usuário e senha sempre (mesmo com usuário errado), para não revelar qual dos dois falhou
            usuario_ok = constant_time_compare(usuario.lower(), settings.ADMIN_USUARIO.lower())
            senha_ok = check_password(senha, settings.ADMIN_SENHA_HASH)
            if usuario_ok and senha_ok:
                cache.delete(chave_tentativas)
                request.session.cycle_key()  # novo cookie a cada login
                request.session[CHAVE_SESSAO] = {"usuario": settings.ADMIN_USUARIO, "desde": time.time()}
                return redirect(proximo)
            cache.set(chave_tentativas, falhas + 1, BLOQUEIO)
            contexto["erro"] = "Usuário ou senha incorretos."
        contexto["usuario"] = usuario
    return render(request, "administrativo/login.html", contexto, status=200 if "erro" not in contexto else 401)


@require_POST
def logout(request):
    # remove só o login: o visitante anônimo (se for o mesmo navegador) continua com suas interações
    request.session.pop(CHAVE_SESSAO, None)
    request.session.cycle_key()
    return redirect("dashboard:login")
