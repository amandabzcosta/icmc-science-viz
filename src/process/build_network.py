import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path
import networkx as nx
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from openalex_api import carregar_config  # noqa: E402

PASTA = Path("data/processed")

def montar_arestas(obras, autorias, autores_rede, max_autores):
    n_autores = obras.set_index("obra_id")["n_autores"]
    obras_ok = n_autores[n_autores <= max_autores].index
    da_rede = autorias[autorias["autor_id"].isin(autores_rede) & autorias["obra_id"].isin(obras_ok)]

    contagem, fracao = Counter(), Counter()
    for obra_id, grupo in da_rede.groupby("obra_id"):
        ids = sorted(grupo["autor_id"])
        for a, b in itertools.combinations(ids, 2):
            contagem[(a, b)] += 1
            fracao[(a, b)] += 1 / (n_autores[obra_id] - 1)

    return pd.DataFrame(
        [(a, b, contagem[(a, b)], fracao[(a, b)]) for a, b in contagem],
        columns=["autor_a", "autor_b", "n_obras", "peso_frac"],
    )

def montar_grafo(arestas):
    grafo = nx.Graph()
    for linha in arestas.itertuples():
        grafo.add_edge(linha.autor_a, linha.autor_b, peso=linha.n_obras,
                       peso_frac=linha.peso_frac, distancia=1 / linha.n_obras)
    return grafo

def detectar_comunidades(grafo, semente):
    """Louvain com semente fixa. Comunidades numeradas da maior (0) para a menor."""
    grupos = nx.community.louvain_communities(grafo, weight="peso", seed=semente)
    grupos = sorted(grupos, key=len, reverse=True)
    modularidade = nx.community.modularity(grafo, grupos, weight="peso")
    comunidade = {autor: i for i, grupo in enumerate(grupos) for autor in grupo}
    return comunidade, modularidade

def rotular_comunidades(comunidade, autorias, obras, n_termos=3):
    membros = autorias[autorias["autor_id"].isin(comunidade)].assign(
        comunidade=lambda d: d["autor_id"].map(comunidade))
    pares = membros[["comunidade", "obra_id"]].drop_duplicates().merge(obras[["obra_id", "topico"]], on="obra_id")
    documentos = pares.dropna().groupby("comunidade")["topico"].apply(list)

    tfidf = TfidfVectorizer(analyzer=lambda lista: lista)  # cada tópico inteiro é um "termo"
    matriz = tfidf.fit_transform(documentos)
    termos = tfidf.get_feature_names_out()
    rotulos = {}
    for linha, com in enumerate(documentos.index):
        pesos = matriz[linha].toarray().ravel()
        melhores = pesos.argsort()[::-1][:n_termos]
        rotulos[com] = " · ".join(termos[i] for i in melhores if pesos[i] > 0)
    return rotulos

def coeficiente_participacao(grafo, comunidade):
    resultado = {}
    for autor in grafo:
        forca_por_com = Counter()
        for vizinho, dados in grafo[autor].items():
            forca_por_com[comunidade[vizinho]] += dados["peso"]
        total = sum(forca_por_com.values())
        resultado[autor] = 1 - sum((k / total) ** 2 for k in forca_por_com.values())
    return resultado

def layout_por_comunidade(grafo, comunidade, semente, reforco=8):
    desenho = nx.Graph()
    for a, b, dados in grafo.edges(data=True):
        mesma = comunidade[a] == comunidade[b]
        desenho.add_edge(a, b, mola=dados["peso"] * (reforco if mesma else 1))
    return nx.spring_layout(desenho, weight="mola", k=1.5 / len(desenho) ** 0.5, iterations=300, seed=semente)

def metricas_autores(grafo, comunidade, semente):
    print("  calculando intermediação (betweenness)...")
    intermediacao = nx.betweenness_centrality(grafo, weight="distancia")  # exata, sem amostragem
    print("  calculando constraint de Burt...")
    constraint = nx.constraint(grafo, weight="peso")
    participacao = coeficiente_participacao(grafo, comunidade)
    print("  calculando layout (spring)...")
    posicao = layout_por_comunidade(grafo, comunidade, semente)
    return pd.DataFrame({
        "autor_id": list(grafo),
        "comunidade": [comunidade[a] for a in grafo],
        "grau": [grafo.degree(a) for a in grafo],
        "forca": [grafo.degree(a, weight="peso") for a in grafo],
        "participacao": [participacao[a] for a in grafo],
        "intermediacao": [intermediacao[a] for a in grafo],
        "constraint": [constraint[a] for a in grafo],
        "x": [posicao[a][0] for a in grafo],
        "y": [posicao[a][1] for a in grafo],
    })

