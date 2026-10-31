"""
build_kindle_epub.py — Gera edições EPUB 3 otimizadas para leitura no Amazon Kindle
a partir dos arquivos de capítulos traduzidos em LaTeX (.tex) e do manifest.json.
"""

import os
import re
import html
import uuid
import zipfile
import shutil
from pathlib import Path
import json

def latex_to_html_body(tex_content: str, image_rel_prefix: str = "assets/images/") -> tuple[str, list[tuple[str, str]]]:
    """
    Converte código LaTeX dos capítulos para XHTML semântico, retornando o corpo HTML
    e uma lista de seções/títulos encontrados (nível, título).
    """
    lines = tex_content.splitlines()
    out = []
    toc_entries = []
    
    in_itemize = False
    in_enumerate = False
    in_table = False
    in_quote = False
    in_box = False
    box_title = ""
    box_type = ""
    table_rows = []
    
    # Pré-processamento de macros simples e caracteres especiais
    def clean_inline(text: str) -> str:
        # Escapamentos LaTeX -> caracteres reais
        # Cuidado com URLs e hrefs primeiro
        
        # href
        def repl_href(m):
            url = m.group(1)
            label = clean_inline(m.group(2))
            return f'<a href="{url}">{label}</a>'
        text = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', repl_href, text)
        
        # url
        def repl_url(m):
            url = m.group(1)
            return f'<a href="{url}">{url}</a>'
        text = re.sub(r'\\url\{([^}]+)\}', repl_url, text)
        
        # textbf
        text = re.sub(r'\\textbf\{([^{}]+)\}', r'<strong>\1</strong>', text)
        text = re.sub(r'\\textbf\{([^{}]+)\}', r'<strong>\1</strong>', text) # pass 2 for nested
        
        # textit / emph
        text = re.sub(r'\\(?:textit|emph)\{([^{}]+)\}', r'<em>\1</em>', text)
        text = re.sub(r'\\(?:textit|emph)\{([^{}]+)\}', r'<em>\1</em>', text)
        
        # texttt
        text = re.sub(r'\\texttt\{([^{}]+)\}', r'<code>\1</code>', text)
        
        # Aspas tipográficas LaTeX: `` e ''
        text = text.replace("``", "“").replace("''", "”")
        text = text.replace("---", "—").replace("--", "–")
        
        # Escapamentos LaTeX comuns
        text = text.replace(r"\%", "%")
        text = text.replace(r"\&", "&amp;")
        text = text.replace(r"\#", "#")
        text = text.replace(r"\$", "$")
        text = text.replace(r"\_", "_")
        text = text.replace(r"\copyright", "©")
        text = text.replace(r"\par\medskip", "<br/>")
        text = text.replace(r"\par\smallskip", "<br/>")
        text = text.replace(r"\par", "<br/>")
        text = text.replace(r"\noindent", "")
        text = text.replace(r"\\", "<br/>")
        
        return text

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        if not line:
            continue
            
        # Comentários LaTeX puros
        if line.startswith("%"):
            continue
            
        # Comandos de página ou geometria ignorados no EPUB
        if any(line.startswith(cmd) for cmd in [
            r"\clearpage", r"\newpage", r"\vfill", r"\vspace", r"\frontmatter", 
            r"\mainmatter", r"\backmatter", r"\tableofcontents", r"\addcontentsline",
            r"\begin{titlepage}", r"\end{titlepage}", r"\begin{center}", r"\end{center}",
            r"\centering", r"\raggedleft", r"\raggedright", r"\pagenumbering", r"\small",
            r"\footnotesize", r"\large", r"\Large", r"\Huge", r"\toprule", r"\midrule",
            r"\bottomrule", r"\addlinespace", r"\hline", r"\endfirsthead", r"\endhead"
        ]):
            continue

        # Inclusão de figuras isoladas (\includegraphics)
        inc_m = re.match(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', line)
        if inc_m:
            img_path = inc_m.group(1)
            img_filename = Path(img_path).name
            out.append(f'<div class="figure-container"><img src="{image_rel_prefix}{img_filename}" alt="Figura" class="kindle-img" /></div>')
            continue

        # Macro \bookfigure{caminho}{legenda}
        bf_m = re.match(r'\\bookfigure\{([^}]+)\}\{([^}]+)\}', line)
        if bf_m:
            img_path = bf_m.group(1)
            caption = clean_inline(bf_m.group(2))
            img_filename = Path(img_path).name
            out.append(f'<figure class="kindle-figure"><img src="{image_rel_prefix}{img_filename}" alt="{html.escape(caption)}" class="kindle-img" /><figcaption>{caption}</figcaption></figure>')
            continue

        # Capítulos e Seções
        ch_m = re.match(r'\\chapter\*?\{([^}]+)\}', line)
        if ch_m:
            title = clean_inline(ch_m.group(1))
            toc_entries.append(("chapter", title))
            out.append(f'<h1 class="chapter-title">{title}</h1>')
            continue

        sec_m = re.match(r'\\section\*?\{([^}]+)\}', line)
        if sec_m:
            title = clean_inline(sec_m.group(1))
            toc_entries.append(("section", title))
            out.append(f'<h2 class="section-title">{title}</h2>')
            continue

        ssec_m = re.match(r'\\subsection\*?\{([^}]+)\}', line)
        if ssec_m:
            title = clean_inline(ssec_m.group(1))
            toc_entries.append(("subsection", title))
            out.append(f'<h3 class="subsection-title">{title}</h3>')
            continue

        sssec_m = re.match(r'\\subsubsection\*?\{([^}]+)\}', line)
        if sssec_m:
            title = clean_inline(sssec_m.group(1))
            out.append(f'<h4 class="subsubsection-title">{title}</h4>')
            continue

        # Ambientes pedagógicos: learningoutcomes
        if line.startswith(r"\begin{learningoutcomes}"):
            in_box = True
            box_type = "learningoutcomes"
            out.append('<aside class="kindle-box outcomes-box">')
            out.append('<h4 class="box-title">Objetivos de Aprendizagem</h4>')
            continue
        elif line.startswith(r"\end{learningoutcomes}"):
            in_box = False
            out.append('</aside>')
            continue

        # Ambientes pedagógicos: featurebox
        fb_m = re.match(r'\\begin\{featurebox\}\{([^}]+)\}', line)
        if fb_m:
            in_box = True
            box_type = "featurebox"
            box_title = clean_inline(fb_m.group(1))
            out.append('<aside class="kindle-box feature-box">')
            out.append(f'<h4 class="box-title">{box_title}</h4>')
            continue
        elif line.startswith(r"\end{featurebox}"):
            in_box = False
            out.append('</aside>')
            continue

        # sampletext
        if line.startswith(r"\begin{sampletext}"):
            out.append('<div class="kindle-sample">')
            continue
        elif line.startswith(r"\end{sampletext}"):
            out.append('</div>')
            continue

        # analysisnote
        if line.startswith(r"\begin{analysisnote}"):
            out.append('<div class="kindle-analysis">')
            continue
        elif line.startswith(r"\end{analysisnote}"):
            out.append('</div>')
            continue

        # quote
        if line.startswith(r"\begin{quote}"):
            in_quote = True
            out.append('<blockquote class="kindle-quote">')
            continue
        elif line.startswith(r"\end{quote}"):
            in_quote = False
            out.append('</blockquote>')
            continue

        # Listas: itemize
        if line.startswith(r"\begin{itemize}"):
            in_itemize = True
            out.append('<ul class="kindle-list">')
            continue
        elif line.startswith(r"\end{itemize}"):
            in_itemize = False
            out.append('</ul>')
            continue

        # Listas: enumerate
        if line.startswith(r"\begin{enumerate}"):
            in_enumerate = True
            out.append('<ol class="kindle-list">')
            continue
        elif line.startswith(r"\end{enumerate}"):
            in_enumerate = False
            out.append('</ol>')
            continue

        # Itens de listas
        item_m = re.match(r'\\item\s*(.*)', line)
        if item_m:
            item_body = clean_inline(item_m.group(1))
            out.append(f'<li>{item_body}</li>')
            continue

        # Tabelas
        if any(line.startswith(tb) for tb in [r"\begin{table}", r"\begin{tabularx}", r"\begin{longtable}", r"\begin{tabular}"]):
            in_table = True
            table_rows = []
            continue
        elif any(line.startswith(tb) for tb in [r"\end{table}", r"\end{tabularx}", r"\end{longtable}", r"\end{tabular}"]):
            in_table = False
            if table_rows:
                out.append('<div class="table-wrapper"><table class="kindle-table">')
                # Primeira linha como cabeçalho
                first_row = True
                for row in table_rows:
                    cols = [clean_inline(c.strip()) for c in row.split("&")]
                    if first_row:
                        out.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cols) + '</tr>')
                        first_row = False
                    else:
                        out.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cols) + '</tr>')
                out.append('</table></div>')
                table_rows = []
            continue

        if in_table:
            # Captura linhas da tabela
            clean_tbl_line = line.replace(r"\\", "").strip()
            if "&" in clean_tbl_line:
                table_rows.append(clean_tbl_line)
            continue

        # Parágrafo normal
        cleaned = clean_inline(line)
        if cleaned:
            out.append(f'<p>{cleaned}</p>')

    return "\n".join(out), toc_entries


