import os
import time

import requests
import yaml
from dotenv import load_dotenv

load_dotenv(".env")
API_KEY = os.environ.get("OPENALEX_API_KEY")

def carregar_config(caminho="config.yaml"):
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)

def filtro_afiliacao(textos):
    return ",".join(f"raw_affiliation_strings.search:{t}" for t in textos)

def get_com_retentativa(url, params, tentativas=6):
    params = dict(params)
    if API_KEY:
        params["api_key"] = API_KEY
    for tentativa in range(tentativas):
        resposta = requests.get(url, params=params, timeout=60)
        if resposta.status_code != 429 and resposta.status_code < 500:
            break
        espera = float(resposta.headers.get("Retry-After", 2 ** tentativa))
        print(f"  (HTTP {resposta.status_code}; aguardando {espera:.0f} s)")
        time.sleep(espera)
    resposta.raise_for_status()
    return resposta

def consultar_orcamento(base_url):
    if not API_KEY:
        return None
    dados = get_com_retentativa(f"{base_url}/rate-limit", {}).json()["rate_limit"]
    return {
        "usado_usd": dados["daily_used_usd"],
        "restante_usd": dados["daily_remaining_usd"],
        "reinicia_em": dados["resets_at"],
    }
