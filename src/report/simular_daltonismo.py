import argparse
from pathlib import Path
import numpy as np
from PIL import Image

MATRIZES = {
    "protanopia": [[0.152286, 1.052583, -0.204868],
                   [0.114503, 0.786281, 0.099216],
                   [-0.003882, -0.048116, 1.051998]],
    "deuteranopia": [[0.367322, 0.860646, -0.227968],
                     [0.280085, 0.672501, 0.047413],
                     [-0.011820, 0.042940, 0.968881]],
    "tritanopia": [[1.255528, -0.076749, -0.178779],
                   [-0.078411, 0.930809, 0.147602],
                   [0.004733, 0.691367, 0.303900]],
}

def srgb_para_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def linear_para_srgb(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def simular(imagem, matriz):
    rgb = np.asarray(imagem.convert("RGB"), dtype=np.float64) / 255
    linear = srgb_para_linear(rgb)
    simulado = np.clip(linear @ np.array(matriz).T, 0, 1)  
    return Image.fromarray(np.round(linear_para_srgb(simulado) * 255).astype(np.uint8))

def main():
    parser = argparse.ArgumentParser(description="Simulação de daltonismo para figuras do relatório")
    parser.add_argument("imagem")
    args = parser.parse_args()
    origem = Path(args.imagem)
    imagem = Image.open(origem)
    for tipo, matriz in MATRIZES.items():
        destino = origem.with_name(f"{origem.stem}_{tipo}.png")
        simular(imagem, matriz).save(destino)
        print("gerado:", destino)

if __name__ == "__main__":
    main()
