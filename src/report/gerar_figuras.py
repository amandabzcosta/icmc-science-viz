import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dados import METRICAS  # noqa: E402
from simular_daltonismo import MATRIZES, simular  # noqa: E402
from tema import PERFIS, aplicar_perfil  # noqa: E402
from views import ranking, rede, serie_tempo, treemap  # noqa: E402

PASTA_SAIDA = RAIZ / "report/entrega1/figuras/individuais"
NAVEGADORES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

def navegador():
    for caminho in NAVEGADORES:
        if Path(caminho).exists():
            return caminho
    raise SystemExit("Edge ou Chrome não encontrado. Ajuste a lista NAVEGADORES em gerar_figuras.py.")

def fotografar(url, destino, largura, altura, escala):
    destino = Path(destino).resolve()  # o navegador roda em outra pasta: precisa do caminho completo
    subprocess.run([navegador(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={escala}", f"--window-size={largura},{altura}",
                    "--virtual-time-budget=10000", f"--screenshot={destino}", url],
                   capture_output=True, timeout=120)
    if not Path(destino).exists():
        raise SystemExit(f"O navegador não gerou {destino}.")

def salvar_figura(fig, destino, perfil):
    p = PERFIS[perfil]
    corpo = fig.to_html(full_html=False, include_plotlyjs=True, config={"staticPlot": True})
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "figura.html"
        html.write_text(f'<html><head><meta charset="utf-8"></head><body style="margin:0;background:white">'
                        f"{corpo}</body></html>", encoding="utf-8")
        fotografar(html.as_uri(), destino, p["largura"], p["altura"], p["escala"])

def autor_maior_intermediacao():
    return METRICAS.nlargest(1, "intermediacao")["autor_id"].iat[0]

def legenda_a_direita(fig, perfil):
    if perfil == "slide":
        fig.update_layout(legend=dict(orientation="v", x=1.01, y=1, xanchor="left", yanchor="top"))
    return fig

FIGURAS = {
    "v1_rede_comunidades": lambda perfil: legenda_a_direita(rede.figura("comunidade", None), perfil),
    "v1_rede_intermediacao": lambda perfil: rede.figura("intermediacao", autor_maior_intermediacao()),
    "v2_paineis_obras_campo": lambda perfil: serie_tempo.figura("campo", "obras"),
    "v2_paineis_percentual_campo": lambda perfil: serie_tempo.figura("campo", "percentual"),
    "v2_paineis_citacoes_campo": lambda perfil: serie_tempo.figura("campo", "citacoes"),
    "v2_paineis_obras_subcampo": lambda perfil: serie_tempo.figura("subcampo", "obras"),
    "v3_treemap": lambda perfil: treemap.figura(),
    "v4_ranking_intermediacao": lambda perfil: ranking.figura("intermediacao", "metrica"),
}

def fonte(tamanho):
    try:
        return ImageFont.truetype("arial.ttf", tamanho)
    except OSError:
        return ImageFont.load_default()

def com_rotulo(imagem, texto):
    altura = imagem.height // 12
    nova = Image.new("RGB", (imagem.width, imagem.height + altura), "white")
    nova.paste(imagem, (0, altura))
    ImageDraw.Draw(nova).text((imagem.width // 40, altura // 5), texto, fill=(11, 11, 11), font=fonte(altura // 2))
    return nova

def grade(imagens, colunas, espaco):
    linhas = (len(imagens) + colunas - 1) // colunas
    w, h = imagens[0].size
    saida = Image.new("RGB", (colunas * w + (colunas - 1) * espaco, linhas * h + (linhas - 1) * espaco), "white")
    for i, im in enumerate(imagens):
        saida.paste(im, ((i % colunas) * (w + espaco), (i // colunas) * (h + espaco)))
    return saida

def acessibilidade(pasta):
    base = Image.open(pasta / "v4_ranking_intermediacao.png").convert("RGB")
    versoes = {"Visão normal": base}
    nomes = {"protanopia": "Protanopia", "deuteranopia": "Deuteranopia", "tritanopia": "Tritanopia"}
    for tipo, matriz in MATRIZES.items():
        versoes[nomes[tipo]] = simular(base, matriz)
    espaco = base.width // 60
    dupla = grade([com_rotulo(versoes[n], n) for n in ("Visão normal", "Deuteranopia")], 2, espaco)
    dupla.save(pasta / "acessibilidade_ranking_normal_vs_deuteranopia.png")
    quatro = grade([com_rotulo(im, n) for n, im in versoes.items()], 2, espaco)
    quatro.save(pasta / "acessibilidade_ranking_4_visoes.png")
    return ["acessibilidade_ranking_normal_vs_deuteranopia", "acessibilidade_ranking_4_visoes"]

def print_do_app(pasta):
    servidor = subprocess.Popen([sys.executable, str(RAIZ / "app/app.py")], cwd=RAIZ,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urlopen("http://127.0.0.1:8050/", timeout=2)
                break
            except OSError:
                time.sleep(1)
        else:
            raise SystemExit("O app não respondeu em http://127.0.0.1:8050/.")
        fotografar("http://127.0.0.1:8050/", pasta / "app_visao_geral.png", 1920, 1420, 2)
    finally:
        servidor.terminate()

def main():
    parser = argparse.ArgumentParser(description="Gera cada visualização sozinha, em tamanho grande")
    parser.add_argument("--perfil", choices=["slide", "relatorio", "ambos"], default="ambos")
    parser.add_argument("--so", choices=list(FIGURAS), help="gera só esta figura")
    parser.add_argument("--com-app", action="store_true", help="inclui o print da tela inteira do app")
    args = parser.parse_args()

    perfis = ["slide", "relatorio"] if args.perfil == "ambos" else [args.perfil]
    nomes = [args.so] if args.so else list(FIGURAS)
    for perfil in perfis:
        pasta = PASTA_SAIDA / perfil
        pasta.mkdir(parents=True, exist_ok=True)
        gerados = []
        for nome in nomes:
            fig = aplicar_perfil(FIGURAS[nome](perfil), perfil)
            salvar_figura(fig, pasta / f"{nome}.png", perfil)
            gerados.append(nome)
        if "v4_ranking_intermediacao" in nomes:
            gerados += acessibilidade(pasta)
        if args.com_app and perfil == perfis[0]:
            print_do_app(pasta)
            gerados.append("app_visao_geral")
        print(f"\n{perfil}: {pasta.relative_to(RAIZ)}")
        for nome in gerados:
            arquivo = pasta / f"{nome}.png"
            w, h = Image.open(arquivo).size
            print(f"  {nome:48s} {w:5d} x {h:<5d} {arquivo.stat().st_size / 1e6:5.2f} MB")

if __name__ == "__main__":
    main()
