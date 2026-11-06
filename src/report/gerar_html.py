import json
import sys
from itertools import product
from pathlib import Path
import plotly.io as pio
from plotly.offline import get_plotlyjs

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "app"))

from dados import AUTORIAS, COMUNIDADES, METRICAS, OBRAS, nome_comunidade, obras_do_autor 
from tema import TINTA  
from views import ranking, rede, serie_tempo, treemap  

SAIDA = RAIZ / "report/entrega1/app_icmc_science_viz.html"
N_OBRAS_DETALHE = 5

def como_json(fig):
    return json.loads(pio.to_json(fig, validate=False))

def tabela_html(df, casas=2):
    return df.round(casas).to_html(index=False, border=0, na_rep="", classes="tabela-dados")

def figuras():
    n_arestas = len(rede.TRACOS_ARESTAS)
    figs = {"rede": {}, "ranking": {}, "serie": {}}
    for cor in rede.METRICAS_COR:
        fig = como_json(rede.figura(cor, None))
        figs["rede"][cor] = {"data": fig["data"][n_arestas:], "layout": fig["layout"]}
    figs["arestas"] = como_json(rede.figura("comunidade", None))["data"][:n_arestas] 
    for metrica, ordem in product(ranking.METRICAS_PONTE, ["metrica", "citacoes"]):
        figs["ranking"][f"{metrica}|{ordem}"] = como_json(ranking.figura(metrica, ordem))
    for nivel, metrica, escala in product(["campo", "subcampo"], serie_tempo.METRICAS, serie_tempo.ESCALAS):
        figs["serie"][f"{nivel}|{metrica}|{escala}"] = como_json(serie_tempo.figura(nivel, metrica, escala))
    figs["treemap"] = como_json(treemap.figura())
    return figs

def tabelas():
    return {
        "rede": tabela_html(rede.tabela_comunidades()),
        "ranking": {f"{m}|{o}": tabela_html(ranking.tabela(m, o))
                    for m, o in product(ranking.METRICAS_PONTE, ["metrica", "citacoes"])},
        "serie": {f"{n}|{m}": tabela_html(serie_tempo.tabela(n, m), casas=1)
                  for n, m in product(["campo", "subcampo"], serie_tempo.METRICAS)},
        "treemap": tabela_html(treemap.tabela_subcampos()),
    }

def detalhes(fig_treemap):
    obras = OBRAS.reset_index(drop=True)
    posicao = {obra_id: i for i, obra_id in enumerate(obras["obra_id"])}
    usadas = set()

    def mais_citadas(df):
        ids = [posicao[o] for o in df.nlargest(N_OBRAS_DETALHE, "citacoes")["obra_id"]]
        usadas.update(ids)
        return ids

    autores = {}
    for a in METRICAS.itertuples():
        c = int(a.comunidade)
        autores[a.autor_id] = {
            "nome": a.nome, "comunidade": nome_comunidade(c), "rotulo": COMUNIDADES.loc[c, "rotulo"], "c": c,
            "n_obras": int(a.n_obras), "citacoes": int(a.citacoes_total), "grau": int(a.grau),
            "participacao": a.participacao, "intermediacao": a.intermediacao, "constraint": a.constraint,
            "x": a.x, "y": a.y, "obras": mais_citadas(obras_do_autor(a.autor_id)),
        }
    areas = {}
    for id_retangulo in fig_treemap["data"][0]["ids"]:
        partes, filtro = treemap.obras_do_caminho(id_retangulo)
        if partes:
            areas[id_retangulo] = {"titulo": " › ".join(partes), "n": len(filtro),
                                   "media": round(float(filtro["citacoes_por_ano"].mean()), 2),
                                   "obras": mais_citadas(filtro)}
    lista_obras = {i: [obras.at[i, "titulo"] or "(sem título)", int(obras.at[i, "ano"]), int(obras.at[i, "citacoes"])]
                   for i in sorted(usadas)}
    return autores, areas, lista_obras

