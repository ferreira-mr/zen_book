"""
compiler_typst.py — Compilador Typst integrado para BookForge
Utiliza a biblioteca Python `typst` (Rust nativo de alta velocidade).
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import typst
except ImportError:
    typst = None

def compile_typst(typ_file: Path, output_pdf: Path, root_dir: Optional[Path] = None) -> bool:
    """
    Compila um arquivo .typ para output_pdf.
    """
    if typst is None:
        raise ImportError("O pacote 'typst' não está instalado no ambiente virtual.")
        
    typ_file = Path(typ_file).resolve()
    output_pdf = Path(output_pdf).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    
    if root_dir is None:
        root_dir = typ_file.parent
    else:
        root_dir = Path(root_dir).resolve()
        
    print(f"[TYPST] Compilando {typ_file.name} -> {output_pdf.name}...")
    try:
        typst.compile(
            input=str(typ_file),
            output=str(output_pdf),
            root=str(root_dir)
        )
        print(f"[TYPST] Sucesso: {output_pdf.name} ({output_pdf.stat().st_size / (1024*1024):.2f} MB)")
        return True
    except Exception as e:
        print(f"[TYPST] Erro ao compilar {typ_file.name}: {e}", file=sys.stderr)
        return False
