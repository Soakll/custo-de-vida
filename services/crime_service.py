import requests
import pandas as pd
import io

URL_UF    = "http://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/feeae05e-faba-406c-8a4a-512aec91a9d1/download/indicadoressegurancapublicauf.xlsx"
URL_MUNIC = "http://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/03af7ce2-174e-4ebd-b085-384503cfb40f/download/indicadoressegurancapublicamunic.xlsx"

CAPITAIS = {
    "Belém":          "Pará",
    "Fortaleza":      "Ceará",
    "Recife":         "Pernambuco",
    "Salvador":       "Bahia",
    "Belo Horizonte": "Minas Gerais",
    "Rio de Janeiro": "Rio de Janeiro",
    "São Paulo":      "São Paulo",
    "Curitiba":       "Paraná",
    "Porto Alegre":   "Rio Grande do Sul",
    "Goiânia":        "Goiás",
    "Brasília":       "Distrito Federal",
}

_cache_uf    = None
_cache_munic = None


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


def _carregar_cache_munic():
    global _cache_munic
    if _cache_munic is not None:
        return _cache_munic
    _cache_munic = _baixar_excel(URL_MUNIC)
    return _cache_munic


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
    df = _carregar_cache_munic()
    if df is None:
        return {"erro": "Não foi possível carregar os dados do SINESP."}

    print("[DEBUG] Colunas município:", df.columns.tolist())
    print(df.head(3))

    ano_max = int(df["Ano"].max()) if ano is None else ano
    df_ano  = df[df["Ano"] == ano_max].copy()
    df_ano["Ocorrências"] = pd.to_numeric(df_ano["Ocorrências"], errors="coerce").fillna(0)

    col_munic = next((c for c in df.columns if "munic" in c.lower() or "cidade" in c.lower()), None)
    col_uf    = next((c for c in df.columns if "uf" in c.lower() or "estado" in c.lower()), None)

    if not col_munic or not col_uf:
        return {"erro": "Colunas de município/UF não encontradas."}

    resultado = {}

    for cidade, uf in CAPITAIS.items():
        df_cidade = df_ano[
            (df_ano[col_munic].str.contains(cidade, case=False, na=False)) &
            (df_ano[col_uf].str.contains(uf, case=False, na=False))
        ]
        if df_cidade.empty:
            continue
        crimes = df_cidade.groupby("Tipo Crime")["Ocorrências"].sum().astype(int).to_dict()
        resultado[cidade] = {"uf": uf, "crimes": crimes, "total": sum(crimes.values())}

    tipos = sorted({t for c in resultado.values() for t in c["crimes"]})
    return {"ano": ano_max, "tipos": tipos, "capitais": resultado}