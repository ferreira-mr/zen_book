import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import re
import html
import shutil
import zipfile
import uuid
from pathlib import Path
from scratch.test_clean_epub_xml import clean_chapter_html

BASE_DIR = Path(".").resolve()
BOOK_DIR = BASE_DIR / "library" / "fundamentos-de-manutencao-de-software"
HTML_DIR = BOOK_DIR / "intermediate" / "html_source"
ASSETS_DIR = BOOK_DIR / "assets" / "figures"
DIST_DIR = BOOK_DIR / "dist"
OUTPUT_EPUB = DIST_DIR / "Fundamentos de Manutenção de Software (Marco Tulio Valente) - Kindle.epub"

CHAPTER_MAP = [
    ("cap0.html", "Prefácio"),
    ("cap1.html", "1 – Introdução"),
    ("cap2.html", "2 – Código Limpo"),
    ("cap3.html", "3 – Documentação de Código"),
    ("cap4.html", "4 – Código Flexível a Mudanças"),
    ("cap5.html", "5 – Bugs"),
    ("cap6.html", "6 – Depuração"),
    ("cap7.html", "7 – Dívida Técnica"),
    ("cap8.html", "8 – Sistemas Legados"),
    ("cap9.html", "9 – Processos"),
    ("cap10.html", "10 – Manutenção Usando IA"),
]

EPUB_CSS = """/* BookForge Kindle EPUB 3 — Enhanced Typography */
@namespace "http://www.w3.org/1999/xhtml";

body {
    margin: 4% 5%;
    font-family: "Bookerly", "Georgia", "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.5;
    text-align: justify;
    color: #111111;
    background-color: #ffffff;
}

h1.chapter-title {
    font-size: 1.55em;
    font-weight: bold;
    text-align: left;
    margin-top: 1.8em;
    margin-bottom: 0.8em;
    border-bottom: 1.5px solid #7A2424;
    padding-bottom: 0.35em;
    color: #7A2424;
    page-break-before: always;
    break-before: page;
}

h2.section-title {
    font-size: 1.25em;
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    color: #7A2424;
    page-break-after: avoid;
    break-after: avoid;
}

h3.subsection-title {
    font-size: 1.1em;
    font-weight: bold;
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
    break-after: avoid;
}

p {
    margin-top: 0;
    margin-bottom: 0.6em;
    text-indent: 1.2em;
}

p.no-indent, h1 + p, h2 + p, h3 + p, h4 + p, aside p {
    text-indent: 0;
}

/* Callout boxes */
aside.kindle-box {
    margin: 1.4em 0;
    padding: 0.9em 1.2em;
    border-left: 4pt solid #1D4ED8;
    border-top: 1px solid #d0d7de;
    border-right: 1px solid #d0d7de;
    border-bottom: 1px solid #d0d7de;
    background-color: #F8FAFC;
    page-break-inside: avoid;
    break-inside: avoid;
}

aside.kindle-box .box-title {
    margin-top: 0;
    margin-bottom: 0.4em;
    font-size: 1.05em;
    font-weight: bold;
    color: #1D4ED8;
    font-family: "Segoe UI", sans-serif;
}

/* Code blocks: NO WEIRD BREAKS */
pre.kindle-code {
    background-color: #F8F9FA;
    border: 1px solid #E2E8F0;
    border-left: 3pt solid #64748B;
    border-radius: 3px;
    padding: 0.8em 1em;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.88em;
    line-height: 1.35;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 1.2em 0;
    page-break-inside: avoid;
    break-inside: avoid;
}

code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.9em;
    background-color: #F1F5F9;
    padding: 1px 4px;
    border-radius: 3px;
}

pre.kindle-code code {
    background-color: transparent;
    padding: 0;
}

/* Tables */
table.kindle-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92em;
    margin: 1.4em 0;
}

table.kindle-table th, table.kindle-table td {
    border: 1px solid #CBD5E1;
    padding: 6px 10px;
    text-align: left;
}

table.kindle-table th {
    background-color: #F1F5F9;
    font-weight: bold;
}

/* Figures */
figure.kindle-figure {
    margin: 1.6em 0;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
}

img.kindle-img {
    max-width: 95%;
    height: auto;
    display: block;
    margin: 0 auto;
}

figcaption {
    font-size: 0.88em;
    margin-top: 0.5em;
    color: #475569;
    font-style: italic;
}

/* Quotes */
blockquote {
    margin: 1.2em 0;
    padding-left: 1.2em;
    border-left: 3pt solid #94A3B8;
    color: #334155;
    font-style: italic;
}

ul, ol {
    margin: 0.6em 0 0.8em 1.5em;
    padding-left: 0;
}

li {
    margin-bottom: 0.35em;
}
"""

