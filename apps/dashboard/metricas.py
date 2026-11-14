"""
Cálculo dos indicadores do painel.

Regra do projeto: os números são calculados AQUI, pela aplicação.
A IA apenas interpreta esses resultados (apps/inteligencia/servico.py).
"""
import threading
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from apps.eventos import repositorio as repo


def _pct(parte, total):
    return round(parte / total * 100, 1) if total else 0


def _media(valores):
    return round(sum(valores) / len(valores), 1) if valores else None


def _agrupar():
    """Uma passada pelas interações: visitantes únicos por (evento, tipo) + avaliações."""
    unicos = defaultdict(lambda: defaultdict(set))  # eid -> tipo -> {visitantes}
    avaliacoes = defaultdict(dict)  # eid -> visitante -> dados (a última avaliação vale)
    for i in repo.listar_interacoes():
        unicos[i["evento_id"]][i["tipo"]].add(i["visitante"])
        if i["tipo"] == repo.AVALIACAO:
            avaliacoes[i["evento_id"]][i["visitante"]] = i["dados"]
    return unicos, avaliacoes


def metricas_por_evento():
    unicos, avaliacoes = _agrupar()
    resultado = {}
    for evento in repo.listar_eventos():
        eid = evento["id"]
        u = unicos.get(eid, {})
        alcance = set().union(*u.values()) if u else set()
        interessados = len(u.get(repo.INTERESSE, ()))
        sem = len(u.get(repo.SEM_INTERESSE, ()))
        checkins = len(u.get(repo.CHECKIN, ()))
        avs = list(avaliacoes.get(eid, {}).values())
        notas = [a["nota"] for a in avs if a.get("nota")]
        novamente = Counter(a.get("novamente") for a in avs if a.get("novamente"))
        melhorias = Counter(m for a in avs for m in a.get("melhorias", []))
        investimento = evento.get("investimento_estimado") or 0
        resultado[eid] = {
            "evento": repo.enriquecer(evento),
            "visualizacoes": len(alcance),
            "interessados": interessados,
            "sem_interesse": sem,
            "presenca_provavel": len(u.get(repo.PRESENCA, ())),
            "checkins": checkins,
            "avaliacoes": len(avs),
            "nota_media": _media(notas),
            "aprovacao": _pct(interessados, interessados + sem),
            "comparecimento": _pct(checkins, interessados) if checkins else None,
            "novamente_pct": _pct(novamente.get("sim", 0), len(avs)) if avs else None,
            "melhorias": dict(melhorias.most_common()),
            "investimento": investimento,
            "custo_por_interessado": round(investimento / interessados, 2) if investimento and interessados else None,
        }
    return resultado


# Cache por versão dos dados (repo.versao()) e dia: o painel consulta a cada 5 s, mas só
# recalcula quando algo muda. Antes, cada consulta lia ~16 mil interações três vezes, o que no
# Render free levava segundos de CPU e derrubava o health check (502).
_cache = {}
_trava_cache = threading.RLock()  # reentrante: o payload chama calcular_indicadores()


def _em_cache(nome, calcular):
    chave = (repo.versao(), date.today())
    with _trava_cache:
        guardado = _cache.get(nome)
        if guardado and guardado[0] == chave:
            return guardado[1]
        valor = calcular()
        # a versão pode ter mudado durante o cálculo: guarda com a de antes (recalcula na próxima)
        _cache[nome] = (chave, valor)
        return valor


def calcular_indicadores():
    return _em_cache("indicadores", _calcular_indicadores)


