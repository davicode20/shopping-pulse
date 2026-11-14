"""
Cria ou troca a senha de um administrador da área /painel/ (usuário do Django com is_staff).

    python manage.py definir_admin                    # pergunta usuário e senha
    python manage.py definir_admin --usuario davi     # pergunta só a senha
    python manage.py definir_admin --hash             # só mostra o hash da senha (para ADMIN_SENHA_HASH no Render)

A senha é guardada como hash pelo Django. O administrador não é superusuário.
"""
import getpass
import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Cria ou atualiza um administrador da área /painel/ (usuário do Django com is_staff)."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", help="nome de usuário do administrador")
        parser.add_argument("--hash", action="store_true",
                            help="não grava nada: pergunta a senha e mostra o hash para ADMIN_SENHA_HASH")

    def handle(self, *args, **opcoes):
        if opcoes["hash"]:
            from django.contrib.auth.hashers import make_password

            self.stdout.write(make_password(self._pedir_senha()))
            return
        usuario = (opcoes["usuario"] or input("Usuário: ")).strip()
        if not re.fullmatch(r"[\w.@-]{2,150}", usuario):
            raise CommandError("Usuário inválido: use letras, números, ponto, hífen ou @ (2 a 150 caracteres).")
        senha = self._pedir_senha()

        modelo = get_user_model()
        conta, criada = modelo.objects.get_or_create(username=usuario)
        conta.is_staff = True
        conta.is_active = True
        conta.is_superuser = False
        conta.set_password(senha)
        conta.save()
        acao = "criado" if criada else "atualizado"
        self.stdout.write(self.style.SUCCESS(f"Administrador \"{usuario}\" {acao}. Pode entrar em /painel/."))

    def _pedir_senha(self):
        senha = getpass.getpass("Senha: ")
        if not senha:
            raise CommandError("A senha não pode ficar vazia.")
        if getpass.getpass("Repita a senha: ") != senha:
            raise CommandError("As senhas não conferem.")
        return senha
