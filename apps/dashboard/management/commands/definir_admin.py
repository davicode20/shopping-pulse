"""
Define (ou troca) o usuário e a senha da área administrativa, gravando no .env.

    python manage.py definir_admin                    # pergunta usuário e senha
    python manage.py definir_admin --usuario davi     # pergunta só a senha

A senha é guardada como hash (PBKDF2), nunca em texto puro. Reinicie o servidor depois.
"""
import getpass
import re

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError


def gravar_no_env(caminho, valores):
    linhas = caminho.read_text(encoding="utf-8").splitlines() if caminho.exists() else []
    for chave, valor in valores.items():
        nova = f"{chave}='{valor}'"  # aspas simples: o python-dotenv não interpreta o "$" do hash
        for i, linha in enumerate(linhas):
            if re.match(rf"\s*{chave}\s*=", linha):
                linhas[i] = nova
                break
        else:
            linhas.append(nova)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


class Command(BaseCommand):
    help = "Define o usuário e a senha do administrador (gravados no .env, senha como hash)."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", help="nome de usuário do administrador")

    def handle(self, *args, **opcoes):
        usuario = (opcoes["usuario"] or input("Usuário: ")).strip()
        if not re.fullmatch(r"[\w.@-]{2,40}", usuario):
            raise CommandError("Usuário inválido: use letras, números, ponto, hífen ou @ (2 a 40 caracteres).")
        senha = getpass.getpass("Senha: ")
        if not senha:
            raise CommandError("A senha não pode ficar vazia.")
        if getpass.getpass("Repita a senha: ") != senha:
            raise CommandError("As senhas não conferem.")

        env = settings.BASE_DIR / ".env"
        gravar_no_env(env, {"ADMIN_USUARIO": usuario, "ADMIN_SENHA_HASH": make_password(senha)})
        self.stdout.write(self.style.SUCCESS(f"Administrador \"{usuario}\" salvo em {env.name}. Reinicie o servidor."))