KINDLE_CSS = """/* Kindle & E-Reader Optimized Stylesheet */
@namespace "http://www.w3.org/1999/xhtml";

body {
    margin: 4% 5%;
    line-height: 1.45;
    text-align: justify;
    color: #111111;
    font-size: 1em;
}

h1, h2, h3, h4, h5, h6 {
    font-family: sans-serif;
    line-height: 1.25;
    text-align: left;
    page-break-after: avoid;
    break-after: avoid;
    color: #000000;
}

h1.chapter-title {
    font-size: 1.6em;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    padding-bottom: 0.3em;
    border-bottom: 1.5px solid #222222;
}

h2.section-title {
    font-size: 1.3em;
    margin-top: 1.4em;
    margin-bottom: 0.6em;
}

h3.subsection-title {
    font-size: 1.15em;
    margin-top: 1.2em;
    margin-bottom: 0.5em;
}

h4.subsubsection-title {
    font-size: 1.05em;
    margin-top: 1.1em;
    margin-bottom: 0.4em;
}

p {
    margin: 0.5em 0;
    text-indent: 0;
}

a {
    color: #000000;
    text-decoration: underline;
}

blockquote.kindle-quote {
    margin: 1.2em 5%;
    padding: 0.5em 1em;
    border-left: 3px solid #444444;
    font-style: italic;
    background-color: #f7f7f7;
}

/* Quadros Pedagógicos (E-Ink High Contrast) */
aside.kindle-box {
    margin: 1.4em 0;
    padding: 0.8em 1em;
    border: 1px solid #222222;
    border-left: 4px solid #000000;
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

div.kindle-sample {
    margin: 1em 0;
    padding: 0.7em 0.9em;
    border-left: 3px solid #555555;
    background-color: #fafafa;
}

div.kindle-analysis {
    margin: 0.8em 0;
    padding: 0.6em 0.9em;
    border-left: 2px solid #777777;
    font-style: italic;
    font-size: 0.95em;
}

ul.kindle-list, ol.kindle-list {
    margin: 0.6em 0 0.8em 1.5em;
    padding-left: 0;
}

li {
    margin-bottom: 0.35em;
}

/* Imagens responsivas sem distorção no Kindle */
figure.kindle-figure, div.figure-container {
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

/* Tabelas adaptadas para leitura no Kindle */
div.table-wrapper {
    width: 100%;
    overflow-x: auto;
    margin: 1.2em 0;
}

table.kindle-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88em;
}

table.kindle-table th, table.kindle-table td {
    border: 1px solid #444444;
    padding: 0.4em 0.6em;
    text-align: left;
}

table.kindle-table th {
    background-color: #e5e5e5;
    font-weight: bold;
    color: #000000;
}

code, pre {
    font-family: monospace;
    font-size: 0.9em;
    background-color: #f2f2f2;
}

pre {
    padding: 0.6em;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}
"""


