from pathlib import Path
import pandas as pd

PASTA = Path(__file__).resolve().parents[1] / "data" / "processed"

OBRAS = pd.read_parquet(PASTA / "obras.parquet")
AUTORIAS = pd.read_parquet(PASTA / "autorias.parquet")
METRICAS = pd.read_parquet(PASTA / "metricas_autores.parquet")   
COMUNIDADES = pd.read_parquet(PASTA / "comunidades.parquet").set_index("comunidade")
ARESTAS = pd.read_parquet(PASTA / "arestas_coautoria.parquet")
ARESTAS = ARESTAS[ARESTAS["no_componente_gigante"]]

PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
CINZA_OUTROS = "#a8a69f"
SIMBOLOS = ["circle", "square", "diamond", "triangle-up", "x", "star", "hexagon"]
N_DESTAQUE = len(PALETA)  

def grupo_comunidade(comunidade):
    return comunidade if comunidade < N_DESTAQUE else None

def cor_comunidade(comunidade):
    g = grupo_comunidade(comunidade)
    return CINZA_OUTROS if g is None else PALETA[g]

def nomes_curtos_unicos():
    usados, nomes = set(), {}
    for comunidade, rotulo in COMUNIDADES["rotulo"].items(): 
        topicos = rotulo.split(" · ")
        escolhido = next((t for t in topicos if t not in usados), topicos[0])
        usados.add(escolhido)
        nomes[comunidade] = escolhido
    return nomes

NOMES_CURTOS = nomes_curtos_unicos()

def nome_comunidade(comunidade, curto=True):
    return f"C{comunidade} · {NOMES_CURTOS[comunidade] if curto else COMUNIDADES.loc[comunidade, 'rotulo']}"

def obras_do_autor(autor_id):
    ids = AUTORIAS.loc[AUTORIAS["autor_id"] == autor_id, "obra_id"]
    return OBRAS[OBRAS["obra_id"].isin(ids)]
