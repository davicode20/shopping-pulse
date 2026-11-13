"""
Geração de dados SIMULADOS para a demonstração.

Todas as interações criadas aqui têm simulado=True, e o painel deixa isso explícito.
A semente é fixa, então a base é sempre a mesma a cada reinício (útil para ensaiar a apresentação).

Os perfis abaixo descrevem o "comportamento" de cada evento: alcance, interesse,
comparecimento, satisfação e comentários típicos.
"""
import random
import uuid
from datetime import date, datetime, time, timedelta

SEMENTE = 2026

# Distribuição etária do "público geral" do shopping (pool de visitantes simulados)
POOL_TAMANHO = 2500
POOL_FAIXAS = {"ate17": 0.12, "18-30": 0.40, "31-45": 0.28, "46-60": 0.14, "60+": 0.06}

IDADE_PADRAO = {"ate17": 0.10, "18-30": 0.40, "31-45": 0.30, "46-60": 0.14, "60+": 0.06}

# visualizacoes: visitantes únicos que viram o evento
# interesse: % dos que viram e demonstraram interesse
# presenca: % dos interessados que disseram "provavelmente vou" (eventos futuros)
# checkin: % dos interessados que compareceram (eventos realizados)
# nota: média e desvio das avaliações (1 a 5)
PERFIS = {
    1: {"visualizacoes": 1200, "interesse": 0.70, "presenca": 0.381,
        "idade": {"ate17": 0.05, "18-30": 0.65, "31-45": 0.18, "46-60": 0.08, "60+": 0.04}},
    2: {"visualizacoes": 650, "interesse": 0.55, "presenca": 0.35,
        "idade": {"ate17": 0.05, "18-30": 0.45, "31-45": 0.30, "46-60": 0.14, "60+": 0.06}},
    3: {"visualizacoes": 700, "interesse": 0.60, "presenca": 0.40,
        "idade": {"ate17": 0.25, "18-30": 0.55, "31-45": 0.15, "46-60": 0.04, "60+": 0.01}},
    4: {"visualizacoes": 380, "interesse": 0.48, "presenca": 0.45,
        "idade": {"ate17": 0.03, "18-30": 0.25, "31-45": 0.55, "46-60": 0.12, "60+": 0.05}},
    5: {"visualizacoes": 900, "interesse": 0.72, "checkin": 0.46, "nota": (4.6, 0.55),
        "melhorias": {"filas": 0.5, "preco": 0.3, "espaco": 0.2},
        "positivos": ["Melhor evento do ano!", "Os burgers estavam incríveis.",
                      "A votação pelo celular foi muito legal."],
        "negativos": ["Fila muito grande nas hamburguerias.", "Faltou lugar para sentar."]},
    6: {"visualizacoes": 420, "interesse": 0.38, "checkin": 0.30, "nota": (3.1, 0.8),
        "melhorias": {"horario": 0.55, "espaco": 0.5, "som": 0.45},
        "positivos": ["Professores muito animados."],
        "negativos": ["Muito calor no estacionamento.", "Som baixo, não dava para ouvir o professor.",
                      "Horário muito cedo para um domingo."]},
    7: {"visualizacoes": 800, "interesse": 0.62, "checkin": 0.40, "nota": (4.4, 0.6),
        "melhorias": {"espaco": 0.35, "som": 0.25, "divulgacao": 0.2},
        "positivos": ["Programa perfeito para a família.", "Amamos a pipoca grátis!"],
        "negativos": ["O som falhou no começo.", "Poderia ter mais cadeiras."]},
    8: {"visualizacoes": 480, "interesse": 0.50, "checkin": 0.42, "nota": (4.7, 0.45),
        "melhorias": {"divulgacao": 0.6, "horario": 0.2},
        "positivos": ["Lindo valorizar as artesãs do Jalapão.", "A oficina de trançado foi demais."],
        "negativos": ["Fiquei sabendo em cima da hora."]},
    9: {"visualizacoes": 520, "interesse": 0.58, "presenca": 0.42,
        "idade": {"ate17": 0.02, "18-30": 0.38, "31-45": 0.40, "46-60": 0.15, "60+": 0.05}},
    10: {"visualizacoes": 610, "interesse": 0.44, "presenca": 0.30,
         "idade": {"ate17": 0.02, "18-30": 0.50, "31-45": 0.30, "46-60": 0.13, "60+": 0.05}},
    11: {"visualizacoes": 560, "interesse": 0.66, "presenca": 0.55,
         "idade": {"ate17": 0.20, "18-30": 0.18, "31-45": 0.45, "46-60": 0.12, "60+": 0.05}},
    12: {"visualizacoes": 300, "interesse": 0.52, "checkin": 0.55, "nota": (4.8, 0.4),
         "melhorias": {"espaco": 0.4, "horario": 0.2},
         "positivos": ["Aprendi muito sobre café.", "Baristas super atenciosos."],
         "negativos": ["Os grupos lotaram rápido."]},
}

