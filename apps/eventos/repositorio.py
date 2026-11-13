"""
Camada de dados do Shopping Pulse (SQLite via Django ORM, decisão D-004).

- Eventos: gravados na tabela Evento. Na primeira execução, são carregados de data/eventos.json.
- Interações (visualização, interesse, check-in, avaliação...): gravadas na tabela Interacao.
- Na primeira execução, uma base SIMULADA é gerada (apps/eventos/simulacao.py) para que o
  painel tenha histórico. Cada interação carrega a flag "simulado", e as interações feitas
  ao vivo na demonstração têm simulado=False.

As funções devolvem dicionários (mesmo formato de antes), para que views e painel não mudem.
"Reiniciar demonstração" apaga tudo e volta aos eventos do JSON com a base simulada.
Para atualizar os eventos a partir do JSON sem apagar nada: python manage.py carregar_eventos
"""
import json
import threading
from datetime import date

from django.conf import settings
from django.utils import timezone

from .models import Evento, Interacao

CATEGORIAS = {
    "gastronomia": "Gastronomia",
    "musica": "Música",
    "tecnologia": "Tecnologia",
    "cultura": "Cultura",
    "esportes": "Esportes",
    "entretenimento": "Entretenimento",
    "infantil": "Infantil",
}

ICONES = {
    "gastronomia": "bi-cup-hot",
    "musica": "bi-music-note-beamed",
    "tecnologia": "bi-controller",
    "cultura": "bi-palette",
    "esportes": "bi-trophy",
    "entretenimento": "bi-film",
    "infantil": "bi-balloon",
}

# Mesmas cores das capas (CSS) e dos gráficos (Chart.js)
CORES = {
    "gastronomia": "#ff6b3d",
    "musica": "#8b3dff",
    "tecnologia": "#1f8bff",
    "cultura": "#e0459b",
    "esportes": "#13b47e",
    "entretenimento": "#f2a900",
    "infantil": "#22c3d6",
}

STATUS = {
    "proposta": "Em validação",
    "confirmado": "Confirmado",
    "realizado": "Realizado",
}

FAIXAS_ETARIAS = {
    "ate17": "Até 17",
    "18-30": "18 a 30",
    "31-45": "31 a 45",
    "46-60": "46 a 60",
    "60+": "60+",
}

MELHORIAS = {
    "horario": "Horário",
    "espaco": "Espaço e conforto",
    "som": "Som e estrutura",
    "divulgacao": "Divulgação",
    "filas": "Filas e organização",
    "preco": "Preços no local",
}

# Tipos de interação
VISUALIZACAO = "visualizacao"
INTERESSE = "interesse"
SEM_INTERESSE = "sem_interesse"
PRESENCA = "presenca_provavel"  # "provavelmente vou comparecer"
CHECKIN = "checkin"
AVALIACAO = "avaliacao"

_CAMPOS_EVENTO = [
    "nome", "descricao", "categoria", "data", "horario", "local",
    "imagem", "informacoes", "status", "investimento_estimado",
]

_trava = threading.RLock()
_pronto = False


# ---------- Conversões ----------

def _como_dict_evento(e):
    return {
        "id": e.id, "nome": e.nome, "descricao": e.descricao, "categoria": e.categoria,
        "data": e.data.isoformat(), "horario": e.horario, "local": e.local, "imagem": e.imagem,
        "informacoes": e.informacoes, "status": e.status,
        "investimento_estimado": e.investimento_estimado,
    }


def _como_dict_interacao(i):
    # O banco guarda com fuso; devolvemos a hora local sem fuso, como o restante do painel espera.
    momento = timezone.localtime(i.momento).replace(tzinfo=None)
    return {
        "tipo": i.tipo, "evento_id": i.evento_id, "visitante": i.visitante,
        "dados": i.dados, "momento": momento, "simulado": i.simulado,
    }


def _campos_evento(dados):
    campos = {k: dados[k] for k in _CAMPOS_EVENTO if k in dados}
    if "data" in campos and isinstance(campos["data"], str):
        campos["data"] = date.fromisoformat(campos["data"])
    return campos


def _com_fuso(momento):
    momento = momento or timezone.now()
    return timezone.make_aware(momento) if timezone.is_naive(momento) else momento


# ---------- Carga inicial e reinício ----------

def carregar_json():
    """Cria ou atualiza os eventos a partir de data/eventos.json (pelo id). Não apaga nada."""
    with open(settings.DATA_DIR / "eventos.json", encoding="utf-8") as arquivo:
        eventos = json.load(arquivo)
    for dados in eventos:
        Evento.objects.update_or_create(id=dados["id"], defaults=_campos_evento(dados))
    return len(eventos)


