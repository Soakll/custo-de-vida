import requests
import pandas as pd
import io

URL_UF = "http://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/feeae05e-faba-406c-8a4a-512aec91a9d1/download/indicadoressegurancapublicauf.xlsx"

CAPITAIS_POR_ESTADO = {
    "Pará":                "Belém",
    "Ceará":               "Fortaleza",
    "Pernambuco":          "Recife",
    "Bahia":               "Salvador",
    "Minas Gerais":        "Belo Horizonte",
    "Rio de Janeiro":      "Rio de Janeiro",
    "São Paulo":           "São Paulo",
    "Paraná":              "Curitiba",
    "Rio Grande do Sul":   "Porto Alegre",
    "Goiás":               "Goiânia",
    "Distrito Federal":    "Brasília",
}

_cache_uf = None


def _baixar_excel(url):
    try:
        print(f"[INFO] Baixando dados de: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content))
        df.columns = [str(c).strip() for c in df.columns]
        print("[INFO] Download concluído.")
        return df
    except Exception as e:
        print(f"[AVISO] Falha ao baixar dados SINESP: {e}")
        return None


def _carregar_cache_uf():
    global _cache_uf
    if _cache_uf is not None:
        return _cache_uf
    _cache_uf = _baixar_excel(URL_UF)
    return _cache_uf


def buscar_crimes_por_uf(ano=None):
    df = _carregar_cache_uf()
    if df is None:
        return {"erro": "Não foi possível carregar os dados do SINESP."}

    ano_max = int(df["Ano"].max()) if ano is None else ano
    df_ano  = df[df["Ano"] == ano_max].copy()
    df_ano["Ocorrências"] = pd.to_numeric(df_ano["Ocorrências"], errors="coerce").fillna(0)

    tipos     = sorted(df_ano["Tipo Crime"].dropna().unique().tolist())
    resultado = {}

    for uf, grupo in df_ano.groupby("UF"):
        crimes = grupo.groupby("Tipo Crime")["Ocorrências"].sum().astype(int).to_dict()
        resultado[str(uf)] = {"crimes": crimes, "total": sum(crimes.values())}

    return {"ano": ano_max, "tipos": tipos, "estados": resultado}


def buscar_crimes_por_capital(ano=None):
    df = _carregar_cache_uf()
    if df is None:
        return {"erro": "Não foi possível carregar os dados do SINESP."}

    ano_max = int(df["Ano"].max()) if ano is None else ano
    df_ano  = df[df["Ano"] == ano_max].copy()
    df_ano["Ocorrências"] = pd.to_numeric(df_ano["Ocorrências"], errors="coerce").fillna(0)

    tipos     = sorted(df_ano["Tipo Crime"].dropna().unique().tolist())
    resultado = {}

    for estado, capital in CAPITAIS_POR_ESTADO.items():
        df_estado = df_ano[df_ano["UF"] == estado]
        if df_estado.empty:
            continue
        crimes = df_estado.groupby("Tipo Crime")["Ocorrências"].sum().astype(int).to_dict()
        resultado[capital] = {
            "estado": estado,
            "crimes": crimes,
            "total":  sum(crimes.values()),
        }

    return {"ano": ano_max, "tipos": tipos, "capitais": resultado}