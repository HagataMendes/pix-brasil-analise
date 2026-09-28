"""
Coleta dos dados abertos do Pix na API Olinda do Banco Central.

Como a API funciona (descoberto testando):
- o parâmetro de mês funciona como "a partir de": pedir '202401' traz
  todos os meses de jan/2024 em diante;
- a API NÃO aceita paginação ($skip), então cada base vem numa chamada só.

Por isso a coleta é incremental assim: se já existe dado salvo, pedimos só
a partir de 2 meses antes do último mês que temos (o BC pode revisar os
números recentes) e substituímos esses meses.

Uso:
    python src/coleta.py                     # todas as bases
    python src/coleta.py --base municipios   # só uma base
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
INICIO_PIX = "202011"  # o Pix foi lançado em novembro de 2020

# nome do arquivo -> (recurso na API, nome do parâmetro de mês)
BASES = {
    "estatisticas": ("EstatisticasTransacoesPix", "Database"),
    "municipios": ("TransacoesPixPorMunicipio", "DataBase"),
}


def baixar(recurso: str, param: str, a_partir_de: str) -> pd.DataFrame:
    url = f"{BASE}/{recurso}({param}=@{param})?@{param}='{a_partir_de}'&$format=json"
    for tentativa in range(3):
        try:
            r = requests.get(url, timeout=600)
            r.raise_for_status()
            return pd.DataFrame(r.json()["value"])
        except requests.RequestException:
            if tentativa == 2:
                raise
            time.sleep(15 * (tentativa + 1))


def mes_anterior(anomes: int, n: int) -> str:
    a, m = divmod(anomes, 100)
    m -= n
    while m < 1:
        a, m = a - 1, m + 12
    return f"{a}{m:02d}"


def coletar(nome: str) -> dict:
    recurso, param = BASES[nome]
    arquivo = RAW / f"{nome}.parquet"
    atual = pd.read_parquet(arquivo) if arquivo.exists() else pd.DataFrame()
    inicio = mes_anterior(int(atual["AnoMes"].max()), 2) if not atual.empty else INICIO_PIX

    t0 = time.time()
    novos = baixar(recurso, param, inicio)
    print(f"-> {nome}: {len(novos):,} linhas a partir de {inicio} ({time.time() - t0:.0f}s)", flush=True)

    if not atual.empty:
        atual = atual[~atual["AnoMes"].isin(novos["AnoMes"].unique())]
    final = pd.concat([atual, novos], ignore_index=True).sort_values("AnoMes", kind="stable")
    final.to_parquet(arquivo, index=False)

    por_mes = final.groupby("AnoMes").size()
    return {
        "linhas": len(final),
        "primeiro_mes": int(por_mes.index.min()),
        "ultimo_mes": int(por_mes.index.max()),
        "meses": len(por_mes),
        "colunas": list(final.columns),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", choices=list(BASES))
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    arq_log = RAW / "_log_coleta.json"
    log = {"executado_em": pd.Timestamp.now(tz="America/Sao_Paulo").isoformat()}
    if arq_log.exists():
        log = {**json.loads(arq_log.read_text()), **log}
    for nome in BASES:
        if args.base and nome != args.base:
            continue
        try:
            log[nome] = coletar(nome)
        except Exception as e:
            log[nome] = {"erro": f"{type(e).__name__}: {e}"[:500]}
            print(f"-> {nome}: ERRO {e}", flush=True)
        arq_log.write_text(json.dumps(log, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
