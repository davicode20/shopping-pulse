from django.db import models
from django.db.models import Q


class Evento(models.Model):
    """Evento ou proposta do shopping. Propostas são eventos com status "proposta" (D-004)."""

    CATEGORIAS = [
        ("gastronomia", "Gastronomia"),
        ("musica", "Música"),
        ("tecnologia", "Tecnologia"),
        ("cultura", "Cultura"),
        ("esportes", "Esportes"),
        ("entretenimento", "Entretenimento"),
        ("infantil", "Infantil"),
    ]
    STATUS = [
        ("proposta", "Em validação"),
        ("confirmado", "Confirmado"),
        ("realizado", "Realizado"),
    ]

    nome = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=30, choices=CATEGORIAS)
    data = models.DateField()
    horario = models.CharField(max_length=5, default="00:00")  # "HH:MM", como no JSON
    local = models.CharField(max_length=160, blank=True)
    imagem = models.CharField(max_length=255, blank=True, default="")
    informacoes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="proposta")
    investimento_estimado = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.nome


class Interacao(models.Model):
    """Ação de um visitante (anônimo, identificado pela sessão) sobre um evento."""

    TIPOS = [
        ("visualizacao", "Visualização"),
        ("interesse", "Interesse"),
        ("sem_interesse", "Sem interesse"),
        ("presenca_provavel", "Presença provável"),
        ("checkin", "Check-in"),
        ("avaliacao", "Avaliação"),
    ]

    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="interacoes")
    tipo = models.CharField(max_length=30, choices=TIPOS)
    visitante = models.CharField(max_length=32)
    dados = models.JSONField(default=dict, blank=True)
    momento = models.DateTimeField()
    simulado = models.BooleanField(default=False)

    class Meta:
        ordering = ["momento", "id"]
        indexes = [models.Index(fields=["evento", "tipo"]), models.Index(fields=["visitante"])]
        constraints = [
            # Um visitante tem no máximo uma interação de cada tipo por evento.
            # "visualizacao" pode repetir: é contada por registro_unica no código.
            models.UniqueConstraint(
                fields=["evento", "tipo", "visitante"],
                condition=~Q(tipo="visualizacao"),
                name="interacao_unica_por_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.tipo} · evento {self.evento_id} · {self.visitante}"
