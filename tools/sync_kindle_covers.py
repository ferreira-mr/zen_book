#!/usr/bin/env python3
"""
sync_kindle_covers.py — Sincroniza capas, miniaturas e formatos nativos no Kindle (E:)
Garante que as capas apareçam tanto na Biblioteca quanto na Proteção de Tela / Tela de Bloqueio.
"""

import sys
import os
import shutil
import hashlib
import io
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pymupdf
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
KINDLE_DRIVE = Path("E:/")
DOCS_DIR = KINDLE_DRIVE / "documents"
THUMB_DIR = KINDLE_DRIVE / "system" / "thumbnails"
BOOKCOVERS_DIR = KINDLE_DRIVE / "system" / "bookcovers"

# Mapeamento de ASINs conhecidos
KNOWN_ASINS = {
    "fundamentos": "B0HJZ35STY",
    "manutencao": "B0HJZ35STY",
    "engenharia": "B0892B1H5K", # Exemplo de identificador
}

# Livros que possuem versão EPUB no BookForge
EPUB_SOURCES = {
    "Fundamentos de Manutenção de Software (Marco Tulio Valente).epub": 
        BASE_DIR / "library/fundamentos-de-manutencao-de-software/dist/fundamentos-de-manutencao-de-software-kindle.epub",
    "Engenharia de Software Moderna (Marco Tulio Valente).epub": 
        BASE_DIR / "library/engenharia-de-software-moderna/dist/engenharia-de-software-moderna-kindle.epub",
    "Matemática para Vencer (Laércio Vasconcelos).epub": 
        BASE_DIR / "library/matematica-para-vencer/dist/matematica-para-vencer-kindle.epub",
    "Novíssima Gramática da Língua Portuguesa (Domingos Paschoal Cegalla).epub": 
        BASE_DIR / "library/cegalla-novissima-gramatica/dist/cegalla-novissima-gramatica-kindle.epub",
    "Writing Guide with Handbook (OpenStax).epub": 
        BASE_DIR / "library/writing-guide-with-handbook/dist/writing-guide-with-handbook-kindle.epub",
    "Aprendizado Sem Limites (Pedro Miranda).epub": 
        BASE_DIR / "library/aprendizado-sem-limites/dist/aprendizado-sem-limites-kindle.epub",
}

