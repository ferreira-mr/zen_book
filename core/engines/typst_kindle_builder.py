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

pre.kindle-code {
    background-color: #f7f7f7;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 0.8em 1em;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.85em;
    line-height: 1.35;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 1.2em 0;
}

code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.9em;
    background-color: #f0f0f0;
    padding: 1px 3px;
    border-radius: 2px;
}

pre code {
    background-color: transparent;
    padding: 0;
}

/* Estruturas geradas pelo exportador HTML do Typst */
div.bf-center { text-align: center; text-indent: 0; }
div.bf-center p, div.bf-right p { text-align: inherit; text-indent: 0; }
div.bf-right { text-align: right; }
div.bf-rect { margin: 0.8em 0; padding: 0.5em 0.8em; border: 0.5pt solid #888888; }
div.bf-stack > div.bf-cell { margin: 0.2em 0; }
table.bf-grid { width: 100%; border-collapse: collapse; margin: 0.6em 0; }
table.bf-grid td { vertical-align: top; padding: 2px 6px; border: none; }
table { border-collapse: collapse; margin: 1em 0; }
td, th { border: 1px solid #cccccc; padding: 4px 6px; vertical-align: top; }
table.bf-grid td p, td p, th p { text-indent: 0; margin: 0; }
h1, h2, h3, h4 { text-indent: 0; }
math[display="block"] { display: block; margin: 0.8em 0; text-align: center; }
aside.footnote { font-size: 0.85em; margin: 0.4em 0; }
aside.footnote p { text-indent: 0; }
div.bf-cover { text-align: center; margin: 0; padding: 0; }
div.bf-cover img { max-width: 100%; max-height: 100%; }
"""

def strip_nested_set_page(text: str) -> str:
    """Remove diretivas #set page(...) e #page(...) preservando o conteúdo interno caso haja bloco [...]."""
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

    while True:
        m = re.search(r'(?<![\w-])#page\(', text)
        if not m:
            break
        idx = m.start()
        depth = 0
        end_idx = m.end() - 1
        for i in range(m.end() - 1, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
        rest = text[end_idx:]
        rest_l = rest.lstrip()
        if rest_l.startswith('['):
            ws = rest[:len(rest) - len(rest_l)]
            text = text[:idx] + "#block" + ws + rest_l
        else:
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
    chapters_dir = book_dir / "source" / "chapters"
    
    if pages_dir.exists() and list(pages_dir.glob("*.typ")):
        pages = sorted(pages_dir.glob("*.typ"))
    elif chapters_dir.exists() and list(chapters_dir.glob("*.typ")):
        pages = sorted(chapters_dir.glob("*.typ"))
    else:
        print(f"Erro: nenhum arquivo .typ encontrado em {pages_dir} ou {chapters_dir}")
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
        '#show heading.where(level: 1): it => {',
        '  v(1.2em)',
        '  block(',
        '    width: 100%,',
        '    stroke: (bottom: 1.5pt + rgb("#7A2424")),',
        '    inset: (bottom: 0.4em),',
        '    text(size: 12.5pt, font: font-sans, weight: "bold", fill: rgb("#7A2424"), tracking: 0.08em)[',
        '      #upper(it.body)',
        '    ]',
        '  )',
        '  v(0.8em)',
        '}',
        '#show heading.where(level: 2): it => {',
        '  v(0.8em)',
        '  it.body',
        '  v(0.4em)',
        '}',
        '#let chapter-header(..args) = { let t = if args.pos().len() > 1 { str(args.pos().at(0)) + " — " + str(args.pos().at(1)) } else { args.pos().at(0, default: "") }; heading(level: 1, outlined: true)[#t] }',
        '#let footnote(body) = text(size: 8.5pt, fill: rgb("#444444"))[ (#body)]',
    ]

    is_chapters = chapters_dir.exists() and not (pages_dir.exists() and list(pages_dir.glob("*.typ")))
    cover_file = book_dir / "assets" / "figures" / "capa.jpg"
    if not cover_file.exists():
        cover_file = book_dir / "assets" / "figures" / "capa.png"
    if cover_file.exists():
        header_lines.append(f'#place(top + left, dx: -8mm, dy: -10mm)[\n  #image("assets/figures/{cover_file.name}", width: 105mm, height: 140mm, fit: "cover")\n]\n#pagebreak()')

    manifest_file = book_dir / "state" / "manifest.json"
    book_title = book_dir.name.replace("-", " ").title()
    book_author = ""
    if manifest_file.exists():
        try:
            m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            book_title = m_data.get("title", book_title)
            book_author = m_data.get("author", book_author)
        except Exception:
            pass

    header_lines.append(f'''
#align(center + horizon)[
  #text(size: 14pt, font: font-sans, weight: "bold", fill: rgb("#7A2424"))[{book_title.upper()}]
  #v(1.2em)
  #text(size: 11pt, font: font-sans, fill: rgb("#333333"))[{book_author}]
  #v(2.5em)
  #text(size: 8pt, font: font-sans, fill: rgb("#666666"))[Edição Digital para Leitura no Kindle]
]
#pagebreak()
''')

    header_lines.append('''
#align(center)[
  #v(0.5em)
  #text(size: 12pt, font: font-sans, weight: "bold", fill: rgb("#7A2424"))[SUMÁRIO]
]
#v(0.6em)
#outline(title: none, indent: 1.2em, depth: 1)
#pagebreak()
''')

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

    sep = "\n\n#pagebreak()\n\n" if is_chapters else "\n\n"
    full_typst = "\n".join(header_lines) + "\n\n" + sep.join(body_lines)
    
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


# ==============================================================================
# EPUB 3 a partir de fontes Typst
# ------------------------------------------------------------------------------
# Em vez de "adivinhar" a sintaxe Typst com expressões regulares (o que deixava
# #text(...)[...], #align, #grid, #let etc. visíveis no EPUB final), o conteúdo é
# avaliado pelo próprio compilador Typst no modo de exportação HTML. Assim todas
# as funções, laços, variáveis e macros do template são executados de verdade e
# a matemática é convertida em MathML nativo.
#
# O exportador HTML do Typst descarta elementos puramente de layout (grid, place,
# rect, align, stack, columns...) JUNTO com o conteúdo deles. As regras abaixo
# desembrulham esses elementos para que nenhum texto do original seja perdido.
# ==============================================================================

_BF_HTML_PRELUDE = r'''
#set text(lang: "pt", region: "BR")
#show pagebreak: none
#show colbreak: none
#let _bf-grid-cells(children) = {
  let out = ()
  for c in children {
    let f = c.func()
    if f == grid.cell { out.push((body: c.body, span: c.at("colspan", default: 1))) }
    else if f == grid.header or f == grid.footer { out += _bf-grid-cells(c.children) }
  }
  out
}
#show grid: it => {
  let n = if type(it.columns) == array { it.columns.len() } else if type(it.columns) == int { it.columns } else { 1 }
  let cells = _bf-grid-cells(it.children)
  if cells.len() == 0 { return none }
  if n <= 1 {
    html.elem("div", attrs: (class: "bf-stack"), cells.map(c => html.elem("div", attrs: (class: "bf-cell"), c.body)).join())
  } else {
    let rows = ()
    let cur = ()
    let used = 0
    for c in cells {
      cur.push(c)
      used += c.span
      if used >= n { rows.push(cur); cur = (); used = 0 }
    }
    if cur.len() > 0 { rows.push(cur) }
    html.elem("table", attrs: (class: "bf-grid"), rows.map(r => html.elem("tr", r.map(c => html.elem("td", attrs: if c.span > 1 { (colspan: str(c.span)) } else { (:) }, c.body)).join())).join())
  }
}
#show align: it => {
  let x = it.alignment.x
  if x == center { html.elem("div", attrs: (class: "bf-center"), it.body) }
  else if x == right or x == end { html.elem("div", attrs: (class: "bf-right"), it.body) }
  else { it.body }
}
#show place: it => it.body
#show pad: it => it.body
#show columns: it => it.body
#show scale: it => it.body
#show rotate: it => it.body
#show move: it => it.body
#show skew: it => it.body
#show hide: none
#show rect: it => if it.body != none { html.elem("div", attrs: (class: "bf-rect"), it.body) }
#show square: it => if it.body != none { html.elem("span", attrs: (class: "bf-shape"), it.body) }
#show circle: it => if it.body != none { html.elem("span", attrs: (class: "bf-shape"), it.body) }
#show ellipse: it => if it.body != none { html.elem("span", attrs: (class: "bf-shape"), it.body) }
#show stack: it => html.elem("div", attrs: (class: "bf-stack"), it.children.filter(c => type(c) == content).map(c => html.elem("div", attrs: (class: "bf-cell"), c)).join())
#show text.where(weight: "bold"): it => html.elem("b", it)
#show text.where(weight: "semibold"): it => html.elem("b", it)
#show text.where(weight: "extrabold"): it => html.elem("b", it)
#show text.where(weight: "black"): it => html.elem("b", it)
#show text.where(style: "italic"): it => html.elem("i", it)
'''

# Macros conhecidas dos templates BookForge -> elemento semântico no EPUB
_BF_HEADING_MACROS = {
    "part-banner": ("h1", "part-title"),
    "chapter-header": ("h1", "chapter-title"),
    "sec": ("h2", "section-title"),
    "subsec": ("h3", "subsection-title"),
    "exercicios-header": ("h3", "subsection-title"),
}
_BF_BOX_MACROS = ("feature-box", "exemplo", "dica", "atencao", "obs", "obss", "questao",
                  "solucao", "gabarito", "caixa-formula")
_BF_CHAPTER_MARKER = re.compile(r"^\s*#(?:chapter-header|part-banner)\s*\(", re.MULTILINE)
_BF_TMP_PREFIX = "_bfepub_"


def _typst_include_order(source_dir: Path) -> List[Path]:
    """Ordem de leitura oficial: os #include do main.typ (cai para glob ordenado)."""
    main_typ = source_dir / "main.typ"
    files: List[Path] = []
    if main_typ.exists():
        main_txt = main_typ.read_text(encoding="utf-8")
        main_txt = re.sub(r"(?m)^\s*//.*$", "", main_txt)
        for m in re.finditer(r'#include\s+"([^"]+\.typ)"', main_txt):
            p = (source_dir / m.group(1)).resolve()
            if p.exists() and p not in files:
                files.append(p)
    if not files:
        for sub in ("pages", "chapters"):
            d = source_dir / sub
            if d.exists() and list(d.glob("*.typ")):
                files = sorted(p.resolve() for p in d.glob("*.typ"))
                break
    return [f for f in files if not f.name.startswith(_BF_TMP_PREFIX)]


def _template_override_layer(template_text: str) -> str:
    """Envolve as macros do template em elementos HTML semânticos (h1/h2/aside...)."""
    lines = ["", "// ---- Camada BookForge EPUB (gerada automaticamente) ----"]
    for name, (tag, cls) in _BF_HEADING_MACROS.items():
        if re.search(rf"(?m)^#let\s+{re.escape(name)}\s*\(", template_text):
            ident = "_bf_orig_" + name.replace("-", "_")
            lines.append(f"#let {ident} = {name}")
            lines.append(f'#let {name}(..args) = html.elem("{tag}", attrs: (class: "{cls}"), {ident}(..args))')
    for name in _BF_BOX_MACROS:
        if re.search(rf"(?m)^#let\s+{re.escape(name)}\s*\(", template_text):
            ident = "_bf_orig_" + name.replace("-", "_")
            lines.append(f"#let {ident} = {name}")
            lines.append(f'#let {name}(..args) = html.elem("aside", attrs: (class: "kindle-box"), {ident}(..args))')
    return "\n".join(lines) + "\n"


def _plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _clean_typst_html(fragment: str) -> str:
    """Pequenos ajustes na serialização HTML do Typst para leitura em e-readers."""
    # <b>A</b><b>B</b> -> <b>AB</b> (o Typst quebra o texto em vários nós)
    fragment = re.sub(r"</b>(\s*)<b>", r"\1", fragment)
    fragment = re.sub(r"</i>(\s*)<i>", r"\1", fragment)

    # Títulos não podem conter <p>/<div> (conteúdo de fluxo dentro de h1..h6)
    def fix_heading(m):
        inner = m.group(3)
        inner = re.sub(r"</p>\s*<p>", " ", inner)
        inner = re.sub(r"</?p>", "", inner)
        inner = re.sub(r"<div\b[^>]*>", "<span>", inner)
        inner = inner.replace("</div>", "</span> ")
        inner = re.sub(r"<table\b.*?</table>", lambda t: " ".join(
            f"<span>{c}</span>" for c in re.findall(r"<td[^>]*>(.*?)</td>", t.group(0), re.S)), inner, flags=re.S)
        return f"<{m.group(1)}{m.group(2)}>{inner.strip()}</{m.group(1)}>"
    fragment = re.sub(r"<(h[1-6])(\b[^>]*)>(.*?)</\1>", fix_heading, fragment, flags=re.S)

    # Remove parágrafos/divs vazios gerados por elementos ignorados
    fragment = re.sub(r"<p>\s*</p>", "", fragment)
    fragment = re.sub(r'<div class="bf-(?:center|right|rect|cell)">\s*</div>', "", fragment)
    return fragment


def _extract_li_items(section_html: str) -> List[tuple]:
    """Extrai (id, conteúdo) dos <li id="..."> de uma seção de notas, respeitando aninhamento."""
    items = []
    for m in re.finditer(r'<li id="([^"]+)">', section_html):
        start = m.end()
        depth, i = 1, start
        while depth and i < len(section_html):
            nxt_open = section_html.find("<li", i)
            nxt_close = section_html.find("</li>", i)
            if nxt_close == -1:
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                i = nxt_open + 3
            else:
                depth -= 1
                i = nxt_close + 5
        items.append((m.group(1), section_html[start:i - 5]))
    return items


def build_typst_kindle_epub(book_dir: Path, output_epub: Path) -> bool:
    """
    Gera um arquivo EPUB 3 refluxável de alta qualidade para Amazon Kindle
    a partir das páginas/capítulos Typst, usando o exportador HTML nativo do Typst.
    """
    from core.engines.epub_utils import (html_to_xhtml_fragment, xhtml_document, validate_xhtml,
                                         report_leaks, write_epub_zip)
    import base64
    import hashlib

    book_dir = Path(book_dir).resolve()
    output_epub = Path(output_epub).resolve()
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    source_dir = book_dir / "source"
    root_dir = book_dir.parent.parent if (book_dir.parent.parent / "core").exists() else book_dir

    manifest_file = book_dir / "state" / "manifest.json"
    manifest = {}
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    title = manifest.get("title", manifest.get("book_title", book_dir.name.replace("-", " ").title()))
    author = manifest.get("author", "Autor Desconhecido")
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, book_dir.name)}"

    files = _typst_include_order(source_dir)
    if not files:
        print(f"[KINDLE-EPUB] Erro: nenhum arquivo .typ encontrado em {source_dir}")
        return False

    # ---- 1. Agrupar arquivos em capítulos EPUB --------------------------------
    texts = {f: f.read_text(encoding="utf-8") for f in files}
    has_markers = any(_BF_CHAPTER_MARKER.search(t) for t in texts.values())
    chunks: List[List[Path]] = []
    if has_markers:
        for f in files:
            if not chunks or _BF_CHAPTER_MARKER.search(texts[f]) or len(chunks[-1]) >= 40:
                chunks.append([f])
            else:
                chunks[-1].append(f)
    elif len(files) <= 60:
        chunks = [[f] for f in files]
    else:
        chunks = [files[i:i + 20] for i in range(0, len(files), 20)]

    # ---- 2. Cópias temporárias apontando para o template com camada EPUB -----
    template = source_dir / "template.typ"
    tmp_template = source_dir / f"{_BF_TMP_PREFIX}template.typ"
    tmp_files: List[Path] = []
    for stale in source_dir.rglob(f"{_BF_TMP_PREFIX}*"):
        stale.unlink(missing_ok=True)

    def rewrite_imports(src_file: Path, text: str) -> str:
        if not template.exists():
            return text
        def repl(m):
            target = (src_file.parent / m.group(2)).resolve()
            if target == template.resolve():
                new_rel = os.path.relpath(tmp_template, src_file.parent).replace("\\", "/")
                return f'{m.group(1)}"{new_rel}"'
            return m.group(0)
        return re.sub(r'(#import\s+)"([^"]*template\.typ)"', repl, text)

    wrapper = source_dir / f"{_BF_TMP_PREFIX}book.typ"
    try:
        if template.exists():
            tpl_text = template.read_text(encoding="utf-8")
            tmp_template.write_text(tpl_text + _template_override_layer(tpl_text), encoding="utf-8")
            tmp_files.append(tmp_template)

        wrapper_lines = [_BF_HTML_PRELUDE]
        for ci, chunk in enumerate(chunks):
            wrapper_lines.append(f'#html.elem("div", attrs: (class: "bf-chunk", "data-bf": "{ci}"))[')
            for f in chunk:
                tmp_f = f.with_name(_BF_TMP_PREFIX + f.name)
                tmp_f.write_text(strip_nested_set_page(rewrite_imports(f, texts[f])), encoding="utf-8")
                tmp_files.append(tmp_f)
                rel = os.path.relpath(tmp_f, source_dir).replace("\\", "/")
                wrapper_lines.append(f'  #include "{rel}"')
            wrapper_lines.append("]")
        wrapper.write_text("\n".join(wrapper_lines) + "\n", encoding="utf-8")
        tmp_files.append(wrapper)

        print(f"[KINDLE-EPUB] Avaliando {len(files)} arquivos Typst com o exportador HTML nativo...")
        try:
            html_bytes, _warns = typst.compile_with_warnings(str(wrapper), root=str(root_dir), format="html")
        except Exception as e:
            msg = str(e).replace(_BF_TMP_PREFIX, "")
            raise RuntimeError(f"Falha ao avaliar o Typst em modo HTML: {msg}") from e
    finally:
        for t in tmp_files:
            t.unlink(missing_ok=True)

    full_html = html_bytes.decode("utf-8")

    # ---- 3. Separar head/body, CSS de MathML e capítulos ----------------------
    head_css = "\n".join(re.findall(r"(?s)<style>(.*?)</style>", full_html.split("<body", 1)[0]))
    body = full_html.split("<body", 1)[1]
    body = body[body.find(">") + 1: body.rfind("</body>")]

    notes_html = ""
    nm = re.search(r'<section role="doc-endnotes">.*?</section>\s*$', body, re.S)
    if nm:
        notes_html = nm.group(0)
        body = body[:nm.start()]

    starts = [(m.start(), m.end()) for m in re.finditer(r'<div class="bf-chunk" data-bf="\d+">', body)]
    chunk_bodies: List[str] = []
    for k, (s, e) in enumerate(starts):
        seg_end = starts[k + 1][0] if k + 1 < len(starts) else len(body)
        seg = body[e:seg_end].rstrip()
        if seg.endswith("</div>"):
            seg = seg[:-6]
        chunk_bodies.append(seg)

    # ---- 4. Staging --------------------------------------------------------------
    staging = book_dir / "_epub_staging"
    if staging.exists():
        shutil.rmtree(staging)
    meta_inf = staging / "META-INF"
    oebps = staging / "OEBPS"
    oebps_images = oebps / "assets" / "images"
    meta_inf.mkdir(parents=True, exist_ok=True)
    oebps_images.mkdir(parents=True, exist_ok=True)
    (staging / "mimetype").write_text("application/epub+zip", encoding="ascii")
    (meta_inf / "container.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>""", encoding="utf-8")
    (oebps / "kindle.css").write_text(KINDLE_EPUB_CSS + "\n/* MathML (gerado pelo Typst) */\n" + head_css, encoding="utf-8")

    # Imagens embutidas (data URI) -> arquivos deduplicados
    images: Dict[str, str] = {}
    ext_by_mime = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/gif": "gif",
                   "image/svg+xml": "svg", "image/webp": "webp"}

    def extract_img(m):
        mime, b64 = m.group(1), m.group(2)
        data = base64.b64decode(b64)
        ext = ext_by_mime.get(mime, "bin")
        name = f"img_{hashlib.sha1(data).hexdigest()[:16]}.{ext}"
        if name not in images:
            (oebps_images / name).write_bytes(data)
            images[name] = mime if mime != "image/jpg" else "image/jpeg"
        return f'src="assets/images/{name}"'

    chunk_bodies = [re.sub(r'src="data:([\w/+.-]+);base64,([^"]+)"', extract_img, cb) for cb in chunk_bodies]
    chunk_bodies = [re.sub(r"<img(?![^>]*\balt=)", '<img alt=""', cb) for cb in chunk_bodies]
    chunk_bodies = [_clean_typst_html(cb) for cb in chunk_bodies]

    # Títulos dos capítulos para o sumário
    chap_titles: List[str] = []
    for idx, (chunk, cb) in enumerate(zip(chunks, chunk_bodies)):
        t = ""
        hm = re.search(r"<h(1)\b[^>]*>(.*?)</h1>", cb, re.S) or re.search(r"<h([2-4])\b[^>]*>(.*?)</h\1>", cb, re.S)
        if hm:
            t = _plain(hm.group(2))
        if not t:
            centers = [_plain(c) for c in re.findall(r'<div class="bf-center">(.*?)</div>', cb, re.S)[:2]]
            centers = [c for c in centers if c]
            if centers:
                t = centers[0] if len(centers) == 1 or len(centers[0]) > 25 else f"{centers[0]} — {centers[1]}"
        if not t:
            t = chunk[0].stem.replace("-", " ").replace("_", " ").title() if len(chunk) == 1 \
                else f"Parte {idx + 1}"
        chap_titles.append(t[:120])

    # Nomes de arquivo e mapa id -> arquivo (para links cruzados e notas)
    chap_files = [f"chap_{i + 1:03d}.xhtml" for i in range(len(chunk_bodies))]
    id_to_file: Dict[str, str] = {}
    for fname, cb in zip(chap_files, chunk_bodies):
        for i_m in re.finditer(r'\bid="([^"]+)"', cb):
            id_to_file[i_m.group(1)] = fname

    # Notas de rodapé: devolvidas ao capítulo onde são chamadas (pop-up no Kindle)
    notes_by_file: Dict[str, List[str]] = {}
    if notes_html:
        for note_id, content in _extract_li_items(notes_html):
            back = re.search(r'<sup role="doc-backlink"><a href="#([^"]+)">(.*?)</a></sup>', content)
            ref_id = back.group(1) if back else ""
            label = _plain(back.group(2)) if back else ""
            content = re.sub(r'<sup role="doc-backlink">.*?</sup>', "", content, count=1, flags=re.S)
            target = id_to_file.get(ref_id, chap_files[-1] if chap_files else "")
            id_to_file[note_id] = target
            notes_by_file.setdefault(target, []).append(
                f'<aside epub:type="footnote" role="doc-footnote" class="footnote" id="{note_id}">'
                f'<p><a href="#{ref_id}">{label}</a> {content.strip()}</p></aside>')

    spine_items, manifest_items, nav_toc_items, ncx_navpoints = [], [], [], []
    xhtml_docs: Dict[str, str] = {}

    # Capa
    cover_img = None
    for cand in ("capa.jpg", "capa.jpeg", "capa.png", "cover.jpg", "cover.png"):
        c = book_dir / "assets" / "figures" / cand
        if c.exists():
            cover_img = c
            break
    cover_manifest = ""
    if cover_img:
        cover_name = "cover" + cover_img.suffix.lower()
        shutil.copy2(cover_img, oebps_images / cover_name)
        cmime = "image/png" if cover_img.suffix.lower() == ".png" else "image/jpeg"
        manifest_items.append(f'<item id="cover-image" href="assets/images/{cover_name}" media-type="{cmime}" properties="cover-image"/>')
        cover_doc = xhtml_document(title, f'<div class="bf-cover"><img src="assets/images/{cover_name}" alt="{html.escape(title)}"/></div>',
                                   body_attrs='epub:type="cover"')
        (oebps / "cover.xhtml").write_text(cover_doc, encoding="utf-8")
        xhtml_docs["cover.xhtml"] = cover_doc
        manifest_items.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
        spine_items.append('<itemref idref="cover" linear="no"/>')
        cover_manifest = '<meta name="cover" content="cover-image"/>'

    for idx, (fname, cb, ctitle) in enumerate(zip(chap_files, chunk_bodies, chap_titles)):
        def fix_href(m):
            target_id = m.group(1)
            target_file = id_to_file.get(target_id)
            if target_file and target_file != fname:
                return f'href="{target_file}#{target_id}"'
            return m.group(0)
        cb = re.sub(r'<sup id="([^"]+)" role="doc-noteref"><a href="#([^"]+)">',
                    r'<sup id="\1" role="doc-noteref"><a epub:type="noteref" href="#\2">', cb)
        cb = re.sub(r'href="#([^"]+)"', fix_href, cb)
        notes = "".join(notes_by_file.get(fname, []))
        if notes:
            notes = re.sub(r'href="#([^"]+)"', fix_href, notes)
        body_xhtml = html_to_xhtml_fragment(cb + notes)
        doc = xhtml_document(ctitle, f'<section class="chapter-content" epub:type="bodymatter">\n{body_xhtml}\n</section>')
        (oebps / fname).write_text(doc, encoding="utf-8")
        xhtml_docs[fname] = doc

        props = []
        if "<math" in doc:
            props.append("mathml")
        if "<svg" in doc:
            props.append("svg")
        prop_attr = f' properties="{" ".join(props)}"' if props else ""
        item_id = f"chap_{idx + 1:03d}"
        manifest_items.append(f'<item id="{item_id}" href="{fname}" media-type="application/xhtml+xml"{prop_attr}/>')
        spine_items.append(f'<itemref idref="{item_id}"/>')
        nav_toc_items.append(f'<li><a href="{fname}">{html.escape(ctitle)}</a></li>')
        ncx_navpoints.append(f"""
        <navPoint id="np_{idx + 1}" playOrder="{idx + 1}">
            <navLabel><text>{html.escape(ctitle)}</text></navLabel>
            <content src="{fname}"/>
        </navPoint>""")

    # nav.xhtml
    nav_xhtml = xhtml_document("Sumário", f"""    <nav epub:type="toc" id="toc">
        <h1>Sumário</h1>
        <ol>{"".join(nav_toc_items)}</ol>
    </nav>""")
    (oebps / "nav.xhtml").write_text(nav_xhtml, encoding="utf-8")
    xhtml_docs["nav.xhtml"] = nav_xhtml
    manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

    # toc.ncx
    toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head><meta name="dtb:uid" content="{book_id}"/><meta name="dtb:depth" content="1"/><meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>
    <docTitle><text>{html.escape(title)}</text></docTitle>
    <docAuthor><text>{html.escape(author)}</text></docAuthor>
    <navMap>{"".join(ncx_navpoints)}</navMap>