def _calcular_indicadores():
    """Indicadores gerais + por categoria + por evento (tudo serializável em JSON)."""
    por_evento = metricas_por_evento()
    interacoes = repo.listar_interacoes()
    notas = [m["nota_media"] for m in por_evento.values() if m["nota_media"]]
    todas_notas = []
    for i in interacoes:
        if i["tipo"] == repo.AVALIACAO and i["dados"].get("nota"):
            todas_notas.append(i["dados"]["nota"])

    com_checkin = [m for m in por_evento.values() if m["checkins"]]
    engajados = {i["visitante"] for i in interacoes if i["tipo"] != repo.VISUALIZACAO}

    # Por categoria
    categorias = []
    for chave, nome in repo.CATEGORIAS.items():
        ms = [m for m in por_evento.values() if m["evento"]["categoria"] == chave]
        if not ms:
            continue
        inter = sum(m["interessados"] for m in ms)
        sem = sum(m["sem_interesse"] for m in ms)
        notas_cat = [m["nota_media"] for m in ms if m["nota_media"]]
        categorias.append({
            "chave": chave, "nome": nome, "cor": repo.CORES[chave],
            "eventos": len(ms),
            "interessados": inter,
            "aprovacao": _pct(inter, inter + sem),
            "checkins": sum(m["checkins"] for m in ms),
            "nota_media": _media(notas_cat),
        })
    categorias.sort(key=lambda c: c["interessados"], reverse=True)

    eventos = []
    for m in por_evento.values():
        e = m["evento"]
        eventos.append({
            "id": e["id"], "nome": e["nome"], "categoria": e["categoria_nome"],
            "status": e.get("status"), "data": e.get("data"),
            **{k: m[k] for k in ("visualizacoes", "interessados", "presenca_provavel", "checkins",
                                 "avaliacoes", "nota_media", "aprovacao", "comparecimento",
                                 "novamente_pct", "investimento", "custo_por_interessado")},
            "principais_melhorias": [repo.MELHORIAS.get(k, k) for k in list(m["melhorias"])[:2]],
        })
    eventos.sort(key=lambda e: e["interessados"], reverse=True)

    total_interesses = sum(m["interessados"] for m in por_evento.values())
    total_checkins = sum(m["checkins"] for m in por_evento.values())

    return {
        "total_eventos": len(por_evento),
        "eventos_por_status": dict(Counter(m["evento"].get("status") for m in por_evento.values())),
        "visitantes_engajados": len(engajados),
        "total_interesses": total_interesses,
        "total_presenca_provavel": sum(m["presenca_provavel"] for m in por_evento.values()),
        "total_checkins": total_checkins,
        # comparecimento só considera eventos que já tiveram check-in
        "taxa_comparecimento": _pct(sum(m["checkins"] for m in com_checkin),
                                    sum(m["interessados"] for m in com_checkin)),
        "total_avaliacoes": len(todas_notas),
        "media_satisfacao": round(sum(todas_notas) / len(todas_notas), 1) if todas_notas else 0,
        "melhor_nota_evento": max(notas) if notas else None,
        "interacoes_reais": sum(1 for i in interacoes if not i["simulado"]),
        "categorias": categorias,
        "eventos": eventos,
        "validacao_demanda": validacao_demanda(por_evento),
        "alertas": alertas(por_evento),
    }


def _faixas_interessados(evento_id):
    faixas = Counter()
    vistos = set()
    for i in repo.listar_interacoes(repo.INTERESSE, evento_id):
        if i["visitante"] not in vistos:
            vistos.add(i["visitante"])
            faixas[i["dados"].get("faixa_etaria") or "nao_informado"] += 1
    return faixas


