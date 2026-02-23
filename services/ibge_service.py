# services/ibge_service.py
# Responsável por toda a comunicação com a API do IBGE via sidrapy

import sidrapy
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# BASE DE DADOS — POF 2017-2018 (IBGE)
# Gasto médio mensal per capita em R$ de 2018, por cidade e categoria.
# Fonte: IBGE, Pesquisa de Orçamentos Familiares 2017-2018
# ─────────────────────────────────────────────────────────────

POF_BASE = {
    "Belém": {
        "Alimentação e Bebidas":     520,
        "Habitação":                 480,
        "Transportes":               280,
        "Saúde e Cuidados Pessoais": 180,
        "Educação":                   90,
        "Vestuário":                  80,
        "Comunicação":                90,
        "Despesas Pessoais":         160,
        "Artigos de Residência":      60,
    },
    "Fortaleza": {
        "Alimentação e Bebidas":     490,
        "Habitação":                 460,
        "Transportes":               270,
        "Saúde e Cuidados Pessoais": 170,
        "Educação":                   85,
        "Vestuário":                  75,
        "Comunicação":                85,
        "Despesas Pessoais":         150,
        "Artigos de Residência":      55,
    },
    "Recife": {
        "Alimentação e Bebidas":     510,
        "Habitação":                 500,
        "Transportes":               290,
        "Saúde e Cuidados Pessoais": 175,
        "Educação":                   88,
        "Vestuário":                  78,
        "Comunicação":                88,
        "Despesas Pessoais":         155,
        "Artigos de Residência":      58,
    },
    "Salvador": {
        "Alimentação e Bebidas":     530,
        "Habitação":                 510,
        "Transportes":               295,
        "Saúde e Cuidados Pessoais": 178,
        "Educação":                   90,
        "Vestuário":                  80,
        "Comunicação":                90,
        "Despesas Pessoais":         158,
        "Artigos de Residência":      60,
    },
    "Belo Horizonte": {
        "Alimentação e Bebidas":     570,
        "Habitação":                 620,
        "Transportes":               340,
        "Saúde e Cuidados Pessoais": 210,
        "Educação":                  110,
        "Vestuário":                  95,
        "Comunicação":               100,
        "Despesas Pessoais":         190,
        "Artigos de Residência":      75,
    },
    "Rio de Janeiro": {
        "Alimentação e Bebidas":     650,
        "Habitação":                 850,
        "Transportes":               380,
        "Saúde e Cuidados Pessoais": 240,
        "Educação":                  140,
        "Vestuário":                 110,
        "Comunicação":               115,
        "Despesas Pessoais":         230,
        "Artigos de Residência":      90,
    },
    "São Paulo": {
        "Alimentação e Bebidas":     680,
        "Habitação":                 920,
        "Transportes":               400,
        "Saúde e Cuidados Pessoais": 260,
        "Educação":                  155,
        "Vestuário":                 115,
        "Comunicação":               120,
        "Despesas Pessoais":         250,
        "Artigos de Residência":      95,
    },
    "Curitiba": {
        "Alimentação e Bebidas":     600,
        "Habitação":                 650,
        "Transportes":               350,
        "Saúde e Cuidados Pessoais": 215,
        "Educação":                  115,
        "Vestuário":                 100,
        "Comunicação":               105,
        "Despesas Pessoais":         200,
        "Artigos de Residência":      78,
    },
    "Porto Alegre": {
        "Alimentação e Bebidas":     620,
        "Habitação":                 660,
        "Transportes":               355,
        "Saúde e Cuidados Pessoais": 220,
        "Educação":                  118,
        "Vestuário":                 102,
        "Comunicação":               106,
        "Despesas Pessoais":         205,
        "Artigos de Residência":      80,
    },
    "Goiânia": {
        "Alimentação e Bebidas":     555,
        "Habitação":                 560,
        "Transportes":               310,
        "Saúde e Cuidados Pessoais": 195,
        "Educação":                  100,
        "Vestuário":                  88,
        "Comunicação":                95,
        "Despesas Pessoais":         175,
        "Artigos de Residência":      68,
    },
    "Distrito Federal": {
        "Alimentação e Bebidas":     700,
        "Habitação":                 880,
        "Transportes":               390,
        "Saúde e Cuidados Pessoais": 255,
        "Educação":                  150,
        "Vestuário":                 112,
        "Comunicação":               118,
        "Despesas Pessoais":         245,
        "Artigos de Residência":      92,
    },
}

# Nome da Região Metropolitana como aparece na API do IBGE
CIDADES_IBGE = {
    "Belém":            "Belém - PA",
    "Fortaleza":        "Fortaleza - CE",
    "Recife":           "Recife - PE",
    "Salvador":         "Salvador - BA",
    "Belo Horizonte":   "Belo Horizonte - MG",
    "Rio de Janeiro":   "Rio de Janeiro - RJ",
    "São Paulo":        "São Paulo - SP",
    "Curitiba":         "Curitiba - PR",
    "Porto Alegre":     "Porto Alegre - RS",
    "Goiânia":          "Goiânia - GO",
    "Distrito Federal": "Brasília - DF",
}

GRUPOS = {
    "7169": "Alimentação e Bebidas",
    "7170": "Habitação",
    "7445": "Artigos de Residência",
    "7486": "Vestuário",
    "7625": "Transportes",
    "7626": "Saúde e Cuidados Pessoais",
    "7627": "Despesas Pessoais",
    "7628": "Educação",
    "7629": "Comunicação",
}

