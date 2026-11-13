"""
Exportação das recomendações para o Miro (REST API v2).

Fecha o ciclo do produto: INTELIGÊNCIA → NOVO PLANEJAMENTO. A análise da IA (ou do plano B
por regras) vira um frame no quadro da equipe, com:
  - título + resumo da leitura geral;
  - colunas de sticky notes: destaques, recomendações (cor por prioridade), validação de
    demanda (com os números calculados) e alertas;
  - eventos sugeridos como cards, na cor da categoria.

Cada exportação cria um frame novo, à direita do conteúdo que já existe no quadro, então
o histórico de planejamentos fica lado a lado.

Sem MIRO_ACCESS_TOKEN, o painel oferece o plano B: um CSV que o Miro importa como sticky notes.
"""
import csv
import html
import io
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.utils import timezone

from apps.eventos import repositorio as repo

logger = logging.getLogger(__name__)

API = "https://api.miro.com/v2"

# Layout do frame (coordenadas do Miro: posição = centro do item; filhos relativos ao canto do frame)
LARGURA_COLUNA = 760
MARGEM = 140
TOPO_COLUNAS = 640      # y do título das colunas
INICIO_ITENS = 720      # borda de cima do primeiro item de cada coluna (abaixo do título)
ESPACO = 60             # espaço vertical entre itens
LARGURA_STICKY = 400
LARGURA_CARD = 620
# Alturas reais no Miro (medidas pela API): o sticky quadrado tem altura ≈ 1,145 × largura
ALTURA = {"sticky": 460, "card": 120}

COR_PRIORIDADE = {"alta": "orange", "media": "yellow", "baixa": "light_green"}
ROTULO_PRIORIDADE = {"alta": "🔴 PRIORIDADE ALTA", "media": "🟡 PRIORIDADE MÉDIA", "baixa": "🟢 PRIORIDADE BAIXA"}
COR_CATEGORIA = {nome.lower(): repo.CORES[chave] for chave, nome in repo.CATEGORIAS.items()}


class ErroMiro(Exception):
    """Erro com mensagem pronta para mostrar no painel."""


# ---------- Configuração ----------

def id_do_quadro():
    """Aceita o ID puro (uXjVEOBOvFo=) ou o link do quadro (https://miro.com/app/board/uXjVEOBOvFo=/)."""
    valor = (settings.MIRO_BOARD_ID or "").strip()
    achado = re.search(r"/board/([^/?#]+)", valor)
    return urllib.parse.unquote(achado.group(1) if achado else valor)


def configurado():
    return bool(settings.MIRO_ACCESS_TOKEN and id_do_quadro())


def link_do_quadro(item_id=None):
    url = f"https://miro.com/app/board/{urllib.parse.quote(id_do_quadro(), safe='')}/"
    return url + (f"?moveToWidget={item_id}" if item_id else "")


# ---------- HTTP ----------

