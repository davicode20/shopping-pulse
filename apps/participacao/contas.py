"""
Conta opcional do visitante (login e cadastro).

- Visitante sem conta continua navegando e participando, identificado pelo navegador.
- O cadastro cria um usuário do Django com is_staff=False: não dá acesso ao painel.
- O identificador anônimo do visitante (visitante_id) é preservado no login e no logout.
- Ao entrar ou se cadastrar, as interações feitas antes no navegador são MOVIDAS para a conta
  (visitante "conta-<id>"). Se a conta já tiver interesse ou presença para o mesmo evento,
  prevalece o registro da conta, para não contar duas vezes o mesmo visitante.
- Depois do logout, o navegador volta a ser anônimo e não vê mais as interações movidas.
"""
from django.contrib.auth import authenticate
from django.contrib.auth import login as entrar
from django.contrib.auth import logout as sair
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.dashboard.acesso import destino_seguro
from apps.eventos.models import Interacao

MAX_TENTATIVAS = 5
BLOQUEIO = 5 * 60


def _ip(request):
    return request.META.get("REMOTE_ADDR", "desconhecido")


def _vincular_interacoes(anonimo, conta):
    """Move as interações do visitante anônimo para a conta recém-autenticada."""
    if not anonimo or conta.is_staff:
        return
    alvo = f"conta-{conta.pk}"
    with transaction.atomic():
        pendentes = Interacao.objects.filter(visitante=anonimo)
        da_conta = Interacao.objects.filter(visitante=alvo, evento_id=OuterRef("evento_id"), tipo=OuterRef("tipo"))
        # Mesmo tipo e evento já existente na conta: descarta a cópia anônima (a regra é uma por tipo).
        pendentes.exclude(tipo="visualizacao").filter(Exists(da_conta)).delete()
        pendentes.update(visitante=alvo)


def _manter_visitante(request, acao):
    """Executa login/logout sem perder o identificador anônimo do visitante."""
    visitante = request.session.get("visitante_id")
    acao()
    if visitante:
        request.session["visitante_id"] = visitante


def _contexto(modo, **extra):
    return {"modo": modo, **extra}


def conta(request):
    modo = "cadastrar" if request.GET.get("modo") == "cadastrar" else "entrar"
    contexto = _contexto(modo, proximo=destino_seguro(request, request.GET.get("proximo"), reverse("eventos:inicio")))
    if modo == "cadastrar":
        contexto["formulario"] = UserCreationForm()
    return render(request, "visitante/conta.html", contexto)


def entrar_visitante(request):
    if request.method != "POST":
        return redirect("participacao:conta")
    proximo = destino_seguro(request, request.POST.get("proximo"), reverse("eventos:inicio"))
    chave = f"login-visitante-falhas:{_ip(request)}"
    falhas = cache.get(chave, 0)
    usuario = request.POST.get("usuario", "").strip()
    contexto = _contexto("entrar", proximo=proximo, usuario=usuario)

    if falhas >= MAX_TENTATIVAS:
        contexto["erro"] = "Muitas tentativas. Aguarde alguns minutos e tente de novo."
        return render(request, "visitante/conta.html", contexto, status=401)

    conta_usuario = authenticate(request, username=usuario, password=request.POST.get("senha", ""))
    if conta_usuario is None or not conta_usuario.is_active:
        cache.set(chave, falhas + 1, BLOQUEIO)
        contexto["erro"] = "Usuário ou senha incorretos."
        return render(request, "visitante/conta.html", contexto, status=401)

    cache.delete(chave)
    anonimo = request.session.get("visitante_id")
    _manter_visitante(request, lambda: entrar(request, conta_usuario))
    _vincular_interacoes(anonimo, conta_usuario)
    return redirect(proximo)


def cadastrar_visitante(request):
    if request.method != "POST":
        return redirect("participacao:conta")
    proximo = destino_seguro(request, request.POST.get("proximo"), reverse("eventos:inicio"))
    formulario = UserCreationForm(request.POST)
    if not formulario.is_valid():
        return render(request, "visitante/conta.html",
                      _contexto("cadastrar", proximo=proximo, formulario=formulario), status=400)

    # is_staff continua False: o cadastro público nunca cria administradores.
    novo = formulario.save(commit=False)
    novo.is_staff = False
    novo.is_superuser = False
    novo.save()
    anonimo = request.session.get("visitante_id")
    _manter_visitante(request, lambda: entrar(request, novo, backend="django.contrib.auth.backends.ModelBackend"))
    _vincular_interacoes(anonimo, novo)
    return redirect(proximo)


@require_POST
def sair_visitante(request):
    _manter_visitante(request, lambda: sair(request))
    return redirect("participacao:conta")
