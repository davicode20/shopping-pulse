"""
Acesso à área administrativa, pelo django.contrib.auth (decisão P-002).

- Administradores são usuários do Django com is_staff=True, criados com `python manage.py definir_admin`.
- O login usa authenticate()/login(); a sessão fica no banco, então o logout invalida a sessão no servidor.
- Visitantes não têm acesso ao painel: a área administrativa exige is_staff.
- Limite de tentativas por IP contra força bruta.
"""
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login as entrar, logout as sair
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

MAX_TENTATIVAS = 5               # erros seguidos por IP...
BLOQUEIO = 5 * 60                # ...bloqueiam novas tentativas por 5 minutos


def admin_logado(request):
    usuario = request.user
    return bool(usuario.is_authenticated and usuario.is_staff and usuario.is_active)


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
    """IP real do visitante. Atrás de um proxy (Render), REMOTE_ADDR é o IP do proxy para todo mundo:
    sem isso, 5 erros de qualquer pessoa bloqueariam o login de todos. O último item do X-Forwarded-For
    é o que o próprio proxy acrescentou (os anteriores podem ser forjados pelo cliente)."""
    if settings.PROXY_CONFIAVEL:
        encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if encaminhado:
            return encaminhado.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "desconhecido")


def _existe_administrador():
    return get_user_model().objects.filter(is_staff=True, is_active=True).exists()


def login(request):
    proximo = destino_seguro(request, request.POST.get("proximo") or request.GET.get("proximo"),
                             reverse("dashboard:painel"))
    if admin_logado(request):
        return redirect(proximo)

    contexto = {"proximo": proximo, "configurado": _existe_administrador()}
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
            # authenticate() confere usuário e senha no mesmo fluxo, sem revelar qual dos dois falhou
            conta = authenticate(request, username=usuario, password=senha)
            if conta is not None and conta.is_staff and conta.is_active:
                cache.delete(chave_tentativas)
                entrar(request, conta)  # troca a chave da sessão a cada login
                return redirect(proximo)
            cache.set(chave_tentativas, falhas + 1, BLOQUEIO)
            contexto["erro"] = "Usuário ou senha incorretos."
        contexto["usuario"] = usuario
    return render(request, "administrativo/login.html", contexto, status=200 if "erro" not in contexto else 401)


@require_POST
def logout(request):
    # Encerra a sessão do administrador no servidor. O logout do Django apaga a sessão inteira,
    # então guardamos o identificador do visitante e o devolvemos: suas interações continuam vinculadas.
    visitante = request.session.get("visitante_id")
    sair(request)
    if visitante:
        request.session["visitante_id"] = visitante
    return redirect("dashboard:login")