def resumo_comunidades(grafo, comunidade, rotulos, autorias, obras):
    linhas = []
    for com in sorted(set(comunidade.values())):
        membros = [a for a in grafo if comunidade[a] == com]
        sub = grafo.subgraph(membros)
        forca_total = sum(grafo.degree(a, weight="peso") for a in membros)
        forca_interna = 2 * sub.size(weight="peso")
        obras_com = set(autorias.loc[autorias["autor_id"].isin(membros), "obra_id"])
        linhas.append({
            "comunidade": com,
            "rotulo": rotulos.get(com, ""),
            "n_autores": len(membros),
            "n_obras": len(obras_com),
            "densidade_interna": nx.density(sub),
            "fracao_peso_interno": forca_interna / forca_total if forca_total else None,
            "citacoes_media_obras": obras.loc[obras["obra_id"].isin(obras_com), "citacoes"].mean(),
            "subcampo_principal": obras.loc[obras["obra_id"].isin(obras_com), "subcampo"].mode().iat[0],
        })
    return pd.DataFrame(linhas)

def pares_de_comunidades(comunidade, autorias):
    com = autorias[autorias["autor_id"].isin(comunidade)].assign(
        comunidade=lambda d: d["autor_id"].map(comunidade))
    contagem = Counter()
    for _, grupo in com.groupby("obra_id"):
        presentes = sorted(set(grupo["comunidade"]))
        for a, b in itertools.combinations_with_replacement(presentes, 2):
            if a != b or len(presentes) == 1:  # diagonal = obras só daquela comunidade
                contagem[(a, b)] += 1
    return pd.DataFrame([(a, b, n) for (a, b), n in contagem.items()],
                        columns=["comunidade_a", "comunidade_b", "n_obras"])

def main():
    parser = argparse.ArgumentParser(description="Rede de coautoria ICMC")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    cfg = carregar_config(args.config)["rede"]

    obras = pd.read_parquet(PASTA / "obras.parquet")
    autorias = pd.read_parquet(PASTA / "autorias.parquet")
    autores = pd.read_parquet(PASTA / "autores.parquet")

    icmc = autores[autores["is_icmc"]]
    autores_rede = set(icmc.loc[icmc["n_obras"] >= cfg["min_obras_por_autor"], "autor_id"])
    arestas = montar_arestas(obras, autorias, autores_rede, cfg["max_autores_por_obra"])
    grafo = montar_grafo(arestas)

    componentes = sorted(nx.connected_components(grafo), key=len, reverse=True)
    gigante = grafo.subgraph(componentes[0]).copy()
    arestas["no_componente_gigante"] = arestas["autor_a"].isin(gigante)

    print(f"Rede: {grafo.number_of_nodes()} autores, {grafo.number_of_edges()} arestas; "
          f"componente gigante: {gigante.number_of_nodes()} autores")
    comunidade, modularidade = detectar_comunidades(gigante, cfg["semente_aleatoria"])
    rotulos = rotular_comunidades(comunidade, autorias, obras)
    metricas = metricas_autores(gigante, comunidade, cfg["semente_aleatoria"])
    metricas = metricas.merge(autores[["autor_id", "nome", "n_obras", "citacoes_total"]], on="autor_id")
    comunidades = resumo_comunidades(gigante, comunidade, rotulos, autorias, obras)
    pares = pares_de_comunidades(comunidade, autorias)

    resumo = {
        "autores_icmc": int(len(icmc)),
        "autores_icmc_com_min_obras": len(autores_rede),
        "autores_icmc_sem_coautor_icmc": len(autores_rede) - grafo.number_of_nodes(),
        "autores_na_rede": grafo.number_of_nodes(),
        "arestas_na_rede": grafo.number_of_edges(),
        "componentes": len(componentes),
        "autores_no_componente_gigante": gigante.number_of_nodes(),
        "arestas_no_componente_gigante": gigante.number_of_edges(),
        "autores_fora_do_gigante": grafo.number_of_nodes() - gigante.number_of_nodes(),
        "obras_excluidas_por_max_autores": int((obras["n_autores"] > cfg["max_autores_por_obra"]).sum()),
        "n_comunidades": len(comunidades),
        "modularidade": round(modularidade, 4),
    }
    arestas.to_parquet(PASTA / "arestas_coautoria.parquet", index=False)
    metricas.to_parquet(PASTA / "metricas_autores.parquet", index=False)
    comunidades.to_parquet(PASTA / "comunidades.parquet", index=False)
    pares.to_parquet(PASTA / "pares_comunidades.parquet", index=False)
    with open(PASTA / "rede_resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)

    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    pd.set_option("display.width", 200, "display.max_colwidth", 70)
    print("\nComunidades:\n" + comunidades[["comunidade", "n_autores", "n_obras", "densidade_interna",
                                            "fracao_peso_interno", "rotulo"]].round(3).to_string(index=False))
    print("\nTop 10 por participação (com grau >= 5):")
    print(metricas[metricas["grau"] >= 5].nlargest(10, "participacao")[
        ["nome", "comunidade", "grau", "participacao", "intermediacao", "constraint", "citacoes_total"]
    ].round(3).to_string(index=False))

if __name__ == "__main__":
    main()
