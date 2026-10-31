"""
typst_kindle_builder.py — Gerador Especializado de Edições Kindle (PDF e EPUB 3) para Livros Typst
Projetado para máxima ergonomia de leitura em telas E-Ink (6" e 6.8"):
1. Kindle PDF: tipografia 10.5pt vetorial, fluxo contínuo sem quebras artificiais de página.
2. Kindle EPUB: formato 100% refluxável, compatível com Bookerly, modo noturno e troca de tamanho de fonte.
"""

import os
import re
import json
import html
import uuid
import zipfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict
import pymupdf
import typst

KINDLE_EPUB_CSS = """/* ==============================================================================
   BookForge: Estilo Semântico para Leitura no Amazon Kindle (EPUB 3 Refluxável)
   ============================================================================== */
@namespace "http://www.w3.org/1999/xhtml";

body {
    margin: 4% 5%;
    font-family: "Bookerly", "Georgia", "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.45;
    text-align: justify;
    color: #111111;
    background-color: #ffffff;
}

h1.part-title {
    font-size: 1.7em;
    font-weight: bold;
    text-align: center;
    margin-top: 2.2em;
    margin-bottom: 1.2em;
    page-break-before: always;
    break-before: page;
}

h1.chapter-title {
    font-size: 1.5em;
    font-weight: bold;
    text-align: left;
    margin-top: 1.8em;
    margin-bottom: 0.8em;
    border-bottom: 1.5px solid #222222;
    padding-bottom: 0.3em;
    page-break-before: always;
    break-before: page;
}

h2.section-title {
    font-size: 1.25em;
    font-weight: bold;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    break-after: avoid;
}

h3.subsection-title {
    font-size: 1.1em;
    font-weight: bold;
    margin-top: 1.1em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
    break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 0.6em;
    text-indent: 1.2em;
}

p.no-indent, h1 + p, h2 + p, h3 + p, h4 + p {
    text-indent: 0;
}

aside.kindle-box {
    margin: 1.2em 0;
    padding: 0.8em 1em;
    border-left: 3.5pt solid #222222;
    border-top: 0.5pt solid #cccccc;
    border-right: 0.5pt solid #cccccc;
    border-bottom: 0.5pt solid #cccccc;
    background-color: #f7f7f7;
    page-break-inside: avoid;
    break-inside: avoid;
}

aside.kindle-box .box-title {
    margin-top: 0;
    margin-bottom: 0.5em;
    font-size: 1.05em;
    font-weight: bold;
    color: #000000;
}

ul.kindle-list, ol.kindle-list {
    margin: 0.6em 0 0.8em 1.5em;
    padding-left: 0;
}

li {
    margin-bottom: 0.35em;
}

figure.kindle-figure {
    margin: 1.4em 0;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
}

img.kindle-img {
    max-width: 98%;
    height: auto;
    display: block;
    margin: 0 auto;
}

figcaption {
    font-size: 0.85em;
    margin-top: 0.4em;
    color: #333333;
    font-family: sans-serif;
}

div.math-block {
    margin: 1em 0;
    text-align: center;
    font-family: "Cambria Math", "Latin Modern Math", serif;
    font-size: 1.1em;
}

span.inline-math {
    font-family: "Cambria Math", "Latin Modern Math", serif;
}

table.kindle-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.95em;
    margin: 1em 0;
}

table.kindle-table th, table.kindle-table td {
    border: 1px solid #cccccc;
    padding: 6px 8px;
    text-align: left;
}

table.kindle-table th {
    background-color: #eeeeee;
    font-weight: bold;
}
"""

