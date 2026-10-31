"""
binarize_clean.py — Restauração e Limpeza de Páginas Escaneadas
Remove sombras de lombada, normaliza o fundo para branco puro e realça o contraste do texto.
"""

import cv2
import numpy as np
from pathlib import Path

def clean_scanned_page(
    input_path: Path,
    output_path: Path,
    mode: str = "enhanced_grayscale"  # "enhanced_grayscale", "pure_white_bg", "binarized"
) -> bool:
    """
    Restaura uma página escaneada:
    1. Estima o modelo de iluminação de fundo (background illumination)
    2. Divide a imagem pelo fundo para eliminar manchas e sombras de lombada
    3. Normaliza o contraste do texto
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(input_path))
    if img is None:
        return False

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Estimar o fundo usando dilatação morfológica com kernel grande
    # ou filtro bilateral / blur gaussiano pesado
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 51))
    background = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    background = cv2.medianBlur(background, 21)

    # 2. Divisão da imagem pelo fundo normalizado (elimina manchas e degradê de iluminação)
    diff = 255 - cv2.absdiff(gray, background)
    norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)

    if mode == "binarized":
        # Limiarização adaptativa de Otsu
        _, result = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif mode == "pure_white_bg":
        # Empurra tons claros para 255 (branco puro) mantendo o anti-aliasing do texto
        result = cv2.multiply(norm, 1.15)
        result = np.clip(result, 0, 255).astype(np.uint8)
        result[result > 230] = 255
    else:
        # enhanced_grayscale com contraste estendido
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        result = clahe.apply(norm)

    cv2.imwrite(str(output_path), result)
    return True