# Usado para eventos cadastrados na hora (botões de simulação do painel)
PERFIL_PADRAO = {
    "interesse": 0.6, "presenca": 0.38, "checkin": 0.42, "nota": (4.4, 0.6),
    "melhorias": {"filas": 0.25, "espaco": 0.25, "divulgacao": 0.2},
    "positivos": ["Gostei muito, quero mais eventos assim!", "Experiência muito bem organizada."],
    "negativos": ["Poderia ter mais estrutura.", "Divulgação chegou tarde."],
}


def _momento_recente(agora, rng, dias=14):
    """Momento nos últimos `dias`, mais concentrado nos dias recentes."""
    dia = agora.date() - timedelta(days=int(dias * rng.random() ** 1.5))
    m = datetime.combine(dia, time(rng.randint(9, 21), rng.randint(0, 59)))
    return m if m <= agora else agora - timedelta(minutes=rng.randint(1, 180))


def _inicio_evento(evento):
    try:
        h, m = map(int, evento.get("horario", "18:00").split(":"))
        return datetime.combine(date.fromisoformat(evento["data"]), time(h, m))
    except (KeyError, ValueError):
        return datetime.now()


def _gerar_para_evento(evento, perfil, visitantes_por_faixa, rng, agora, n_visualizacoes):
    """Cria visualizações, interesses, presença, check-ins e avaliações de um evento."""
    interacoes = []
    eid = evento["id"]
    realizado = evento.get("status") == "realizado"
    inicio = _inicio_evento(evento)

    def momento_pre():
        if realizado:  # engajamento nas duas semanas antes do evento
            m = inicio - timedelta(days=1 + int(13 * rng.random() ** 1.3), hours=rng.randint(0, 10))
            return min(m, agora)
        return _momento_recente(agora, rng)

    def limitar(m):
        """Momentos que cairiam no futuro são espalhados entre o início do evento e agora."""
        if m <= agora:
            return m
        base = min(inicio, agora)
        return base + (agora - base) * rng.random()

    def add(tipo, visitante, momento, dados=None):
        interacoes.append({"tipo": tipo, "evento_id": eid, "visitante": visitante,
                           "dados": dados or {}, "momento": momento, "simulado": True})

    # 1) Quem viu o evento, respeitando o perfil etário
    idade = perfil.get("idade", IDADE_PADRAO)
    vistos = []
    for faixa, share in idade.items():
        grupo = visitantes_por_faixa[faixa]
        qtd = min(round(n_visualizacoes * share), len(grupo))
        vistos += [(v, faixa) for v in rng.sample(grupo, qtd)]
    rng.shuffle(vistos)

    n_interesse = round(len(vistos) * perfil["interesse"])
    interessados, demais = vistos[:n_interesse], vistos[n_interesse:]

    for v, faixa in vistos:
        add("visualizacao", v, momento_pre(), {"faixa_etaria": faixa})
    for v, faixa in interessados:
        add("interesse", v, momento_pre(), {"faixa_etaria": faixa})
    for v, faixa in demais:
        if rng.random() < 0.7:  # a maioria dos que não se interessaram deslizou para a esquerda
            add("sem_interesse", v, momento_pre(), {"faixa_etaria": faixa})

    if not realizado:
        n_presenca = round(len(interessados) * perfil.get("presenca", 0.35))
        for v, faixa in rng.sample(interessados, n_presenca):
            add("presenca_provavel", v, momento_pre(), {"faixa_etaria": faixa})
        return interacoes

    # 2) Evento realizado: check-ins (interessados + alguns que passaram por acaso)
    n_checkin = round(len(interessados) * perfil.get("checkin", 0.4))
    presentes = rng.sample(interessados, n_checkin)
    presentes += rng.sample(demais, min(len(demais), round(n_checkin * 0.12)))
    for v, faixa in presentes:
        m = inicio + timedelta(minutes=rng.randint(-15, 120))
        add("checkin", v, limitar(m), {"faixa_etaria": faixa})

    # 3) Avaliações (cerca de 60% de quem fez check-in)
    media, desvio = perfil.get("nota", (4.3, 0.6))
    for v, faixa in presentes:
        if rng.random() > 0.6:
            continue
        nota = max(1, min(5, round(rng.gauss(media, desvio))))
        if nota >= 4:
            novamente = rng.choices(["sim", "talvez"], [0.85, 0.15])[0]
        elif nota == 3:
            novamente = rng.choices(["sim", "talvez", "nao"], [0.3, 0.5, 0.2])[0]
        else:
            novamente = rng.choices(["talvez", "nao"], [0.3, 0.7])[0]
        peso_melhoria = 0.6 if nota >= 4 else 1.0
        melhorias = [k for k, p in perfil.get("melhorias", {}).items() if rng.random() < p * peso_melhoria]
        pool = perfil.get("positivos" if nota >= 4 else "negativos") or []
        comentario = rng.choice(pool) if pool and rng.random() < 0.35 else ""
        m = inicio + timedelta(hours=2, minutes=rng.randint(0, 48 * 60))
        add("avaliacao", v, limitar(m), {
            "nota": nota, "novamente": novamente, "melhorias": melhorias,
            "comentario": comentario, "faixa_etaria": faixa,
        })
    return interacoes


