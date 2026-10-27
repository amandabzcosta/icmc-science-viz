import argparse
from openalex_api import carregar_config, consultar_orcamento, filtro_afiliacao, get_com_retentativa

def main():
    parser = argparse.ArgumentParser(description="Contagem de obras por variante de afiliação ICMC")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--escopo", action="store_true", help="restringe aos anos e tipos do config.yaml")
    args = parser.parse_args()

    config = carregar_config(args.config)
    base_url = config["openalex"]["base_url"]
    escopo = config["escopo"]

    filtro_escopo = ""
    if args.escopo:
        filtro_escopo = (f",publication_year:{escopo['ano_inicio']}-{escopo['ano_fim']}"
                         f",type:{'|'.join(escopo['tipos_incluidos'])}")
        print(f"Escopo: {escopo['ano_inicio']}-{escopo['ano_fim']}, tipos {escopo['tipos_incluidos']}")
    else:
        print("Escopo: todos os anos e tipos")

    print("Orçamento antes:", consultar_orcamento(base_url), "\n")
    custo_total = 0.0
    for variante in config["afiliacao_icmc"]["variantes"]:
        filtro = filtro_afiliacao(variante["textos"]) + filtro_escopo
        meta = get_com_retentativa(f"{base_url}/works", {"filter": filtro, "per_page": 1}).json()["meta"]
        custo_total += meta.get("cost_usd") or 0.0
        print(f"{variante['id']:36s} {meta['count']:7d}   {' + '.join(variante['textos'])}")

    print(f"\nCusto informado pela API nesta execução: US$ {custo_total:.4f}")
    print("Orçamento depois:", consultar_orcamento(base_url))

if __name__ == "__main__":
    main()