def build_perfect_epub():
    print(">>> Construindo EPUB 3 com validação XML estrita e tipografia Bookerly...")
    staging = BOOK_DIR / "_staging_epub_perfect"
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
    (oebps / "kindle.css").write_text(EPUB_CSS, encoding="utf-8")

    # 4. Images
    image_items = []
    cover_file = None
    for img in ASSETS_DIR.glob("*"):
        if img.is_file() and img.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
            dest = oebps_images / img.name
            shutil.copy2(img, dest)
            mtype = "image/svg+xml" if img.suffix.lower() == ".svg" else ("image/png" if img.suffix.lower() == ".png" else "image/jpeg")
            img_id = f"img_{re.sub(r'[^a-zA-Z0-9_]', '_', img.stem)}"
            if "capa" in img.name.lower() and not cover_file:
                cover_file = img
                image_items.append(f'<item id="{img_id}" href="assets/images/{img.name}" media-type="{mtype}" properties="cover-image"/>')
            else:
                image_items.append(f'<item id="{img_id}" href="assets/images/{img.name}" media-type="{mtype}"/>')

    # 5. Capa XHTML
    cover_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR">
<head>
    <meta charset="utf-8"/>
    <title>Capa</title>
    <link rel="stylesheet" type="text/css" href="kindle.css"/>
    <style>
        body {{ margin: 0; padding: 0; text-align: center; }}
        img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body epub:type="cover">
    <figure class="kindle-figure">
        <img src="assets/images/{cover_file.name}" alt="Capa"/>
    </figure>
</body>
</html>"""
    (oebps / "cover.xhtml").write_text(cover_xhtml, encoding="utf-8")

    # 6. Chapters XHTML
    spine_items = ['<itemref idref="cover"/>']
    manifest_items = ['<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>']
    toc_links = []
    ncx_points = [
        '<navPoint id="navpoint-1" playOrder="1"><navLabel><text>Capa</text></navLabel><content src="cover.xhtml"/></navPoint>'
    ]

    for idx, (h_file, title) in enumerate(CHAPTER_MAP):
        raw = (HTML_DIR / h_file).read_text(encoding="utf-8")
        clean_xml = clean_chapter_html(raw, title)
        chap_id = f"chap_{idx:02d}"
        chap_fname = f"{chap_id}.xhtml"
        (oebps / chap_fname).write_text(clean_xml, encoding="utf-8")
        
        manifest_items.append(f'<item id="{chap_id}" href="{chap_fname}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{chap_id}"/>')
        toc_links.append(f'<li><a href="{chap_fname}">{html.escape(title)}</a></li>')
        ncx_points.append(f'<navPoint id="navpoint-{idx+2}" playOrder="{idx+2}"><navLabel><text>{html.escape(title)}</text></navLabel><content src="{chap_fname}"/></navPoint>')

    # 7. nav.xhtml
    nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR">
<head>
    <meta charset="utf-8"/>
    <title>Sumário</title>
    <link rel="stylesheet" type="text/css" href="kindle.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1 class="chapter-title">Sumário</h1>
        <ol>
            {"".join(toc_links)}
        </ol>
    </nav>
</body>
</html>"""
    (oebps / "nav.xhtml").write_text(nav_xhtml, encoding="utf-8")
    manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

    # 8. toc.ncx
    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:fundamentos-manutencao-software"/>
        <meta name="dtb:depth" content="2"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>Fundamentos de Manutenção de Software</text></docTitle>
    <docAuthor><text>Marco Tulio Valente</text></docAuthor>
    <navMap>
        {"".join(ncx_points)}
    </navMap>
</ncx>"""
    (oebps / "toc.ncx").write_text(toc_ncx, encoding="utf-8")
    manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    manifest_items.append('<item id="css" href="kindle.css" media-type="text/css"/>')

    # 9. content.opf
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="pub-id">urn:uuid:fundamentos-manutencao-software</dc:identifier>
        <dc:title>Fundamentos de Manutenção de Software</dc:title>
        <dc:creator>Marco Tulio Valente</dc:creator>
        <dc:language>pt-BR</dc:language>
        <meta property="dcterms:modified">2026-11-02T15:00:00Z</meta>
        <meta name="cover" content="img_{cover_file.stem}"/>
    </metadata>
    <manifest>
        {"".join(manifest_items)}
        {"".join(image_items)}
    </manifest>
    <spine toc="ncx">
        {"".join(spine_items)}
    </spine>
</package>"""
    (oebps / "content.opf").write_text(content_opf, encoding="utf-8")

    # 10. Zip archive (mimetype FIRST and uncompressed!)
    if OUTPUT_EPUB.exists():
        OUTPUT_EPUB.unlink()

    with zipfile.ZipFile(OUTPUT_EPUB, "w") as z:
        z.write(staging / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
        for root, dirs, files in os.walk(staging):
            for file in files:
                p = Path(root) / file
                rel = p.relative_to(staging)
                if rel.as_posix() != "mimetype":
                    z.write(p, rel.as_posix(), compress_type=zipfile.ZIP_DEFLATED)

    shutil.rmtree(staging)
    sz_mb = OUTPUT_EPUB.stat().st_size / (1024 * 1024)
    print(f"✓ EPUB 3 gerado com sucesso: {OUTPUT_EPUB.name} ({sz_mb:.2f} MB)")

if __name__ == "__main__":
    build_perfect_epub()