def opcoes_busca():
    ordenados = METRICAS.sort_values("nome")
    repetidos = ordenados["nome"].duplicated(keep=False)
    return [{"rotulo": f"{a.nome} · C{a.comunidade}" if rep else a.nome, "id": a.autor_id}
            for a, rep in zip(ordenados.itertuples(), repetidos)]

def radios(nome, opcoes, marcado):
    return "".join(f'<label><input type="radio" name="{nome}" value="{valor}"{" checked" if valor == marcado else ""}>'
                   f"{rotulo}</label>" for valor, rotulo in opcoes.items())

def main():
    figs = figuras()
    autores, areas, lista_obras = detalhes(figs["treemap"])
    dados = {"figs": figs, "tabelas": tabelas(), "autores": autores, "areas": areas, "obras": lista_obras,
             "busca": opcoes_busca(), "tinta": TINTA,
             "dicas": {"rede": rede.DICA, "ranking": ranking.DICA, "treemap": treemap.DICA}}
    anos = f"{OBRAS['ano'].min()}–{OBRAS['ano'].max()}"
    resumo = (f"{len(OBRAS):,} obras ({anos}) · {AUTORIAS['autor_id'].nunique():,} autores · "
              f"{len(METRICAS):,} autores ICMC na rede · fonte: OpenAlex").replace(",", ".")
    html = (MODELO
            .replace("__CSS__", (RAIZ / "app/assets/estilo.css").read_text(encoding="utf-8"))
            .replace("__RESUMO__", resumo)
            .replace("__RADIOS_REDE__", radios("rede-cor", {m: r.split(" (")[0] for m, r in rede.METRICAS_COR.items()},
                                               "comunidade"))
            .replace("__RADIOS_RANKING_METRICA__", radios("ranking-metrica", {m: r.split(" (")[0] for m, r
                                                                               in ranking.METRICAS_PONTE.items()},
                                                          "intermediacao"))
            .replace("__RADIOS_RANKING_ORDEM__", radios("ranking-ordem", {"metrica": "Ordenar pela métrica",
                                                                          "citacoes": "Ordenar por citações"},
                                                        "metrica"))
            .replace("__NOTA_RANKING__", f"Top {ranking.N_AUTORES} autores com pelo menos {ranking.GRAU_MINIMO} "
                                         "coautores ICMC. Cor e código (C0, C1…) = comunidade, com as mesmas cores da rede.")
            .replace("__RADIOS_SERIE_METRICA__", radios("serie-metrica", serie_tempo.METRICAS, "obras"))
            .replace("__RADIOS_SERIE_NIVEL__", radios("serie-nivel", {"campo": "Campo", "subcampo": "Subcampo"}, "campo"))
            .replace("__RADIOS_SERIE_ESCALA__", radios("serie-escala", serie_tempo.ESCALAS, "propria"))
            .replace("__PLOTLY__", get_plotlyjs())
            .replace("__DADOS__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(html, encoding="utf-8")
    print(f"{SAIDA.relative_to(RAIZ)}: {SAIDA.stat().st_size / 1e6:.1f} MB")

MODELO = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ICMC Science Viz</title>
<style>
__CSS__
.busca { padding: 6px 8px; font: inherit; border: 1px solid var(--borda); border-radius: 4px; background: white; }
.grafico { width: 100%; }
.tabela-rolagem { max-height: 360px; overflow: auto; margin-top: 6px; }
.tabela-dados { border-collapse: collapse; font-size: 13px; width: 100%; }
.tabela-dados th { position: sticky; top: 0; background: #f0efec; font-weight: 600; text-align: left; padding: 4px 8px; }
.tabela-dados td { padding: 4px 8px; border-top: 1px solid var(--borda); font-variant-numeric: tabular-nums; }
</style>
</head>
<body>
<main>
<header>
  <h1>Produção científica do ICMC-USP</h1>
  <p>__RESUMO__</p>
</header>
<div class="grade">
  <section class="cartao">
    <h2>Rede de coautoria</h2>
    <p class="pergunta">Q1: quais grupos colaboram entre si? · Q3: quem faz a ponte entre eles?</p>
    <div class="controles">
      <div>__RADIOS_REDE__</div>
      <input id="rede-busca" class="busca" list="lista-autores" placeholder="Buscar autor pelo nome…" autocomplete="off">
      <datalist id="lista-autores"></datalist>
    </div>
    <div id="rede-grafico" class="grafico"></div>
    <div id="rede-detalhes"></div>
    <details class="painel-tabela"><summary>Ver os dados em tabela</summary><div id="rede-tabela" class="tabela-rolagem"></div></details>
  </section>
  <section class="cartao">
    <h2>Autores-ponte</h2>
    <p class="pergunta">Q3: quem faz a ponte entre grupos — e se destaca também em citações?</p>
    <div class="controles">
      <div>__RADIOS_RANKING_METRICA__</div>
      <div>__RADIOS_RANKING_ORDEM__</div>
    </div>
    <div id="ranking-grafico" class="grafico"></div>
    <p class="meta">__NOTA_RANKING__</p>
    <div id="ranking-detalhes"></div>
    <details class="painel-tabela"><summary>Ver os dados em tabela</summary><div id="ranking-tabela" class="tabela-rolagem"></div></details>
  </section>
  <section class="cartao">
    <h2>Evolução das áreas</h2>
    <p class="pergunta">Q2: como as áreas e subáreas evoluíram em volume e impacto?</p>
    <div class="controles">
      <div>__RADIOS_SERIE_METRICA__</div>
      <div>__RADIOS_SERIE_NIVEL__</div>
      <div>__RADIOS_SERIE_ESCALA__</div>
    </div>
    <div id="serie-grafico" class="grafico"></div>
    <p class="meta">Um painel por área (as 6 maiores). Escala própria mostra a tendência de cada área; escala comum mostra
      a diferença de volume. Citações de obras recentes ainda estão crescendo.</p>
    <details class="painel-tabela"><summary>Ver os dados em tabela</summary><div id="serie-tabela" class="tabela-rolagem"></div></details>
  </section>
  <section class="cartao">
    <h2>Hierarquia de tópicos</h2>
    <p class="pergunta">Q2: quais áreas concentram a produção e qual o impacto de cada uma?</p>
    <div id="treemap-grafico" class="grafico"></div>
    <div id="treemap-detalhes"></div>
    <details class="painel-tabela"><summary>Ver os dados em tabela</summary><div id="treemap-tabela" class="tabela-rolagem"></div></details>
  </section>
</div>
</main>
<script>__PLOTLY__</script>
<script>
const D = __DADOS__;
const CONFIG = {displaylogo: false, responsive: true};
const $ = id => document.getElementById(id);
const valor = nome => document.querySelector(`input[name="${nome}"]:checked`).value;
const esc = t => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const copia = o => JSON.parse(JSON.stringify(o));

function desenhar(id, data, layout, extra) {
  Plotly.react(id, copia(data), copia(layout), Object.assign({}, CONFIG, extra || {}));
}

function dica(texto) { return `<div class="detalhes vazio">${esc(texto)}</div>`; }

function listaObras(indices) {
  return "<ol>" + indices.map(i => {
    const [titulo, ano, cit] = D.obras[i];
    return `<li><span class="titulo-obra">${esc(titulo)}</span><span class="meta"> (${ano}) — ${cit} citações</span></li>`;
  }).join("") + "</ol>";
}

function detalhesAutor(id) {
  const a = D.autores[id];
  if (!a) return null;
  return `<div class="detalhes"><h3>${esc(a.nome)}</h3>
    <p class="meta">${esc(a.comunidade)} — ${esc(a.rotulo)}</p>
    <table class="tabela-metricas"><tbody>
      <tr><th>Obras</th><td>${a.n_obras}</td><th>Citações</th><td>${a.citacoes}</td></tr>
      <tr><th>Coautores ICMC (grau)</th><td>${a.grau}</td><th>Participação</th><td>${a.participacao.toFixed(2)}</td></tr>
      <tr><th>Intermediação</th><td>${a.intermediacao.toFixed(3)}</td><th>Constraint</th><td>${a.constraint.toFixed(2)}</td></tr>
    </tbody></table>
    <p class="meta">Obras mais citadas:</p>${listaObras(a.obras)}</div>`;
}

// ---- rede
const nomeParaId = {};
$("lista-autores").innerHTML = D.busca.map(o => {
  nomeParaId[o.rotulo] = o.id;
  return `<option value="${esc(o.rotulo)}"></option>`;
}).join("");
let autorBuscado = null;

function destaque(id) {
  const a = D.autores[id];
  return {type: "scatter", x: [a.x], y: [a.y], mode: "markers+text", showlegend: false, text: [a.nome],
          textposition: "top center", textfont: {size: 14, color: D.tinta}, hoverinfo: "skip",
          marker: {size: 34, color: "rgba(0,0,0,0)", line: {width: 3, color: D.tinta}}};
}

function desenharRede() {
  const f = D.figs.rede[valor("rede-cor")];
  const data = D.figs.arestas.concat(f.data, autorBuscado ? [destaque(autorBuscado)] : []);
  desenhar("rede-grafico", data, f.layout, {scrollZoom: true});
}

document.querySelectorAll('input[name="rede-cor"]').forEach(r => r.addEventListener("change", desenharRede));
$("rede-busca").addEventListener("input", e => {
  const id = nomeParaId[e.target.value];
  if (id) {
    autorBuscado = id;
    $("rede-detalhes").innerHTML = detalhesAutor(id);
  } else if (!e.target.value) {
    autorBuscado = null;
    $("rede-detalhes").innerHTML = dica(D.dicas.rede);
  } else {
    return;
  }
  desenharRede();
});
desenharRede();
$("rede-detalhes").innerHTML = dica(D.dicas.rede);
$("rede-tabela").innerHTML = D.tabelas.rede;
$("rede-grafico").on("plotly_click", ev => {
  const p = ev.points[0];
  if (p.customdata) $("rede-detalhes").innerHTML = detalhesAutor(p.customdata[0]) || dica(D.dicas.rede);
});

// ---- ranking
function desenharRanking() {
  const chave = valor("ranking-metrica") + "|" + valor("ranking-ordem");
  const f = D.figs.ranking[chave];
  desenhar("ranking-grafico", f.data, f.layout);
  $("ranking-tabela").innerHTML = D.tabelas.ranking[chave];
}
document.querySelectorAll('input[name="ranking-metrica"], input[name="ranking-ordem"]')
  .forEach(r => r.addEventListener("change", desenharRanking));
desenharRanking();
$("ranking-detalhes").innerHTML = dica(D.dicas.ranking);
$("ranking-grafico").on("plotly_click", ev => {
  const p = ev.points[0];
  if (p.customdata) $("ranking-detalhes").innerHTML = detalhesAutor(p.customdata[0]) || dica(D.dicas.ranking);
});

// ---- série temporal
function desenharSerie() {
  const nivel = valor("serie-nivel"), metrica = valor("serie-metrica");
  const f = D.figs.serie[`${nivel}|${metrica}|${valor("serie-escala")}`];
  desenhar("serie-grafico", f.data, f.layout);
  $("serie-tabela").innerHTML = D.tabelas.serie[`${nivel}|${metrica}`];
}
document.querySelectorAll('input[name="serie-metrica"], input[name="serie-nivel"], input[name="serie-escala"]')
  .forEach(r => r.addEventListener("change", desenharSerie));
desenharSerie();

// ---- treemap
desenhar("treemap-grafico", D.figs.treemap.data, D.figs.treemap.layout);
$("treemap-detalhes").innerHTML = dica(D.dicas.treemap);
$("treemap-tabela").innerHTML = D.tabelas.treemap;
$("treemap-grafico").on("plotly_click", ev => {
  const area = D.areas[ev.points[0].id];
  $("treemap-detalhes").innerHTML = !area ? dica(D.dicas.treemap) :
    `<div class="detalhes"><h3>${esc(area.titulo)}</h3>
     <p class="meta">${area.n} obras · citações por ano (média): ${area.media.toFixed(2)}</p>
     <p class="meta">Obras mais citadas:</p>${listaObras(area.obras)}</div>`;
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
