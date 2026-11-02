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
import struct
import json
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


def extract_azw3_identifiers(file_path: Path) -> set[str]:
    """Extrai UUIDs e ASINs armazenados no cabeçalho EXTH do arquivo AZW3/MOBI."""
    ids = set()
    if not file_path or file_path.suffix.lower() != ".azw3" or not file_path.exists():
        return ids
    try:
        data = file_path.read_bytes()
        pos = data.find(b"EXTH")
        if pos != -1:
            length, count = struct.unpack(">II", data[pos + 4 : pos + 12])
            ptr = pos + 12
            for _ in range(count):
                rtype, rlen = struct.unpack(">II", data[ptr : ptr + 8])
                rdata = data[ptr + 8 : ptr + rlen]
                if rtype in (112, 113, 501, 504):
                    try:
                        text = rdata.decode("utf-8", errors="ignore").strip()
                        if text:
                            ids.add(text)
                            if text.startswith("calibre:"):
                                ids.add(text.split(":", 1)[1])
                    except Exception:
                        pass
                ptr += rlen
    except Exception as e:
        print(f"  Aviso: erro ao ler cabeçalho EXTH de {file_path.name} ({e})")
    return ids


def find_sdr_hashes(kindle_drive: Path, stem: str) -> set[str]:
    """Extrai hashes CDE gerados pelo Kindle dentro de pastas .sdr associadas."""
    hashes = set()
    docs_dir = kindle_drive / "documents"
    if not docs_dir.exists():
        return hashes
    try:
        for sdr_dir in docs_dir.rglob(f"{stem}.sdr"):
            if sdr_dir.is_dir():
                for item in sdr_dir.glob(f"{stem}*"):
                    ext = item.suffix
                    remainder = item.name[len(stem) : -len(ext) if ext else None]
                    if remainder:
                        hashes.add(remainder)
    except Exception:
        pass
    return hashes


def extract_azw3_internal_cover(file_path: Path) -> Optional[Image.Image]:
    """Extrai a capa interna embutida no AZW3 via ponteiro EXTH 201 (CoverOffset)."""
    if not file_path or not file_path.exists() or file_path.suffix.lower() != ".azw3":
        return None
    try:
        data = file_path.read_bytes()
        num_records = struct.unpack(">H", data[76:78])[0]
        record_offsets = []
        for i in range(num_records):
            offset = struct.unpack(">I", data[78 + i * 8 : 82 + i * 8])[0]
            record_offsets.append(offset)
        record_offsets.append(len(data))

        rec0 = data[record_offsets[0] : record_offsets[1]]
        exth_pos = rec0.find(b"EXTH")
        if exth_pos == -1:
            return None
        exth_len, exth_count = struct.unpack(">II", rec0[exth_pos + 4 : exth_pos + 12])
        ptr = exth_pos + 12
        cover_offset = None
        for _ in range(exth_count):
            rtype, rlen = struct.unpack(">II", rec0[ptr : ptr + 8])
            rdata = rec0[ptr + 8 : ptr + rlen]
            if rtype == 201:
                cover_offset = struct.unpack(">I", rdata)[0]
                break
            ptr += rlen

        if cover_offset is None:
            return None

        img_records = []
        for i in range(1, num_records):
            rec = data[record_offsets[i] : record_offsets[i + 1]]
            if rec.startswith(b"\xff\xd8\xff") or rec.startswith(b"\x89PNG") or rec.startswith(b"GIF"):
                img_records.append(rec)

        if cover_offset < len(img_records):
            raw_img = img_records[cover_offset]
            img = Image.open(io.BytesIO(raw_img)).convert("RGB")
            return img
    except Exception:
        pass
    return None


