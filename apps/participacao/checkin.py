"""
Check-in por QR Code.

Cada evento tem um token curto, derivado da SECRET_KEY (HMAC). O QR Code aponta para
/participacao/checkin/<id>/<token>/, então não dá para "adivinhar" o link de check-in.
Para o protótipo isso basta: em produção o token poderia expirar ou girar a cada sessão.
"""
import socket

from django.conf import settings
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac


def token_checkin(evento_id):
    return salted_hmac("checkin-evento", str(evento_id)).hexdigest()[:12]


def token_valido(evento_id, token):
    return constant_time_compare(token_checkin(evento_id), token)


def _ip_rede_local():
    """IP do computador na rede (para o celular conseguir abrir o link do QR Code)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))  # não envia pacotes; só descobre a interface
            return s.getsockname()[0]
    except OSError:
        return None


def url_checkin(request, evento_id):
    caminho = reverse("participacao:checkin", args=[evento_id, token_checkin(evento_id)])
    if settings.URL_PUBLICA:
        return settings.URL_PUBLICA.rstrip("/") + caminho
    host = request.get_host()
    nome, _, porta = host.partition(":")
    if nome in ("127.0.0.1", "localhost"):
        ip = _ip_rede_local()
        if ip:
            host = f"{ip}:{porta}" if porta else ip
    return f"{request.scheme}://{host}{caminho}"
