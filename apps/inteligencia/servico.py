"""
Inteligência: interpretação dos indicadores e recomendações estratégicas.

- Recebe indicadores JÁ CALCULADOS pela aplicação (apps/dashboard/metricas.py).
- Com GEMINI_API_KEY: o Gemini interpreta os números e devolve JSON estruturado.
- Sem chave (ou se a chamada falhar): análise por regras, montada a partir dos MESMOS
  números calculados. Assim a apresentação nunca depende da internet e nada é inventado.
"""
import json
import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

PROMPT = """Você é um analista de experiências e eventos de um shopping center em Palmas (TO).
Abaixo estão indicadores CALCULADOS PELO SISTEMA a partir das interações dos visitantes
(interesse demonstrado, presença provável, check-ins por QR Code e avaliações pós-evento).

Sua tarefa é interpretar esses números e orientar a administração na próxima programação.

Regras obrigatórias:
- Use SOMENTE os números fornecidos. Não invente estatísticas, percentuais ou valores.
- Ao citar um número, ele deve existir nos dados abaixo.
- Seja objetivo e prático. Escreva em português do Brasil.
- "aprovacao" = % de interessados entre quem deslizou o cartão (interesse vs. sem interesse).
- "comparecimento" = % de check-ins em relação aos interessados.
- Eventos com status "proposta" ainda não aconteceram: estão em validação de demanda.

Responda APENAS com um JSON neste formato:
{{
  "resumo": "2 a 3 frases com a leitura geral",
  "destaques": ["3 a 4 observações curtas baseadas nos dados"],
  "recomendacoes": [
    {{"titulo": "curto", "descricao": "1 a 2 frases", "prioridade": "alta|media|baixa"}}
  ],
  "sugestoes_eventos": [
    {{"nome": "nome do evento sugerido", "categoria": "categoria", "justificativa": "1 frase ligada aos dados"}}
  ],
  "alertas": ["pontos de atenção (pode ser lista vazia)"]
}}
Gere de 3 a 4 recomendações e 2 a 3 sugestões de eventos.

Indicadores:
{indicadores}
"""

_cache = {"chave": None, "resultado": None}
_trava = threading.Lock()


def _dados_para_ia(ind):
    """Versão enxuta dos indicadores (só o que a IA precisa)."""
    return {
        "geral": {k: ind[k] for k in (
            "total_eventos", "eventos_por_status", "visitantes_engajados", "total_interesses",
            "total_presenca_provavel", "total_checkins", "taxa_comparecimento",
            "total_avaliacoes", "media_satisfacao")},
        "categorias": [{k: c[k] for k in ("nome", "eventos", "interessados", "aprovacao", "checkins", "nota_media")}
                       for c in ind["categorias"]],
        "eventos": [{k: v for k, v in e.items() if k not in ("id", "data")} for e in ind["eventos"]],
        "validacao_demanda": [{k: v for k, v in p.items() if k != "id"} for p in ind["validacao_demanda"]],
        "alertas_calculados": ind["alertas"],
    }


def _n(valor):
    """Número no formato brasileiro: 1.644 / 75,6."""
    if isinstance(valor, float):
        return f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{valor:,}".replace(",", ".")