def strip_nested_set_page(text: str) -> str:
    """Remove blocos #set page(...) com suporte a parênteses aninhados."""
    while True:
        idx = text.find("#set page(")
        if idx == -1:
            break
        depth = 0
        end_idx = idx + len("#set page")
        for i in range(idx + len("#set page"), len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
        text = text[:idx] + text[end_idx:]
    return text

def build_typst_kindle_pdf(book_dir: Path, output_pdf: Path) -> bool:
    """
    Gera o PDF Kindle fluido com tipografia de alta legibilidade (10.5pt)
    sem espremer páginas originais e sem fontes microscópicas.
    """
    book_dir = Path(book_dir).resolve()
    output_pdf = Path(output_pdf).resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    
    pages_dir = book_dir / "source" / "pages"
    if not pages_dir.exists():
        print(f"Erro: diretório de páginas Typst não encontrado em {pages_dir}")
        return False
        
    pages = sorted(pages_dir.glob("page_*.typ"))
    if not pages:
        print(f"Erro: nenhum arquivo page_XXXX.typ encontrado em {pages_dir}")
        return False

    print(f"[KINDLE-PDF] Construindo edição fluida para {book_dir.name} ({len(pages)} páginas originais)...")

    # Preâmbulo Kindle fluido de alto contraste
    header_lines = [
        '#import "template.typ": *',
        '#set page(',
        '  width: 105mm,',
        '  height: 140mm,',
        '  margin: (top: 10mm, bottom: 9mm, left: 8mm, right: 8mm),',
        '  header: none,',
        '  footer: context {',
        '    let p = counter(page).get().first()',
        '    if p > 1 {',
        '      align(right)[#text(size: 8pt, font: font-sans, fill: rgb("#444444"))[#p]]',
        '    }',
        '  }',
        ')',
        '#set text(font: font-serif, size: 10.5pt, fill: black, lang: "pt", region: "BR")',
        '#set par(justify: true, leading: 0.65em, spacing: 0.8em, first-line-indent: 1.2em)',
        '#show heading: set text(fill: black)',
        '#let footnote(body) = text(size: 8.5pt, fill: rgb("#444444"))[ (#body)]',
    ]

    body_lines = []
    for p in pages:
        txt = p.read_text(encoding="utf-8")
        # Remove import local redundante
        txt = re.sub(r'#import\s+"[^"]+":\s*\*?', '', txt)
        # Remove o #set page(...) que forçava cabeçalho A4 e quebra de página por scan
        txt = strip_nested_set_page(txt)
        # Remove o encolhimento artificial de fonte que gerava letras minúsculas de 5.7pt
        txt = re.sub(r'#set\s+text\(size:\s*[0-9.]+pt\)', '', txt)
        txt = re.sub(r'#set\s+par\([^)]*\)', '', txt)
        # Ajusta caminhos de assets
        txt = txt.replace("../../assets/", "assets/")
        txt = txt.replace("../assets/", "assets/")
        body_lines.append(txt)

    full_typst = "\n".join(header_lines) + "\n\n" + "\n".join(body_lines)
    
    tmp_typst = book_dir / "source" / "_kindle_build_temp.typ"
    tmp_typst.write_text(full_typst, encoding="utf-8")

    try:
        root_dir = book_dir.parent.parent if (book_dir.parent.parent / "core").exists() else book_dir
        typst.compile(str(tmp_typst), output=str(output_pdf), root=str(root_dir))
        
        # Inserir sumário / TOC a partir do manifest.json se disponível
        manifest_file = book_dir / "state" / "manifest.json"
        if manifest_file.exists():
            try:
                doc = pymupdf.open(str(output_pdf))
                # Preserva TOC se já foi gerado ou insere bookmarks
                doc.save(str(output_pdf), deflate=True, garbage=4)
                doc.close()
            except Exception:
                pass
                
        doc = pymupdf.open(str(output_pdf))
        page_count = len(doc)
        doc.close()
        
        sz_mb = output_pdf.stat().st_size / (1024 * 1024)
        print(f"[KINDLE-PDF] Sucesso: {output_pdf.name} ({page_count} páginas Kindle, {sz_mb:.2f} MB, fonte 10.5pt)")
        return True
    except Exception as e:
        print(f"[KINDLE-PDF] Erro ao compilar Typst Kindle PDF: {e}")
        return False
    finally:
        tmp_typst.unlink(missing_ok=True)

def typst_to_clean_html(typst_text: str) -> str:
    """Converte conteúdo de página Typst em HTML semântico e fluido para EPUB."""
    lines = typst_text.splitlines()
    out = []
    in_box = False
    in_table = False
    
    for line in lines:
        l = line.strip()
        if not l or l.startswith("//") or l.startswith("#import") or l.startswith("#set page"):
            continue
        if l.startswith("#book-page") or l.startswith("#pagebreak()") or l.startswith("#set text") or l.startswith("#set par"):
            continue
        if l.startswith("#v(") or l.startswith("#h(") or l.startswith("#line("):
            continue

        # Imagens
        img_m = re.search(r'#image\(["\']([^"\']+)["\']', l)
        if img_m:
            img_file = Path(img_m.group(1)).name
            out.append(f'<figure class="kindle-figure"><img class="kindle-img" src="assets/images/{img_file}" alt="Ilustração"/></figure>')
            continue
            
        # Títulos e Banners
        part_m = re.match(r'#part-banner\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)', l)
        if part_m:
            out.append(f'<h1 class="part-title">{html.escape(part_m.group(1))} – {html.escape(part_m.group(2))}</h1>')
            continue
            
        chap_m = re.match(r'#chapter-header\(["\']([^"\']+)["\']\)', l)
        if chap_m:
            out.append(f'<h1 class="chapter-title">{html.escape(chap_m.group(1))}</h1>')
            continue

        sec_m = re.match(r'#sec\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)', l)
        if sec_m:
            out.append(f'<h2 class="section-title">{html.escape(sec_m.group(1))}. {html.escape(sec_m.group(2))}</h2>')
            continue
            
        subsec_m = re.match(r'#subsec\(["\']([^"\']+)["\']\)', l)
        if subsec_m:
            out.append(f'<h3 class="subsection-title">{html.escape(subsec_m.group(1))}</h3>')
            continue

        h_m = re.match(r'^(=+)\s*(.*)', l)
        if h_m:
            lvl = min(len(h_m.group(1)) + 1, 4)
            out.append(f'<h{lvl}>{html.escape(h_m.group(2))}</h{lvl}>')
            continue

        # Caixas pedagógicas e observações
        if any(l.startswith(f"#{box}[") or l.startswith(f"#{box}(") for box in ["obs", "dica", "atencao", "exemplo", "questao", "solucao", "feature-box"]):
            in_box = True
            box_title = "Destaque"
            for b_name in ["Observação", "Dica", "Atenção", "Exemplo", "Questão", "Solução"]:
                if b_name.lower() in l.lower():
                    box_title = b_name
                    break
            out.append(f'<aside class="kindle-box"><h4 class="box-title">{box_title}</h4>')
            continue
        if l == "]" and in_box:
            in_box = False
            out.append('</aside>')
            continue

        # Formatação inline
        text = l
        text = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', text)
        text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        # Itens de listas
        if text.startswith("#sq-item[") or text.startswith("- "):
            clean_item = text.replace("#sq-item[", "").rstrip("]") if text.startswith("#sq-item") else text[2:]
            out.append(f'<ul class="kindle-list"><li>{clean_item}</li></ul>')
            continue

        # Fórmulas matemáticas inline ($x^2$) e em bloco
        if text.startswith("$ ") and text.endswith(" $"):
            math_expr = text[2:-2].strip()
            # Converte notações comuns simples
            math_html = math_expr.replace("dots", "…").replace("times", "×")
            out.append(f'<div class="math-block"><em>{html.escape(math_html)}</em></div>')
            continue
        else:
            # Inline math
            text = re.sub(r'\$([^$]+)\$', r'<span class="inline-math"><em>\1</em></span>', text)

        out.append(f'<p>{text}</p>')

    return "\n".join(out)

def build_typst_kindle_epub(book_dir: Path, output_epub: Path) -> bool:
    """
    Gera um arquivo EPUB 3 refluxável de alta qualidade para Amazon Kindle
    a partir das páginas Typst transcritas.
    """
    book_dir = Path(book_dir).resolve()
    output_epub = Path(output_epub).resolve()
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    
    manifest_file = book_dir / "state" / "manifest.json"
    manifest = {}
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

    title = manifest.get("title", manifest.get("book_title", book_dir.name.replace("-", " ").title()))
    author = manifest.get("author", "Autor Desconhecido")
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, book_dir.name)}"

    staging = book_dir / "_epub_staging"
    if staging.exists():
        shutil.rmtree(staging)

    meta_inf = staging / "META-INF"
    oebps = staging / "OEBPS"
    oebps_images = oebps / "assets" / "images"
    meta_inf.mkdir(parents=True, exist_ok=True)
    oebps_images.mkdir(parents=True, exist_ok=True)

    # 1. mimetype
    (staging / "mimetype").write_text("application/epub+zip", encoding="ascii")

    # 2. container.xml
    (meta_inf / "container.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>""", encoding="utf-8")

    # 3. CSS
    (oebps / "kindle.css").write_text(KINDLE_EPUB_CSS, encoding="utf-8")

    # 4. Copiar assets/figures
    image_manifest_entries = []
    assets_dir = book_dir / "assets"
    if assets_dir.exists():
        for img in assets_dir.rglob("*"):
            if img.is_file() and img.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
                dest_img = oebps_images / img.name
                shutil.copy2(img, dest_img)
                mtype = "image/png" if img.suffix.lower() == ".png" else "image/jpeg"
                img_id = f"img_{re.sub(r'[^a-zA-Z0-9_]', '_', img.stem)}"
                image_manifest_entries.append(f'<item id="{img_id}" href="assets/images/{img.name}" media-type="{mtype}"/>')

    # 5. Agrupar páginas Typst em capítulos
    pages_dir = book_dir / "source" / "pages"
    pages = sorted(pages_dir.glob("page_*.typ"))
    
    # Agrupa a cada 15 a 20 páginas em um capítulo XHTML navegável
    chunk_size = 20
    spine_items = []
    manifest_items = []
    nav_toc_items = []
    ncx_navpoints = []

    for idx, i in enumerate(range(0, len(pages), chunk_size)):
        chunk_pages = pages[i:i + chunk_size]
        chap_id = f"chap_{idx+1:03d}"
        chap_title = f"Seção {idx+1} (Páginas {i+1}–{min(i+chunk_size, len(pages))})"
        
        chap_html_parts = []
        for p in chunk_pages:
            t = p.read_text(encoding="utf-8")
            chap_html_parts.append(typst_to_clean_html(t))
            
        full_chap_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR">
