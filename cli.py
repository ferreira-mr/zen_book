#!/usr/bin/env python3
"""
=============================================================================
BookForge CLI — Plataforma Integrada de Editoração, Tradução e Restauração de Livros
=============================================================================
"""

import sys
import os
import argparse
import yaml
import json
import shutil
from pathlib import Path

# Adiciona o diretório raiz ao path para imports de core
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Configurar encoding seguro para Windows Console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.engines.compiler_latex import compile_latex, assemble_master_tex
from core.engines.compiler_typst import compile_typst
from core.engines.kindle_pdf_scaler import scale_pdf_to_kindle
from core.engines.build_kindle_epub import build_epub_for_book
from core.engines.typst_kindle_builder import build_typst_kindle_pdf, build_typst_kindle_epub
from core.image_pipeline.deskew import deskew_image
from core.image_pipeline.binarize_clean import clean_scanned_page
from core.image_pipeline.extract_figures import extract_pdf_embedded_images
from core.image_pipeline.ocr_draft import render_page_image
from core.state_manager import load_manifest, save_manifest, update_progress_md, get_manifest_stats

LIBRARY_DIR = BASE_DIR / "library"

def get_book_dir(slug: str) -> Path:
    book_dir = LIBRARY_DIR / slug
    if not book_dir.exists():
        print(f"Erro: Livro '{slug}' não encontrado em {LIBRARY_DIR}", file=sys.stderr)
        sys.exit(1)
    return book_dir

