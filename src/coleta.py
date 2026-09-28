"""
Coleta dos dados abertos do Pix na API Olinda do Banco Central.

Para cada endpoint, baixa um arquivo por mês (AAAAMM) e salva em
data/raw/<endpoint>.parquet. Meses já baixados não são baixados de novo,
exceto os 2 mais recentes (o BC pode revisar os números).

Uso:
    python src/coleta.py            # coleta tudo (incremental)
    python src/coleta.py --inicio 202401
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pandas as pd
import requests

BASE = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
PAGINA = 10_000
INICIO_PIX = "202011"  # o Pix foi lançado em novembro de 2020

# nome do arquivo -> (recurso OData, nome do parâmetro de mês)
ENDPOINTS = {
    "estatisticas": ("EstatisticasTransacoesPix", "Database"),
    "municipios": ("TransacoesPixPorMunicipio", "DataBase"),
}
TRABALHADORES = 6  # meses baixados em paralelo


def meses(inicio: str, fim: str) -> list[str]:
    a, m = int(inicio[:4]), int(inicio[4:])
    out = []
    while f"{a}{m:02d}" <= fim:
        out.append(f"{a}{m:02d}")
        m += 1
        if m == 13:
            a, m = a + 1, 1
    return out


def baixar(recurso: str, param: str, valor: str) -> pd.DataFrame:
    """Baixa todas as páginas de um recurso para um valor de parâmetro."""
    linhas, skip = [], 0
    while True:
        url = (
            f"{BASE}/{recurso}({param}=@{param})"
            f"?@{param}='{valor}'&$format=json&$top={PAGINA}&$skip={skip}"
        )
        for tentativa in range(3):
            try:
                r = requests.get(url, timeout=90)
                r.raise_for_status()
                break
            except requests.RequestException:
                if tentativa == 2:
                    raise
                time.sleep(5 * (tentativa + 1))
        lote = r.json().get("value", [])
        linhas.extend(lote)
        if len(lote) < PAGINA:
            break
        skip += PAGINA
    return pd.DataFrame(linhas)


def coletar(nome: str, recurso: str, param: str, lista_meses: list[str], log: dict) -> None:
    arquivo = RAW / f"{nome}.parquet"
    atual = pd.read_parquet(arquivo) if arquivo.exists() else pd.DataFrame()
    ja_tem = set(atual["_mes_ref"].unique()) if "_mes_ref" in atual else set()
    recentes = set(lista_meses[-2:])

    info = log.setdefault(nome, {"meses": {}})
    pendentes = [m for m in lista_meses if m not in ja_tem or m in recentes]

    def tarefa(mes: str):
        inicio = time.time()
        try:
            df = baixar(recurso, param, mes)
            print(f"   {nome} {mes}: {len(df)} linhas ({time.time() - inicio:.0f}s)", flush=True)
            return mes, df, None
        except Exception as e:  # registra o erro e segue para o próximo mês
            print(f"   {nome} {mes}: ERRO {e}", flush=True)
            return mes, None, f"ERRO: {type(e).__name__}: {e}"[:300]

    novos = []
    with ThreadPoolExecutor(max_workers=TRABALHADORES) as pool:
        for mes, df, erro in pool.map(tarefa, pendentes):
            if erro:
                info["meses"][mes] = erro
                continue
            info["meses"][mes] = len(df)
            if df.empty:
                continue
            df["_mes_ref"] = mes
            novos.append(df)
            info["colunas"] = [c for c in df.columns if c != "_mes_ref"]
            info["exemplo"] = json.loads(df.head(3).to_json(orient="records", force_ascii=False))

    if not novos:
        return
    novos_df = pd.concat(novos, ignore_index=True)
    if not atual.empty:
        atual = atual[~atual["_mes_ref"].isin(novos_df["_mes_ref"].unique())]
    final = pd.concat([atual, novos_df], ignore_index=True).sort_values("_mes_ref")
    final.to_parquet(arquivo, index=False)
    info["linhas_total"] = len(final)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default=INICIO_PIX)
    ap.add_argument("--base", choices=list(ENDPOINTS), help="coleta só uma base")
    args = ap.parse_args()

    hoje = date.today()
    fim = f"{hoje.year}{hoje.month:02d}"
    lista = meses(args.inicio, fim)
    RAW.mkdir(parents=True, exist_ok=True)

    arq_log = RAW / "_log_coleta.json"
    log: dict = json.loads(arq_log.read_text()) if arq_log.exists() else {}
    log["executado_em"] = pd.Timestamp.now(tz="America/Sao_Paulo").isoformat()
    for nome, (recurso, param) in ENDPOINTS.items():
        if args.base and nome != args.base:
            continue
        print(f"-> {nome}", flush=True)
        coletar(nome, recurso, param, lista, log)
        arq_log.write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
