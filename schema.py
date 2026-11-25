# -*- coding: utf-8 -*-
"""Validacao e normalizacao do JSON enviado pelo formulario.

Tudo que chega do navegador passa por aqui: campos desconhecidos sao ignorados,
textos sao aparados e truncados, listas tem tamanho maximo e itens vazios somem.

Datas: o formulario manda as partes separadas (mes e ano, inicio e fim, mais a
marca "atual") e e aqui que elas viram o texto que aparece no PDF, sempre no
formato "Fev 2025 - Atual". O campo antigo de texto livre ("periodo", ou "data"
nas certificacoes) continua aceito e serve de reserva para quem monta o JSON na
mao: ele e usado quando as partes vem vazias.
"""
import re

CURTO = 120
MEDIO = 300
LONGO = 1500
MAX_ITENS = 15
PARTE = 20          # tamanho maximo das partes de data (mes, ano)
PERIODO = 40        # tamanho maximo do texto final do periodo
BOOLEANO = None     # marca, no dicionario de campos, que o campo e um sim/nao

MESES = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez")
_NOMES = ("janeiro", "fevereiro", "marco", "abril", "maio", "junho",
          "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
ATUAL = "Atual"

# partes de data que o formulario manda e que somem depois de virar texto
INTERVALO = {"inicio_mes": PARTE, "inicio_ano": PARTE, "fim_mes": PARTE,
             "fim_ano": PARTE, "atual": BOOLEANO}
DATA = {"mes": PARTE, "ano": PARTE}

# secao -> (campos e tamanho maximo de cada um)
SECOES = {
    "habilidades": {"categoria": 60, "itens": MEDIO},
    "experiencias": {"cargo": CURTO, "empresa": CURTO, "local": CURTO,
                     **INTERVALO, "periodo": PERIODO, "pontos": LONGO, "contexto": LONGO},
    "formacoes": {"instituicao": CURTO, "grau": 60, "curso": CURTO,
                  **INTERVALO, "periodo": PERIODO},
    "palestras": {"titulo": MEDIO, **DATA, "periodo": PERIODO, "descricao": LONGO},
    "publicacoes": {"titulo": MEDIO, **DATA, "periodo": PERIODO, "descricao": LONGO},
    "certificacoes": {"nome": CURTO, **DATA, "data": PARTE},
    "voluntariado": {"funcao": CURTO, **INTERVALO, "periodo": PERIODO, "descricao": LONGO},
}

# secoes com periodo de inicio e fim, e secoes com uma data so (campo de destino)
SECOES_INTERVALO = ("experiencias", "formacoes", "voluntariado")
SECOES_DATA = {"palestras": "periodo", "publicacoes": "periodo", "certificacoes": "data"}

# campo que precisa estar preenchido para o item entrar no CV
OBRIGATORIO_NO_ITEM = {
    "habilidades": ("itens",),
    "experiencias": ("cargo", "empresa"),
    "formacoes": ("instituicao", "curso"),
    "palestras": ("titulo",),
    "publicacoes": ("titulo",),
    "certificacoes": ("nome",),
    "voluntariado": ("funcao",),
}

PESSOAL = {"nome": 80, "email": 120, "celular": 40, "linkedin": 200, "github": 200}
CATEGORIA_PADRAO = "Gerais"

_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ErroValidacao(ValueError):
    pass


def _texto(valor, limite, multilinha=False):
    if not isinstance(valor, str):
        return ""
    valor = _CONTROLE.sub("", valor).replace("\r\n", "\n").replace("\r", "\n")
    if not multilinha:
        valor = " ".join(valor.split())
    else:
        valor = "\n".join(" ".join(linha.split()) for linha in valor.split("\n"))
        valor = re.sub(r"\n{3,}", "\n\n", valor)
    return valor.strip()[:limite].strip()


def _sim_nao(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(valor)
    return isinstance(valor, str) and valor.strip().casefold() in {"true", "on", "1", "sim", "yes"}


def _mes(valor):
    """Aceita 'Fev', 'fevereiro', '2' ou '02' e devolve sempre 'Fev'."""
    v = _texto(valor, PARTE).casefold().replace("ç", "c")
    if not v:
        return ""
    if v.isdigit():
        n = int(v)
        return MESES[n - 1] if 1 <= n <= 12 else ""
    for i, nome in enumerate(_NOMES):
        if v in (nome, nome[:3]):
            return MESES[i]
    return ""


def _ano(valor):
    digitos = "".join(c for c in _texto(valor, PARTE) if c.isdigit())
    if len(digitos) == 2:           # '26' -> '2026'
        return "20" + digitos
    return digitos if len(digitos) == 4 else ""


def _data(mes, ano):
    """'Fev 2025'. Sem ano nao forma data: mes solto e descartado."""
    mes, ano = _mes(mes), _ano(ano)
    return f"{mes} {ano}" if mes and ano else ano


def _intervalo(item):
    """'Fev 2025 - Atual', 'Fev 2025 - Dez 2026' ou so uma das pontas."""
    inicio = _data(item.get("inicio_mes"), item.get("inicio_ano"))
    fim = ATUAL if _sim_nao(item.get("atual")) else _data(item.get("fim_mes"), item.get("fim_ano"))
    if inicio and fim:
        return f"{inicio} - {fim}"
    return inicio or fim


def _lista(itens, campos, obrigatorios):
    if not isinstance(itens, list):
        return []
    limpos = []
    for item in itens[:MAX_ITENS]:
        if not isinstance(item, dict):
            continue
        limpo = {}
        for campo, limite in campos.items():
            if limite is BOOLEANO:
                limpo[campo] = _sim_nao(item.get(campo))
            else:
                limpo[campo] = _texto(item.get(campo), limite, multilinha=limite >= LONGO)
        if any(limpo[c] for c in obrigatorios):
            limpos.append(limpo)
    return limpos


def _montar_datas(cv):
    """Troca as partes de data pelo texto final, no campo que o PDF le."""
    for secao in SECOES_INTERVALO:
        for item in cv[secao]:
            item["periodo"] = _intervalo(item) or item["periodo"]
            for parte in INTERVALO:
                item.pop(parte, None)
    for secao, destino in SECOES_DATA.items():
        for item in cv[secao]:
            montado = _data(item.pop("mes", ""), item.pop("ano", ""))
            item[destino] = montado or item[destino]


def validar(dados):
    if not isinstance(dados, dict):
        raise ErroValidacao("Dados inválidos.")

    bruto = dados.get("pessoal") if isinstance(dados.get("pessoal"), dict) else {}
    pessoal = {c: _texto(bruto.get(c), lim) for c, lim in PESSOAL.items()}
    if not pessoal["nome"]:
        raise ErroValidacao("Informe seu nome completo.")
    if not pessoal["email"]:
        raise ErroValidacao("Informe seu e-mail.")
    if not _EMAIL.match(pessoal["email"]):
        raise ErroValidacao("O e-mail informado não parece válido.")

    cv = {
        "pessoal": pessoal,
        "resumo": _texto(dados.get("resumo"), LONGO, multilinha=True),
    }
    for secao, campos in SECOES.items():
        cv[secao] = _lista(dados.get(secao), campos, OBRIGATORIO_NO_ITEM[secao])

    _montar_datas(cv)
    for exp in cv["experiencias"]:
        exp["pontos"] = [
            linha.lstrip("-•*· ").strip()
            for linha in exp["pontos"].split("\n")
            if linha.lstrip("-•*· ").strip()
        ]
    cv["habilidades"] = _agrupar_habilidades(cv["habilidades"])
    return cv


def _agrupar_habilidades(itens):
    """Junta linhas com a mesma categoria numa so, sem repetir habilidades."""
    grupos = {}
    for item in itens:
        categoria = item["categoria"] or CATEGORIA_PADRAO
        grupo = grupos.setdefault(categoria.casefold(), {"categoria": categoria, "lista": []})
        vistos = {h.casefold() for h in grupo["lista"]}
        for habilidade in re.split(r"[,;]", item["itens"]):
            habilidade = habilidade.strip()
            if habilidade and habilidade.casefold() not in vistos:
                grupo["lista"].append(habilidade)
                vistos.add(habilidade.casefold())
    return [{"categoria": g["categoria"], "itens": ", ".join(g["lista"])} for g in grupos.values() if g["lista"]]
