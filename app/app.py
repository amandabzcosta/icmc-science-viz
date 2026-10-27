from dash import Dash, html
from dados import AUTORIAS, METRICAS, OBRAS
from views import rede, ranking, serie_tempo, treemap

app = Dash(__name__, title="ICMC Science Viz")

anos = f"{OBRAS['ano'].min()}–{OBRAS['ano'].max()}"
n_autores = AUTORIAS["autor_id"].nunique()
cabecalho = html.Header([
    html.H1("Produção científica do ICMC-USP"),
    html.P(f"{len(OBRAS):,} obras ({anos}) · {n_autores:,} autores · {len(METRICAS):,} autores ICMC na rede "
           "· fonte: OpenAlex".replace(",", ".")),
])

app.layout = html.Main([
    cabecalho,
    html.Div(className="grade", children=[
        rede.layout(),
        ranking.layout(),
        serie_tempo.layout(),
        treemap.layout(),
    ]),
])

for visao in (rede, ranking, serie_tempo, treemap):
    visao.registrar_callbacks(app)

if __name__ == "__main__":
    app.run(debug=False)
