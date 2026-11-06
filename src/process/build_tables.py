import argparse
import json
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "collect"))
from afiliacao import autoria_icmc, normalizar  # noqa: E402
from openalex_api import carregar_config  # noqa: E402

ARQUIVO_UNIDO = Path("data/raw/obras_unidas.jsonl")
PASTA_SAIDA = Path("data/processed")

def id_curto(url):
    return url.rsplit("/", 1)[-1] if url else None

def reconstruir_resumo(indice_invertido):
    if not indice_invertido:
        return None
    posicoes = {}
    for palavra, lista in indice_invertido.items():
        for pos in lista:
            posicoes[pos] = palavra
    return " ".join(posicoes[p] for p in sorted(posicoes))

def nome_de(objeto, chave):
    return ((objeto or {}).get(chave) or {}).get("display_name")

def linha_obra(obra):
    topico = obra.get("primary_topic") or {}
    return {
        "obra_id": id_curto(obra["id"]),
        "doi": obra.get("doi"),
        "titulo": " ".join((obra.get("title") or "").split()) or None,
        "ano": obra.get("publication_year"),
        "tipo": obra.get("type"),
        "idioma": obra.get("language"),
        "citacoes": obra.get("cited_by_count") or 0,
        "n_referencias": obra.get("referenced_works_count"),
        "retratado": bool(obra.get("is_retracted")),
        "resumo": reconstruir_resumo(obra.get("abstract_inverted_index")),
        "topico": topico.get("display_name"),
        "subcampo": nome_de(topico, "subfield"),
        "campo": nome_de(topico, "field"),
        "dominio": nome_de(topico, "domain"),
        "palavras_chave": "; ".join(k["display_name"] for k in obra.get("keywords") or []) or None,
        "campos_todos_topicos": sorted({nome_de(t, "field") for t in obra.get("topics") or []} - {None}),
        "citacoes_por_ano_lista": obra.get("counts_by_year") or [],
        "matched_by": "; ".join(obra["matched_by"]),
    }

def linhas_autorias(obra, regras):
    linhas = []
    for autoria in obra["authorships"]:
        autor = autoria.get("author") or {}
        textos = autoria.get("raw_affiliation_strings") or []
        linhas.append({
            "obra_id": id_curto(obra["id"]),
            "autor_id": id_curto(autor.get("id")),
            "nome": autor.get("display_name") or autoria.get("raw_author_name"),
            "orcid": autor.get("orcid"),
            "posicao": autoria.get("author_position"),
            "regra_icmc": autoria_icmc(autoria, regras),
            "paises": "; ".join(autoria.get("countries") or []) or None,
            "instituicoes": "; ".join(i["display_name"] for i in autoria.get("institutions") or []) or None,
            "afiliacao_bruta": " | ".join(textos) or None,
        })
    return linhas

def ler_dados(regras):
    obras, autorias = [], []
    with open(ARQUIVO_UNIDO, encoding="utf-8") as f:
        for linha in f:
            obra = json.loads(linha)
            obras.append(linha_obra(obra))
            autorias.extend(linhas_autorias(obra, regras))
    autorias = pd.DataFrame(autorias)
    autorias["autoria_icmc"] = autorias["regra_icmc"].notna()
    return pd.DataFrame(obras), autorias

def limpar(obras, autorias, excluir_retratados):
    etapas = {"coletadas": len(obras)}

    obras_icmc = set(autorias.loc[autorias["autoria_icmc"], "obra_id"])
    obras = obras[obras["obra_id"].isin(obras_icmc)]
    etapas["apos_remover_sem_autor_icmc"] = len(obras)

    if excluir_retratados:
        etapas["retratadas_removidas"] = int(obras["retratado"].sum())
        obras = obras[~obras["retratado"]]

    com_doi = obras[obras["doi"].notna()].sort_values("citacoes", ascending=False)
    repetidos = com_doi[com_doi.duplicated("doi")]["obra_id"]
    etapas["doi_repetido_removidas"] = len(repetidos)
    obras = obras[~obras["obra_id"].isin(repetidos)]

    autorias = autorias[autorias["obra_id"].isin(obras["obra_id"])]
    repetida = autorias["autor_id"].notna() & autorias.duplicated(["obra_id", "autor_id"])
    autorias = autorias[~repetida]
    etapas["autorias_sem_autor_id"] = int(autorias["autor_id"].isna().sum())
    etapas["final"] = len(obras)
    return obras.reset_index(drop=True), autorias.reset_index(drop=True), etapas

def adicionar_features(obras, autorias, ano_referencia):
    por_obra = autorias.groupby("obra_id")
    obras["n_autores"] = obras["obra_id"].map(por_obra.size())
    obras["n_autores_icmc"] = obras["obra_id"].map(por_obra["autoria_icmc"].sum()).astype(int)

    paises = autorias.dropna(subset=["paises"]).assign(pais=lambda d: d["paises"].str.split("; ")).explode("pais")
    paises_por_obra = paises.groupby("obra_id")["pais"].agg(lambda s: sorted(set(s)))
    obras["paises"] = obras["obra_id"].map(paises_por_obra)
    obras["tem_pais"] = obras["paises"].notna()
    obras["n_paises"] = obras["paises"].map(lambda p: len(p) if isinstance(p, list) else 0)
    obras["internacional"] = obras["paises"].map(lambda p: isinstance(p, list) and any(x != "BR" for x in p))
    obras["paises"] = obras["paises"].map(lambda p: "; ".join(p) if isinstance(p, list) else None)

    obras["n_campos"] = obras["campos_todos_topicos"].map(len)
    obras["campos_todos_topicos"] = obras["campos_todos_topicos"].map("; ".join)

    obras["idade"] = ano_referencia - obras["ano"]
    obras["citacoes_por_ano"] = obras["citacoes"] / (obras["idade"] + 1)

    media = obras.groupby(["ano", "campo"])["citacoes"].transform("mean")
    obras["citacoes_normalizadas"] = (obras["citacoes"] / media).where(media > 0)

    obras["tem_resumo"] = obras["resumo"].notna()
    return obras

