"""
Cria ou atualiza o administrador da área /painel/ a partir das variáveis de ambiente.

    ADMIN_USUARIO=davi
    ADMIN_SENHA_HASH=pbkdf2_sha256$...   # hash do Django, nunca a senha em texto

Feito para o deploy (Render): o banco SQLite é recriado a cada deploy/reinício, então o
administrador precisa ser recriado na inicialização. Sem as variáveis, não faz nada.

Para gerar o hash de uma senha:
    python -c "from django.contrib.auth.hashers import make_password; print(make_password('SUA_SENHA'))"
(rode com DJANGO_SETTINGS_MODULE=config.settings, ou dentro de `python manage.py shell`).
"""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Cria/atualiza o administrador a partir de ADMIN_USUARIO e ADMIN_SENHA_HASH."

    def handle(self, *args, **opcoes):
        usuario = os.getenv("ADMIN_USUARIO", "").strip()
        senha_hash = os.getenv("ADMIN_SENHA_HASH", "").strip()
        if not usuario or not senha_hash:
            self.stdout.write("ADMIN_USUARIO/ADMIN_SENHA_HASH não definidos; nenhum administrador criado.")
            return
        try:
            identify_hasher(senha_hash)
        except ValueError:
            raise CommandError("ADMIN_SENHA_HASH não é um hash válido do Django (ex.: pbkdf2_sha256$...).")

        conta, criada = get_user_model().objects.get_or_create(username=usuario)
        conta.is_staff = True
        conta.is_active = True
        conta.is_superuser = False
        conta.password = senha_hash
        conta.save()
        self.stdout.write(self.style.SUCCESS(f"Administrador \"{usuario}\" {'criado' if criada else 'atualizado'}."))
