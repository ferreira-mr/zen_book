"""
ocr_draft.py — Extração de Texto Bruto / Pré-OCR de Apoio
Gera um rascunho de texto preliminar para auxiliar o Agente Gemini Flash
na transcrição e validação visual de páginas escaneadas.
"""

from pathlib import Path
from typing import Optional
import pymupdf

def extract_page_text_draft(pdf_path: Path, page_num: int, image_fallback_dir: Optional[Path] = None) -> str:
    """
    Tenta extrair a camada de texto nativa da página (se existir).
    Retorna o texto bruto encontrado.
    """
    doc = pymupdf.open(str(pdf_path))
    if page_num < 1 or page_num > len(doc):
        return ""
    
    page = doc[page_num - 1]
    text = page.get_text()
    
    if text and len(text.strip()) > 30:
        return text.strip()
        
    return ""

def render_page_image(pdf_path: Path, page_num: int, output_png: Path, dpi: int = 160) -> bool:
    """
    Renderiza uma página do PDF para PNG sob demanda com o DPI especificado.
    """
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    
    doc = pymupdf.open(str(pdf_path))
    if page_num < 1 or page_num > len(doc):
        return False
        
    page = doc[page_num - 1]
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(str(output_png))
    return True