# Data base da POF — usada para calcular quantos meses de IPCA aplicar
_MES_BASE_POF = datetime(2018, 12, 1)

# Cache do IPCA — evita chamar a API repetidamente na mesma sessão
_cache_ipca: pd.DataFrame | None = None


# ─────────────────────────────────────────────────────────────
# FUNÇÕES PÚBLICAS
# ─────────────────────────────────────────────────────────────

def buscar_custo_estimado(nome_cidade: str, pessoas: int = 1) -> dict:
    """
    Estima o custo de vida mensal atual de uma cidade em R$,
    atualizando os dados da POF 2018 com o IPCA acumulado por categoria.

    Args:
        nome_cidade: Nome da cidade (ex: "São Paulo")
        pessoas: Número de pessoas na residência

    Returns:
        Dicionário com cidade, total, categorias e mês de referência.
    """
    if nome_cidade not in POF_BASE:
        raise ValueError(f"Cidade '{nome_cidade}' não disponível.")

    ipca = _buscar_ipca_acumulado(nome_cidade)

    categorias = {
        categoria: round(valor_base * (1 + ipca.get(categoria, 0) / 100) * pessoas, 2)
        for categoria, valor_base in POF_BASE[nome_cidade].items()
    }

    return {
        "cidade":     nome_cidade,
        "total":      round(sum(categorias.values()), 2),
        "categorias": categorias,
        "referencia": datetime.now().strftime("%b/%Y"),
    }


def buscar_cidades_por_orcamento(orcamento: float, pessoas: int = 1) -> list:
    """
    Retorna todas as cidades com custo estimado, ordenadas da mais barata
    para a mais cara, indicando se cabem no orçamento informado.

    Args:
        orcamento: Valor mensal disponível em R$
        pessoas: Número de pessoas na residência

    Returns:
        Lista de dicionários ordenada pelo custo total.
    """
    resultados = []

    for cidade in POF_BASE:
        try:
            dados = buscar_custo_estimado(cidade, pessoas)
            dados["cabe_no_orcamento"] = dados["total"] <= orcamento
            dados["sobra"] = round(orcamento - dados["total"], 2)
            resultados.append(dados)
        except Exception as erro:
            print(f"[AVISO] Erro ao calcular custo de {cidade}: {erro}")

    resultados.sort(key=lambda x: x["total"])
    return resultados


def listar_cidades() -> list:
    """Retorna a lista de cidades disponíveis em ordem alfabética."""
    return sorted(POF_BASE.keys())


# ─────────────────────────────────────────────────────────────
# FUNÇÕES INTERNAS
# ─────────────────────────────────────────────────────────────

def _carregar_cache_ipca() -> None:
    """
    Faz UMA única chamada à API do IBGE buscando o IPCA de todas as
    cidades e grupos de uma vez, e armazena o resultado em cache.
    Chamadas subsequentes reutilizam o cache sem nova requisição.
    """
    global _cache_ipca

    if _cache_ipca is not None:
        return  # já carregado, não precisa buscar de novo

    hoje = datetime.now()
    meses = (hoje.year - _MES_BASE_POF.year) * 12 + (hoje.month - _MES_BASE_POF.month)

    print(f"[INFO] Buscando IPCA acumulado ({meses} meses) para todas as cidades...")

    try:
        df = sidrapy.get_table(
            table_code="7060",
            territorial_level="7",
            ibge_territorial_code="all",
            period=f"last {meses}",
            variable="63",
            classifications={"315": ",".join(GRUPOS.keys())},
        )

        if df.empty or len(df) <= 1:
            print("[AVISO] API retornou dados vazios. Usando valores base sem correção de inflação.")
            _cache_ipca = pd.DataFrame()
            return

        df = df.iloc[1:].copy()
        df["V"] = pd.to_numeric(df["V"], errors="coerce")
        df = df.dropna(subset=["V"])
        _cache_ipca = df
        print("[INFO] Cache do IPCA carregado com sucesso.")

    except Exception as erro:
        print(f"[AVISO] Falha ao carregar IPCA da API: {erro}. Usando valores base.")
        _cache_ipca = pd.DataFrame()


def _buscar_ipca_acumulado(nome_cidade: str) -> dict:
    """
    Retorna o IPCA acumulado por categoria para uma cidade,
    calculado a partir do cache carregado pela função acima.

    Returns:
        Dicionário {nome_categoria: percentual_acumulado}
        Retorna zeros se os dados não estiverem disponíveis.
    """
    _carregar_cache_ipca()

    zeros = {nome: 0 for nome in GRUPOS.values()}

    if _cache_ipca is None or _cache_ipca.empty:
        return zeros

    nome_rm = CIDADES_IBGE.get(nome_cidade)
    if not nome_rm:
        return zeros

    df_cidade = _cache_ipca[_cache_ipca["D1N"] == nome_rm]

    if df_cidade.empty:
        print(f"[AVISO] Cidade '{nome_cidade}' ('{nome_rm}') não encontrada no cache.")
        return zeros

    acumulado = {}
    for codigo, nome_cat in GRUPOS.items():
        df_grupo = df_cidade[df_cidade["D3C"] == codigo]
        if df_grupo.empty:
            acumulado[nome_cat] = 0
            continue
        # Fórmula de inflação acumulada composta
        fator = 1.0
        for variacao in df_grupo["V"]:
            fator *= (1 + variacao / 100)
        acumulado[nome_cat] = round((fator - 1) * 100, 2)

    return acumulado