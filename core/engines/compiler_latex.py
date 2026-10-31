"""
compiler_latex.py — Compilador LaTeX unificado para BookForge
Suporta tectonic (rápido e autossuficiente) e pdflatex (MiKTeX / TeXLive).
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

PDFLATEX_CANDIDATES = [
    r"C:\Users\ferreira-mr\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe",
    "pdflatex"
]

TECTONIC_CANDIDATES = [
    r"C:\Users\ferreira-mr\.gemini\antigravity\bin\tectonic.exe",
    "tectonic"
]

def find_engine(prefer_tectonic: bool = True) -> tuple[str, str]:
    """Retorna (engine_name, executable_path)."""
    if prefer_tectonic:
        for c in TECTONIC_CANDIDATES:
            if Path(c).exists() or shutil.which(c):
                return ("tectonic", c)
    for c in PDFLATEX_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return ("pdflatex", c)
    if not prefer_tectonic:
        for c in TECTONIC_CANDIDATES:
            if Path(c).exists() or shutil.which(c):
                return ("tectonic", c)
    raise FileNotFoundError("Nenhum motor LaTeX (tectonic ou pdflatex) foi encontrado no sistema.")

def assemble_master_tex(template_path: Path, chapter_inputs: List[str], output_path: Path):
    """
    Combina o template LaTeX central com a lista de capítulos para gerar o master .tex.
    """
    template_content = template_path.read_text(encoding="utf-8")
    
    # Se já tem inputs demarcados ou marcador __CHAPTER_INPUTS__
    if "__CHAPTER_INPUTS__" in template_content:
        inputs_block = "\n".join(f"\\input{{{c}}}" for c in chapter_inputs)
        full_content = template_content.replace("__CHAPTER_INPUTS__", inputs_block)
    else:
        # Se termina antes do \end{document}
        idx_doc = template_content.find(r"\begin{document}")
        if idx_doc == -1:
            raise ValueError(f"Não encontrou \\begin{{document}} em {template_path}")
        
        preamble = template_content[:idx_doc + len(r"\begin{document}")]
        inputs_code = "\n".join(f"\\input{{{c}}}" for c in chapter_inputs)
        full_content = f"{preamble}\n\n{inputs_code}\n\n\\end{{document}}\n"
        
    output_path.write_text(full_content, encoding="utf-8")

def compile_latex(tex_file: Path, output_pdf: Path, work_dir: Optional[Path] = None, engine: Optional[str] = None) -> bool:
    """
    Compila o arquivo .tex para o output_pdf desejado.
    """
    tex_file = Path(tex_file).resolve()
    output_pdf = Path(output_pdf).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    
    if work_dir is None:
        work_dir = tex_file.parent
    else:
        work_dir = Path(work_dir).resolve()
        work_dir.mkdir(parents=True, exist_ok=True)

    eng_name, eng_bin = find_engine(prefer_tectonic=(engine != "pdflatex"))
    print(f"[{eng_name.upper()}] Compilando {tex_file.name} -> {output_pdf.name}...")

    if eng_name == "tectonic":
        cmd = [
            eng_bin,
            "-X", "compile",
            str(tex_file),
            "--outdir", str(work_dir)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(work_dir))
        if res.returncode != 0:
            print(f"Erro na compilação via Tectonic (código {res.returncode}):")
            print(res.stderr[-1500:] if res.stderr else res.stdout[-1500:])
            return False
            
        gen_pdf = work_dir / (tex_file.stem + ".pdf")
        if gen_pdf.exists() and gen_pdf != output_pdf:
            shutil.copy2(gen_pdf, output_pdf)
        return True
    else:
        # pdflatex precisa de 2 passagens para sumário e referências
        for p in range(1, 3):
            cmd = [
                eng_bin,
                "-interaction=nonstopmode",
                "--enable-installer",
                f"-output-directory={work_dir}",
                str(tex_file)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(work_dir))
            if res.returncode != 0 and p == 2:
                print(f"Erro na passagem {p} do pdflatex (código {res.returncode}):")
                print(res.stdout[-1500:])
                return False
                
        gen_pdf = work_dir / (tex_file.stem + ".pdf")
        if gen_pdf.exists() and gen_pdf != output_pdf:
            shutil.copy2(gen_pdf, output_pdf)
        return True
