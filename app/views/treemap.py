import plotly.express as px
from dash import Input, Output, dcc, html
from componentes import cartao, dica, lista_obras, painel_tabela
from dados import OBRAS
from tema import SEQUENCIAL, aplicar_tema

NIVEIS = ["dominio", "campo", "subcampo", "topico"]
RAIZ = "ICMC"
LIMITE_COR = 5
DICA = "Clique em um retângulo para descer um nível e ver as obras mais citadas daquela área."

def figura():
    dados = OBRAS.dropna(subset=NIVEIS).assign(n=1)
    fig = px.treemap(
        dados, path=[px.Constant(RAIZ)] + NIVEIS, values="n", color="citacoes_por_ano",
        color_continuous_scale=SEQUENCIAL, range_color=[0, LIMITE_COR],
        maxdepth=3,  # mostra raiz + domínio + campo; o resto aparece ao clicar
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>%{value} obras<br>Citações por ano (média): %{color:.2f}<extra></extra>",
        texttemplate="%{label}<br>%{value}", marker=dict(line=dict(width=2, color="white")),
        pathbar=dict(visible=True, thickness=22), root=dict(color="#f0efec"),
    )
    fig.update_layout(coloraxis_colorbar=dict(title=dict(text="Citações por ano<br>(média)", side="right"),
                                              thickness=12, tickvals=[0, 1, 2, 3, 4, 5],
                                              ticktext=["0", "1", "2", "3", "4", "≥ 5"]))
    return aplicar_tema(fig, altura=480)

def obras_do_caminho(id_retangulo):
    partes = id_retangulo.split("/", maxsplit=len(NIVEIS))[1:]
    filtro = OBRAS
    for nivel, valor in zip(NIVEIS, partes):
        filtro = filtro[filtro[nivel] == valor]
    return partes, filtro

def tabela_subcampos():
    return (OBRAS.groupby(["campo", "subcampo"])
            .agg(Obras=("obra_id", "size"), **{"Citações por ano (média)": ("citacoes_por_ano", "mean")})
            .reset_index().sort_values("Obras", ascending=False)
            .rename(columns={"campo": "Campo", "subcampo": "Subcampo"}))

def layout():
    return cartao("Hierarquia de tópicos", "Q2: quais áreas concentram a produção e qual o impacto de cada uma?",
                  [], dcc.Graph(id="treemap-grafico", figure=figura(), config={"displaylogo": False}),
                  html.Div([html.Div(id="treemap-detalhes", children=dica(DICA)),
                            painel_tabela("treemap-tabela", tabela_subcampos())]))

def registrar_callbacks(app):
    @app.callback(Output("treemap-detalhes", "children"), Input("treemap-grafico", "clickData"))
    def detalhes(clique):
        if not clique or not clique["points"][0].get("id"):
            return dica(DICA)
        partes, obras = obras_do_caminho(clique["points"][0]["id"])
        if not partes:
            return dica(DICA)
        return html.Div(className="detalhes", children=[
            html.H3(" › ".join(partes)),
            html.P(f"{len(obras)} obras · citações por ano (média): "
                   f"{obras['citacoes_por_ano'].mean():.2f}", className="meta"),
            html.P("Obras mais citadas:", className="meta"),
            lista_obras(obras),
        ])