def extract_cover_image(source_file: Path) -> Optional[Image.Image]:
    """Extrai a capa em alta definição a partir do original, PDF renderizado ou EPUB."""
    if not source_file or not source_file.exists():
        return None

    ext = source_file.suffix.lower()

    # 1. Se for AZW3, buscar primeiro a capa interna real embutida no livro
    if ext == ".azw3":
        internal_cov = extract_azw3_internal_cover(source_file)
        if internal_cov:
            return internal_cov

        parent = source_file.parent
        book_dir = parent.parent if parent.name == "dist" else parent

        # (a) PDF original na pasta original/
        orig_dir = book_dir / "original"
        if orig_dir.is_dir():
            for orig_pdf in orig_dir.glob("*.pdf"):
                cov = extract_cover_image(orig_pdf)
                if cov:
                    return cov

        # (b) PDFs irmãos (screen, print, etc.)
        for sibling_name in [
            f"{source_file.stem}.pdf",
            f"{source_file.stem.replace('Kindle', 'Screen')}.pdf",
            f"{source_file.stem.replace('Kindle', 'Print-A4')}.pdf",
            f"{source_file.stem.replace('-kindle', '-screen')}.pdf",
            f"{source_file.stem.replace('-kindle', '-print-a4')}.pdf",
        ]:
            cand = parent / sibling_name
            if cand.exists():
                cov = extract_cover_image(cand)
                if cov:
                    return cov

        for cand in parent.glob("*.pdf"):
            cov = extract_cover_image(cand)
            if cov:
                return cov

        # (c) Figuras extraídas em assets/figures/
        fig_dir = book_dir / "assets" / "figures"
        if fig_dir.is_dir():
            for pattern in ["*cover*", "*capa*", "*p0001*", "*page_0001*"]:
                for f in fig_dir.glob(pattern):
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                        try:
                            img = Image.open(f).convert("RGB")
                            if img.width >= 250 and img.height >= 250:
                                return img
                        except Exception:
                            pass

        # (d) EPUB irmão
        for sibling_name in [f"{source_file.stem}.epub", f"{source_file.stem.replace('-kindle', '')}.epub"]:
            cand = parent / sibling_name
            if cand.exists():
                cov = extract_cover_image(cand)
                if cov:
                    return cov

    # 3. Se for EPUB, busca capa nos arquivos internos
    elif ext == ".epub":
        try:
            with zipfile.ZipFile(source_file, "r") as z:
                cover_entries = []
                other_images = []
                for name in z.namelist():
                    n_low = name.lower()
                    if n_low.endswith((".jpg", ".jpeg", ".png")):
                        if any(k in n_low for k in ["cover", "capa", "p0001", "page_0001", "front", "title"]):
                            cover_entries.append(name)
                        else:
                            other_images.append(name)

                for entry in cover_entries:
                    try:
                        data = z.read(entry)
                        img = Image.open(io.BytesIO(data)).convert("RGB")
                        if img.width >= 250 and img.height >= 250:
                            return img
                    except Exception:
                        continue

                for entry in other_images[:5]:
                    try:
                        data = z.read(entry)
                        img = Image.open(io.BytesIO(data)).convert("RGB")
                        if img.width >= 300 and img.height >= 300:
                            return img
                    except Exception:
                        continue
        except Exception as e:
            print(f"  Aviso: falha ao extrair capa do EPUB ({e})")

    return None


