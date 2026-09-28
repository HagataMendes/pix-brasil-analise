"""
Coleta da população por município no IBGE (API SIDRA).

Tenta primeiro as estimativas anuais de população (tabela 6579) e, se não
conseguir, usa o Censo 2022 (tabela 4709). Salva em data/raw/populacao.parquet.

Uso:
    python src/coleta_ibge.py
"""
import json
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
CABECALHOS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json",
}
FONTES = [
    ("Estimativas de população (IBGE, API de Agregados)",
     "https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/-1/variaveis/9324?localidades=N6[all]"),
    ("Censo Demográfico 2022 (IBGE, API de Agregados)",
     "https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/variaveis/93?localidades=N6[all]"),
    ("Estimativas de população (IBGE, tabela 6579)", "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last%201"),
    ("Censo Demográfico 2022 (IBGE, tabela 4709)", "https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/all"),
]


def ler_agregados(url: str) -> pd.DataFrame:
    """Formato da API servicodados: [{variavel, resultados:[{series:[{localidade:{id,nome}, serie:{ano: valor}}]}]}]"""
    r = requests.get(url, headers=CABECALHOS, timeout=300)
    r.raise_for_status()
    linhas = []
    for serie in r.json()[0]["resultados"][0]["series"]:
        ano, valor = next(iter(serie["serie"].items()))
        linhas.append({"Municipio_Ibge": int(serie["localidade"]["id"]), "populacao": pd.to_numeric(valor, errors="coerce"),
                       "ano_populacao": int(ano)})
    return pd.DataFrame(linhas).dropna(subset=["populacao"])


def ler_sidra(url: str) -> pd.DataFrame:
    if "servicodados" in url:
        return ler_agregados(url)
    r = requests.get(url, headers=CABECALHOS, timeout=300)
    r.raise_for_status()
    linhas = r.json()
    cab, dados = linhas[0], linhas[1:]          # a 1ª linha do SIDRA é o cabeçalho
    df = pd.DataFrame(dados)
    col_mun = next(k for k, v in cab.items() if v.startswith("Município") and k.endswith("C"))
    col_ano = next(k for k, v in cab.items() if v.startswith("Ano") and k.endswith("N"))
    out = pd.DataFrame({
        "Municipio_Ibge": df[col_mun].astype(int),
        "populacao": pd.to_numeric(df["V"], errors="coerce"),
        "ano_populacao": df[col_ano].astype(int),
    })
    return out.dropna(subset=["populacao"])


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = {}
    for nome, url in FONTES:
        try:
            pop = ler_sidra(url)
            if len(pop) > 5000:
                pop["fonte"] = nome
                pop.to_parquet(RAW / "populacao.parquet", index=False)
                log = {"fonte": nome, "municipios": len(pop), "ano": int(pop["ano_populacao"].max()),
                       "populacao_total": int(pop["populacao"].sum())}
                break
            log[nome] = f"poucas linhas: {len(pop)}"
        except Exception as e:
            log[nome] = f"ERRO: {type(e).__name__}: {e}"[:400]
    (RAW / "_log_ibge.json").write_text(json.dumps(log, ensure_ascii=False, indent=2))
    print(json.dumps(log, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
