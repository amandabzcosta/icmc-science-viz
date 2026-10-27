import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from afiliacao import autoria_icmc, normalizar, regra_que_casa
from openalex_api import carregar_config

ARQUIVO_UNIDO = Path("data/raw/obras_unidas.jsonl")
ARQUIVO_SAIDA = Path("docs/validacao_afiliacao.md")
PISTAS_NEGATIVO = r"\b(usp|sao carlos|sao paulo)\b"  

def carregar_obras():
    with open(ARQUIVO_UNIDO, encoding="utf-8") as f:
        return [json.loads(linha) for linha in f]

def listar_autorias(obras, regras):
    linhas = []
    for obra in obras:
        for autoria in obra["authorships"]:
            textos = autoria.get("raw_affiliation_strings") or []
            if not textos:
                continue
            # o texto que casou com alguma regra vem primeiro, para aparecer mesmo após o corte
            textos = sorted(textos, key=lambda t: regra_que_casa(t, regras) is None)
            linhas.append({
                "obra": obra["id"].rsplit("/", 1)[-1],
                "ano": obra["publication_year"],
                "autor": autoria["author"].get("display_name") or autoria.get("raw_author_name"),
                "afiliacao": " | ".join(textos),
                "regra": autoria_icmc(autoria, regras),
            })
    return linhas

def resumo(obras, autorias, regras):
    obras_com_icmc = {a["obra"] for a in autorias if a["regra"]}
    sem_texto = sum(
        all(not (a.get("raw_affiliation_strings") or []) for a in o["authorships"]) for o in obras
    )
    print(f"Obras coletadas:                    {len(obras)}")
    print(f"Obras com >= 1 autoria ICMC:        {len(obras_com_icmc)}")
    print(f"Obras sem nenhuma autoria ICMC:     {len(obras) - len(obras_com_icmc)}")
    print(f"  (dessas, sem nenhum texto de afiliação: {sem_texto})")
    print(f"Autorias com texto de afiliação:    {len(autorias)}")
    print(f"Autorias marcadas ICMC:             {sum(1 for a in autorias if a['regra'])}")
    print("Por regra:", dict(Counter(a["regra"] for a in autorias if a["regra"])))
    return obras_com_icmc

def linha_tabela(i, a):
    afiliacao = a["afiliacao"].replace("|", "/")[:180]
    return f"| {i} | {a['obra']} | {a['ano']} | {a['autor']} | {afiliacao} | {a['regra'] or '—'} | |"

def gravar_amostra(positivos, negativos, args, totais):
    cabecalho = "| # | Obra | Ano | Autor | Afiliação bruta (até 180 caracteres) | Regra | Correto? (S/N) |\n|---|---|---|---|---|---|---|"
    partes = [
        "# Validação da afiliação ICMC (amostra manual)",
        "",
        f"Gerado por `src/collect/validate_affiliation.py` (semente {args.semente}).",
        f"Base: {totais['obras']} obras coletadas; {totais['obras_icmc']} com >= 1 autoria marcada como ICMC.",
        "",
        "**Como preencher:** na última coluna, escreva **S** se a classificação automática está certa e **N** se está errada.",
        "- Na tabela A, \"certa\" = a autoria é mesmo do ICMC.",
        "- Na tabela B, \"certa\" = a autoria realmente NÃO é do ICMC.",
        "",
        f"## A. Autorias marcadas como ICMC ({len(positivos)}) — estima a precisão",
        "",
        cabecalho,
        *[linha_tabela(i, a) for i, a in enumerate(positivos, 1)],
        "",
        f"## B. Autorias NÃO marcadas, mas que citam USP/São Carlos ({len(negativos)}) — procura autores perdidos",
        "",
        cabecalho,
        *[linha_tabela(i, a) for i, a in enumerate(negativos, 1)],
        "",
        "## Resultado (preencher após a conferência)",
        "",
        "- Precisão estimada (A): ___ / ___ corretas",
        "- Autores ICMC perdidos (B): ___ / ___",
        "- Padrões de erro observados:",
        "",
    ]
    ARQUIVO_SAIDA.write_text("\n".join(partes), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Validação da afiliação ICMC por autoria")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--positivos", type=int, default=30)
    parser.add_argument("--negativos", type=int, default=20)
    parser.add_argument("--semente", type=int, default=42)
    args = parser.parse_args()

    regras = carregar_config(args.config)["afiliacao_icmc"]["regras_autoria"]
    obras = carregar_obras()
    autorias = listar_autorias(obras, regras)
    obras_icmc = resumo(obras, autorias, regras)

    sorteio = random.Random(args.semente)
    marcadas = [a for a in autorias if a["regra"]]
    suspeitas = [a for a in autorias
                 if not a["regra"] and re.search(PISTAS_NEGATIVO, normalizar(a["afiliacao"]))]
    print(f"Autorias não marcadas que citam USP/São Carlos: {len(suspeitas)}")

    positivos = sorteio.sample(marcadas, min(args.positivos, len(marcadas)))
    negativos = sorteio.sample(suspeitas, min(args.negativos, len(suspeitas)))
    gravar_amostra(positivos, negativos, args, {"obras": len(obras), "obras_icmc": len(obras_icmc)})
    print(f"\nAmostra gravada em {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