def generate_and_inject_thumbnails(
    target_file: Path,
    cover_img: Image.Image,
    thumb_dirs: list[Path],
    asin: str = "",
    kindle_drive: Optional[Path] = None,
):
    """Injeta as miniaturas no Kindle para o arquivo alvo cobrindo todas as variantes de ID e hash."""
    img_thumb = cover_img.copy()
    img_thumb.thumbnail((330, 470), Image.Resampling.LANCZOS)

    img_full = cover_img.copy()
    img_full.thumbnail((1072, 1448), Image.Resampling.LANCZOS)

    # Coletar identificadores
    ids = set()
    if asin:
        ids.add(asin)

    for azw_id in extract_azw3_identifiers(target_file):
        ids.add(azw_id)

    if kindle_drive:
        for sdr_hash in find_sdr_hashes(kindle_drive, target_file.stem):
            ids.add(sdr_hash)

    # Hashes SHA1 e MD5 do arquivo
    data_1mb = b""
    data_full = b""
    try:
        with open(target_file, "rb") as f:
            data_1mb = f.read(1024 * 1024)
            f.seek(0)
            data_full = f.read()
    except Exception:
        pass

    if data_1mb:
        sha1_1mb = hashlib.sha1(data_1mb).hexdigest()
        ids.add(sha1_1mb[:32])
        ids.add(sha1_1mb)
        md5_1mb = hashlib.md5(data_1mb).hexdigest()
        ids.add(md5_1mb)

    if data_full:
        sha1_full = hashlib.sha1(data_full).hexdigest()
        ids.add(sha1_full[:32])
        ids.add(sha1_full)
        md5_full = hashlib.md5(data_full).hexdigest()
        ids.add(md5_full)

    # Construir nomes de miniaturas
    thumb_names = set()
    thumb_names.add(f"thumbnail_{target_file.name}_portrait.jpg")
    thumb_names.add(f"thumbnail_{target_file.name}.jpg")
    thumb_names.add(f"thumbnail_{target_file.stem}_portrait.jpg")
    thumb_names.add(f"thumbnail_{target_file.stem}.jpg")

    for ident in ids:
        clean_id = ident.replace(":", "_").replace("/", "_").replace("\\", "_")
        thumb_names.add(f"thumbnail_{clean_id}_EBOK_portrait.jpg")
        thumb_names.add(f"thumbnail_{clean_id}_PDOC_portrait.jpg")
        thumb_names.add(f"thumbnail_{clean_id}_portrait.jpg")
        thumb_names.add(f"thumbnail_{clean_id}.jpg")
        if "-" in clean_id:
            no_dash = clean_id.replace("-", "")
            thumb_names.add(f"thumbnail_{no_dash}_EBOK_portrait.jpg")
            thumb_names.add(f"thumbnail_{no_dash}_PDOC_portrait.jpg")

    # Injetar em cada diretório de miniaturas
    injected_count = 0
    for t_dir in thumb_dirs:
        try:
            t_dir.mkdir(parents=True, exist_ok=True)
            for t_name in thumb_names:
                dest = t_dir / t_name
                if dest.exists():
                    try:
                        dest.chmod(0o666)
                    except Exception:
                        pass
                img_thumb.save(str(dest), "JPEG", quality=90)
                try:
                    dest.chmod(0o444)
                except Exception:
                    pass
                injected_count += 1

            if any(k in t_dir.name.lower() for k in ["bookcovers", "cover-bug"]):
                hd_names = [f"{target_file.stem}.jpg"]
                for ident in ids:
                    clean_id = ident.replace(":", "_").replace("/", "_").replace("\\", "_")
                    hd_names.append(f"{clean_id}.jpg")
                for hd in hd_names:
                    full_dest = t_dir / hd
                    if full_dest.exists():
                        try:
                            full_dest.chmod(0o666)
                        except Exception:
                            pass
                    img_full.save(str(full_dest), "JPEG", quality=92)
                    try:
                        full_dest.chmod(0o444)
                    except Exception:
                        pass
        except Exception as e:
            print(f"    Aviso ao injetar em {t_dir}: {e}")

    print(f"  ✓ {injected_count} miniaturas e variantes de capa geradas e protegidas.")


