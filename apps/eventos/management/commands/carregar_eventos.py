from django.core.management.base import BaseCommand

from apps.eventos import repositorio


class Command(BaseCommand):
    help = "Cria ou atualiza os eventos a partir de data/eventos.json (pelo id), sem apagar interações."

    def handle(self, *args, **options):
        total = repositorio.carregar_json()
        self.stdout.write(self.style.SUCCESS(f"{total} eventos carregados do JSON."))