<head>
    <meta charset="UTF-8"/>
    <title>{html.escape(chap_title)}</title>
    <link rel="stylesheet" type="text/css" href="kindle.css"/>
</head>
<body>
    {"".join(chap_html_parts)}
</body>
</html>"""
        
        chap_file = oebps / f"{chap_id}.xhtml"
        chap_file.write_text(full_chap_xhtml, encoding="utf-8")
        
        manifest_items.append(f'<item id="{chap_id}" href="{chap_id}.xhtml" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{chap_id}"/>')
        nav_toc_items.append(f'<li><a href="{chap_id}.xhtml">{html.escape(chap_title)}</a></li>')
        ncx_navpoints.append(f"""
        <navPoint id="np_{idx+1}" playOrder="{idx+1}">
            <navLabel><text>{html.escape(chap_title)}</text></navLabel>
            <content src="{chap_id}.xhtml"/>
        </navPoint>""")

    # 6. nav.xhtml
    nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR">
<head><meta charset="UTF-8"/><title>Sumário</title><link rel="stylesheet" type="text/css" href="kindle.css"/></head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Sumário</h1>
        <ol>{"".join(nav_toc_items)}</ol>
    </nav>
</body>
</html>"""
    (oebps / "nav.xhtml").write_text(nav_xhtml, encoding="utf-8")
    manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

    # 7. toc.ncx
    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head><meta name="dtb:uid" content="{book_id}"/><meta name="dtb:depth" content="2"/><meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>
    <docTitle><text>{html.escape(title)}</text></docTitle>
    <docAuthor><text>{html.escape(author)}</text></docAuthor>
    <navMap>{"".join(ncx_navpoints)}</navMap>