</ncx>"""
    (oebps / "toc.ncx").write_text(toc_ncx, encoding="utf-8")
    manifest_items.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
    manifest_items.append('<item id="css" href="kindle.css" media-type="text/css"/>')
    for name, mime in sorted(images.items()):
        manifest_items.append(f'<item id="{name.rsplit(".", 1)[0]}" href="assets/images/{name}" media-type="{mime}"/>')

    # Validação XML (um XHTML malformado faz o Kindle exibir código ou recusar o arquivo)
    errors = [err for err in (validate_xhtml(c, n) for n, c in xhtml_docs.items()) if err]
    if errors:
        shutil.rmtree(staging, ignore_errors=True)
        raise RuntimeError("XHTML inválido gerado para o EPUB:\n  " + "\n  ".join(errors[:10]))
    report_leaks({n: c for n, c in xhtml_docs.items() if n.startswith("chap_")}, tag="KINDLE-EPUB")

    modified = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest_str = "\n        ".join(manifest_items)
    spine_str = "\n        ".join(spine_items)
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0" xml:lang="pt-BR">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">{book_id}</dc:identifier>
        <dc:title>{html.escape(title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:language>pt-BR</dc:language>
        <meta property="dcterms:modified">{modified}</meta>
        {cover_manifest}
    </metadata>
    <manifest>
        {manifest_str}
    </manifest>
    <spine toc="ncx">
        {spine_str}
    </spine>
</package>"""
    (oebps / "content.opf").write_text(content_opf, encoding="utf-8")

    write_epub_zip(staging, output_epub)
    shutil.rmtree(staging)
    sz_mb = output_epub.stat().st_size / (1024 * 1024)
    print(f"[KINDLE-EPUB] Sucesso: {output_epub.name} ({sz_mb:.2f} MB, {len(files)} arquivos-fonte, "
          f"{len(chunk_bodies)} capítulos, {len(images)} imagens)")
    return True
