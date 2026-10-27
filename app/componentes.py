from dash import dash_table, html
from dados import COMUNIDADES, METRICAS, nome_comunidade, obras_do_autor

def cartao(titulo, pergunta, controles, grafico, detalhes):
    return html.Section(className="cartao", children=[
        html.H2(titulo),
        html.P(pergunta, className="pergunta"),
        html.Div(controles, className="controles"),
        grafico,
        detalhes,
    ])

def lista_obras(obras, n=5):
    itens = []
    for obra in obras.nlargest(n, "citacoes").itertuples():
        itens.append(html.Li([
            html.Span(obra.titulo or "(sem título)", className="titulo-obra"),
            html.Span(f" ({obra.ano}) — {obra.citacoes} citações", className="meta"),
        ]))
    return html.Ol(itens)

def detalhes_autor(autor_id):
    autor = METRICAS.set_index("autor_id").loc[autor_id]
    obras = obras_do_autor(autor_id)
    comunidade = int(autor["comunidade"])
    return html.Div(className="detalhes", children=[
        html.H3(autor["nome"]),
        html.P(f"{nome_comunidade(comunidade)} — {COMUNIDADES.loc[comunidade, 'rotulo']}", className="meta"),
        html.Table(className="tabela-metricas", children=[html.Tbody([
            html.Tr([html.Th("Obras"), html.Td(int(autor["n_obras"])),
                     html.Th("Citações"), html.Td(int(autor["citacoes_total"]))]),
            html.Tr([html.Th("Coautores ICMC (grau)"), html.Td(int(autor["grau"])),
                     html.Th("Participação"), html.Td(f"{autor['participacao']:.2f}")]),
            html.Tr([html.Th("Intermediação"), html.Td(f"{autor['intermediacao']:.3f}"),
                     html.Th("Constraint"), html.Td(f"{autor['constraint']:.2f}")]),
        ])]),
        html.P("Obras mais citadas:", className="meta"),
        lista_obras(obras),
    ])

def dica(texto):
    return html.Div(texto, className="detalhes vazio")

def colunas_e_linhas(df, casas=2):
    df = df.round(casas)
    return [{"name": c, "id": c} for c in df.columns], df.to_dict("records")

def painel_tabela(id_tabela, df=None):
    colunas, linhas = colunas_e_linhas(df) if df is not None else ([], [])
    return html.Details(className="painel-tabela", children=[
        html.Summary("Ver os dados em tabela"),
        dash_table.DataTable(
            id=id_tabela, columns=colunas, data=linhas, page_size=10, sort_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"fontFamily": "system-ui, sans-serif", "fontSize": 13, "padding": "4px 8px",
                        "textAlign": "left", "maxWidth": 320, "whiteSpace": "normal"},
            style_header={"fontWeight": "600", "backgroundColor": "#f0efec"},
        ),
    ])