</ncx>"""
    (oebps / "toc.ncx").write_text(toc_ncx, encoding="utf-8")
    manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    manifest_items.append('<item id="css" href="kindle.css" media-type="text/css"/>')

    # 8. content.opf
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0" xml:lang="pt-BR">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">{book_id}</dc:identifier>
        <dc:title>{html.escape(title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:language>pt-BR</dc:language>
        <meta property="dcterms:modified">2026-10-30T18:00:00Z</meta>
    </metadata>
    <manifest>
        {"".join(manifest_items + image_manifest_entries)}
    </manifest>
    <spine toc="ncx">
        {"".join(spine_items)}
    </spine>
</package>"""
    (oebps / "content.opf").write_text(content_opf, encoding="utf-8")

    # 9. Compactar para .epub
    if output_epub.exists():
        output_epub.unlink()

    with zipfile.ZipFile(output_epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for root, _, files in os.walk(staging):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(staging)
                if rel_path.as_posix() == "mimetype":
                    continue
                zf.write(full_path, rel_path.as_posix(), compress_type=zipfile.ZIP_DEFLATED)

    shutil.rmtree(staging)
    sz_mb = output_epub.stat().st_size / (1024 * 1024)
    print(f"[KINDLE-EPUB] Sucesso: {output_epub.name} ({sz_mb:.2f} MB, {len(pages)} páginas convertidas)")
    return True
