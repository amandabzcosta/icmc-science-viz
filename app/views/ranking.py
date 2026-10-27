"""V4 — Ranking de autores-ponte, com as citações ao lado. Responde Q3.

Dois painéis lado a lado com o mesmo eixo de autores (pequenos múltiplos, NÃO eixo duplo):
à esquerda a métrica de ponte, à direita o total de citações.
Interações (1ª entrega): escolher a métrica, ordenar, tooltip, clique -> detalhes.
"""
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from plotly.subplots import make_subplots

from componentes import cartao, colunas_e_linhas, detalhes_autor, dica, painel_tabela
from dados import METRICAS, cor_comunidade, nome_comunidade
from tema import aplicar_tema

GRAU_MINIMO = 5   # decisão D22: participação alta com poucos coautores é acaso
N_AUTORES = 20
METRICAS_PONTE = {
    "participacao": "Participação (maior = mais ponte)",
    "intermediacao": "Intermediação (maior = mais ponte)",
    "constraint": "Constraint de Burt (menor = mais ponte)",
}
DICA = "Clique em uma barra para ver os detalhes do autor."


def selecionar(metrica, ordenar_por):
    candidatos = METRICAS[METRICAS["grau"] >= GRAU_MINIMO]
    menor_e_melhor = metrica == "constraint"
    top = candidatos.sort_values(metrica, ascending=menor_e_melhor).head(N_AUTORES)
    if ordenar_por == "citacoes":
        top = top.sort_values("citacoes_total", ascending=False)
    return top.iloc[::-1]  # o 1º do ranking fica no topo do gráfico


def figura(metrica, ordenar_por):
    top = selecionar(metrica, ordenar_por)
    cores = top["comunidade"].map(cor_comunidade)
    # O código da comunidade no rótulo é a 2ª pista além da cor: na simulação de
    # protanopia/deuteranopia, laranja (C1), amarelo (C3) e verde (C5) ficam iguais.
    rotulos = top["nome"] + " · C" + top["comunidade"].astype(str)
    dados = list(zip(top["autor_id"], top["comunidade"].map(nome_comunidade), top["grau"]))
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.58, 0.42], horizontal_spacing=0.03,
                        subplot_titles=[METRICAS_PONTE[metrica], "Citações (total das obras)"])
    fig.add_trace(go.Bar(x=top[metrica], y=rotulos, orientation="h", marker=dict(color=cores, cornerradius=3),
                         customdata=dados, showlegend=False,
                         hovertemplate="<b>%{y}</b><br>%{customdata[1]}<br>%{x:.3f}<br>"
                                       "Coautores ICMC: %{customdata[2]}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=top["citacoes_total"], y=rotulos, orientation="h",
                         marker=dict(color=cores, cornerradius=3), customdata=dados, showlegend=False,
                         hovertemplate="<b>%{y}</b><br>%{x} citações<extra></extra>"), row=1, col=2)
    fig.update_annotations(font=dict(size=12))
    aplicar_tema(fig, altura=560)
    fig.update_layout(bargap=0.25, margin=dict(t=30))  # espaço para os títulos dos dois painéis
    return fig


def tabela(metrica, ordenar_por):
    top = selecionar(metrica, ordenar_por).iloc[::-1]  # de volta à ordem do ranking
    return pd.DataFrame({
        "Autor": top["nome"], "Comunidade": top["comunidade"].map(nome_comunidade),
        METRICAS_PONTE[metrica]: top[metrica].round(3), "Coautores ICMC": top["grau"],
        "Citações": top["citacoes_total"],
    })


def layout():
    controles = [
        dcc.RadioItems(id="ranking-metrica", value="intermediacao", inline=True,
                       options=[{"label": v.split(" (")[0], "value": k} for k, v in METRICAS_PONTE.items()]),
        dcc.RadioItems(id="ranking-ordem", value="metrica", inline=True,
                       options=[{"label": "Ordenar pela métrica", "value": "metrica"},
                                {"label": "Ordenar por citações", "value": "citacoes"}]),
    ]
    nota = html.P(f"Top {N_AUTORES} autores com pelo menos {GRAU_MINIMO} coautores ICMC. "
                  "Cor e código (C0, C1…) = comunidade, com as mesmas cores da rede.", className="meta")
    return cartao("Autores-ponte", "Q3: quem faz a ponte entre grupos — e se destaca também em citações?",
                  controles, dcc.Graph(id="ranking-grafico", config={"displaylogo": False}),
                  html.Div([nota, html.Div(id="ranking-detalhes", children=dica(DICA)),
                            painel_tabela("ranking-tabela")]))


def registrar_callbacks(app):
    @app.callback(Output("ranking-grafico", "figure"), Output("ranking-tabela", "columns"),
                  Output("ranking-tabela", "data"),
                  Input("ranking-metrica", "value"), Input("ranking-ordem", "value"))
    def atualizar(metrica, ordenar_por):
        return figura(metrica, ordenar_por), *colunas_e_linhas(tabela(metrica, ordenar_por), casas=3)

    @app.callback(Output("ranking-detalhes", "children"), Input("ranking-grafico", "clickData"))
    def detalhes(clique):
        if not clique:
            return dica(DICA)
        return detalhes_autor(clique["points"][0]["customdata"][0])