def validacao_demanda(por_evento=None):
    """Propostas publicadas para validar a demanda antes do investimento."""
    por_evento = por_evento or metricas_por_evento()
    propostas = []
    for m in por_evento.values():
        e = m["evento"]
        if e.get("status") != "proposta":
            continue
        faixas = _faixas_interessados(e["id"])
        informadas = {k: v for k, v in faixas.items() if k != "nao_informado"}
        total_inf = sum(informadas.values())
        principal = max(informadas, key=informadas.get) if informadas else None
        propostas.append({
            "id": e["id"], "nome": e["nome"], "categoria": e["categoria_nome"],
            "investimento": m["investimento"],
            "visualizacoes": m["visualizacoes"],
            "interessados": m["interessados"],
            "presenca_provavel": m["presenca_provavel"],
            "conversao_interesse": _pct(m["interessados"], m["visualizacoes"]),
            "custo_por_interessado": m["custo_por_interessado"],
            "custo_por_presenca": round(m["investimento"] / m["presenca_provavel"], 2)
            if m["investimento"] and m["presenca_provavel"] else None,
            "faixa_principal": repo.FAIXAS_ETARIAS.get(principal) if principal else None,
            "faixa_principal_pct": _pct(informadas.get(principal, 0), total_inf) if principal else None,
        })
    propostas.sort(key=lambda p: p["interessados"], reverse=True)
    return propostas


def alertas(por_evento):
    """Regras simples e transparentes que destacam o que merece atenção."""
    lista = []
    for m in por_evento.values():
        e = m["evento"]
        if m["nota_media"] is not None and m["avaliacoes"] >= 5 and m["nota_media"] < 3.8:
            top = [repo.MELHORIAS.get(k, k) for k in list(m["melhorias"])[:2]]
            lista.append({"tipo": "satisfacao_baixa", "evento": e["nome"], "nota": m["nota_media"],
                          "melhorias": top})
        if m["comparecimento"] is not None and m["comparecimento"] < 25 and m["interessados"] >= 20:
            lista.append({"tipo": "comparecimento_baixo", "evento": e["nome"],
                          "comparecimento": m["comparecimento"]})
    return lista


def serie_temporal(dias=21):
    """Interações por dia (interesses, check-ins, avaliações) nos últimos `dias`."""
    hoje = date.today()
    inicio = hoje - timedelta(days=dias - 1)
    contagem = {t: Counter() for t in (repo.INTERESSE, repo.CHECKIN, repo.AVALIACAO)}
    for i in repo.listar_interacoes(list(contagem)):
        d = i["momento"].date()
        if inicio <= d <= hoje:
            contagem[i["tipo"]][d] += 1
    datas = [inicio + timedelta(days=n) for n in range(dias)]
    return {
        "labels": [d.strftime("%d/%m") for d in datas],
        "interesses": [contagem[repo.INTERESSE][d] for d in datas],
        "checkins": [contagem[repo.CHECKIN][d] for d in datas],
        "avaliacoes": [contagem[repo.AVALIACAO][d] for d in datas],
    }


TEXTO_ATIVIDADE = {
    repo.INTERESSE: ("bi-heart-fill", "demonstrou interesse em"),
    repo.SEM_INTERESSE: ("bi-x-lg", "passou"),
    repo.PRESENCA: ("bi-calendar-check", "pretende ir a"),
    repo.CHECKIN: ("bi-qr-code-scan", "fez check-in em"),
    repo.AVALIACAO: ("bi-star-fill", "avaliou"),
}


