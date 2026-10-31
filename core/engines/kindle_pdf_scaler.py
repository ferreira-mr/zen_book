"""
kindle_pdf_scaler.py — Conversor/Reescalador Inteligente para Kindle E-Ink PDF (3:4)
Recorta margens excessivas e reescala o conteúdo vetorial para 105mm x 140mm.
"""

from pathlib import Path
from typing import Optional, List
import pymupdf

def scale_pdf_to_kindle(src_pdf: Path, out_pdf: Path, toc: Optional[List[list]] = None) -> bool:
    """
    Reescala um PDF para proporção nativa de telas E-Ink Kindle (105x140mm).
    """
    src_pdf = Path(src_pdf).resolve()
    out_pdf = Path(out_pdf).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[KINDLE-SCALER] Reescalando {src_pdf.name} -> {out_pdf.name}...")
    try:
        src = pymupdf.open(str(src_pdf))
        out = pymupdf.open()
        
        target_w = 105 * 72 / 25.4  # 297.64 pt
        target_h = 140 * 72 / 25.4  # 396.85 pt
        
        total = len(src)
        for i in range(total):
            p = src[i]
            bbox = pymupdf.Rect()
            for b in p.get_text('blocks'):
                bbox.include_rect(pymupdf.Rect(b[:4]))
            for d in p.get_drawings():
                r = d['rect']
                if r.width < p.rect.width - 5 or r.height < p.rect.height - 5:
                    bbox.include_rect(r)
                    
            if bbox.is_empty:
                bbox = p.rect
            else:
                # Padding de conforto para leitura no e-reader
                bbox = pymupdf.Rect(bbox.x0 - 14, bbox.y0 - 14, bbox.x1 + 14, bbox.y1 + 14)
                bbox.intersect(p.rect)
                
            np = out.new_page(width=target_w, height=target_h)
            scale = min(target_w / bbox.width, target_h / bbox.height)
            fit_w = bbox.width * scale
            fit_h = bbox.height * scale
            dest_rect = pymupdf.Rect((target_w - fit_w)/2, (target_h - fit_h)/2, (target_w + fit_w)/2, (target_h + fit_h)/2)
            np.show_pdf_page(dest_rect, src, i, clip=bbox)
            
        if toc:
            out.set_toc(toc)
        else:
            orig_toc = src.get_toc()
            if orig_toc:
                out.set_toc(orig_toc)
                
        out.save(str(out_pdf), deflate=True, garbage=4)
        print(f"[KINDLE-SCALER] Concluído: {out_pdf.name} ({out_pdf.stat().st_size / (1024*1024):.2f} MB)")
        return True
    except Exception as e:
        print(f"[KINDLE-SCALER] Erro ao reescalar PDF: {e}")
        return False
