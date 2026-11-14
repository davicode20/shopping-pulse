import logging
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# Servidor no ar (gunicorn/Render). Fica aqui, e não no AppConfig.ready(), para não rodar em testes e comandos.
# 1) Prepara o banco: o SQLite do Render free nasce vazio a cada deploy/reinício. Antes isso dependia do
#    startCommand do render.yaml, mas o painel do Render pode ignorar o arquivo (Blueprint sem sincronizar),
#    e aí a home dava 500 ("no such table") e o deploy expirava no health check.
from django.core.management import call_command  # noqa: E402

call_command("migrate", interactive=False, verbosity=0)
try:
    call_command("admin_do_ambiente")
except Exception:  # hash inválido etc.: o site sobe mesmo assim, só sem o admin
    logging.getLogger(__name__).exception("Não foi possível criar o administrador a partir do ambiente.")

# 2) Já deixa a análise da IA pronta em segundo plano.
from apps.inteligencia.servico import pre_aquecer  # noqa: E402

pre_aquecer()
