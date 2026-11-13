"""
Camada de dados do protótipo (sem banco de dados).

- Eventos: carregados de data/eventos.json e mantidos em memória.
- Interações (visualização, interesse, check-in, avaliação...): guardadas em memória.
- Na primeira carga, uma base SIMULADA é gerada (apps/eventos/simulacao.py) para que o
  painel tenha histórico. Cada interação carrega a flag "simulado", e as interações feitas
  ao vivo na demonstração têm simulado=False.

Tudo volta ao estado inicial ao reiniciar o servidor (ou pelo botão "Reiniciar demonstração").
Se depois precisarmos persistir, basta trocar as funções deste módulo.
"""
import json
import threading
from datetime import date, datetime

from django.conf import settings

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

_trava = threading.Lock()
_eventos = None
_interacoes = []  # {"tipo", "evento_id", "visitante", "dados", "momento", "simulado"}


def _carregar():
    global _eventos
    if _eventos is None:
        with _trava:
            if _eventos is None:
                with open(settings.DATA_DIR / "eventos.json", encoding="utf-8") as arquivo:
                    eventos = json.load(arquivo)
                _interacoes.clear()
                from .simulacao import gerar_base_simulada

                _interacoes.extend(gerar_base_simulada(eventos))
                _eventos = eventos
    return _eventos


def reiniciar():
    """Volta ao estado inicial (eventos do JSON + base simulada)."""
    global _eventos
    _eventos = None
    _carregar()


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
    eventos = _carregar()
    if categoria:
        eventos = [e for e in eventos if e["categoria"] == categoria]
    if status:
        status = [status] if isinstance(status, str) else status
        eventos = [e for e in eventos if e.get("status") in status]
    return list(eventos)


def obter_evento(evento_id):
    try:
        evento_id = int(evento_id)
    except (TypeError, ValueError):
        return None
    return next((e for e in _carregar() if e["id"] == evento_id), None)


def adicionar_evento(dados):
    eventos = _carregar()
    with _trava:
        novo = {"imagem": "", **dados, "id": max((e["id"] for e in eventos), default=0) + 1}
        eventos.append(novo)
    return novo


# ---------- Interações ----------

def registrar_interacao(tipo, evento_id, visitante, dados=None, momento=None, simulado=False):
    _carregar()
    interacao = {
        "tipo": tipo,
        "evento_id": int(evento_id),
        "visitante": visitante,
        "dados": dados or {},
        "momento": momento or datetime.now(),
        "simulado": simulado,
    }
    with _trava:
        _interacoes.append(interacao)
    return interacao


def remover_interacao(tipo, evento_id, visitante):
    _carregar()
    with _trava:
        _interacoes[:] = [
            i for i in _interacoes
            if not (i["tipo"] == tipo and i["evento_id"] == int(evento_id) and i["visitante"] == visitante)
        ]


def existe_interacao(tipo, evento_id, visitante):
    return any(
        i["tipo"] == tipo and i["evento_id"] == int(evento_id) and i["visitante"] == visitante
        for i in _carregar_interacoes()
    )


def registrar_unica(tipo, evento_id, visitante, dados=None):
    """Registra apenas se o visitante ainda não tiver essa interação com o evento."""
    if not existe_interacao(tipo, evento_id, visitante):
        return registrar_interacao(tipo, evento_id, visitante, dados)
    return None


def _carregar_interacoes():
    _carregar()
    return _interacoes


def listar_interacoes(tipo=None, evento_id=None, visitante=None):
    resultado = list(_carregar_interacoes())
    if tipo:
        tipos = [tipo] if isinstance(tipo, str) else tipo
        resultado = [i for i in resultado if i["tipo"] in tipos]
    if evento_id is not None:
        resultado = [i for i in resultado if i["evento_id"] == int(evento_id)]
    if visitante is not None:
        resultado = [i for i in resultado if i["visitante"] == visitante]
    return resultado
