import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# Servidor no ar (gunicorn/Render): já deixa a análise da IA pronta em segundo plano.
# Fica aqui, e não no AppConfig.ready(), para não rodar em migrate, testes e outros comandos.
from apps.inteligencia.servico import pre_aquecer  # noqa: E402

pre_aquecer()
