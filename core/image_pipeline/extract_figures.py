"""
extract_figures.py — Extração de Figuras e Ilustrações de Alta Resolução
Extrai ilustrações vetoriais e rasterizadas do PDF original para a pasta de assets.
"""

from pathlib import Path
from typing import List, Dict
import pymupdf
from PIL import Image

def extract_pdf_embedded_images(pdf_path: Path, output_dir: Path, min_width: int = 150, min_height: int = 150) -> List[Dict]:
    """
    Extrai imagens originais (lossless) incorporadas no PDF.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(str(pdf_path))
    extracted = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        image_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            width = base_image["width"]
            height = base_image["height"]

            if width < min_width or height < min_height:
                continue

            fname = f"page_{page_idx+1:04d}_img_{img_idx+1:02d}.{image_ext}"
            out_file = output_dir / fname
            out_file.write_bytes(image_bytes)

            extracted.append({
                "page": page_idx + 1,
                "xref": xref,
                "width": width,
                "height": height,
                "file": str(out_file.relative_to(output_dir.parent))
            })

    print(f"[EXTRACT] Extraídas {len(extracted)} ilustrações em {output_dir}")
    return extracted

def crop_scanned_figure(
    page_img_path: Path,
    bbox: tuple[int, int, int, int],  # (x0, y0, x1, y1)
    output_path: Path,
    clean_border: bool = True
) -> bool:
    """
    Recorta uma região específica de uma página escaneada para salvar como figura limpa.
    """
    page_img_path = Path(page_img_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(page_img_path) as img:
        cropped = img.crop(bbox)
        cropped.save(output_path, quality=95)
    return True
