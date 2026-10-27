"""V2 — Evolução das áreas ao longo do tempo (small multiples). Responde Q2.

Um painel por área (as 6 maiores), todos com o mesmo eixo de anos. Cada painel tem
a sua própria linha e o seu título, então dá para ler o valor de cada área sem a
distorção do empilhamento — e a identidade vem do título, não da cor.

Interações (1ª entrega): alternar métrica (nº de obras / % do ano / citações),
agrupar por campo ou subcampo, escala própria ou comum, tooltip.
"""
import textwrap

import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from plotly.subplots import make_subplots

from componentes import cartao, colunas_e_linhas, painel_tabela
from dados import OBRAS, PALETA
from tema import TINTA_FRACA, aplicar_tema

N_SERIES = 6        # as 6 maiores áreas, em grade 2 x 3
COLUNAS = 3
METRICAS = {
    "obras": "Nº de obras",
    "percentual": "% das obras do ano",
    "citacoes": "Citações médias por obra",
}
ESCALAS = {"propria": "Escala própria de cada painel", "comum": "Escala comum"}


def grupos_fixos(nivel):
    """As N maiores áreas no período inteiro (a ordem dos painéis não muda com a métrica)."""
    return OBRAS[nivel].value_counts().head(N_SERIES).index.tolist()


def tabela_por_ano(nivel):
    principais = grupos_fixos(nivel)
    dados = OBRAS.assign(grupo=OBRAS[nivel].where(OBRAS[nivel].isin(principais), "Outros"))
    tabela = dados.groupby(["ano", "grupo"]).agg(obras=("obra_id", "size"), citacoes=("citacoes", "mean"))
    return tabela.reset_index(), principais + ["Outros"]


def valores(tabela, metrica):
    """Ano nas linhas, área nas colunas, com o valor da métrica escolhida."""
    coluna = "citacoes" if metrica == "citacoes" else "obras"
    largura = tabela.pivot(index="ano", columns="grupo", values=coluna).fillna(0)
    if metrica == "percentual":
        largura = largura.div(largura.sum(axis=1), axis=0) * 100  # % sobre todas as obras do ano (inclui "Outros")
    return largura


def titulo_painel(grupo, total):
    """Nome da área (quebrado se for longo) e, na linha de baixo, o total: assim o título cabe na largura do painel."""
    nome = "<br>".join(textwrap.wrap(grupo, 28))
    return f"{nome}<br>({total:,} obras)".replace(",", ".")


def figura(nivel, metrica, escala="propria"):
    tabela, ordem = tabela_por_ano(nivel)
    largura = valores(tabela, metrica)
    totais = OBRAS[nivel].value_counts()
    principais = ordem[:N_SERIES]
    linhas = (len(principais) + COLUNAS - 1) // COLUNAS
    fig = make_subplots(rows=linhas, cols=COLUNAS, shared_xaxes=True, vertical_spacing=0.2, horizontal_spacing=0.06,
                        subplot_titles=[titulo_painel(g, totais[g]) for g in principais])
    sufixo = "%" if metrica == "percentual" else ""
    formato = "%{y:.1f}" if metrica != "obras" else "%{y:.0f}"
    for i, grupo in enumerate(principais):
        linha, coluna = i // COLUNAS + 1, i % COLUNAS + 1
        fig.add_trace(go.Scatter(
            x=largura.index, y=largura[grupo], name=grupo, mode="lines", showlegend=False,
            line=dict(color=PALETA[0], width=2), fill="tozeroy", fillcolor="rgba(42,120,214,0.12)",
            hovertemplate=f"<b>{grupo}</b><br>%{{x}}: {formato}{sufixo}<extra></extra>",
        ), row=linha, col=coluna)
        # 2026 ainda não terminou (coleta em out/2026) e obras recentes tiveram pouco tempo para ser citadas
        fig.add_vrect(x0=2025.5, x1=2026.5, fillcolor="#f0efec", opacity=0.7, line_width=0, layer="below",
                      row=linha, col=coluna)
    fig.update_annotations(font_size=13)  # títulos dos painéis
    fig.add_annotation(text="faixa cinza = 2026 parcial", xref="paper", yref="paper", x=1, y=-0.07,
                       showarrow=False, xanchor="right", yanchor="top", font=dict(size=11, color=TINTA_FRACA))
    if escala == "comum":
        fig.update_yaxes(matches="y")
    fig.update_yaxes(rangemode="tozero")
    fig.update_xaxes(dtick=4, showticklabels=True)
    fig.update_layout(hovermode="x")
    aplicar_tema(fig, altura=470)
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=60))  # espaço para os títulos dos painéis
    return fig


def tabela(nivel, metrica):
    """Ano nas linhas, área nas colunas (inclui "Outros"), com o mesmo valor que o gráfico mostra."""
    dados, ordem = tabela_por_ano(nivel)
    return valores(dados, metrica)[ordem].reset_index().rename(columns={"ano": "Ano"})


def layout():
    controles = [
        dcc.RadioItems(id="serie-metrica", value="obras", inline=True,
                       options=[{"label": v, "value": k} for k, v in METRICAS.items()]),
        dcc.RadioItems(id="serie-nivel", value="campo", inline=True,
                       options=[{"label": "Campo", "value": "campo"}, {"label": "Subcampo", "value": "subcampo"}]),
        dcc.RadioItems(id="serie-escala", value="propria", inline=True,
                       options=[{"label": v, "value": k} for k, v in ESCALAS.items()]),
    ]
    nota = html.P("Um painel por área (as 6 maiores). Escala própria mostra a tendência de cada área; escala "
                  "comum mostra a diferença de volume. Citações de obras recentes ainda estão crescendo.",
                  className="meta")
    return cartao("Evolução das áreas", "Q2: como as áreas e subáreas evoluíram em volume e impacto?",
                  controles, dcc.Graph(id="serie-grafico", config={"displaylogo": False}),
                  html.Div([nota, painel_tabela("serie-tabela")]))


def registrar_callbacks(app):
    @app.callback(Output("serie-grafico", "figure"), Output("serie-tabela", "columns"), Output("serie-tabela", "data"),
                  Input("serie-nivel", "value"), Input("serie-metrica", "value"), Input("serie-escala", "value"))
    def atualizar(nivel, metrica, escala):
        return figura(nivel, metrica, escala), *colunas_e_linhas(tabela(nivel, metrica), casas=1)