def _brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def analise_por_regras(ind):
    """Plano B: recomendações geradas por regras simples a partir dos números calculados."""
    cats = [c for c in ind["categorias"] if c["interessados"]]
    destaques, recomendacoes, sugestoes, alertas = [], [], [], []

    if cats:
        top = cats[0]
        destaques.append(
            f"{top['nome']} é a categoria com mais interesse: {_n(top['interessados'])} interessados "
            f"e {_n(top['aprovacao'])}% de aprovação nos cartões."
        )
        recomendacoes.append({
            "titulo": f"Priorizar {top['nome'].lower()}",
            "descricao": f"Reserve as melhores datas da próxima programação para {top['nome'].lower()}, "
                         f"que lidera em interesse ({_n(top['interessados'])} interessados).",
            "prioridade": "alta",
        })
        if len(cats) > 1:
            seg = cats[1]
            destaques.append(f"{seg['nome']} aparece em seguida, com {_n(seg['interessados'])} interessados.")
            recomendacoes.append({
                "titulo": f"Usar {seg['nome'].lower()} como complemento",
                "descricao": f"Combine {seg['nome'].lower()} com eventos de {top['nome'].lower()} "
                             f"para ampliar o público nos mesmos dias.",
                "prioridade": "media",
            })

    propostas = ind["validacao_demanda"]
    if propostas:
        p = propostas[0]
        texto = (f"A proposta \"{p['nome']}\" reuniu {_n(p['interessados'])} interessados e "
                 f"{_n(p['presenca_provavel'])} presenças prováveis")
        if p["faixa_principal"]:
            texto += f", com predominância da faixa de {p['faixa_principal']} anos ({_n(p['faixa_principal_pct'])}%)"
        destaques.append(texto + ".")
        if p["custo_por_presenca"]:
            recomendacoes.append({
                "titulo": f"Aprovar \"{p['nome']}\"",
                "descricao": f"A demanda validada sustenta o investimento de {_brl(p['investimento'])}: "
                             f"{_brl(p['custo_por_presenca'])} por presença provável.",
                "prioridade": "alta",
            })

    for a in ind["alertas"]:
        if a["tipo"] == "satisfacao_baixa":
            pontos = ", ".join(a["melhorias"]).lower() or "a estrutura"
            alertas.append(f"\"{a['evento']}\" teve satisfação média de {_n(a['nota'])}. Pontos citados: {pontos}.")
            recomendacoes.append({
                "titulo": f"Reformular \"{a['evento']}\"",
                "descricao": f"Antes de repetir o evento, ajuste {pontos}, que foram os pontos mais apontados pelos participantes.",
                "prioridade": "alta",
            })
        elif a["tipo"] == "comparecimento_baixo":
            alertas.append(f"\"{a['evento']}\" converteu só {_n(a['comparecimento'])}% dos interessados em check-in.")

    avaliados = [e for e in ind["eventos"] if e["nota_media"] and e["avaliacoes"] >= 5]
    if avaliados:
        melhor = max(avaliados, key=lambda e: e["nota_media"])
        destaques.append(f"\"{melhor['nome']}\" teve a melhor avaliação: nota {_n(melhor['nota_media'])}.")
        if any("Divulgação" in e["principais_melhorias"] for e in avaliados):
            recomendacoes.append({
                "titulo": "Antecipar a divulgação",
                "descricao": "Participantes citaram a divulgação como ponto de melhoria. Publique os eventos na plataforma com mais antecedência.",
                "prioridade": "media",
            })

    ideias = {
        "Gastronomia": ("Circuito Gastronômico de Fim de Semana", "Gastronomia"),
        "Tecnologia": ("Feira de Inovação e Games", "Tecnologia"),
        "Música": ("Festival de Música Autoral Tocantinense", "Música"),
        "Entretenimento": ("Cinema ao Ar Livre Mensal", "Entretenimento"),
        "Infantil": ("Manhã Criativa em Família", "Infantil"),
        "Cultura": ("Mostra de Cultura do Jalapão", "Cultura"),
        "Esportes": ("Corrida Noturna do Shopping", "Esportes"),
    }
    for c in cats[:3]:
        nome, categoria = ideias.get(c["nome"], (f"Experiência de {c['nome']}", c["nome"]))
        sugestoes.append({"nome": nome, "categoria": categoria,
                          "justificativa": f"A categoria soma {_n(c['interessados'])} interessados, com {_n(c['aprovacao'])}% de aprovação."})

    resumo = (f"Com {_n(ind['visitantes_engajados'])} visitantes engajados e satisfação média de "
              f"{_n(ind['media_satisfacao'])}, os dados indicam onde concentrar a próxima programação.")
    if cats:
        resumo += f" {cats[0]['nome']} lidera o interesse do público."

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    recomendacoes.sort(key=lambda r: ordem[r["prioridade"]])
    return {"resumo": resumo, "destaques": destaques[:4], "recomendacoes": recomendacoes[:4],
            "sugestoes_eventos": sugestoes, "alertas": alertas}


def _consultar_gemini(dados):
    from google import genai
    from google.genai import types

    cliente = genai.Client(api_key=settings.GEMINI_API_KEY,
                           http_options=types.HttpOptions(timeout=25_000))
    resposta = cliente.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=PROMPT.format(indicadores=json.dumps(dados, ensure_ascii=False, indent=1)),
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4),
    )
    analise = json.loads(resposta.text)
    for campo in ("resumo", "destaques", "recomendacoes", "sugestoes_eventos", "alertas"):
        analise.setdefault(campo, [] if campo != "resumo" else "")
    return analise


def gerar_analise(indicadores, forcar=False):
    """Retorna {"fonte": "gemini"|"regras", "analise": {...}, "dados_enviados": {...}}."""
    dados = _dados_para_ia(indicadores)
    chave = json.dumps(dados, sort_keys=True, default=str)
    with _trava:
        if not forcar and _cache["chave"] == chave:
            return _cache["resultado"]

    resultado = None
    if settings.GEMINI_API_KEY:
        try:
            resultado = {"fonte": "gemini", "modelo": settings.GEMINI_MODEL,
                         "analise": _consultar_gemini(dados)}
        except Exception:  # protótipo: qualquer falha cai no plano B
            logger.exception("Falha ao consultar o Gemini; usando análise por regras.")
    if resultado is None:
        resultado = {"fonte": "regras", "analise": analise_por_regras(indicadores)}

    resultado["dados_enviados"] = dados
    with _trava:
        _cache.update(chave=chave, resultado=resultado)
    return resultado
