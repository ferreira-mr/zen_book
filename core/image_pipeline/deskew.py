"""
deskew.py — Algoritmo de desinclinação (deskew) para páginas digitalizadas
Detecta o ângulo de rotação da página escaneada e aplica rotação precisa.
"""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image

def detect_skew_angle(image: np.ndarray) -> float:
    """
    Detecta o ângulo de inclinação da página em graus.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Inverter cores para que o texto fique branco e o fundo preto
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
    )

    # Detectar linhas horizontais de texto usando morfologia matemática
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
    dilate = cv2.dilate(thresh, kernel, iterations=2)

    # Encontrar contornos
    contours, _ = cv2.findContours(dilate, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    angles = []
    for c in contours:
        if cv2.contourArea(c) < 500:
            continue
        rect = cv2.minAreaRect(c)
        angle = rect[-1]
        
        # Ajustar convenção de ângulo do OpenCV
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
            
        if abs(angle) < 15:  # Filtra rotações anômalas
            angles.append(angle)

    if not angles:
        return 0.0

    # Usar a mediana para robustez contra outliers
    return float(np.median(angles))

def deskew_image(input_path: Path, output_path: Path) -> float:
    """
    Carrega a imagem, detecta inclinação e salva a versão desinclinada.
    Retorna o ângulo corrigido.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(input_path))
    if img is None:
        raise ValueError(f"Não foi possível abrir a imagem: {input_path}")

    angle = detect_skew_angle(img)
    if abs(angle) < 0.2:
        # Praticamente reta, não necessita interpolação
        cv2.imwrite(str(output_path), img)
        return 0.0

    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    cv2.imwrite(str(output_path), rotated)
    return angle
