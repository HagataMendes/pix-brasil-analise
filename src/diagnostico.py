"""Testa variações de URL na API do Pix e salva o resultado (status + trecho da resposta)."""
import json
import requests
from pathlib import Path

BASE = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
testes = {}
for rec, p in [("EstatisticasTransacoesPix", "Database"), ("TransacoesPixPorMunicipio", "DataBase")]:
    raiz = f"{BASE}/{rec}({p}=@{p})?@{p}='202401'&$format=json"
    for rot, url in {
        "so_format": raiz,
        "top100": raiz + "&$top=100",
        "top10000": raiz + "&$top=10000",
        "top100_skip0": raiz + "&$top=100&$skip=0",
        "top100_skip100": raiz + "&$top=100&$skip=100",
        "mes_sem_aspas": f"{BASE}/{rec}({p}=@{p})?@{p}=202401&$format=json&$top=5",
        "mes_2021": f"{BASE}/{rec}({p}=@{p})?@{p}='202106'&$format=json&$top=5",
    }.items():
        try:
            r = requests.get(url, timeout=180)
            corpo = r.text
            n = len(r.json().get("value", [])) if r.ok else None
            testes[f"{rec}:{rot}"] = {"status": r.status_code, "n": n, "segundos": r.elapsed.total_seconds(), "trecho": corpo[:600]}
        except Exception as e:
            testes[f"{rec}:{rot}"] = {"erro": repr(e)[:300]}
        print(rot, testes[f"{rec}:{rot}"].get("status"), flush=True)
try:
    r = requests.get(f"{BASE}/$metadata", timeout=120)
    testes["metadata"] = r.text[:20000]
except Exception as e:
    testes["metadata"] = repr(e)
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/raw/_diagnostico.json").write_text(json.dumps(testes, ensure_ascii=False, indent=2))
