#!/usr/bin/env python3
"""
send_to_kindle.py — Transfere livros (AZW3 e/ou PDF) e simula o Calibre injetando capas na memória do Kindle
Compatível com Windows, macOS e Linux.
"""

import sys
import os
import shutil
import string
import hashlib
import io
import zipfile
import argparse
from pathlib import Path
from typing import Optional

# Configurar encoding UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import pymupdf
    from PIL import Image
except ImportError as e:
    print(f"Erro: Dependências ausentes ({e}). Execute via .venv\\Scripts\\python.exe", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from core.engines.azw3_converter import convert_epub_to_azw3, find_ebook_convert
except ImportError:
    convert_epub_to_azw3 = None
    find_ebook_convert = None


def detect_kindle_drive() -> list[Path]:
    """Detecta automaticamente unidades USB montadas com estrutura do Kindle."""
    candidates = []

    if os.name == "nt":
        # Windows: busca de D: a Z:
        for letter in string.ascii_uppercase:
            if letter in ["C"]:
                continue
            drive = Path(f"{letter}:\\")
            if drive.exists():
                docs_dir = drive / "documents"
                if docs_dir.is_dir():
                    candidates.append(drive)
    else:
        # Linux / macOS
        mount_roots = [Path("/media"), Path("/run/media"), Path("/Volumes")]
        for root in mount_roots:
            if root.exists():
                for sub in root.iterdir():
                    if (sub / "documents").is_dir():
                        candidates.append(sub)

    return candidates


def extract_cover_image(source_file: Path) -> Optional[Image.Image]:
    """Extrai a capa da página 1 (PDF) ou de imagem interna de capa (EPUB)."""
    if not source_file or not source_file.exists():
        return None

    ext = source_file.suffix.lower()

    if ext == ".pdf":
        try:
            doc = pymupdf.open(str(source_file))
            if len(doc) > 0:
                pix = doc[0].get_pixmap(dpi=180)
                return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        except Exception as e:
            print(f"  Aviso: falha ao extrair capa do PDF ({e})")

    elif ext == ".epub":
        try:
            with zipfile.ZipFile(source_file, "r") as z:
                # Procura por arquivos com 'cover' ou 'capa' no nome
                cover_entries = []
                for name in z.namelist():
                    n_low = name.lower()
                    if any(k in n_low for k in ["cover", "capa"]) and n_low.endswith((".jpg", ".jpeg", ".png")):
                        cover_entries.append(name)
                # Se não achou com cover/capa, pega a primeira imagem raster
                if not cover_entries:
                    for name in z.namelist():
                        if name.lower().endswith((".jpg", ".jpeg", ".png")):
                            cover_entries.append(name)
                            break

                if cover_entries:
                    img_data = z.read(cover_entries[0])
                    return Image.open(io.BytesIO(img_data)).convert("RGB")
        except Exception as e:
            print(f"  Aviso: falha ao extrair capa do EPUB ({e})")

    # Se for AZW3, tenta encontrar o EPUB ou PDF irmão
    elif ext == ".azw3":
        parent = source_file.parent
        for sibling_name in [f"{source_file.stem}.epub", f"{source_file.stem}.pdf"]:
            cand = parent / sibling_name
            if cand.exists():
                img = extract_cover_image(cand)
                if img:
                    return img

    return None


def generate_and_inject_thumbnails(target_file: Path, cover_img: Image.Image, thumb_dir: Path, asin: str = ""):
    """Injeta as miniaturas no Kindle para o arquivo de livro alvo (AZW3 ou PDF)."""
    thumb_dir.mkdir(parents=True, exist_ok=True)

    # Redimensiona para resolução ideal do Kindle E-Ink (330x470)
    img_thumb = cover_img.copy()
    img_thumb.thumbnail((330, 470), Image.Resampling.LANCZOS)

    # Versão em alta definição para lockscreen/bookcovers (600x800)
    img_full = cover_img.copy()
    img_full.thumbnail((600, 800), Image.Resampling.LANCZOS)

    # Calcula hash SHA1 do primeiro MB do arquivo
    try:
        sha1 = hashlib.sha1(target_file.read_bytes()[: 1024 * 1024]).hexdigest()
    except Exception:
        sha1 = hashlib.sha1(target_file.name.encode("utf-8")).hexdigest()

    thumb_names = [
        f"thumbnail_{target_file.name}_portrait.jpg",
        f"thumbnail_{target_file.stem}_portrait.jpg",
        f"thumbnail_{target_file.stem}.jpg",
        f"thumbnail_{sha1[:32]}_EBOK_portrait.jpg",
        f"thumbnail_{sha1[:32]}_PDOC_portrait.jpg",
    ]

    if asin:
        thumb_names.extend([
            f"thumbnail_{asin}_EBOK_portrait.jpg",
            f"thumbnail_{asin}_PDOC_portrait.jpg",
        ])

    for t_name in thumb_names:
        dest = thumb_dir / t_name
        img_thumb.save(str(dest), "JPEG", quality=90)

    # Se for a pasta bookcovers, salva também a versão full
    if "bookcovers" in thumb_dir.name.lower():
        full_dest = thumb_dir / f"{target_file.stem}.jpg"
        img_full.save(str(full_dest), "JPEG", quality=92)


def send_book_to_kindle(
    book_slug_or_path: str,
    target_drive: Optional[str] = None,
    format_choice: str = "both",
    include_epub: bool = False,
    asin: str = "",
) -> bool:
    """
    Transfere o livro para o Kindle via USB (suporta AZW3 nativo e/ou PDF).
    Injeta as capas na memória interna do Kindle (simulando o Calibre).
    """
    print(f"\n{'='*70}")
    print("📲 BOOKFORGE: TRANSFERÊNCIA DIRETA USB PARA O AMAZON KINDLE")
    print(f"{'='*70}\n")

    # 1. Localizar arquivos na biblioteca
    pdf_path = None
    azw3_path = None
    epub_path = None

    potential_path = Path(book_slug_or_path)
    if potential_path.is_file():
        if potential_path.suffix.lower() == ".pdf":
            pdf_path = potential_path
        elif potential_path.suffix.lower() == ".azw3":
            azw3_path = potential_path
        elif potential_path.suffix.lower() == ".epub":
            epub_path = potential_path
    else:
        # Busca por slug em library/<slug>/dist/
        dist_dir = BASE_DIR / "library" / book_slug_or_path / "dist"
        if dist_dir.exists():
            azw3_candidates = list(dist_dir.glob("*-kindle.azw3")) or list(dist_dir.glob("*.azw3"))
            if azw3_candidates:
                azw3_path = azw3_candidates[0]

            epub_candidates = list(dist_dir.glob("*-kindle.epub")) or list(dist_dir.glob("*.epub"))
            if epub_candidates:
                epub_path = epub_candidates[0]

            pdf_candidates = list(dist_dir.glob("*-kindle.pdf")) or list(dist_dir.glob("*.pdf"))
            if pdf_candidates:
                pdf_path = pdf_candidates[0]

    # Se AZW3 foi solicitado (ou padrão both) e não existe, mas temos EPUB, converter automaticamente!
    if format_choice in ["azw3", "both", "all"] and (not azw3_path or not azw3_path.exists()):
        if epub_path and epub_path.exists() and convert_epub_to_azw3 is not None:
            print("[AUTO-CONVERT] AZW3 não encontrado na pasta dist/. Convertendo EPUB para AZW3 agora...")
            target_azw3 = epub_path.with_suffix(".azw3")
            ok, out_path, _ = convert_epub_to_azw3(epub_path, target_azw3)
            if ok and out_path:
                azw3_path = out_path

    # Determinar quais arquivos serão transferidos
    files_to_send: list[Path] = []
    if format_choice in ["azw3", "both", "all"] and azw3_path and azw3_path.exists():
        files_to_send.append(azw3_path)
    if format_choice in ["pdf", "both", "all"] and pdf_path and pdf_path.exists():
        files_to_send.append(pdf_path)
    if include_epub and epub_path and epub_path.exists():
        files_to_send.append(epub_path)

    # Se nenhum foi selecionado mas temos algum arquivo disponível
    if not files_to_send:
        for cand in [azw3_path, pdf_path, epub_path]:
            if cand and cand.exists():
                files_to_send.append(cand)
                break

    if not files_to_send:
        print(f"Erro: Nenhum arquivo (AZW3, PDF ou EPUB) encontrado para '{book_slug_or_path}'.", file=sys.stderr)
        return False

    # 2. Localizar Kindle
    kindle_drive = None
    if target_drive:
        d_path = Path(target_drive)
        if not d_path.is_absolute() and os.name == "nt":
            d_path = Path(f"{target_drive.rstrip(':')}:\\")
        if (d_path / "documents").is_dir():
            kindle_drive = d_path
        else:
            print(f"Aviso: Pasta 'documents' não encontrada na unidade informada ({d_path}).", file=sys.stderr)
            kindle_drive = d_path
    else:
        drives = detect_kindle_drive()
        if not drives:
            print("⚠️  Nenhum Kindle detectado via USB!")
            print("   Por favor, conecte o Kindle com o cabo USB ao computador.")
            print("   Se ele estiver conectado com outra letra de unidade, especifique com: --drive X:")
            print("\nExemplo:")
            print(f"  .venv\\Scripts\\python.exe cli.py send-kindle {book_slug_or_path} --drive E:")
            return False
        kindle_drive = drives[0]
        print(f"✓ Dispositivo Kindle detectado em: {kindle_drive}\n")

    docs_dir = kindle_drive / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Identificar ASIN se não fornecido
    if not asin and "manutencao" in str(book_slug_or_path).lower():
        asin = "B0HJZ35STY"

    # 3. Extrair capa base para miniaturas
    cover_img = None
    for src in [pdf_path, epub_path, azw3_path]:
        if src and src.exists():
            cover_img = extract_cover_image(src)
            if cover_img:
                print(f"✓ Capa extraída com sucesso a partir de: {src.name}")
                break

    # 4. Copiar arquivos para a pasta documents/
    copied_files: list[Path] = []
    print("\nTransferindo livros para o Kindle (documents/):")
    for f in files_to_send:
        dest = docs_dir / f.name
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  • {f.name:45} ({size_mb:6.2f} MB) -> documents/")
        shutil.copy2(f, dest)
        copied_files.append(dest)
    print("  ✓ Arquivos transferidos com sucesso!")

    # 5. Injetar Miniaturas de Capa (Simulação Calibre)
    if cover_img:
        print("\nInjeção de Capa (Simulação Calibre):")
        thumb_dirs = [
            kindle_drive / "system" / "thumbnails",
            kindle_drive / ".system" / "thumbnails",
            kindle_drive / "system" / "bookcovers",
        ]

        for target_file in copied_files:
            print(f"  Injetando miniaturas para: {target_file.name}...")
            for td in thumb_dirs:
                try:
                    generate_and_inject_thumbnails(target_file, cover_img, td, asin=asin)
                except Exception as e:
                    print(f"    Aviso ao injetar em {td}: {e}")
        print("  ✓ Miniaturas de capa injetadas com sucesso!")
    else:
        print("\nAviso: Imagem de capa não encontrada para injeção de miniaturas.")

    print(f"\n{'='*70}")
    print("🎉 TRANSFERÊNCIA CONCLUÍDA COM SUCESSO!")
    print(f"{'='*70}")
    print("Instruções finais:")
    print("1. No computador, clique em 'Ejetar / Remover com segurança' na unidade do Kindle.")
    print("2. Desconecte o cabo USB.")
    print("3. O livro e a capa já estarão disponíveis na sua biblioteca e na tela de descanso!")
    print(f"{'='*70}\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transfere livro para o Kindle e injeta miniaturas de capa (Calibre Sim).")
    parser.add_argument("book", help="Slug do livro (ex: fundamentos-de-manutencao-de-software) ou caminho direto.")
    parser.add_argument("--drive", help="Letra da unidade do Kindle (ex: E: ou E:\\)", default=None)
    parser.add_argument("--format", choices=["azw3", "pdf", "both", "all"], default="both", help="Formato(s) a transferir (padrão: both)")
    parser.add_argument("--include-epub", action="store_true", help="Copia também o arquivo EPUB se existir.")
    parser.add_argument("--asin", help="ASIN da Amazon para associação de capa (opcional)", default="")

    args = parser.parse_args()
    send_book_to_kindle(args.book, target_drive=args.drive, format_choice=args.format, include_epub=args.include_epub, asin=args.asin)