def build_epub_for_book(book_dir_or_slug, output_epub: Path = None, root_dir: Path = Path(".")) -> Path:
    target_path = Path(book_dir_or_slug)
    if target_path.exists() and target_path.is_dir():
        work_dir = target_path.resolve()
        book_slug = work_dir.name
    else:
        book_slug = str(book_dir_or_slug)
        work_dir = root_dir / "work" / book_slug
        if not work_dir.exists():
            work_dir = root_dir / "library" / book_slug
            
    manifest_file = work_dir / "state" / "manifest.json"
    if not manifest_file.exists():
        manifest_file = work_dir / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest não encontrado em {manifest_file}")
        
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    
    title = manifest.get("bookTitleTranslated", manifest.get("bookTitleOriginal", book_slug))
    author = manifest.get("author", "Autor Desconhecido")
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, book_slug)}"
    
    # Criar pasta temporária de montagem do EPUB
    epub_staging = work_dir / "_epub_staging"
    if epub_staging.exists():
        shutil.rmtree(epub_staging)
        
    meta_inf = epub_staging / "META-INF"
    oebps = epub_staging / "OEBPS"
    oebps_images = oebps / "assets" / "images"
    oebps_images.mkdir(parents=True, exist_ok=True)
    meta_inf.mkdir(parents=True, exist_ok=True)
    
    # 1. mimetype (SEM quebra de linha)
    (epub_staging / "mimetype").write_text("application/epub+zip", encoding="ascii")
    
    # 2. container.xml
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
    (meta_inf / "container.xml").write_text(container_xml, encoding="utf-8")
    
    # 3. Copiar stylesheet Kindle
    (oebps / "kindle.css").write_text(KINDLE_CSS, encoding="utf-8")
    
    # 4. Copiar todas as imagens existentes
    assets_src = work_dir / "assets" / "images"
    if not assets_src.exists():
        assets_src = work_dir / "assets"
    if not assets_src.exists():
        assets_src = work_dir / "source" / "assets" / "images"

    image_manifest_entries = []
    cover_image_id = None
    
    if assets_src.exists():
        for img_file in assets_src.rglob("*"):
            if img_file.is_file() and img_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]:
                dest_file = oebps_images / img_file.name
                shutil.copy2(img_file, dest_file)
                mtype = "image/png" if img_file.suffix.lower() == ".png" else "image/jpeg"
                if img_file.suffix.lower() == ".svg":
                    mtype = "image/svg+xml"
                img_id = f"img_{re.sub(r'[^a-zA-Z0-9_]', '_', img_file.stem)}"
                is_cover = "cover" in img_file.name.lower()
                if is_cover and not cover_image_id:
                    cover_image_id = img_id
                    image_manifest_entries.append(f'<item id="{img_id}" href="assets/images/{img_file.name}" media-type="{mtype}" properties="cover-image"/>')
                else:
                    image_manifest_entries.append(f'<item id="{img_id}" href="assets/images/{img_file.name}" media-type="{mtype}"/>')
                    
    # 5. Processar capítulos e gerar XHTML
    spine_items = []
    manifest_items = []
    nav_toc_items = []
    ncx_navpoints = []
    
    chapters_dir = work_dir / "source" / "chapters"
    if not chapters_dir.exists():
        chapters_dir = work_dir / "chapters"

    raw_list = manifest.get("chapters", manifest.get("units", []))
    chapters = []
    for item in raw_list:
        cid = item.get("id", "")
        candidates = [
            chapters_dir / f"{cid}.tex",
            work_dir / "source" / item.get("outputFile", "---"),
            work_dir / item.get("outputFile", "---"),
            root_dir / item.get("outputFile", "---")
        ]
        found_p = next((c for c in candidates if c.exists()), None)
        if found_p:
            item["_resolved_path"] = found_p
            chapters.append(item)

    play_order = 1
    
    for idx, chap in enumerate(chapters):
        chap_id = chap.get("id", f"chap_{idx:02d}")
        chap_tex_path = chap.get("_resolved_path")
        
        if not chap_tex_path.exists():
            print(f"Aviso: arquivo {chap_tex_path} não encontrado, pulando...")
            continue
            
        tex_text = chap_tex_path.read_text(encoding="utf-8")
        html_body, toc_entries = latex_to_html_body(tex_text, image_rel_prefix="assets/images/")
        
        doc_title = chap.get("titleTranslated", chap.get("titleOriginal", f"Capítulo {idx+1}"))
        xhtml_filename = f"{chap_id}.xhtml"
        
        xhtml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR" lang="pt-BR">
