import argparse
import zipfile
from pathlib import Path

ARQUIVOS = ["README.md", "LICENSE", "requirements.txt", "config.yaml", ".env.example",
            "data/raw/obras_unidas.jsonl", "data/raw/log_coleta.jsonl"]
PASTAS = ["src", "app", "data/processed"]
IGNORAR = {"__pycache__", ".env", ".venv"}

def listar_arquivos():
    faltando = [a for a in ARQUIVOS if not Path(a).is_file()]
    if faltando:
        raise SystemExit(f"Arquivos não encontrados: {', '.join(faltando)}")
    lista = [Path(a) for a in ARQUIVOS]
    for pasta in PASTAS:
        lista += [p for p in Path(pasta).rglob("*") if p.is_file()]
    return [p for p in lista if not IGNORAR & set(p.parts)]

def main():
    parser = argparse.ArgumentParser(description="Empacota código + dados para entrega")
    parser.add_argument("--nome", required=True, help="ex.: entrega1")
    args = parser.parse_args()

    arquivos = listar_arquivos()
    assert not any(p.name == ".env" for p in arquivos), "o .env (chave da API) não pode ir no pacote"
    destino = Path("dist") / f"icmc-science-viz_{args.nome}.zip"
    destino.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as zipado:
        for arquivo in arquivos:
            zipado.write(arquivo, Path("icmc-science-viz") / arquivo)

    print(f"{destino}: {len(arquivos)} arquivos, {destino.stat().st_size / 1e6:.1f} MB")

if __name__ == "__main__":
    main()