def _gravar_interacoes(lista):
    # Só usa ORM direto (não as funções públicas), para não disparar _garantir de novo.
    objetos = [
        Interacao(
            evento_id=i["evento_id"], tipo=i["tipo"], visitante=i["visitante"],
            dados=i.get("dados") or {}, momento=_com_fuso(i.get("momento")),
            simulado=i.get("simulado", True),
        )
        for i in lista
    ]
    # Uma interação por tipo e visitante: duplicatas da simulação são descartadas.
    Interacao.objects.bulk_create(objetos, ignore_conflicts=True, batch_size=500)


def _garantir():
    """Na primeira chamada, cria os dados iniciais se o banco ainda não tiver nada."""
    global _pronto
    if _pronto:
        return
    with _trava:
        if _pronto:
            return
        if not Evento.objects.exists():
            carregar_json()
        if not Interacao.objects.exists():
            from .simulacao import gerar_base_simulada

            eventos = [_como_dict_evento(e) for e in Evento.objects.all()]
            _gravar_interacoes(gerar_base_simulada(eventos))
        _pronto = True


def reiniciar():
    """Volta ao estado inicial: eventos do JSON + base simulada. Apaga eventos criados e interações."""
    global _pronto
    with _trava:
        Interacao.objects.all().delete()
        Evento.objects.all().delete()
        _pronto = False
    _garantir()


# ---------- Eventos ----------

def enriquecer(evento):
    """Acrescenta campos de exibição (nome da categoria, ícone, data como objeto...)."""
    try:
        data_obj = date.fromisoformat(evento["data"])
    except (KeyError, ValueError):
        data_obj = None
    return {
        **evento,
        "categoria_nome": CATEGORIAS.get(evento["categoria"], evento["categoria"]),
        "icone": ICONES.get(evento["categoria"], "bi-stars"),
        "cor": CORES.get(evento["categoria"], "#6c2bd9"),
        "status_nome": STATUS.get(evento.get("status"), evento.get("status", "")),
        "data_obj": data_obj,
    }


def listar_eventos(categoria=None, status=None):
    _garantir()
    qs = Evento.objects.all()
    if categoria:
        qs = qs.filter(categoria=categoria)
    if status:
        status = [status] if isinstance(status, str) else status
        qs = qs.filter(status__in=status)
    return [_como_dict_evento(e) for e in qs]


def obter_evento(evento_id):
    _garantir()
    try:
        evento_id = int(evento_id)
    except (TypeError, ValueError):
        return None
    evento = Evento.objects.filter(pk=evento_id).first()
    return _como_dict_evento(evento) if evento else None


def adicionar_evento(dados):
    _garantir()
    with _trava:
        evento = Evento.objects.create(**_campos_evento(dados))
    return _como_dict_evento(evento)


# ---------- Interações ----------

def registrar_interacao(tipo, evento_id, visitante, dados=None, momento=None, simulado=False):
    _garantir()
    campos = {"dados": dados or {}, "momento": _com_fuso(momento), "simulado": simulado}
    if tipo == VISUALIZACAO:
        interacao = Interacao.objects.create(
            tipo=tipo, evento_id=int(evento_id), visitante=visitante, **campos)
    else:
        # Um registro por tipo e visitante: se já existir, vale o mais recente.
        interacao, _ = Interacao.objects.update_or_create(
            tipo=tipo, evento_id=int(evento_id), visitante=visitante, defaults=campos)
    return _como_dict_interacao(interacao)


def remover_interacao(tipo, evento_id, visitante):
    _garantir()
    Interacao.objects.filter(tipo=tipo, evento_id=int(evento_id), visitante=visitante).delete()


def existe_interacao(tipo, evento_id, visitante):
    _garantir()
    return Interacao.objects.filter(tipo=tipo, evento_id=int(evento_id), visitante=visitante).exists()


def registrar_unica(tipo, evento_id, visitante, dados=None):
    """Registra apenas se o visitante ainda não tiver essa interação com o evento."""
    if not existe_interacao(tipo, evento_id, visitante):
        return registrar_interacao(tipo, evento_id, visitante, dados)
    return None


def listar_interacoes(tipo=None, evento_id=None, visitante=None):
    _garantir()
    qs = Interacao.objects.all()
    if tipo:
        qs = qs.filter(tipo__in=[tipo] if isinstance(tipo, str) else tipo)
    if evento_id is not None:
        qs = qs.filter(evento_id=int(evento_id))
    if visitante is not None:
        qs = qs.filter(visitante=visitante)
    return [_como_dict_interacao(i) for i in qs]
