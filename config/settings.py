"""
Configurações do Shopping Pulse (protótipo — Hackarun Palmas).

Persistência: SQLite (decisão D-004 em docs/DECISOES.md).
- O arquivo db.sqlite3 fica na raiz do projeto e está fora do Git.
- A carga inicial de eventos continua vindo de /data e a camada de dados ainda está em memória
  (apps/eventos/repositorio.py); a migração para o banco é a próxima etapa.
- Sessões continuam em cookies assinados (SESSION_ENGINE abaixo).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-inseguro-troque-no-env")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"

# A SECRET_KEY assina os cookies de sessão (inclusive o login do admin) e os tokens de check-in.
# As chaves de exemplo são públicas no repositório: fora do modo de desenvolvimento, não sobe com elas.
CHAVES_PUBLICAS = {"dev-inseguro-troque-no-env", "troque-esta-chave", ""}
if not DEBUG and SECRET_KEY in CHAVES_PUBLICAS:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "Defina DJANGO_SECRET_KEY no .env. Gere uma com: "
        "python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\""
    )
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    # Apps do projeto
    "apps.eventos",
    "apps.participacao",
    "apps.dashboard",
    "apps.inteligencia",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.projeto",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco SQLite (D-004). Arquivo ignorado pelo Git.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
MESSAGE_STORAGE = "django.contrib.messages.storage.cookie.CookieStorage"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Araguaina"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Projeto
DATA_DIR = BASE_DIR / "data"
NOME_PROJETO = os.getenv("NOME_PROJETO", "Shopping Pulse")
SLOGAN_PROJETO = "Transformando preferências em experiências."

# Inteligência artificial (Gemini). Sem chave => modo demonstração com análises prontas.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
# Reservas (separadas por vírgula), usadas se o principal estiver sobrecarregado ou lento
GEMINI_MODELOS_RESERVA = os.getenv("GEMINI_MODELOS_RESERVA", "gemini-3.5-flash-lite")
GEMINI_TEMPO_LIMITE = int(os.getenv("GEMINI_TEMPO_LIMITE", "35"))  # segundos, para o modelo principal

# Endereço público usado nos QR Codes (ex.: http://192.168.0.10:8000 ou uma URL do ngrok).
# Vazio => usa o endereço acessado; se for localhost, troca pelo IP da rede automaticamente.
URL_PUBLICA = os.getenv("URL_PUBLICA", "")

# Administrador da área /painel/ (protótipo sem banco: um usuário, definido no .env).
# Defina com: python manage.py definir_admin
ADMIN_USUARIO = os.getenv("ADMIN_USUARIO", "")
ADMIN_SENHA_HASH = os.getenv("ADMIN_SENHA_HASH", "")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Miro: exporta as recomendações para o quadro da equipe. Sem token => download em CSV (plano B).
MIRO_ACCESS_TOKEN = os.getenv("MIRO_ACCESS_TOKEN", "")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID", "")  # ID (uXjV...=) ou o link do quadro