<head>
    <meta charset="utf-8" />
    <title>{html.escape(doc_title)}</title>
    <link rel="stylesheet" type="text/css" href="kindle.css" />
</head>
<body epub:type="bodymatter">
    <section class="chapter-content">
        {html_body}
    </section>
</body>
</html>"""
        (oebps / xhtml_filename).write_text(xhtml_content, encoding="utf-8")
        
        item_id = f"chap_{idx:02d}"
        manifest_items.append(f'<item id="{item_id}" href="{xhtml_filename}" media-type="application/xhtml+xml"/>')
        spine_items.append(f'<itemref idref="{item_id}"/>')
        
        # TOC entries
        nav_toc_items.append(f'<li><a href="{xhtml_filename}">{html.escape(doc_title)}</a></li>')
        ncx_navpoints.append(f"""    <navPoint id="np_{play_order}" playOrder="{play_order}">
        <navLabel><text>{html.escape(doc_title)}</text></navLabel>
        <content src="{xhtml_filename}"/>
    </navPoint>""")
        play_order += 1

    # 6. nav.xhtml (EPUB 3 Navigation Document)
    nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="pt-BR" lang="pt-BR">
<head>
    <meta charset="utf-8" />
    <title>Sumário</title>
    <link rel="stylesheet" type="text/css" href="kindle.css" />
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Sumário</h1>
        <ol>
            {"".join(nav_toc_items)}
        </ol>
    </nav>
</body>
</html>"""
    (oebps / "nav.xhtml").write_text(nav_xhtml, encoding="utf-8")
    manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

    # 7. toc.ncx (EPUB 2 / Kindle Backward Compatibility)
    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="{book_id}"/>
        <meta name="dtb:depth" content="2"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(title)}</text></docTitle>
    <docAuthor><text>{html.escape(author)}</text></docAuthor>
    <navMap>
{"".join(ncx_navpoints)}
    </navMap>
