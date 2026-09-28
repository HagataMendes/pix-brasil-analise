"""Estilo visual único para todos os gráficos do projeto (matplotlib)."""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Paleta categórica (ordem fixa, validada para daltonismo) e tons de texto
AZUL, LARANJA, VERDE_AGUA, AMARELO, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
CATEGORICAS = [AZUL, LARANJA, VERDE_AGUA, AMARELO, MAGENTA, "#008300", "#4a3aa7", "#e34948"]
TEXTO, TEXTO_2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def aplicar():
    plt.rcParams.update({
        "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
        "figure.dpi": 110, "font.size": 10.5,
        "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO_2,
        "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlecolor": TEXTO, "axes.titlepad": 12,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.axisbelow": True, "axes.grid.axis": "y", "grid.color": GRADE, "grid.linewidth": 0.8,
        "xtick.color": TEXTO_2, "ytick.color": TEXTO_2, "ytick.left": False,
        "lines.linewidth": 2.2, "legend.frameon": False, "legend.labelcolor": TEXTO_2,
    })


def br(valor: float, casas: int = 1) -> str:
    """Formata número no padrão brasileiro: 1.234,5"""
    s = f"{valor:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def eixo_br(ax, casas: int = 0, sufixo: str = "", prefixo: str = ""):
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{prefixo}{br(v, casas)}{sufixo}"))


def fonte(fig, texto="Fonte: Banco Central do Brasil – Dados Abertos do Pix. Elaboração: Hágata Mendes."):
    fig.text(0.01, -0.02, texto, fontsize=8.5, color=TEXTO_2, ha="left")


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def mes_abrev(data) -> str:
    """Nome do mês em português (o %b do Python sai em inglês)."""
    return MESES[data.month - 1]


def pct(valor: float) -> str:
    """Percentual legível: valores abaixo de 1% aparecem como '<1%'."""
    return "<1%" if 0 < valor < 1 else f"{br(valor, 0)}%"


def rotulos_finais(ax, series: dict, folga: float = 0.05):
    """
    Escreve o nome de cada linha ao lado do seu último ponto, afastando os rótulos
    que ficariam sobrepostos. `series` = {rótulo: pd.Series}; `folga` = distância mínima
    entre rótulos, como fração da altura do eixo.
    """
    y0, y1 = ax.get_ylim()
    minimo = (y1 - y0) * folga
    itens = sorted(((s.iloc[-1], nome, s.index[-1]) for nome, s in series.items()))
    posicoes = []
    for valor, nome, x in itens:
        y = valor if not posicoes else max(valor, posicoes[-1][0] + minimo)
        posicoes.append((y, nome, x))
    for y, nome, x in posicoes:
        ax.annotate(nome, (x, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9, color=TEXTO, annotation_clip=False)
