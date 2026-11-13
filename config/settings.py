"""
Configurações do Shopping Pulse (protótipo — Hackarun Palmas).

Decisão importante: o protótipo NÃO usa banco de dados.
- Os dados vêm de arquivos JSON em /data e ficam em memória (apps/eventos/repositorio.py).
- Sessões ficam em cookies assinados, então não precisamos de migrations.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-inseguro-troque-no-env")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "django.contrib.messages",
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

# Sem banco de dados no protótipo
DATABASES = {}
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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Endereço público usado nos QR Codes (ex.: http://192.168.0.10:8000 ou uma URL do ngrok).
# Vazio => usa o endereço acessado; se for localhost, troca pelo IP da rede automaticamente.
URL_PUBLICA = os.getenv("URL_PUBLICA", "")
