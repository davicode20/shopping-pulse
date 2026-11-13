"""
Checagem dos números citados pela IA.

Regra do projeto: os números são calculados pela aplicação e a IA só interpreta.
O prompt pede isso, e este módulo CONFERE: cada número que aparece no texto da análise
precisa existir nos dados enviados à IA (com tolerância para o arredondamento exibido).
O que não bater é marcado no painel como "não encontrado nos dados".

Aceita os dois formatos que a IA costuma usar: brasileiro (1.644 / 75,4) e americano (1644 / 75.4).
"""
import re

# número: dígitos com separadores . e , no meio (ex.: 1.644 | 75,4 | 46,88 | 2393 | 48.2)
_NUMERO = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)*(?![\w])")
# inteiros pequenos são usados como contagem em texto corrido ("3 propostas", "2 eventos");
# para não gerar falsos alarmes, só checamos a partir daqui
MENOR_CHECADO = 3


def _valores_permitidos(dados):
    """Todos os números presentes nos dados: valores numéricos, números dentro de textos
    (nomes de eventos, faixas como "18 a 30") e tamanhos de listas (ex.: 3 propostas)."""
    valores = set()

    def visitar(item):
        if isinstance(item, bool):
            return
        if isinstance(item, (int, float)):
            valores.add(float(item))
        elif isinstance(item, str):
            for trecho in _NUMERO.findall(item):
                valores.update(_interpretacoes(trecho))
        elif isinstance(item, dict):
            for valor in item.values():
                visitar(valor)
        elif isinstance(item, (list, tuple)):
            valores.add(float(len(item)))
            for valor in item:
                visitar(valor)

    visitar(dados)
    return valores


def _interpretacoes(texto):
    """'1.644' pode ser 1644 (BR) ou 1,644 (US); '75,4' é 75.4 (BR) ou 754 (US). Devolve as leituras possíveis."""
    leituras = set()
    br = texto.replace(".", "").replace(",", ".")
    us = texto.replace(",", "")
    for candidato in (br, us):
        try:
            leituras.add(float(candidato))
        except ValueError:
            pass
    return leituras


def _casas_decimais(texto, valor):
    """Casas decimais exibidas, para definir a tolerância do arredondamento."""
    for separador in (",", "."):
        if separador in texto:
            parte = texto.rsplit(separador, 1)[1]
            # "1.644" lido como 1644 não tem casas; "75,4" lido como 75.4 tem 1
            if float(texto.replace(".", "").replace(",", "")) != valor:
                return len(parte)
    return 0


def _confere(texto, permitidos):
    for valor in _interpretacoes(texto):
        tolerancia = 10 ** -_casas_decimais(texto, valor) * 0.51
        if any(abs(valor - p) <= tolerancia for p in permitidos):
            return True
    return False


def _textos(analise):
    """(campo, texto) de toda a análise, na ordem em que aparece no painel."""
    yield "resumo", analise.get("resumo", "")
    for t in analise.get("destaques", []):
        yield "destaques", t
    for r in analise.get("recomendacoes", []):
        yield "recomendacoes", f"{r.get('titulo', '')} {r.get('descricao', '')}"
    for s in analise.get("sugestoes_eventos", []):
        yield "sugestoes_eventos", f"{s.get('nome', '')} {s.get('justificativa', '')}"
    for t in analise.get("alertas", []):
        yield "alertas", t


def verificar(analise, dados):
    """
    Retorna {"citados", "conferidos", "nao_encontrados": [{"numero", "campo", "trecho"}]}.
    `numero` é exatamente como aparece no texto, para o painel destacar.
    """
    permitidos = _valores_permitidos(dados)
    citados, nao_encontrados = 0, []
    for campo, texto in _textos(analise):
        for achado in _NUMERO.finditer(str(texto)):
            numero = achado.group()
            if max(_interpretacoes(numero), default=0) < MENOR_CHECADO and "," not in numero and "." not in numero:
                continue
            citados += 1
            if not _confere(numero, permitidos):
                inicio, fim = max(achado.start() - 40, 0), achado.end() + 40
                nao_encontrados.append({"numero": numero, "campo": campo, "trecho": texto[inicio:fim].strip()})
    return {"citados": citados, "conferidos": citados - len(nao_encontrados), "nao_encontrados": nao_encontrados}