def tabela_citacoes_por_ano(obras):
    linhas = [
        {"obra_id": o, "ano_citacao": c["year"], "citacoes": c["cited_by_count"]}
        for o, lista in zip(obras["obra_id"], obras["citacoes_por_ano_lista"])
        for c in lista
    ]
    return pd.DataFrame(linhas)

def tabela_autores(autorias, obras):
    citacoes = autorias.merge(obras[["obra_id", "citacoes", "ano"]], on="obra_id")
    autores = citacoes.groupby("autor_id").agg(
        nome=("nome", lambda s: s.mode().iat[0]),
        orcid=("orcid", "first"),
        n_obras=("obra_id", "nunique"),
        n_obras_com_afiliacao_icmc=("autoria_icmc", "sum"),
        citacoes_total=("citacoes", "sum"),
        primeiro_ano=("ano", "min"),
        ultimo_ano=("ano", "max"),
    ).reset_index()
    autores["is_icmc"] = autores["n_obras_com_afiliacao_icmc"] > 0
    return autores

def tabela_topicos(obras):
    colunas = ["dominio", "campo", "subcampo", "topico"]
    return (obras.dropna(subset=colunas).groupby(colunas)
            .agg(n_obras=("obra_id", "size"), citacoes_media=("citacoes", "mean")).reset_index())

def cobertura(obras, autorias):
    linhas = [
        ("obras", "doi", obras["doi"].notna().mean()),
        ("obras", "titulo", obras["titulo"].notna().mean()),
        ("obras", "ano", obras["ano"].notna().mean()),
        ("obras", "resumo", obras["tem_resumo"].mean()),
        ("obras", "topico principal", obras["topico"].notna().mean()),
        ("obras", "palavras-chave", obras["palavras_chave"].notna().mean()),
        ("obras", "idioma", obras["idioma"].notna().mean()),
        ("obras", "pais de >= 1 autor", obras["tem_pais"].mean()),
        ("autorias", "texto de afiliacao", autorias["afiliacao_bruta"].notna().mean()),
        ("autorias", "instituicao", autorias["instituicoes"].notna().mean()),
        ("autorias", "pais", autorias["paises"].notna().mean()),
        ("autorias", "orcid", autorias["orcid"].notna().mean()),
    ]
    return pd.DataFrame(linhas, columns=["tabela", "campo", "cobertura"]).assign(
        cobertura=lambda d: (100 * d["cobertura"]).round(1))

def ids_fragmentados(autores):
    icmc = autores[autores["is_icmc"]].assign(nome_norm=lambda d: d["nome"].map(normalizar))
    contagem = icmc.groupby("nome_norm")["autor_id"].nunique()
    return contagem[contagem > 1].sort_values(ascending=False)

def main():
    parser = argparse.ArgumentParser(description="Tabelas limpas do M2")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    config = carregar_config(args.config)
    regras = config["afiliacao_icmc"]["regras_autoria"]

    obras, autorias = ler_dados(regras)
    obras, autorias, etapas = limpar(obras, autorias, config["escopo"]["excluir_retratados"])
    obras = adicionar_features(obras, autorias, config["escopo"]["ano_fim"])
    citacoes_ano = tabela_citacoes_por_ano(obras)
    obras = obras.drop(columns=["citacoes_por_ano_lista"])
    autores = tabela_autores(autorias, obras)
    fragmentados = ids_fragmentados(autores)
    etapas["autores_icmc_nomes_com_mais_de_1_id"] = len(fragmentados)

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    obras.to_parquet(PASTA_SAIDA / "obras.parquet", index=False)
    autorias.to_parquet(PASTA_SAIDA / "autorias.parquet", index=False)
    autores.to_parquet(PASTA_SAIDA / "autores.parquet", index=False)
    tabela_topicos(obras).to_parquet(PASTA_SAIDA / "topicos.parquet", index=False)
    citacoes_ano.to_parquet(PASTA_SAIDA / "citacoes_por_ano.parquet", index=False)
    tabela_cobertura = cobertura(obras, autorias)
    tabela_cobertura.to_csv(PASTA_SAIDA / "cobertura.csv", index=False)
    fragmentados.to_csv(PASTA_SAIDA / "autores_fragmentados.csv")
    with open(PASTA_SAIDA / "limpeza.json", "w", encoding="utf-8") as f:
        json.dump(etapas, f, indent=2, ensure_ascii=False)

    print("Etapas da limpeza:", json.dumps(etapas, indent=2, ensure_ascii=False))
    print(f"\nObras: {len(obras)} | autorias: {len(autorias)} | autores: {len(autores)} "
          f"(ICMC: {autores['is_icmc'].sum()})")
    print("\nCobertura (%):\n" + tabela_cobertura.to_string(index=False))
    print("\nTipos:", obras["tipo"].value_counts().to_dict())
    print(f"Internacionais: {obras['internacional'].mean():.1%} | "
          f"autores por obra (mediana): {obras['n_autores'].median():.0f} | "
          f"obras com > 30 autores: {(obras['n_autores'] > 30).sum()}")
    print("\nNomes ICMC com mais de 1 ID (top 10):\n" + fragmentados.head(10).to_string())

if __name__ == "__main__":
    main()