def load_book_config(book_dir: Path) -> dict:
    cfg_file = book_dir / "book.yaml"
    if cfg_file.exists():
        with open(cfg_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

# -----------------------------------------------------------------------------
# COMANDOS DA CLI
# -----------------------------------------------------------------------------

def cmd_list(args):
    """Lista todos os livros na biblioteca com status e entregáveis."""
    print(f"\n{'='*75}")
    print(f"📚 BIBLIOTECA BOOKFORGE ({LIBRARY_DIR})")
    print(f"{'='*75}\n")
    
    if not LIBRARY_DIR.exists():
        print("Biblioteca vazia. Use 'python cli.py init <slug>' para adicionar livros.")
        return

    books = [d for d in sorted(LIBRARY_DIR.iterdir()) if d.is_dir()]
    if not books:
        print("Nenhum livro cadastrado em library/.")
        return

    for b in books:
        cfg = load_book_config(b)
        title = cfg.get("title", b.name)
        author = cfg.get("author", "Autor Desconhecido")
        engine = cfg.get("engine", "typst")
        mode = cfg.get("mode", "standard")
        
        manifest = load_manifest(b)
        total, done = get_manifest_stats(manifest)
        pct = (done / total * 100) if total > 0 else 0.0

        dist_files = []
        dist_dir = b / "dist"
        if dist_dir.exists():
            dist_files = [f.name for f in dist_dir.iterdir() if f.is_file() and f.suffix in [".pdf", ".epub"]]

        print(f"📖 [{b.name}]")
        print(f"   Título:   {title} ({author})")
        print(f"   Motor:    {engine.upper()} | Modo: {mode}")
        if total > 0:
            print(f"   Progresso: {done}/{total} ({pct:.1f}%)")
        print(f"   Entregáveis ({len(dist_files)}): {', '.join(dist_files) if dist_files else 'Nenhum'}")
        print()

def cmd_init(args):
    """Inicializa a estrutura padronizada para um novo livro."""
    slug = args.slug
    book_dir = LIBRARY_DIR / slug
    if book_dir.exists():
        print(f"Livro '{slug}' já existe em {book_dir}", file=sys.stderr)
        return

    print(f"Inicializando novo livro: {slug}...")
    for sub in ["original", "assets/figures", "intermediate/page_images", "source", "state", "dist"]:
        (book_dir / sub).mkdir(parents=True, exist_ok=True)

    # Copiar arquivo original se fornecido
    orig_name = ""
    if args.file:
        src_file = Path(args.file).resolve()
        if src_file.exists():
            dest = book_dir / "original" / src_file.name
            shutil.copy2(src_file, dest)
            orig_name = src_file.name
            print(f"Copiado arquivo original: {orig_name}")

    # Gerar book.yaml
    cfg = {
        "slug": slug,
        "title": args.title or slug.replace("-", " ").title(),
        "author": args.author or "",
        "engine": args.engine or "typst",
        "mode": args.mode or "standard",
        "original_file": orig_name
    }
    with open(book_dir / "book.yaml", "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)

    # Iniciar manifest
    save_manifest(book_dir, {"total_pages": 0, "completed_pages": 0, "pages": [], "chapters": []})
    update_progress_md(book_dir, cfg["title"], cfg["author"], cfg["engine"])
    print(f"Estrutura criada com sucesso em: {book_dir}")

def cmd_status(args):
    """Exibe o dashboard de status e progresso de um livro."""
    book_dir = get_book_dir(args.slug)
    cfg = load_book_config(book_dir)
    manifest = load_manifest(book_dir)
    total, done = get_manifest_stats(manifest)
    pct = (done / total * 100) if total > 0 else 0.0

    print(f"\n{'='*70}")
    print(f"STATUS DO LIVRO: {cfg.get('title', args.slug)}")
    print(f"{'='*70}")
    print(f"Slug:        {args.slug}")
    print(f"Autor:       {cfg.get('author', 'Não especificado')}")
    print(f"Motor:       {cfg.get('engine', 'typst').upper()}")
    print(f"Modo:        {cfg.get('mode', 'standard')}")
    print(f"Progresso:   {done} de {total} ({pct:.1f}%)")
    
    # Barra de progresso visual
    bar_len = 40
    filled = int(bar_len * pct / 100) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"[{bar}] {pct:.1f}%\n")

    dist_dir = book_dir / "dist"
    print("Entregáveis em dist/:")
    if dist_dir.exists():
        found = False
        for f in sorted(dist_dir.iterdir()):
            if f.is_file() and f.suffix in [".pdf", ".epub"]:
                found = True
                print(f"  ✓ {f.name:45} ({f.stat().st_size / (1024*1024):6.2f} MB)")
        if not found:
            print("  (Nenhum entregável encontrado)")
    print()

def cmd_build(args):
    """Compila os formatos finais do livro."""
    book_dir = get_book_dir(args.slug)
    cfg = load_book_config(book_dir)
    engine = cfg.get("engine", "typst")
    target = args.target  # screen, print, kindle, all

    print(f"\n[BUILD] Compilando '{args.slug}' via motor {engine.upper()} (alvo: {target})...")
    dist_dir = book_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    source_dir = book_dir / "source"

    if engine == "typst":
        # Compilação Typst
        main_typ = source_dir / "main.typ"
        if not main_typ.exists():
            # Procura por qualquer .typ principal
            candidates = list(source_dir.glob("*.typ"))
            if candidates:
                main_typ = candidates[0]
            else:
                print(f"Erro: Arquivo principal Typst não encontrado em {source_dir}", file=sys.stderr)
                return

        screen_pdf = dist_dir / f"{args.slug}-screen.pdf"
        print_pdf = dist_dir / f"{args.slug}-print-a4.pdf"
        kindle_pdf = dist_dir / f"{args.slug}-kindle.pdf"

        if target in ["screen", "all"]:
            compile_typst(main_typ, screen_pdf, root_dir=BASE_DIR)

        if target in ["print", "all"]:
            # Se houver template de impressão ou compilação dedicada
            compile_typst(main_typ, print_pdf, root_dir=BASE_DIR)

        if target in ["kindle", "all"]:
            kindle_pdf = dist_dir / f"{args.slug}-kindle.pdf"
            kindle_epub = dist_dir / f"{args.slug}-kindle.epub"
            print(f"[KINDLE] Construindo edições ergonômicas para Kindle (PDF fluido 10.5pt e EPUB 3)...")
            # 1. PDF Kindle nativo fluido (105x140mm, tipografia 10.5pt, fluxo livre entre páginas)
            build_typst_kindle_pdf(book_dir, kindle_pdf)
            # 2. EPUB 3 refluxável com Bookerly CSS
            try:
                build_typst_kindle_epub(book_dir, kindle_epub)
            except Exception as e:
                print(f"[KINDLE-EPUB] Aviso ao gerar EPUB: {e}")

    elif engine == "latex":
        # Compilação LaTeX
        screen_tex = source_dir / "book-screen.tex"
        print_tex = source_dir / "book-print-a4.tex"
        kindle_tex = source_dir / "book-kindle.tex"

        if target in ["screen", "all"]:
            if screen_tex.exists():
                out_screen = dist_dir / f"{args.slug}-screen.pdf"
                compile_latex(screen_tex, out_screen, work_dir=source_dir)

        if target in ["print", "all"]:
            if print_tex.exists():
                out_print = dist_dir / f"{args.slug}-print-a4.pdf"
                compile_latex(print_tex, out_print, work_dir=source_dir)

        if target in ["kindle", "all"]:
            if kindle_tex.exists():
                out_kpdf = dist_dir / f"{args.slug}-kindle.pdf"
                compile_latex(kindle_tex, out_kpdf, work_dir=source_dir)

            # Construir Kindle EPUB se houver capítulos LaTeX
            try:
                build_epub_for_book(book_dir, dist_dir / f"{args.slug}-kindle.epub")
            except Exception as e:
                print(f"[EPUB] Aviso ao gerar EPUB: {e}")

    update_progress_md(book_dir, cfg.get("title", args.slug), cfg.get("author", ""), engine)
    print(f"\n[BUILD] Processo de compilação finalizado para {args.slug}.\n")

def cmd_enhance(args):
    """Executa restauração e desinclinação nas imagens de páginas escaneadas."""
    book_dir = get_book_dir(args.slug)
    images_dir = book_dir / "intermediate" / "page_images"
    if not images_dir.exists():
        print(f"Diretório de imagens não encontrado: {images_dir}", file=sys.stderr)
        return

    images = sorted(images_dir.glob("*.png")) + sorted(images_dir.glob("*.jpg"))
    if not images:
        print("Nenhuma imagem encontrada em intermediate/page_images/")
        return

    print(f"Processando restauração de {len(images)} páginas para '{args.slug}'...")
    for idx, img_p in enumerate(images):
        if (idx + 1) % 25 == 0 or idx == len(images) - 1:
            print(f"Restauração: {idx+1}/{len(images)} páginas...")
        if args.deskew:
            deskew_image(img_p, img_p)
        if args.clean:
            clean_scanned_page(img_p, img_p, mode="enhanced_grayscale")

    print("[ENHANCE] Processamento de imagens concluído com sucesso.")

def cmd_extract_figures(args):
    """Extrai ilustrações em alta resolução do PDF original."""
    book_dir = get_book_dir(args.slug)
    orig_dir = book_dir / "original"
    pdfs = list(orig_dir.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em {orig_dir}", file=sys.stderr)
        return
    
    out_figures = book_dir / "assets" / "figures"
    extract_pdf_embedded_images(pdfs[0], out_figures)

def cmd_render_pages(args):
    """Renderiza um intervalo de páginas do PDF original para PNG sob demanda."""
    book_dir = get_book_dir(args.slug)
    orig_dir = book_dir / "original"
    pdfs = list(orig_dir.glob("*.pdf"))
    if not pdfs:
        print(f"Nenhum PDF encontrado em {orig_dir}", file=sys.stderr)
        return

    out_dir = book_dir / "intermediate" / "page_images"
    dpi = args.dpi or 160
    start = args.start
    end = args.end
    
    print(f"Renderizando páginas {start} a {end} do PDF a {dpi} DPI...")
    for p in range(start, end + 1):
        target_png = out_dir / f"page_{p:04d}.png"
        render_page_image(pdfs[0], p, target_png, dpi=dpi)
    print("[RENDER] Renderização concluída.")

# -----------------------------------------------------------------------------
# MAIN CLI PARSER
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BookForge CLI — Gestão Editorial de Livros")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="Lista livros da biblioteca")
    p_list.set_defaults(func=cmd_list)

    # init
    p_init = subparsers.add_parser("init", help="Inicializa novo livro")
    p_init.add_argument("slug", help="Identificador único (ex: historia-da-computacao)")
    p_init.add_argument("--file", help="Caminho do arquivo original (PDF ou EPUB)")
    p_init.add_argument("--title", help="Título completo da obra")
    p_init.add_argument("--author", help="Nome do autor")
    p_init.add_argument("--engine", choices=["typst", "latex"], default="typst")
    p_init.add_argument("--mode", choices=["translate", "transcribe-image", "remaster"], default="standard")
    p_init.set_defaults(func=cmd_init)

    # status
    p_status = subparsers.add_parser("status", help="Dashboard de progresso do livro")
    p_status.add_argument("slug", help="Slug do livro")
    p_status.set_defaults(func=cmd_status)

    # build
    p_build = subparsers.add_parser("build", help="Compila entregáveis")
    p_build.add_argument("slug", help="Slug do livro")
    p_build.add_argument("--target", choices=["screen", "print", "kindle", "all"], default="all")
    p_build.set_defaults(func=cmd_build)

    # enhance
    p_enh = subparsers.add_parser("enhance", help="Restaura e alinha páginas em imagem")
    p_enh.add_argument("slug", help="Slug do livro")
    p_enh.add_argument("--deskew", action="store_true", help="Corrige rotação/inclinação")
    p_enh.add_argument("--clean", action="store_true", help="Remove fundo cinza e sombras de lombada")
    p_enh.set_defaults(func=cmd_enhance)

    # extract-figures
    p_ext = subparsers.add_parser("extract-figures", help="Extrai figuras do PDF original")
    p_ext.add_argument("slug", help="Slug do livro")
    p_ext.set_defaults(func=cmd_extract_figures)

    # render-pages
    p_rnd = subparsers.add_parser("render-pages", help="Renderiza páginas para PNG sob demanda")
    p_rnd.add_argument("slug", help="Slug do livro")
    p_rnd.add_argument("--start", type=int, required=True)
    p_rnd.add_argument("--end", type=int, required=True)
    p_rnd.add_argument("--dpi", type=int, default=160)
    p_rnd.set_defaults(func=cmd_render_pages)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
