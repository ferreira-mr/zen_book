#!/usr/bin/env python3
"""
organize_kindle.py — Organiza a pasta documents do Kindle em pastas semânticas,
renomeia os livros para títulos legíveis e limpos, preserva anotações/SDRs
e atualiza miniaturas de capa na memória do Kindle.
"""

import sys
import os
import shutil
import hashlib
import io
from pathlib import Path

# Configurar encoding UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pymupdf
from PIL import Image

KINDLE_DRIVE = Path("E:/")
DOCS_DIR = KINDLE_DRIVE / "documents"
THUMB_DIR = KINDLE_DRIVE / "system" / "thumbnails"

ORGANIZATION_PLAN = [
    # 1. Computação
    {
        "old_name": "fundamentos-de-manutencao-de-software-kindle.pdf",
        "category": "Computação",
        "new_name": "Fundamentos de Manutenção de Software (Marco Tulio Valente).pdf",
        "asin": "B0HJZ35STY"
    },
    {
        "old_name": "engenharia-de-software-moderna-kindle.pdf",
        "category": "Computação",
        "new_name": "Engenharia de Software Moderna (Marco Tulio Valente).pdf",
        "asin": ""
    },
    {
        "old_name": "ai-native-software-engineering-kindle.pdf",
        "category": "Computação",
        "new_name": "AI-Native Software Engineering (Alfonso Graziano).pdf",
        "asin": ""
    },
    {
        "old_name": "ai-native-software-engineering-kindle.epub",
        "category": "Computação",
        "new_name": "AI-Native Software Engineering (Alfonso Graziano).epub",
        "asin": ""
    },
    {
        "old_name": "algoritmos-furlan-kindle.pdf",
        "category": "Computação",
        "new_name": "Algoritmos e Lógica de Programação (Marco A. Furlan de Souza).pdf",
        "asin": ""
    },
    {
        "old_name": "algoritmos-manzano-kindle.pdf",
        "category": "Computação",
        "new_name": "Algoritmos (José Augusto Manzano).pdf",
        "asin": ""
    },

    # 2. Matemática
    {
        "old_name": "matematica-para-vencer-kindle.pdf",
        "category": "Matemática",
        "new_name": "Matemática para Vencer (Laércio Vasconcelos).pdf",
        "asin": ""
    },

    # 3. Línguas e Redação
    {
        "old_name": "cegalla-novissima-gramatica-kindle.pdf",
        "category": "Línguas e Redação",
        "new_name": "Novíssima Gramática da Língua Portuguesa (Domingos Paschoal Cegalla).pdf",
        "asin": ""
    },
    {
        "old_name": "writing-guide-with-handbook-kindle.pdf",
        "category": "Línguas e Redação",
        "new_name": "Writing Guide with Handbook (OpenStax).pdf",
        "asin": ""
    },

    # 4. Aprendizado e Produtividade
    {
        "old_name": "aprendizado-sem-limites-kindle.pdf",
        "category": "Aprendizado e Produtividade",
        "new_name": "Aprendizado Sem Limites (Pedro Miranda).pdf",
        "asin": ""
    },
]

def update_thumbnails(file_path: Path, asin: str = ""):
    """Extrai capa da página 1 (se PDF) e injeta miniaturas no Kindle."""
    if file_path.suffix.lower() != ".pdf":
        return
    try:
        doc = pymupdf.open(str(file_path))
        if len(doc) == 0:
            return
        pix = doc[0].get_pixmap(dpi=180)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img.thumbnail((330, 470), Image.Resampling.LANCZOS)
        
        sha1 = hashlib.sha1(file_path.read_bytes()[:1024*1024]).hexdigest()
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        
        names = [
            f"thumbnail_{file_path.stem}_portrait.jpg",
            f"thumbnail_{file_path.stem}.jpg",
            f"thumbnail_{sha1[:32]}_EBOK_portrait.jpg",
            f"thumbnail_{sha1[:32]}_PDOC_portrait.jpg"
        ]
        if asin:
            names.extend([
                f"thumbnail_{asin}_EBOK_portrait.jpg",
                f"thumbnail_{asin}_PDOC_portrait.jpg"
            ])
            
        for n in names:
            out = THUMB_DIR / n
            img.save(str(out), "JPEG", quality=90)
    except Exception as e:
        print(f"    [Aviso miniatura]: {e}")