def _requisicao(metodo, caminho, corpo=None):
    url = f"{API}/boards/{urllib.parse.quote(id_do_quadro(), safe='')}{caminho}"
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={
        "Authorization": f"Bearer {settings.MIRO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resposta:
            return json.loads(resposta.read() or b"{}")
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode(errors="replace")[:300]
        logger.warning("Miro %s %s -> %s: %s", metodo, caminho, erro.code, detalhe)
        mensagens = {
            401: "Token do Miro inválido ou expirado. Confira MIRO_ACCESS_TOKEN no .env.",
            403: "O app do Miro não tem permissão de escrita neste quadro (escopo boards:write).",
            404: "Quadro não encontrado. Confira MIRO_BOARD_ID e se o app foi instalado na equipe do quadro.",
            429: "Limite de requisições do Miro atingido. Aguarde um minuto e tente de novo.",
        }
        raise ErroMiro(mensagens.get(erro.code, f"O Miro recusou a requisição (HTTP {erro.code}).")) from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroMiro("Sem conexão com o Miro. Verifique a internet e tente de novo.") from erro


# ---------- Montagem do conteúdo ----------

def _p(*linhas):
    """Texto para sticky/shape: o Miro aceita HTML simples (<p>, <strong>)."""
    return "".join(f"<p>{linha}</p>" for linha in linhas if linha)


def _e(texto):
    return html.escape(str(texto or ""))


def _num(valor, casas=0):
    if valor is None:
        return "—"
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_itens(resultado, indicadores):
    """
    Lista de itens a criar dentro do frame + tamanho do frame.
    Função pura (sem rede): facilita testar o layout.
    """
    analise = resultado["analise"]
    agora = timezone.localtime()
    fonte = "Google Gemini" if resultado.get("fonte") == "gemini" else "modo demonstração (regras)"

    colunas = []
    if analise.get("destaques"):
        colunas.append(("📊 O que os dados mostram", [
            {"tipo": "sticky", "cor": "light_blue", "conteudo": _p(_e(t))} for t in analise["destaques"]
        ]))
    if analise.get("recomendacoes"):
        colunas.append(("✅ Recomendações", [
            {"tipo": "sticky", "cor": COR_PRIORIDADE.get(r.get("prioridade"), "gray"),
             "conteudo": _p(f"<strong>{ROTULO_PRIORIDADE.get(r.get('prioridade'), '')}</strong>",
                            f"<strong>{_e(r.get('titulo'))}</strong>", _e(r.get("descricao")))}
            for r in analise["recomendacoes"]
        ]))
    if analise.get("sugestoes_eventos"):
        colunas.append(("💡 Eventos sugeridos", [
            {"tipo": "card", "titulo": _e(s.get("nome")),
             "descricao": _e(f"{s.get('categoria', '')} · {s.get('justificativa', '')}"),
             "cor": COR_CATEGORIA.get(str(s.get("categoria", "")).lower(), "#6c2bd9")}
            for s in analise["sugestoes_eventos"]
        ]))
    propostas = indicadores.get("validacao_demanda") or []
    if propostas:
        colunas.append(("🗳️ Validação de demanda", [
            {"tipo": "sticky", "cor": "light_yellow", "conteudo": _p(
                f"<strong>{_e(p['nome'])}</strong>",
                f"👀 {_num(p['visualizacoes'])} viram · 💜 {_num(p['interessados'])} interessados",
                f"📅 {_num(p['presenca_provavel'])} presenças prováveis",
                f"💰 R$ {_num(p['custo_por_presenca'], 2)} por presença" if p.get("custo_por_presenca") else "",
                f"👥 {_num(p['faixa_principal_pct'], 1)}% com {_e(p['faixa_principal'])} anos" if p.get("faixa_principal") else "",
            )} for p in propostas[:5]
        ]))
    if analise.get("alertas"):
        colunas.append(("⚠️ Pontos de atenção", [
            {"tipo": "sticky", "cor": "red", "conteudo": _p(_e(t))} for t in analise["alertas"]
        ]))

    largura = MARGEM * 2 + LARGURA_COLUNA * max(len(colunas), 1)

    itens = [
        {"tipo": "texto", "x": largura / 2, "y": 150, "largura": largura - 2 * MARGEM, "tamanho": 64,
         "conteudo": f"<p><strong>{_e(settings.NOME_PROJETO)} · Próxima programação</strong></p>"},
        {"tipo": "texto", "x": largura / 2, "y": 250, "largura": largura - 2 * MARGEM, "tamanho": 28,
         "conteudo": _p(f"Gerado em {agora:%d/%m/%Y às %H:%M} · análise: {fonte} · "
                        "números calculados pela plataforma, a IA apenas interpreta")},
        {"tipo": "resumo", "x": largura / 2, "y": 430, "largura": largura - 2 * MARGEM, "altura": 200,
         "conteudo": _p(_e(analise.get("resumo")))},
    ]
    fundo = INICIO_ITENS
    for i, (titulo, conteudo) in enumerate(colunas):
        x = MARGEM + LARGURA_COLUNA * i + LARGURA_COLUNA / 2
        itens.append({"tipo": "texto", "x": x, "y": TOPO_COLUNAS, "largura": LARGURA_COLUNA - 80, "tamanho": 40,
                      "conteudo": f"<p><strong>{_e(titulo)}</strong></p>"})
        topo = INICIO_ITENS
        for item in conteudo:  # empilha pela altura real de cada tipo: nada se sobrepõe
            h = ALTURA[item["tipo"]]
            itens.append({**item, "x": x, "y": topo + h / 2})
            topo += h + ESPACO
        fundo = max(fundo, topo)
    altura = fundo + MARGEM

    titulo_frame = f"{settings.NOME_PROJETO} · Planejamento {agora:%d/%m %H:%M}"
    return {"titulo": titulo_frame, "largura": largura, "altura": altura, "itens": itens}


def _corpo_item(item, frame_id):
    base = {
        "position": {"x": item["x"], "y": item["y"], "origin": "center"},
        "parent": {"id": frame_id},
    }
    if item["tipo"] == "sticky":
        return "/sticky_notes", {**base, "data": {"content": item["conteudo"], "shape": "square"},
                                 "style": {"fillColor": item["cor"], "textAlign": "left", "textAlignVertical": "top"},
                                 "geometry": {"width": LARGURA_STICKY}}
    if item["tipo"] == "card":
        return "/cards", {**base, "data": {"title": item["titulo"], "description": item["descricao"]},
                          "style": {"cardTheme": item["cor"]}, "geometry": {"width": LARGURA_CARD}}
    if item["tipo"] == "resumo":
        return "/shapes", {**base, "data": {"shape": "round_rectangle", "content": item["conteudo"]},
                           "style": {"fillColor": "#14112b", "fontSize": "28", "color": "#ffffff",
                                     "borderColor": "#6c2bd9", "borderWidth": "4", "textAlign": "left"},
                           "geometry": {"width": item["largura"], "height": item["altura"]}}
    return "/texts", {**base, "data": {"content": item["conteudo"]},
                      "style": {"fontSize": str(item["tamanho"]), "textAlign": "left", "color": "#14112b"},
                      "geometry": {"width": item["largura"]}}


def _posicao_livre(largura, altura):
    """Centro para o novo frame: à direita de tudo o que já está no quadro."""
    direita, cursor = None, None
    for _ in range(10):  # até 500 itens de nível superior
        caminho = "/items?limit=50" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
        pagina = _requisicao("GET", caminho)
        for item in pagina.get("data", []):
            if item.get("parent"):
                continue
            pos, geo = item.get("position") or {}, item.get("geometry") or {}
            if "x" in pos:
                borda = pos["x"] + (geo.get("width") or 0) / 2
                direita = borda if direita is None else max(direita, borda)
        cursor = pagina.get("cursor")
        if not cursor:
            break
    x = (direita + 600 + largura / 2) if direita is not None else largura / 2
    return x, altura / 2


# ---------- Exportação ----------

def exportar(resultado, indicadores):
    """Cria o frame com a análise no quadro. Retorna {"link", "itens", "titulo"}."""
    if not configurado():
        raise ErroMiro("Miro não configurado: defina MIRO_ACCESS_TOKEN e MIRO_BOARD_ID no .env.")

    plano = montar_itens(resultado, indicadores)
    x, y = _posicao_livre(plano["largura"], plano["altura"])
    frame = _requisicao("POST", "/frames", {
        "data": {"title": plano["titulo"], "format": "custom", "type": "freeform"},
        "style": {"fillColor": "#f5f3fb"},
        "position": {"x": x, "y": y, "origin": "center"},
        "geometry": {"width": plano["largura"], "height": plano["altura"]},
    })

    # Poucas requisições em paralelo: rápido o bastante para a demo e longe do limite da API
    with ThreadPoolExecutor(max_workers=4) as pool:
        tarefas = [pool.submit(_requisicao, "POST", *_corpo_item(item, frame["id"])) for item in plano["itens"]]
        erros = [t.exception() for t in tarefas if t.exception()]
    if erros and len(erros) == len(tarefas):
        raise erros[0]

    return {
        "titulo": plano["titulo"],
        "link": link_do_quadro(frame["id"]),
        "itens": len(tarefas) - len(erros),
        "falhas": len(erros),
    }


def gerar_csv(resultado, indicadores):
    """Plano B sem token: CSV que o Miro importa (Upload → CSV) como sticky notes, uma por linha."""
    plano = montar_itens(resultado, indicadores)
    saida = io.StringIO()
    escritor = csv.writer(saida)
    escritor.writerow(["Conteúdo"])
    for item in plano["itens"]:
        if item["tipo"] == "card":
            texto = f"💡 {item['titulo']} — {item['descricao']}"
        else:
            texto = item["conteudo"]
        texto = html.unescape(re.sub(r"</p><p>", " · ", re.sub(r"<(?!/?p>)[^>]+>", "", texto)))
        escritor.writerow([re.sub(r"</?p>", "", texto).strip()])
    return "﻿" + saida.getvalue()  # BOM: acentos corretos ao abrir no Excel
