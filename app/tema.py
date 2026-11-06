import plotly.graph_objects as go

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_FRACA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
FONTE = 'system-ui, -apple-system, "Segoe UI", sans-serif'
DIVERGENTE = [[0.0, "#e34948"], [0.5, "#f0efec"], [1.0, "#2a78d6"]]
SEQUENCIAL = [[0.0, "#cde2fb"], [0.5, "#3987e5"], [1.0, "#0d366b"]]

def aplicar_tema(fig, altura=420):
    fig.update_layout(
        height=altura,
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font=dict(family=FONTE, size=13, color=TINTA_SECUNDARIA),
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(bgcolor="white", bordercolor=EIXO, font=dict(family=FONTE, size=13, color=TINTA)),
        legend=dict(font=dict(size=12)),
    )
    fig.update_xaxes(gridcolor=GRADE, linecolor=EIXO, zeroline=False, tickcolor=EIXO)
    fig.update_yaxes(gridcolor=GRADE, linecolor=EIXO, zeroline=False, tickcolor=EIXO)
    return fig

PERFIS = {
    "slide": dict(largura=1280, altura=720, k_texto=1.6, k_marca=1.2, escala=2),      # 2560 x 1440 px
    "relatorio": dict(largura=820, altura=560, k_texto=1.2, k_marca=1.0, escala=3),   # 2460 x 1680 px
}

def _escalar(valor, k):
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return valor * k
    return [v * k for v in valor]

def aplicar_perfil(fig, nome):
    p = PERFIS[nome]
    kt, km = p["k_texto"], p["k_marca"]
    base = fig.layout.font.size or 13
    margem = fig.layout.margin
    fig.update_layout(
        width=p["largura"], height=p["altura"], paper_bgcolor="white", plot_bgcolor="white",
        font=dict(size=base * kt),
        legend=dict(font=dict(size=(fig.layout.legend.font.size or 12) * kt)),
        margin=dict(l=(margem.l or 10) * kt, r=(margem.r or 10) * kt, t=(margem.t or 10) * kt, b=(margem.b or 10) * kt),
    )
    for anotacao in fig.layout.annotations:
        anotacao.font.size = (anotacao.font.size or base) * kt
    for traco in fig.data:
        marker = getattr(traco, "marker", None)
        if marker is not None and getattr(marker, "size", None) is not None:
            marker.size = _escalar(marker.size, km)
        if marker is not None and getattr(marker, "line", None) is not None and marker.line.width is not None:
            marker.line.width = marker.line.width * km
        if marker is not None and getattr(marker, "colorbar", None) is not None and marker.colorbar.thickness:
            marker.colorbar.thickness = marker.colorbar.thickness * kt
        texto = getattr(traco, "textfont", None)
        if texto is not None and getattr(texto, "size", None) is not None:
            texto.size = _escalar(texto.size, kt)
        linha = getattr(traco, "line", None)
        if linha is not None and getattr(linha, "width", None) is not None:
            linha.width = linha.width * km
        if traco.type == "treemap" and traco.pathbar.thickness:
            traco.pathbar.thickness = traco.pathbar.thickness * kt
    if fig.layout.coloraxis.colorbar.thickness:
        fig.layout.coloraxis.colorbar.thickness *= kt
    return fig

def figura_vazia(mensagem):
    fig = go.Figure()
    fig.add_annotation(text=mensagem, showarrow=False, font=dict(size=14, color=TINTA_FRACA))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return aplicar_tema(fig, altura=200)
