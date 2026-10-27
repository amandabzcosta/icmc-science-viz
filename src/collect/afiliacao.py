import html
import re
import unicodedata

def normalizar(texto):
    texto = html.unescape(texto).replace("#N#", " ")
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    so_letras = re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())
    return so_letras.strip()

def compactar(texto):
    return normalizar(texto).replace(" ", "")

def regra_que_casa(texto_afiliacao, regras):
    texto = compactar(texto_afiliacao)
    for regra in regras:
        if not re.search(regra["padrao"], texto):
            continue
        if "exige_tambem" in regra and not re.search(regra["exige_tambem"], texto):
            continue
        return regra["id"]
    return None

def autoria_icmc(autoria, regras):
    for texto in autoria.get("raw_affiliation_strings") or []:
        regra = regra_que_casa(texto, regras)
        if regra:
            return regra
    return None
