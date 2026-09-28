"""
Regras de negócio compartilhadas entre notebooks e dashboard.
Centralizar aqui garante que todo lugar do projeto agrupe os dados do mesmo jeito.
"""
import pandas as pd

# NATUREZA: 1ª letra = quem paga, 2ª = quem recebe (P = pessoa, B = empresa, G = governo)
NATUREZA = {
    "P2P": "Pessoa → Pessoa",
    "P2B": "Pessoa → Empresa",
    "B2P": "Empresa → Pessoa",
    "B2B": "Empresa → Empresa",
}
NATUREZA_ORDEM = list(NATUREZA.values()) + ["Governo (qualquer ponta)"]


def natureza(cod: pd.Series) -> pd.Series:
    out = cod.map(NATUREZA)
    out = out.mask(cod.str.contains("G", na=False), "Governo (qualquer ponta)")
    return out  # "Nao disponivel" vira NaN (fica de fora das contas de participação)


# FORMAINICIACAO: como o Pix foi iniciado
FORMA = {
    "DICT": "Chave Pix",
    "QRDN": "QR Code dinâmico",
    "QRES": "QR Code estático",
    "MANU": "Manual (agência e conta)",
    "INIC": "Outras",  # iniciadores de pagamento (Open Finance)
    "AUTO": "Outras",  # Pix Automático
    "APDN": "Outras",  # modalidades lançadas em 2025
    "APES": "Outras",
}
FORMA_ORDEM = ["Chave Pix", "QR Code dinâmico", "QR Code estático", "Manual (agência e conta)", "Outras"]
FORMA_INICIO = 202112  # antes disso o campo quase sempre vinha "Nao disponivel"


def forma(cod: pd.Series) -> pd.Series:
    return cod.map(FORMA)


def para_data(anomes: pd.Series | pd.Index):
    return pd.to_datetime(pd.Series(anomes).astype(str).values, format="%Y%m")