def extract_cover_from_file(file_path: Path) -> Image.Image:
    """Extrai a capa da página 1 (PDF) ou do arquivo de imagem embutido (EPUB)."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        doc = pymupdf.open(str(file_path))
        if len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=180)
            return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    elif ext == ".epub":
        with zipfile.ZipFile(file_path, "r") as z:
            for name in z.namelist():
                if "cover" in name.lower() or "capa" in name.lower() or name.lower().endswith((".jpg", ".jpeg", ".png")):
                    try:
                        data = z.read(name)
                        return Image.open(io.BytesIO(data)).convert("RGB")
                    except Exception:
                        continue
    elif ext == ".azw3":
        for sib in [file_path.with_suffix(".epub"), file_path.with_suffix(".pdf")]:
            if sib.exists():
                return extract_cover_from_file(sib)
    return None

def inject_all_thumbnail_variants(img: Image.Image, file_path: Path, target_dirs: list[Path]):
    """Salva a imagem da capa com todas as variações de hash, ASIN e nome de arquivo."""
    # Redimensiona para resolução padrão Kindle E-Ink (330x470)
    thumb_img = img.copy()
    thumb_img.thumbnail((330, 470), Image.Resampling.LANCZOS)
    
    # Redimensiona versão tela cheia para proteção de tela (600x800)
    full_img = img.copy()
    full_img.thumbnail((600, 800), Image.Resampling.LANCZOS)

    sha1 = hashlib.sha1(file_path.read_bytes()[:1024*1024]).hexdigest()
    
    names = [
        f"thumbnail_{file_path.name}_portrait.jpg",
        f"thumbnail_{file_path.name}.jpg",
        f"thumbnail_{file_path.stem}_portrait.jpg",
        f"thumbnail_{file_path.stem}.jpg",
        f"thumbnail_{sha1[:32]}_EBOK_portrait.jpg",
        f"thumbnail_{sha1[:32]}_PDOC_portrait.jpg",
    ]

    for k, asin_val in KNOWN_ASINS.items():
        if k in file_path.name.lower():
            names.extend([
                f"thumbnail_{asin_val}_EBOK_portrait.jpg",
                f"thumbnail_{asin_val}_PDOC_portrait.jpg"
            ])

    for t_dir in target_dirs:
        t_dir.mkdir(parents=True, exist_ok=True)
        for n in names:
            out_file = t_dir / n
            thumb_img.save(str(out_file), "JPEG", quality=90)
            
        # Salva versão de capa completa se for diretório de bookcovers
        if "bookcovers" in t_dir.name:
            full_out = t_dir / f"{file_path.stem}.jpg"
            full_img.save(str(full_out), "JPEG", quality=92)

def run():
    print(f"\n{'='*75}")
    print("🎨 SINCRONIZADOR DE CAPAS E TELA DE PROTEÇÃO DO KINDLE (E:)")
    print(f"{'='*75}\n")

    if not DOCS_DIR.exists():
        print("Erro: Kindle não encontrado em E:/documents", file=sys.stderr)
        return False

    # 1. Copiar versões EPUB correspondentes para cada pasta semântica
    print(">>> 1. Sincronizando edições EPUB (nativas para Tela de Proteção / Lock Screen)...")
    semantic_dirs = {
        "Computação": [
            "Fundamentos de Manutenção de Software (Marco Tulio Valente).epub",
            "Engenharia de Software Moderna (Marco Tulio Valente).epub"
        ],
        "Matemática": [
            "Matemática para Vencer (Laércio Vasconcelos).epub"
        ],
        "Línguas e Redação": [
            "Novíssima Gramática da Língua Portuguesa (Domingos Paschoal Cegalla).epub",
            "Writing Guide with Handbook (OpenStax).epub"
        ],
        "Aprendizado e Produtividade": [
            "Aprendizado Sem Limites (Pedro Miranda).epub"
        ]
    }

    for cat, epubs in semantic_dirs.items():
        cat_dir = DOCS_DIR / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        for ep in epubs:
            src = EPUB_SOURCES.get(ep)
            dest = cat_dir / ep
            if src and src.exists():
                if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                    shutil.copy2(src, dest)
                    print(f"  ✓ Copiado para [{cat}]: {ep}")
                else:
                    print(f"  • Já presente [{cat}]: {ep}")

    # 2. Varrer todos os livros na pasta documents e injetar capas
    print("\n>>> 2. Gerando e injetando miniaturas na memória do Kindle (thumbnails & bookcovers)...")
    target_dirs = [
        THUMB_DIR,
        BOOKCOVERS_DIR
    ]
    
    total_processed = 0
    for f in sorted(DOCS_DIR.rglob("*")):
        if f.is_file() and f.suffix.lower() in [".pdf", ".epub", ".azw3"]:
            # Ignora arquivos de dicionários e downloads do sistema
            if any(p in str(f) for p in ["dictionaries", "Downloads", ".cache"]):
                continue
            print(f"  Processando: {f.name}...")
            img = extract_cover_from_file(f)
            if img:
                inject_all_thumbnail_variants(img, f, target_dirs)
                total_processed += 1
                print(f"    ✓ Capas e miniaturas injetadas com sucesso!")
            else:
                print(f"    ⚠️ Não foi possível extrair imagem de capa.")

    print(f"\n{'='*75}")
    print(f"🎉 CONCLUÍDO! {total_processed} livros atualizados com capas para Biblioteca e Tela de Descanso.")
    print(f"{'='*75}")
    print("\nComo testar no Kindle:")
    print("1. No Windows, clique em 'Ejetar / Remover com segurança' na unidade E: e retire o cabo USB.")
    print("2. No Kindle, abra qualquer um dos livros (ex: Fundamentos de Manutenção de Software).")
    print("3. Pressione o botão de energia ou feche a capa magnética: a capa aparecerá na tela de descanso!")
    print(f"{'='*75}\n")
    return True

if __name__ == "__main__":
    run()
