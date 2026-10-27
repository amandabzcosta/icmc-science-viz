import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from openalex_api import API_KEY, carregar_config, consultar_orcamento, filtro_afiliacao, get_com_retentativa

PASTA_RAW = Path("data/raw")
PASTA_OBRAS = PASTA_RAW / "obras"
ARQUIVO_LOG = PASTA_RAW / "log_coleta.jsonl"
ARQUIVO_UNIDO = PASTA_RAW / "obras_unidas.jsonl"

def registrar_log(evento):
    evento["quando"] = datetime.now().isoformat(timespec="seconds")
    with open(ARQUIVO_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")

def coletar_ano(config, variante, ano, destino):
    openalex, escopo = config["openalex"], config["escopo"]
    filtro = (filtro_afiliacao(variante["textos"])
              + f",publication_year:{ano}"
              + f",type:{'|'.join(escopo['tipos_incluidos'])}")
    params = {
        "filter": filtro,
        "select": openalex["campos"].replace(" ", ""),
        "per_page": openalex["per_page"],
        "cursor": "*",
    }
    temporario = destino.with_suffix(".part")
    n_obras = n_paginas = 0
    custo = 0.0
    with open(temporario, "w", encoding="utf-8") as f:
        while params["cursor"]:
            dados = get_com_retentativa(f"{openalex['base_url']}/works", params).json()
            for obra in dados["results"]:
                f.write(json.dumps(obra, ensure_ascii=False) + "\n")
            n_obras += len(dados["results"])
            n_paginas += 1
            custo += dados["meta"].get("cost_usd") or 0.0
            params["cursor"] = dados["meta"].get("next_cursor") if dados["results"] else None
            time.sleep(0.1)  
    temporario.replace(destino)  
    return n_obras, n_paginas, custo

def coletar_tudo(config):
    escopo = config["escopo"]
    anos = range(escopo["ano_inicio"], escopo["ano_fim"] + 1)
    custo_total = 0.0
    for variante in config["afiliacao_icmc"]["variantes"]:
        pasta = PASTA_OBRAS / variante["id"]
        pasta.mkdir(parents=True, exist_ok=True)
        total_variante = 0
        for ano in anos:
            destino = pasta / f"{ano}.jsonl"
            if destino.exists():
                continue  
            n_obras, n_paginas, custo = coletar_ano(config, variante, ano, destino)
            total_variante += n_obras
            custo_total += custo
            registrar_log({"variante": variante["id"], "ano": ano, "obras": n_obras,
                           "paginas": n_paginas, "custo_usd": round(custo, 4)})
        print(f"{variante['id']:36s} {total_variante:6d} obras novas baixadas")
    return custo_total

def unir_variantes(config):
    obras = {}
    for variante in config["afiliacao_icmc"]["variantes"]:
        for arquivo in sorted((PASTA_OBRAS / variante["id"]).glob("*.jsonl")):
            with open(arquivo, encoding="utf-8") as f:
                for linha in f:
                    obra = json.loads(linha)
                    if obra["id"] not in obras:
                        obra["matched_by"] = []
                        obras[obra["id"]] = obra
                    if variante["id"] not in obras[obra["id"]]["matched_by"]:
                        obras[obra["id"]]["matched_by"].append(variante["id"])

    with open(ARQUIVO_UNIDO, "w", encoding="utf-8") as f:
        for obra in obras.values():
            f.write(json.dumps(obra, ensure_ascii=False) + "\n")

    print(f"\nObras únicas após a união: {len(obras)}")
    print(f"{'variante':36s} {'achou':>7s} {'só ela':>7s}")
    for variante in config["afiliacao_icmc"]["variantes"]:
        vid = variante["id"]
        achou = sum(vid in o["matched_by"] for o in obras.values())
        so_ela = sum(o["matched_by"] == [vid] for o in obras.values())
        print(f"{vid:36s} {achou:7d} {so_ela:7d}")
    return len(obras)

def main():
    parser = argparse.ArgumentParser(description="Coleta das obras do ICMC na OpenAlex")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--so-unir", action="store_true", help="não baixa nada; só refaz a união")
    args = parser.parse_args()
    config = carregar_config(args.config)
    base_url = config["openalex"]["base_url"]

    if not args.so_unir:
        if not API_KEY:
            raise SystemExit("Defina OPENALEX_API_KEY no arquivo .env antes de coletar.")
        antes = consultar_orcamento(base_url)
        print("Orçamento antes:", antes)
        custo = coletar_tudo(config)
        depois = consultar_orcamento(base_url)
        print(f"\nCusto somado das respostas: US$ {custo:.4f}")
        print("Orçamento depois:", depois)
        registrar_log({"evento": "sessao", "custo_somado_usd": round(custo, 4),
                       "orcamento_antes": antes, "orcamento_depois": depois})

    total = unir_variantes(config)
    registrar_log({"evento": "uniao", "obras_unicas": total})

if __name__ == "__main__":
    main()