def _pool_visitantes(rng):
    pool = {}
    contador = 1
    for faixa, share in POOL_FAIXAS.items():
        qtd = round(POOL_TAMANHO * share)
        pool[faixa] = [f"sim-{contador + i:04d}" for i in range(qtd)]
        contador += qtd
    return pool


def gerar_base_simulada(eventos):
    """Base histórica usada na primeira carga (determinística)."""
    rng = random.Random(SEMENTE)
    agora = datetime.now()
    pool = _pool_visitantes(rng)
    interacoes = []
    for evento in eventos:
        perfil = PERFIS.get(evento["id"])
        if perfil:
            interacoes += _gerar_para_evento(evento, perfil, pool, rng, agora, perfil["visualizacoes"])
    return interacoes


def _pool_novo(qtd):
    """Visitantes novos (ids únicos) para as simulações disparadas durante a demonstração."""
    pool = {f: [] for f in POOL_FAIXAS}
    faixas = list(POOL_FAIXAS)
    pesos = list(POOL_FAIXAS.values())
    for _ in range(qtd * 2):
        faixa = random.choices(faixas, pesos)[0]
        pool[faixa].append(f"sim-{uuid.uuid4().hex[:8]}")
    return pool


def simular_engajamento(evento, quantidade=150):
    """Simula visitantes vendo e demonstrando interesse em um evento (últimas horas)."""
    rng = random.Random()
    perfil = {**PERFIL_PADRAO, **PERFIS.get(evento["id"], {})}
    evento_futuro = {**evento, "status": "confirmado"}
    agora = datetime.now()
    novas = _gerar_para_evento(evento_futuro, perfil, _pool_novo(quantidade), rng, agora, quantidade)
    for i in novas:  # concentra nas últimas horas, para aparecer na linha do tempo de hoje
        i["momento"] = agora - timedelta(minutes=rng.randint(1, 240))
    return novas


def simular_realizacao(evento, quantidade=120):
    """Simula o evento acontecendo: check-ins e avaliações de visitantes."""
    rng = random.Random()
    perfil = {**PERFIL_PADRAO, **PERFIS.get(evento["id"], {})}
    agora = datetime.now()
    inicio = agora - timedelta(hours=3)
    evento_passado = {**evento, "status": "realizado",
                      "data": inicio.date().isoformat(), "horario": inicio.strftime("%H:%M")}
    return _gerar_para_evento(evento_passado, perfil, _pool_novo(quantidade), rng, agora, quantidade)