</ncx>"""
    (oebps / "toc.ncx").write_text(toc_ncx, encoding="utf-8")
    manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    manifest_items.append('<item id="css" href="kindle.css" media-type="text/css"/>')

    # 8. content.opf
    cover_meta = f'<meta name="cover" content="{cover_image_id}"/>' if cover_image_id else ""
    manifest_str = "\n        ".join(manifest_items + image_manifest_entries)
    spine_str = "\n        ".join(spine_items)
    
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0" xml:lang="pt-BR">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">{book_id}</dc:identifier>
        <dc:title>{html.escape(title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:language>pt-BR</dc:language>
        <meta property="dcterms:modified">2026-10-30T18:00:00Z</meta>
        {cover_meta}
    </metadata>
    <manifest>
        {manifest_str}
    </manifest>
    <spine toc="ncx">
        {spine_str}
    </spine>
</package>"""
    (oebps / "content.opf").write_text(content_opf, encoding="utf-8")

    # 9. Compactar para arquivo .epub (o mimetype DEVE ser armazenado sem compressão no início)
    if output_epub:
        final_epub = Path(output_epub)
        final_epub.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = work_dir / "dist"
        output_dir.mkdir(parents=True, exist_ok=True)
        final_epub = output_dir / f"{book_slug}-kindle.epub"
        
    if final_epub.exists():
        final_epub.unlink()

    with zipfile.ZipFile(final_epub, "w") as zf:
        # Primeiro o mimetype sem compressão
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        
        # Em seguida os demais arquivos com ZIP_DEFLATED
        for root, _, files in os.walk(epub_staging):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(epub_staging)
                if rel_path.as_posix() == "mimetype":
                    continue
                zf.write(full_path, rel_path.as_posix(), compress_type=zipfile.ZIP_DEFLATED)
                
    # Limpar staging
    shutil.rmtree(epub_staging)
    
    print(f"EPUB Kindle gerado com sucesso: {final_epub} ({final_epub.stat().st_size} bytes)")
    return final_epub

if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "ai-native-software-engineering"
    build_epub_for_book(slug)