def update_kindle_metadata_calibre(kindle_drive: Path, target_file: Path, title: str = "", author: str = ""):
    """Atualiza o arquivo metadata.calibre na raiz do Kindle se estiver presente."""
    meta_path = kindle_drive / "metadata.calibre"
    if not meta_path.exists():
        return
    try:
        content = meta_path.read_text(encoding="utf-8", errors="ignore")
        data = json.loads(content)
        rel_lpath = str(target_file.relative_to(kindle_drive)).replace("\\", "/")

        azw_ids = extract_azw3_identifiers(target_file)
        uuid_str = ""
        for ident in azw_ids:
            if not ident.startswith("calibre:") and len(ident) > 20:
                uuid_str = ident
                break

        record = None
        for item in data:
            if item.get("lpath") == rel_lpath or item.get("lpath") == f"documents/{target_file.name}":
                record = item
                break

        if record is None:
            record = {
                "user_metadata": {},
                "series_index": None,
                "title_sort": None,
                "publisher": None,
                "series": None,
                "pages": None,
                "comments": None,
                "pubdate": "2026-11-02T19:14:29+00:00",
                "languages": ["por"],
                "thumbnail": None,
                "rating": None,
                "last_modified": "None",
                "book_producer": "BookForge",
                "tags": [],
                "cover": None,
                "link_maps": {},
                "db_id": None,
                "publication_type": None,
                "timestamp": "None",
                "rights": None,
                "user_categories": {},
                "author_sort_map": {},
            }
            data.append(record)

        record["title"] = title or target_file.stem
        record["authors"] = [author] if author else ["Autor Desconhecido"]
        record["author_sort"] = author or "Desconhecido"
        record["lpath"] = rel_lpath
        record["size"] = target_file.stat().st_size
        if uuid_str:
            record["uuid"] = uuid_str
            record["application_id"] = uuid_str
            record["identifiers"] = {"mobi-asin": uuid_str}
        record["mime"] = "application/x-mobi8-ebook" if target_file.suffix.lower() == ".azw3" else "application/pdf"

        meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("  ✓ Registro atualizado em metadata.calibre no Kindle!")
    except Exception as e:
        print(f"  Aviso: não foi possível atualizar metadata.calibre ({e})")


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
    book_title = ""
    book_author = ""

    potential_path = Path(book_slug_or_path)
    if potential_path.is_file():
        if potential_path.suffix.lower() == ".pdf":
            pdf_path = potential_path
        elif potential_path.suffix.lower() == ".azw3":
            azw3_path = potential_path
        elif potential_path.suffix.lower() == ".epub":
            epub_path = potential_path
        # Tenta carregar book.yaml do livro se estiver em library/<slug>/...
        parent_dir = potential_path.parent
        book_dir = parent_dir.parent if parent_dir.name == "dist" else parent_dir
        cfg_file = book_dir / "book.yaml"
        if cfg_file.exists():
            try:
                import yaml

                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    book_title = cfg.get("title", "")
                    book_author = cfg.get("author", "")
            except Exception:
                pass
    else:
        # Busca por slug em library/<slug>/dist/
        book_dir = BASE_DIR / "library" / book_slug_or_path
        dist_dir = book_dir / "dist"
        cfg_file = book_dir / "book.yaml"
        if cfg_file.exists():
            try:
                import yaml

                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    book_title = cfg.get("title", "")
                    book_author = cfg.get("author", "")
            except Exception:
                pass

        if dist_dir.exists():
            azw3_candidates = (
                list(dist_dir.glob("*Kindle*.azw3"))
                or list(dist_dir.glob("*-kindle.azw3"))
                or list(dist_dir.glob("*.azw3"))
            )
            if azw3_candidates:
                azw3_path = azw3_candidates[0]

            epub_candidates = (
                list(dist_dir.glob("*Kindle*.epub"))
                or list(dist_dir.glob("*-kindle.epub"))
                or list(dist_dir.glob("*.epub"))
            )
            if epub_candidates:
                epub_path = epub_candidates[0]

            pdf_candidates = (
                list(dist_dir.glob("*Kindle*.pdf"))
                or list(dist_dir.glob("*-kindle.pdf"))
                or list(dist_dir.glob("*.pdf"))
            )
            if pdf_candidates:
                pdf_path = pdf_candidates[0]

    # Se AZW3 foi solicitado e não existe, converter EPUB se disponível
    if format_choice in ["azw3", "both", "all"] and (not azw3_path or not azw3_path.exists()):
        if epub_path and epub_path.exists() and convert_epub_to_azw3 is not None:
            print("[AUTO-CONVERT] AZW3 não encontrado na pasta dist/. Convertendo EPUB para AZW3 agora...")
            target_azw3 = epub_path.with_suffix(".azw3")
            ok, out_path, _ = convert_epub_to_azw3(
                epub_path,
                target_azw3,
                title=book_title,
                author=book_author,
            )
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

    # Função para determinar pasta destino ideal dentro de documents/
    def get_dest_folder(book_file: Path) -> Path:
        stem = book_file.stem
        for sdr in docs_dir.rglob(f"{stem}.sdr"):
            if sdr.is_dir() and sdr.parent != docs_dir:
                return sdr.parent
        for existing in docs_dir.rglob(book_file.name):
            if existing.is_file() and existing.parent != docs_dir:
                return existing.parent
        import unicodedata
        stem_norm = unicodedata.normalize("NFKD", stem).encode("ASCII", "ignore").decode("utf-8").lower()
        if any(k in stem_norm for k in ["computacao", "algoritmo", "software", "programacao", "ai-native", "manutencao"]):
            comp_dir = docs_dir / "Computação"
            comp_dir.mkdir(parents=True, exist_ok=True)
            return comp_dir
        if any(k in stem_norm for k in ["matematica", "calculo", "algebra"]):
            mat_dir = docs_dir / "Matemática"
            mat_dir.mkdir(parents=True, exist_ok=True)
            return mat_dir
        if any(k in stem_norm for k in ["gramatica", "redacao", "lingua", "writing"]):
            ling_dir = docs_dir / "Línguas e Redação"
            ling_dir.mkdir(parents=True, exist_ok=True)
            return ling_dir
        if any(k in stem_norm for k in ["aprendizado", "produtividade", "limites"]):
            apr_dir = docs_dir / "Aprendizado e Produtividade"
            apr_dir.mkdir(parents=True, exist_ok=True)
            return apr_dir
        return docs_dir

    # Identificar ASIN se não fornecido
    if not asin and "manutencao" in str(book_slug_or_path).lower():
        asin = "B0HJZ35STY"

    # 3. Extrair capa base para miniaturas
    cover_img = None
    for src in [azw3_path, pdf_path, epub_path]:
        if src and src.exists():
            cover_img = extract_cover_image(src)
            if cover_img:
                print(f"✓ Capa extraída com sucesso em alta definição a partir de: {src.name} ({cover_img.size[0]}x{cover_img.size[1]})")
                break

    # 4. Copiar arquivos para o Kindle
    copied_files: list[Path] = []
    print("\nTransferindo livros para o Kindle:")
    for f in files_to_send:
        target_folder = get_dest_folder(f)
        target_folder.mkdir(parents=True, exist_ok=True)
        dest = target_folder / f.name
        size_mb = f.stat().st_size / (1024 * 1024)
        rel_folder = target_folder.relative_to(kindle_drive)
        print(f"  • {f.name:45} ({size_mb:6.2f} MB) -> {rel_folder}/")
        shutil.copy2(f, dest)
        copied_files.append(dest)
        update_kindle_metadata_calibre(kindle_drive, dest, title=book_title, author=book_author)
    print("  ✓ Arquivos transferidos com sucesso!")

    # 5. Injetar Miniaturas de Capa (Simulação Calibre e Proteção contra Cover Bug)
    if cover_img:
        print("\nInjeção e Proteção de Capas no Kindle:")
        thumb_dirs = [
            kindle_drive / "system" / "thumbnails",
            kindle_drive / ".system" / "thumbnails",
            kindle_drive / "system" / "bookcovers",
            kindle_drive / "system" / "grok_thumbnails",
            kindle_drive / "amazon-cover-bug",
        ]

        for target_file in copied_files:
            print(f"  Injetando miniaturas para: {target_file.name}...")
            generate_and_inject_thumbnails(target_file, cover_img, thumb_dirs, asin=asin, kindle_drive=kindle_drive)
        print("  ✓ Miniaturas de capa injetadas e protegidas com sucesso!")
    else:
        print("\nAviso: Imagem de capa não encontrada para injeção de miniaturas.")

    print(f"\n{'='*70}")
    print("🎉 TRANSFERÊNCIA CONCLUÍDA COM SUCESSO!")
    print(f"{'='*70}")
    print("Instruções finais:")
    print("1. No computador, clique em 'Ejetar / Remover com segurança' na unidade do Kindle.")
    print("2. Desconecte o cabo USB.")
    print("3. O livro e a capa estarão disponíveis na sua biblioteca e na tela de descanso!")
    print(f"{'='*70}\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transfere livro para o Kindle e injeta miniaturas de capa (Calibre Sim).")
    parser.add_argument("book", help="Slug do livro ou caminho direto do arquivo.")
    parser.add_argument("--drive", help="Letra da unidade do Kindle (ex: E: ou E:\\)", default=None)
    parser.add_argument("--format", choices=["azw3", "pdf", "both", "all"], default="both", help="Formato(s) a transferir (padrão: both)")
    parser.add_argument("--include-epub", action="store_true", help="Copia também o arquivo EPUB se existir.")
    parser.add_argument("--asin", help="ASIN da Amazon para associação de capa (opcional)", default="")

    args = parser.parse_args()
    send_book_to_kindle(args.book, target_drive=args.drive, format_choice=args.format, include_epub=args.include_epub, asin=args.asin)