def run_organization():
    print(f"\n{'='*75}")
    print("📁 ORGANIZADOR DE DOCUMENTOS DO AMAZON KINDLE (E:/documents)")
    print(f"{'='*75}\n")

    if not DOCS_DIR.exists():
        print(f"Erro: Pasta do Kindle não encontrada em {DOCS_DIR}", file=sys.stderr)
        return False

    # 1. Limpar arquivos duplicados conhecidos
    dup_files = [
        DOCS_DIR / "Fundamentos_de_Manutencao_de_Software_Kindle.pdf",
        DOCS_DIR / "Fundamentos_de_Manutencao_de_Software_Kindle.sdr",
        DOCS_DIR / "Matematica_para_Vencer_Kindle.sdr",
    ]
    for d in dup_files:
        if d.exists():
            print(f"Limpando duplicata/órfão: {d.name}")
            if d.is_dir():
                shutil.rmtree(d)
            else:
                d.unlink()

    # Limpar pastas vazias de Livros se estiverem sem arquivos
    livros_dir = DOCS_DIR / "Livros"
    if livros_dir.exists():
        for sub in list(livros_dir.iterdir()):
            if sub.is_dir() and not list(sub.rglob("*")):
                print(f"Removendo pasta vazia: Livros/{sub.name}")
                sub.rmdir()
        if not list(livros_dir.iterdir()):
            print(f"Removendo pasta vazia: Livros/")
            livros_dir.rmdir()

    # 2. Criar diretórios semânticos e mover livros + SDRs
    total_moved = 0
    for item in ORGANIZATION_PLAN:
        old_name = item["old_name"]
        cat_name = item["category"]
        new_name = item["new_name"]
        asin = item.get("asin", "")

        dest_dir = DOCS_DIR / cat_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / new_name

        cand_names = [
            old_name,
            f"{Path(new_name).stem} - Kindle{Path(new_name).suffix}",
            f"{Path(new_name).stem} - kindle{Path(new_name).suffix}"
        ]
        src_file = None
        for cn in cand_names:
            if (DOCS_DIR / cn).exists():
                src_file = DOCS_DIR / cn
                break
            if (dest_dir / cn).exists():
                src_file = dest_dir / cn
                break

        if not src_file or not src_file.exists():
            # Pode já ter sido movido anteriormente
            if dest_file.exists():
                print(f"✓ Já organizado: [{cat_name}] {new_name}")
            else:
                print(f"⚠️  Não encontrado: {old_name}")
            continue

        print(f"\nOrganizando: {old_name}")
        print(f"  ➜ Categoria: {cat_name}/")
        print(f"  ➜ Novo nome: {new_name}")

        # Mover arquivo principal
        shutil.move(str(src_file), str(dest_file))
        total_moved += 1

        # Mover e atualizar pasta .sdr se existir (para não perder posição de leitura)
        old_sdr = DOCS_DIR / f"{src_file.stem}.sdr"
        new_sdr = dest_dir / f"{dest_file.stem}.sdr"
        if old_sdr.exists():
            print(f"  ➜ Movendo histórico de leitura: {old_sdr.name} -> {new_sdr.name}")
            if new_sdr.exists():
                shutil.rmtree(new_sdr)
            shutil.move(str(old_sdr), str(new_sdr))
            
            # Atualizar prefixo dos arquivos internos .pds/.pdt
            old_stem = src_file.stem
            new_stem = dest_file.stem
            for internal in new_sdr.iterdir():
                if internal.is_file() and internal.name.startswith(old_stem):
                    remainder = internal.name[len(old_stem):]
                    renamed_internal = new_sdr / f"{new_stem}{remainder}"
                    try:
                        internal.rename(renamed_internal)
                    except Exception:
                        pass

        # Injetar capa atualizada no sistema de thumbnails
        update_thumbnails(dest_file, asin=asin)

    print(f"\n{'='*75}")
    print(f"🎉 ORGANIZAÇÃO CONCLUÍDA: {total_moved} livros organizados com sucesso!")
    print(f"{'='*75}\n")
    return True

if __name__ == "__main__":
    run_organization()
