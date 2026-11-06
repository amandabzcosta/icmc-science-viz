from pathlib import Path
import pandas as pd

PASTA = Path("data/processed")
ANOS_INICIO, ANOS_FIM = (2010, 2014), (2021, 2025)  

def q1(comunidades, pares):
    print("=" * 70, "\nQ1 — Quais grupos mais colaboram entre si, e quão coesos são?\n")
    entre = pares[pares["comunidade_a"] != pares["comunidade_b"]].nlargest(5, "n_obras")
    rotulo = comunidades.set_index("comunidade")["rotulo"].str.split(" · ").str[0]
    print("Pares de comunidades com mais obras em conjunto:")
    for p in entre.itertuples():
        print(f"  C{p.comunidade_a} ({rotulo[p.comunidade_a]}) × C{p.comunidade_b} ({rotulo[p.comunidade_b]}): {p.n_obras} obras")
    print("\nCoesão (fração do peso das coautorias que fica dentro da comunidade):")
    c = comunidades.sort_values("fracao_peso_interno")
    print(f"  mediana: {comunidades['fracao_peso_interno'].median():.2f}")
    print("  menos coesas: " + "; ".join(f"C{r.comunidade} {r.fracao_peso_interno:.2f}" for r in c.head(3).itertuples()))
    print("  mais coesas:  " + "; ".join(f"C{r.comunidade} {r.fracao_peso_interno:.2f}" for r in c.tail(3).itertuples()))

def q2(obras):
    print("=" * 70, "\nQ2 — Como as áreas evoluíram (volume e impacto)?\n")
    for nivel in ("campo", "subcampo"):
        principais = obras[nivel].value_counts().head(6).index

        def fatia(anos):
            parte = obras[obras["ano"].between(*anos)]
            return parte[nivel].value_counts(normalize=True).reindex(principais).fillna(0) * 100

        tabela = pd.DataFrame({f"% {ANOS_INICIO[0]}–{ANOS_INICIO[1]}": fatia(ANOS_INICIO),
                               f"% {ANOS_FIM[0]}–{ANOS_FIM[1]}": fatia(ANOS_FIM)})
        tabela["variação (p.p.)"] = tabela.iloc[:, 1] - tabela.iloc[:, 0]
        tabela["citações/ano (média)"] = obras.groupby(nivel)["citacoes_por_ano"].mean().reindex(principais)
        print(f"Participação das 6 maiores áreas ({nivel}):")
        print(tabela.round(1).to_string(), "\n")
    print(f"Obras por ano: {obras.groupby('ano').size().to_dict()}")

def q3(metricas):
    print("=" * 70, "\nQ3 — Autores-ponte se destacam em citações ou só em conectividade?\n")
    m = metricas[metricas["grau"] >= 5]
    print(f"Autores com >= 5 coautores ICMC: {len(m)}")
    corr = m[["participacao", "intermediacao", "constraint", "grau", "citacoes_total"]].corr(method="spearman")
    print("Correlação de Spearman com o total de citações:")
    print(corr["citacoes_total"].drop("citacoes_total").round(2).to_string())
    top = m.nlargest(10, "intermediacao")
    mediana = m["citacoes_total"].median()
    acima = (top["citacoes_total"] > mediana).sum()
    print(f"\nTop 10 em intermediação: {acima} de 10 estão acima da mediana de citações ({mediana:.0f}).")
    print(top[["nome", "comunidade", "grau", "intermediacao", "participacao", "citacoes_total"]]
          .round(3).to_string(index=False))

def main():
    obras = pd.read_parquet(PASTA / "obras.parquet")
    metricas = pd.read_parquet(PASTA / "metricas_autores.parquet")
    comunidades = pd.read_parquet(PASTA / "comunidades.parquet")
    pares = pd.read_parquet(PASTA / "pares_comunidades.parquet")
    pd.set_option("display.width", 160)
    q1(comunidades, pares)
    q2(obras)
    q3(metricas)

if __name__ == "__main__":
    main()
