import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, ctx, dcc, html

from componentes import cartao, detalhes_autor, dica, painel_tabela
from dados import (ARESTAS, CINZA_OUTROS, COMUNIDADES, METRICAS, N_DESTAQUE, PALETA, SIMBOLOS,
                   grupo_comunidade, nome_comunidade)
from tema import SEQUENCIAL, TINTA, aplicar_tema

POSICAO = METRICAS.set_index("autor_id")[["x", "y"]]
METRICAS_COR = {
    "comunidade": "Comunidade",
    "participacao": "Participação (maior = mais ponte)",
    "intermediacao": "Intermediação (maior = mais ponte)",
    "constraint": "Constraint de Burt (menor = mais ponte)",
}

def tamanho_no(n_obras):
    return np.clip(4 + 2.2 * np.sqrt(n_obras), 6, 26)

def tracos_arestas():
    faixas = [(1, 1, 0.4, 0.25), (2, 3, 1.0, 0.4), (4, 10_000, 2.2, 0.55)]
    tracos = []
    for minimo, maximo, largura, opacidade in faixas:
        parte = ARESTAS[ARESTAS["n_obras"].between(minimo, maximo)]
        xs, ys = [], []
        for a, b in zip(parte["autor_a"], parte["autor_b"]):
            xs += [POSICAO.at[a, "x"], POSICAO.at[b, "x"], None]
            ys += [POSICAO.at[a, "y"], POSICAO.at[b, "y"], None]
        tracos.append(go.Scattergl(x=xs, y=ys, mode="lines", hoverinfo="skip", showlegend=False,
                                   line=dict(width=largura, color=f"rgba(82,81,78,{opacidade})")))
    return tracos

TRACOS_ARESTAS = tracos_arestas()
DICA = "Clique em um autor (ou busque pelo nome) para ver os detalhes."
TEXTO_HOVER = ("<b>%{customdata[1]}</b><br>%{customdata[2]}<br>"
               "Obras: %{customdata[3]} · Citações: %{customdata[4]}<br>"
               "Coautores ICMC: %{customdata[5]}<extra></extra>")

def dados_hover(df):
    return np.stack([
        df["autor_id"], df["nome"], df["comunidade"].map(nome_comunidade),
        df["n_obras"], df["citacoes_total"], df["grau"],
    ], axis=-1)

def tracos_por_comunidade():
    tracos = []
    grupos = METRICAS["comunidade"].map(grupo_comunidade)
    for g in list(range(N_DESTAQUE)) + [None]:
        parte = METRICAS[grupos.isna()] if g is None else METRICAS[grupos == g]
        tracos.append(go.Scatter(
            x=parte["x"], y=parte["y"], mode="markers",
            name="Outras comunidades" if g is None else nome_comunidade(g),
            marker=dict(size=tamanho_no(parte["n_obras"]), color=CINZA_OUTROS if g is None else PALETA[g],
                        symbol="circle" if g is None else SIMBOLOS[g],
                        line=dict(width=1, color="white"), opacity=0.9),
            customdata=dados_hover(parte), hovertemplate=TEXTO_HOVER,
        ))
    return tracos

def traco_por_metrica(metrica):
    return [go.Scatter(
        x=METRICAS["x"], y=METRICAS["y"], mode="markers", showlegend=False,
        marker=dict(size=tamanho_no(METRICAS["n_obras"]), color=METRICAS[metrica],
                    colorscale=SEQUENCIAL, reversescale=(metrica == "constraint"),
                    colorbar=dict(title=dict(text=METRICAS_COR[metrica], side="right"), thickness=12),
                    line=dict(width=1, color="white")),
        customdata=dados_hover(METRICAS), hovertemplate=TEXTO_HOVER,
    )]

def traco_destaque(autor_id):
    linha = METRICAS[METRICAS["autor_id"] == autor_id].iloc[0]
    return go.Scatter(x=[linha["x"]], y=[linha["y"]], mode="markers+text", showlegend=False,
                      text=[linha["nome"]], textposition="top center", textfont=dict(size=14, color=TINTA),
                      marker=dict(size=34, color="rgba(0,0,0,0)", line=dict(width=3, color=TINTA)),
                      hoverinfo="skip")

def figura(cor_por, autor_buscado):
    tracos = TRACOS_ARESTAS + (tracos_por_comunidade() if cor_por == "comunidade" else traco_por_metrica(cor_por))
    if autor_buscado:
        tracos.append(traco_destaque(autor_buscado))
    fig = go.Figure(tracos)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x")
    fig.update_layout(dragmode="pan", uirevision="rede", hovermode="closest",
                      legend=dict(orientation="h", y=-0.02, yanchor="top", itemsizing="constant"))
    return aplicar_tema(fig, altura=560)

def tabela_comunidades():
    c = COMUNIDADES.reset_index()
    return c.assign(Comunidade=c["comunidade"].map(nome_comunidade))[
        ["Comunidade", "n_autores", "n_obras", "fracao_peso_interno", "densidade_interna", "rotulo"]
    ].rename(columns={"n_autores": "Autores", "n_obras": "Obras", "fracao_peso_interno": "Coesão (peso interno)",
                      "densidade_interna": "Densidade", "rotulo": "Tópicos característicos"})

def layout():
    opcoes_busca = [{"label": n, "value": a}
                    for a, n in METRICAS.sort_values("nome")[["autor_id", "nome"]].itertuples(index=False)]
    controles = [
        dcc.RadioItems(id="rede-cor", value="comunidade", inline=True,
                       options=[{"label": rotulo.split(" (")[0], "value": m} for m, rotulo in METRICAS_COR.items()]),
        dcc.Dropdown(id="rede-busca", options=opcoes_busca, placeholder="Buscar autor pelo nome…",
                     clearable=True, className="busca"),
    ]
    return cartao(
        "Rede de coautoria", "Q1: quais grupos colaboram entre si? · Q3: quem faz a ponte entre eles?",
        controles,
        dcc.Graph(id="rede-grafico", config={"scrollZoom": True, "displaylogo": False}),
        html.Div([html.Div(id="rede-detalhes", children=dica(DICA)),
                  painel_tabela("rede-tabela", tabela_comunidades())]),
    )

def registrar_callbacks(app):
    @app.callback(Output("rede-grafico", "figure"), Input("rede-cor", "value"), Input("rede-busca", "value"))
    def atualizar_figura(cor_por, autor_buscado):
        return figura(cor_por, autor_buscado)

    @app.callback(Output("rede-detalhes", "children"),
                  Input("rede-grafico", "clickData"), Input("rede-busca", "value"))
    def atualizar_detalhes(clique, autor_buscado):
        if ctx.triggered_id == "rede-busca" and autor_buscado:
            return detalhes_autor(autor_buscado)
        if ctx.triggered_id == "rede-grafico" and clique and "customdata" in clique["points"][0]:
            return detalhes_autor(clique["points"][0]["customdata"][0])
        return dica(DICA)