def atividade_recente(limite=8):
    eventos = {e["id"]: e["nome"] for e in repo.listar_eventos()}
    recentes = [i for i in repo.listar_interacoes(list(TEXTO_ATIVIDADE))]
    recentes.sort(key=lambda i: i["momento"], reverse=True)
    agora = datetime.now()
    saida = []
    for i in recentes[:limite]:
        icone, verbo = TEXTO_ATIVIDADE[i["tipo"]]
        minutos = int((agora - i["momento"]).total_seconds() // 60)
        quando = "agora" if minutos < 1 else f"há {minutos} min" if minutos < 60 else \
            f"há {minutos // 60} h" if minutos < 1440 else f"há {minutos // 1440} d"
        extra = f" · nota {i['dados']['nota']}" if i["tipo"] == repo.AVALIACAO else ""
        saida.append({
            "icone": icone, "tipo": i["tipo"], "quando": quando, "ao_vivo": not i["simulado"],
            "texto": f"{verbo} {eventos.get(i['evento_id'], 'evento')}{extra}",
        })
    return saida


def payload_painel():
    """Tudo o que o dashboard precisa (renderização inicial e atualização ao vivo)."""
    return {**_em_cache("payload", _payload_painel), "atualizado_em": datetime.now().strftime("%H:%M:%S")}


def _payload_painel():
    ind = calcular_indicadores()
    top = ind["eventos"][:8]
    cats = [c for c in ind["categorias"] if c["interessados"]]
    return {
        "kpis": {k: ind[k] for k in (
            "total_eventos", "visitantes_engajados", "total_interesses", "total_checkins",
            "taxa_comparecimento", "media_satisfacao", "total_avaliacoes", "interacoes_reais")},
        "eventos_por_status": ind["eventos_por_status"],
        "top_eventos": {
            "labels": [e["nome"] for e in top],
            "interessados": [e["interessados"] for e in top],
            "checkins": [e["checkins"] for e in top],
        },
        "categorias": {
            "labels": [c["nome"] for c in cats],
            "valores": [c["interessados"] for c in cats],
            "cores": [c["cor"] for c in cats],
            "aprovacao": [c["aprovacao"] for c in cats],
        },
        "serie": serie_temporal(),
        "eventos": ind["eventos"],
        "validacao": ind["validacao_demanda"],
        "alertas": ind["alertas"],
        "atividade": atividade_recente(),
        "atualizado_em": datetime.now().strftime("%H:%M:%S"),
    }


def detalhe_evento(evento_id):
    """Métricas completas de um evento (página de detalhe no painel)."""
    m = metricas_por_evento().get(int(evento_id))
    if not m:
        return None
    faixas = _faixas_interessados(evento_id)
    avaliacoes = {}
    for i in repo.listar_interacoes(repo.AVALIACAO, evento_id):
        avaliacoes[i["visitante"]] = i
    avs = sorted(avaliacoes.values(), key=lambda i: i["momento"], reverse=True)
    distribuicao = Counter(a["dados"].get("nota") for a in avs)
    novamente = Counter(a["dados"].get("novamente") for a in avs)
    comentarios = [
        {"texto": a["dados"]["comentario"], "nota": a["dados"].get("nota"),
         "momento": a["momento"], "ao_vivo": not a["simulado"]}
        for a in sorted(avs, key=lambda a: (a["simulado"], -a["momento"].timestamp()))  # reais primeiro
        if a["dados"].get("comentario")
    ][:8]
    return {
        **m,
        "funil": [e for e in [
            {"etapa": "Visualizaram", "valor": m["visualizacoes"]},
            {"etapa": "Demonstraram interesse", "valor": m["interessados"]},
            {"etapa": "Provavelmente vão", "valor": m["presenca_provavel"]},
            {"etapa": "Fizeram check-in", "valor": m["checkins"]},
            {"etapa": "Avaliaram", "valor": m["avaliacoes"]},
        ] if e["valor"] or e["etapa"] in ("Visualizaram", "Demonstraram interesse")],
        "graficos": {
            "faixas": {
                "labels": [repo.FAIXAS_ETARIAS[f] for f in repo.FAIXAS_ETARIAS],
                "valores": [faixas.get(f, 0) for f in repo.FAIXAS_ETARIAS],
            },
            "notas": {"labels": ["1", "2", "3", "4", "5"],
                      "valores": [distribuicao.get(n, 0) for n in range(1, 6)]},
            "melhorias": {"labels": [repo.MELHORIAS.get(k, k) for k in m["melhorias"]],
                          "valores": list(m["melhorias"].values())},
            "novamente": {"labels": ["Sim", "Talvez", "Não"],
                          "valores": [novamente.get(k, 0) for k in ("sim", "talvez", "nao")]},
        },
        "comentarios": comentarios,
    }
