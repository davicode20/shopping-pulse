"""
Inteligência: interpretação dos indicadores e recomendações estratégicas.

- Recebe indicadores JÁ CALCULADOS pela aplicação (apps/dashboard/metricas.py).
- Com GEMINI_API_KEY: o Gemini interpreta os números e devolve JSON estruturado.
- Sem chave (ou se a chamada falhar): análise por regras, montada a partir dos MESMOS
  números calculados. Assim a apresentação nunca depende da internet e nada é inventado.
- A resposta do Gemini tem formato garantido (schema) e cada número citado é conferido
  com os dados enviados (verificacao.py); o que não bater é destacado no painel.
- Se o modelo principal estiver sobrecarregado, tenta os modelos de reserva antes do plano B.
"""
import json
import logging
import threading
from typing import Literal

from django.conf import settings
from pydantic import BaseModel, Field, ValidationError

from .verificacao import verificar

logger = logging.getLogger(__name__)

PROMPT = """Você é um analista de experiências e eventos de um shopping center em Palmas (TO).
Abaixo estão indicadores CALCULADOS PELO SISTEMA a partir das interações dos visitantes
(interesse demonstrado, presença provável, check-ins por QR Code e avaliações pós-evento).

Sua tarefa é interpretar esses números e orientar a administração na próxima programação.

Regras obrigatórias:
- Use SOMENTE os números fornecidos. Não invente estatísticas, percentuais ou valores.
- Ao citar um número, ele deve existir nos dados abaixo.
- Seja objetivo e prático. Escreva em português do Brasil.
- Escreva números no formato brasileiro: 1.644 (milhar com ponto), 75,4% (decimal com vírgula)
  e valores em dinheiro com R$ (ex.: R$ 46,88). Copie os números como estão nos dados, sem recalcular.
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
# Uma geração por vez: quem chega durante uma geração (ex.: o painel abrindo enquanto o
# pré-aquecimento roda) espera e reaproveita o resultado, em vez de chamar o Gemini de novo.
_gerando = threading.Lock()


# Formato obrigatório da resposta (enviado ao Gemini como schema e validado na volta)
class Recomendacao(BaseModel):
    titulo: str
    descricao: str
    prioridade: Literal["alta", "media", "baixa"]


class SugestaoEvento(BaseModel):
    nome: str
    categoria: str
    justificativa: str


class Analise(BaseModel):
    resumo: str = Field(min_length=1)
    destaques: list[str]
    recomendacoes: list[Recomendacao]
    sugestoes_eventos: list[SugestaoEvento]
    alertas: list[str]


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


def _modelos():
    """Modelo principal + reservas (sem repetir), na ordem de tentativa."""
    lista = [settings.GEMINI_MODEL] + [m.strip() for m in settings.GEMINI_MODELOS_RESERVA.split(",")]
    return list(dict.fromkeys(m for m in lista if m))


def _consultar_gemini(dados, modelo, tempo_limite):
    from google import genai
    from google.genai import types

    # sem novas tentativas automáticas do SDK: quem decide o que fazer na falha somos nós
    cliente = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(
        timeout=tempo_limite * 1000, retry_options=types.HttpRetryOptions(attempts=1)))
    resposta = cliente.models.generate_content(
        model=modelo,
        contents=PROMPT.format(indicadores=json.dumps(dados, ensure_ascii=False, indent=1)),
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           response_schema=Analise, temperature=0.4),
    )
    analise = Analise.model_validate_json(resposta.text).model_dump()
    # limites do prompt (o schema garante o formato; aqui garantimos o tamanho do painel)
    for campo, limite in (("destaques", 4), ("recomendacoes", 4), ("sugestoes_eventos", 3), ("alertas", 4)):
        analise[campo] = analise[campo][:limite]
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    analise["recomendacoes"].sort(key=lambda r: ordem[r["prioridade"]])
    return analise


def _tentar_modelos(dados):
    """Tenta o principal e as reservas; devolve (modelo, análise) ou None. Loga cada falha."""
    for i, modelo in enumerate(_modelos()):
        # o principal ganha mais tempo (raciocina mais); as reservas são modelos mais leves
        tempo = settings.GEMINI_TEMPO_LIMITE if i == 0 else max(settings.GEMINI_TEMPO_LIMITE // 2, 10)
        try:
            return modelo, _consultar_gemini(dados, modelo, tempo)
        except ValidationError:
            logger.warning("Gemini (%s) respondeu fora do formato esperado.", modelo)
        except Exception as erro:  # sobrecarga (503), tempo esgotado (504), rede...
            logger.warning("Gemini (%s) falhou: %s", modelo, str(erro)[:200])
    return None


def gerar_analise(indicadores, forcar=False):
    """Retorna {"fonte": "gemini"|"regras", "analise": {...}, "dados_enviados": {...}}."""
    dados = _dados_para_ia(indicadores)
    chave = json.dumps(dados, sort_keys=True, default=str)
    with _trava:
        if not forcar and _cache["chave"] == chave:
            return _cache["resultado"]

    with _gerando:
        with _trava:  # outra requisição pode ter gerado enquanto esperávamos
            if not forcar and _cache["chave"] == chave:
                return _cache["resultado"]

        resultado = None
        if settings.GEMINI_API_KEY:
            tentativa = _tentar_modelos(dados)
            if tentativa:
                resultado = {"fonte": "gemini", "modelo": tentativa[0], "analise": tentativa[1]}
            else:
                logger.error("Nenhum modelo do Gemini respondeu; usando análise por regras.")
        if resultado is None:
            resultado = {"fonte": "regras", "analise": analise_por_regras(indicadores)}

        resultado["dados_enviados"] = dados
        resultado["verificacao"] = verificar(resultado["analise"], dados)
        with _trava:
            _cache.update(chave=chave, resultado=resultado)
        return resultado


def pre_aquecer():
    """
    Gera a análise em segundo plano assim que o servidor sobe (chamado pelo config/wsgi.py).
    No Render free o cache em memória some a cada reinício; sem isto, o primeiro acesso ao
    painel esperava ~30 s pelo Gemini. Falhas só vão para o log: o painel gera sob demanda.
    """
    def tarefa():
        from django.db import connection

        from apps.dashboard.metricas import calcular_indicadores
        try:
            resultado = gerar_analise(calcular_indicadores())
            logger.info("Análise pré-gerada na inicialização (fonte: %s).", resultado.get("fonte"))
        except Exception:
            logger.exception("Falha ao pré-gerar a análise; o painel vai gerar sob demanda.")
        finally:
            connection.close()

    threading.Thread(target=tarefa, name="pre-aquecer-analise", daemon=True).start()
