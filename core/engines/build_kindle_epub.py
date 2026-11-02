"""
build_kindle_epub.py — Gera edições EPUB 3 otimizadas para leitura no Amazon Kindle
a partir dos arquivos de capítulos traduzidos em LaTeX (.tex) e do manifest.json.
"""

from __future__ import annotations

import os
import re
import html
import uuid
import shutil
from pathlib import Path
import json
from typing import List, Tuple, Dict

from core.engines.epub_utils import (
    html_to_xhtml_fragment,
    xhtml_document,
    validate_xhtml,
    report_leaks,
    write_epub_zip,
)

def extract_macro_args(text: str, macro_name: str, num_args: int = 1) -> List[Tuple[int, int, List[str]]]:
    """Localiza chamadas de macro \\macro_name{arg1}{arg2}... com suporte rigoroso a chaves aninhadas."""
    pattern = re.compile(rf'\\{re.escape(macro_name)}\*?\b')
    results = []
    pos = 0
    while True:
        m = pattern.search(text, pos)
        if not m:
            break
        start_idx = m.start()
        cur = m.end()
        args = []
        valid = True
        for _ in range(num_args):
            while cur < len(text) and text[cur].isspace():
                cur += 1
            if cur >= len(text) or text[cur] != '{':
                valid = False
                break
            depth = 1
            arg_start = cur + 1
            cur += 1
            while cur < len(text) and depth > 0:
                if text[cur] == '{':
                    depth += 1
                elif text[cur] == '}':
                    depth -= 1
                cur += 1
            if depth != 0:
                valid = False
                break
            args.append(text[arg_start:cur - 1])
        if valid and len(args) == num_args:
            results.append((start_idx, cur, args))
            pos = cur
        else:
            pos = m.end()
    return results

def latex_to_html_body(tex_content: str, image_rel_prefix: str = "assets/images/") -> Tuple[str, List[Tuple[str, str]]]:
    """
    Converte código LaTeX dos capítulos para XHTML semântico, retornando o corpo HTML
    e uma lista de seções/títulos encontrados (nível, título).
    """
    toc_entries = []

    # 1. Remover comentários LaTeX puros
    tex = re.sub(r'(?<!\\)%.*$', '', tex_content, flags=re.MULTILINE)

    # 2. Remover macros de cabeçalho/numeração e espaçamentos
    for start, end, _ in reversed(extract_macro_args(tex, 'addcontentsline', 3)):
        tex = tex[:start] + '' + tex[end:]
    for start, end, _ in reversed(extract_macro_args(tex, 'thispagestyle', 1)):
        tex = tex[:start] + '' + tex[end:]
    for start, end, _ in reversed(extract_macro_args(tex, 'pagenumbering', 1)):
        tex = tex[:start] + '' + tex[end:]

    tex = re.sub(r'\\vspace\*?(?:\{[^}]*\}|\s*\\fill|\s*[0-9.]+[a-zA-Z]+)', '', tex)
    tex = re.sub(r'\\hspace\*?(?:\{[^}]*\}|\s*\\fill|\s*[0-9.]+[a-zA-Z]+)', '', tex)
    tex = re.sub(r'\\(?:clearpage|newpage|vfill|noindent|frontmatter|mainmatter|backmatter|tableofcontents|centering|raggedleft|raggedright)\b', '', tex)

    # Normalizar quebras de parágrafo LaTeX
    tex = re.sub(r'\\par\s*\}', r'}\n\n', tex)
    tex = re.sub(r'\\par\\(?:medskip|smallskip|bigskip)\b', '\n\n', tex)
    tex = re.sub(r'\\par\b', '\n\n', tex)
    tex = re.sub(r'\\newline\b', '<br/>', tex)

    # Fill-in-the-blank underlines (com ou sem hspace)
    tex = re.sub(r'\\underline\{(?:\\hspace\*?(?:\{[^}]*\}|[0-9.]+[a-zA-Z]+)|\s*)\}', '_______', tex)

    # TeX accents e caracteres especiais
    tex = re.sub(r'\\=[{]?u[}]?', 'ū', tex)
    tex = re.sub(r'\\=[{]?a[}]?', 'ā', tex)
    tex = re.sub(r'\\=[{]?(?:\\i\{\}|\\i|i)[}]?', 'ī', tex)
    tex = re.sub(r'\\i\{\}|\\i\b', 'i', tex)
    tex = tex.replace('{}', '')

    # Links com suporte a chaves aninhadas no rótulo
    for start, end, (url, label) in reversed(extract_macro_args(tex, 'href', 2)):
        tex = tex[:start] + f'<a href="{url}">{label}</a>' + tex[end:]
    tex = re.sub(r'\\url\{([^}]+)\}', r'<a href="\1">\1</a>', tex)

    # 3. Proteger chaves escapadas \{ e \}
    tex = tex.replace(r'\{', '@@LBRACE@@').replace(r'\}', '@@RBRACE@@')

    # 4. Símbolos LaTeX e tipografia
    SYMBOLS = [
        (r'\copyright', '©'),
        (r'\textregistered', '®'),
        (r'\textbullet', '•'),
        (r'\textordmasculine', 'º'),
        (r'\textordfeminine', 'ª'),
        (r'\textbackslash', '\\'),
        (r'\textasciitilde{}', '~'),
        (r'\textasciitilde', '~'),
        (r'\textasciicircum', '^'),
        (r'\textbar', '|'),
        (r'\textless', '&lt;'),
        (r'\textgreater', '&gt;'),
        (r'\dots', '…'),
        (r'\ldots', '…'),
        (r'\times', '×'),
        (r'\div', '÷'),
        (r'\rightarrow', '→'),
        (r'\leftarrow', '←'),
        (r'\uparrow', '↑'),
        (r'\downarrow', '↓'),
        (r'\pi', 'π'),
        (r'\Sigma', 'Σ'),
        (r'\alpha', 'α'),
        (r'\beta', 'β'),
        (r'\lambda', 'λ'),
        (r'\mu', 'μ'),
        (r'\infty', '∞'),
        (r'\ge', '≥'),
        (r'\le', '≤'),
        (r'\neq', '≠'),
        (r'\approx', '≈'),
        (r'\forall', '∀'),
        (r'\exists', '∃'),
        (r'\wedge', '∧'),
        (r'\circ', '°'),
        (r'\quad', ' '),
        (r'\qquad', '  '),
        (r'\%', '%'),
        (r'\&', '&amp;'),
        (r'\#', '#'),
        (r'\_', '_'),
        (r'\$', '$'),
    ]

    def clean_math(expr: str) -> str:
        expr = re.sub(r'([a-zA-Z0-9])\^\{?([a-zA-Z0-9+-]+)\}?', r'\1<sup>\2</sup>', expr)
        expr = re.sub(r'([a-zA-Z0-9])_\{?([a-zA-Z0-9+-]+)\}?', r'\1<sub>\2</sub>', expr)
        expr = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', expr)
        expr = re.sub(r'\\frac([0-9a-zA-Z])([0-9a-zA-Z])', r'\1/\2', expr)
        for sym, rep in SYMBOLS:
            expr = expr.replace(sym, rep)
        expr = expr.replace(r'\ ', ' ')
        return f'<span class="inline-math"><em>{expr.strip()}</em></span>'

    # 1. Proteger valores monetários antes de avaliar fórmulas matemáticas
    currency_tokens = []
    def save_curr(m):
        currency_tokens.append(m.group(0))
        return f"@@CURRENCY_{len(currency_tokens)-1}@@"
    tex = re.sub(r'\b(?:R|US|U\$|BRL)\$\s*\d+([.,]\d+)?\b', save_curr, tex)
    tex = re.sub(r'\$\s*\d+([.,]\d+)?\b', save_curr, tex)

    # 2. Fórmulas matemáticas inline ($...$ e \(...\))
    def repl_inline_math(m):
        return clean_math(m.group(1))

    tex = re.sub(r'(?<!\\)\$([^$\n]+?)\$', repl_inline_math, tex)
    tex = re.sub(r'\\\((.+?)\\\)', repl_inline_math, tex)

    # Restaurar valores monetários
    for c_idx, c_val in enumerate(currency_tokens):
        tex = tex.replace(f"@@CURRENCY_{c_idx}@@", c_val)

    for sym, rep in SYMBOLS:
        tex = tex.replace(sym, rep)

    tex = tex.replace("``", "“").replace("''", "”")
    tex = tex.replace("---", "—").replace("--", "–")

    # Grupos tipográficos comutadores de fonte { \Huge\bfseries\sffamily ... } com suporte a chaves aninhadas
    FONT_SWITCHES = r'\\(?:Huge|huge|LARGE|Large|large|normalsize|small|footnotesize|scriptsize|tiny|bfseries|sffamily|itshape|rmfamily|centering|raggedright|raggedleft)\b\s*'
    font_pattern = re.compile(r'\{(\s*' + FONT_SWITCHES + r')')
    while True:
        m = font_pattern.search(tex)
        if not m:
            break
        start_idx = m.start()
        depth = 1
        cur = m.start() + 1
        while cur < len(tex) and depth > 0:
            if tex[cur] == '{':
                depth += 1
            elif tex[cur] == '}':
                depth -= 1
            cur += 1
        if depth == 0:
            inner = tex[m.start() + 1:cur - 1]
            is_bold = '\\bfseries' in inner
            inner = re.sub(FONT_SWITCHES, '', inner).strip()
            rep = f'<strong>{inner}</strong>' if is_bold and inner else inner
            tex = tex[:start_idx] + rep + tex[cur:]
        else:
            break
    tex = re.sub(FONT_SWITCHES, '', tex)

    # Labels e referências
    tex = re.sub(r'\\ref\{([^}]+)\}', r'\1', tex)
    tex = re.sub(r'\\label\{[^}]*\}', '', tex)

    # Formatação inline padrão
    for _ in range(3):
        tex = re.sub(r'\\textbf\{([^{}]+)\}', r'<strong>\1</strong>', tex)
        tex = re.sub(r'\\(?:textit|emph)\{([^{}]+)\}', r'<em>\1</em>', tex)
        tex = re.sub(r'\\texttt\{([^{}]+)\}', r'<code>\1</code>', tex)
        tex = re.sub(r'\\underline\{\s*\}', r'<span class="blank">_______</span>', tex)
        tex = re.sub(r'\\underline\{([^{}]+)\}', r'<u>\1</u>', tex)
        tex = re.sub(r'\\textsuperscript\{([^{}]+)\}', r'<sup>\1</sup>', tex)

    # 5. Sistema de Armazenamento de Blocos Isolados (evita wrappers <p> inválidos)
    blocks_store = []
    def store_block(html_code: str) -> str:
        idx = len(blocks_store)
        blocks_store.append(html_code.strip())
        return f"\n\n@@BLOCK_{idx}@@\n\n"

    # Ambientes verbatim / lstlisting
    def repl_verbatim(m):
        return store_block(f'<pre class="kindle-code"><code>{html.escape(m.group(1).strip())}</code></pre>')
    tex = re.sub(r'\\begin\{(?:verbatim|lstlisting)\}(.*?)\\end\{(?:verbatim|lstlisting)\}', repl_verbatim, tex, flags=re.S)

    # Titlepage
    def repl_titlepage(m):
        inner = m.group(1)
        gm = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', inner)
        img_tag = ""
        if gm:
            img_name = Path(gm.group(1)).name
            img_tag = f'<div class="titlepage-cover"><img src="{image_rel_prefix}{img_name}" alt="Capa" class="kindle-img" /></div>'
        return store_block(img_tag) if img_tag else ""
    tex = re.sub(r'\\begin\{titlepage\}(.*?)\\end\{titlepage\}', repl_titlepage, tex, flags=re.S)

    # Display math
    def repl_disp_math(m):
        return store_block(f'<div class="math-block"><em>{clean_math(m.group(1).strip())}</em></div>')
    tex = re.sub(r'\\\[(.+?)\\\]', repl_disp_math, tex, flags=re.S)
    tex = re.sub(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', repl_disp_math, tex, flags=re.S)

    # Figuras: \bookfigure{caminho}{legenda} com suporte a chaves aninhadas na legenda
    for start, end, (path, caption) in reversed(extract_macro_args(tex, 'bookfigure', 2)):
        fname = Path(path.strip()).name
        cap = caption.strip()
        cap = re.sub(r'(?<![R\w\\])\$([^$\n]+?)\$(?!\w)', repl_inline_math, cap)
        for sym, rep in SYMBOLS:
            cap = cap.replace(sym, rep)
        fig_html = f'<figure class="kindle-figure"><img src="{image_rel_prefix}{fname}" alt="{html.escape(cap)}" class="kindle-img" /><figcaption>{cap}</figcaption></figure>'
        token = store_block(fig_html)
        tex = tex[:start] + token + tex[end:]

    # Ambiente figure
    def repl_fig_env(m):
        inner = m.group(1)
        cap_m = re.search(r'\\caption\{([^}]+)\}', inner)
        caption = cap_m.group(1) if cap_m else ""
        img_m = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', inner)
        if img_m:
            fname = Path(img_m.group(1)).name
            return store_block(f'<figure class="kindle-figure"><img src="{image_rel_prefix}{fname}" alt="{html.escape(caption)}" class="kindle-img" /><figcaption>{caption}</figcaption></figure>')
        return ""
    tex = re.sub(r'\\begin\{figure\}(.*?)\\end\{figure\}', repl_fig_env, tex, flags=re.S)

    # Inclusão de figuras isoladas (\includegraphics)
    def repl_incfig(m):
        fname = Path(m.group(1)).name
        return store_block(f'<div class="figure-container"><img src="{image_rel_prefix}{fname}" alt="Figura" class="kindle-img" /></div>' )
    tex = re.sub(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', repl_incfig, tex)

    # 1. Ambientes tabulares internos: tabular, tabularx, longtable
    def repl_tabular(m):
        inner = m.group(1).strip()
        while inner.startswith('{'):
            d, end_b = 0, 0
            for i, ch in enumerate(inner):
                if ch == '{': d += 1
                elif ch == '}':
                    d -= 1
                    if d == 0: end_b = i + 1; break
            inner = inner[end_b:].strip()
        inner = re.sub(r'\\(?:toprule|midrule|bottomrule|hline|addlinespace|small|footnotesize|centering|endfirsthead|endhead|endfoot|endlastfoot)\b', '', inner)
        rows = [r.strip() for r in re.split(r'\\\\', inner) if r.strip()]
        if not rows:
            return ""
        out_rows = ['<table class="kindle-table">']
        for i, row in enumerate(rows):
            cols = [c.strip() for c in row.split('&')]
            tag = 'th' if i == 0 else 'td'
            out_rows.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cols) + '</tr>')
        out_rows.append('</table>')
        return "\n".join(out_rows)

    tex = re.sub(r'\\begin\{(?:tabularx|longtable|tabular)\}(.*?)\\end\{(?:tabularx|longtable|tabular)\}', repl_tabular, tex, flags=re.S)

    # 2. Wrapper externo table: \begin{table}[H] ... \end{table}
    def repl_table_float(m):
        inner = m.group(1).strip()
        cap_m = re.search(r'\\caption\{([^}]+)\}', inner)
        caption = cap_m.group(1).strip() if cap_m else ""
        inner = re.sub(r'\\caption\{[^}]*\}', '', inner)
        inner = re.sub(r'\\label\{[^}]*\}', '', inner)
        cap_tag = f'<div class="table-caption">{caption}</div>\n' if caption else ""
        return store_block(f'<div class="table-wrapper">\n{inner.strip()}\n{cap_tag}</div>')

    tex = re.sub(r'\\begin\{table\}(?:\[[^\]]*\])?(.*?)\\end\{table\}', repl_table_float, tex, flags=re.S)

    # Listas aninhadas: processadas do nível mais interno para o mais externo
    pattern_list = re.compile(r'\\begin\{(itemize|enumerate)\}(?:\[[^\]]*\])?')
    while True:
        begins = list(pattern_list.finditer(tex))
        if not begins:
            break
        found = False
        for b_m in reversed(begins):
            tag_type = b_m.group(1)
            end_tag = f'\\end{{{tag_type}}}'
            end_pos = tex.find(end_tag, b_m.end())
            if end_pos == -1:
                continue
            intermediate = pattern_list.search(tex, b_m.end())
            if intermediate and intermediate.start() < end_pos:
                continue
            inner = tex[b_m.end():end_pos].strip()
            raw_items = [it.strip() for it in re.split(r'\\item\b', inner) if it.strip()]
            html_tag = "ol" if tag_type == "enumerate" else "ul"
            lis = []
            for it in raw_items:
                paras = [p.strip() for p in re.split(r'\n\s*\n|\\par\b', it) if p.strip()]
                if len(paras) <= 1:
                    item_content = paras[0] if paras else ""
                else:
                    item_content = "".join(f'<p>{p}</p>' if not p.startswith('@@BLOCK_') else p for p in paras)
                lis.append(f'<li>{item_content}</li>')
            list_html = f'<{html_tag} class="kindle-list">\n' + "\n".join(lis) + f'\n</{html_tag}>'
            placeholder = store_block(list_html)
            tex = tex[:b_m.start()] + placeholder + tex[end_pos + len(end_tag):]
            found = True
            break
        if not found:
            break

    # Descrições: \begin{description} \item[...] ... \end{description}
    def repl_desc_env(m):
        inner = m.group(1).strip()
        items = re.split(r'\\item\s*\[(.*?)\]', inner)
        out_dl = ['<dl class="kindle-description">']
        for k in range(1, len(items), 2):
            term = items[k].strip()
            defn = items[k + 1].strip() if k + 1 < len(items) else ""
            out_dl.append(f'<dt><strong>{term}</strong></dt>\n<dd>{defn}</dd>')
        out_dl.append('</dl>')
        return store_block("\n".join(out_dl))
    tex = re.sub(r'\\begin\{description\}(.*?)\\end\{description\}', repl_desc_env, tex, flags=re.S)

    # Ambientes pedagógicos e caixas de destaque
    def repl_learningoutcomes(m):
        return store_block(f'<aside class="kindle-box outcomes-box"><h4 class="box-title">Objetivos de Aprendizagem</h4>\n{m.group(1).strip()}\n</aside>')
    tex = re.sub(r'\\begin\{learningoutcomes\}(.*?)\\end\{learningoutcomes\}', repl_learningoutcomes, tex, flags=re.S)

    def repl_featurebox(m):
        title = m.group(1).strip()
        body = m.group(2).strip()
        return store_block(f'<aside class="kindle-box feature-box"><h4 class="box-title">{title}</h4>\n{body}\n</aside>')
    tex = re.sub(r'\\begin\{featurebox\}\{([^}]+)\}(.*?)\\end\{featurebox\}', repl_featurebox, tex, flags=re.S)

    tex = re.sub(r'\\begin\{sampletext\}(.*?)\\end\{sampletext\}', lambda m: store_block(f'<div class="kindle-sample">{m.group(1).strip()}</div>'), tex, flags=re.S)
    tex = re.sub(r'\\begin\{analysisnote\}(.*?)\\end\{analysisnote\}', lambda m: store_block(f'<div class="kindle-analysis">{m.group(1).strip()}</div>'), tex, flags=re.S)
    tex = re.sub(r'\\begin\{quote\}(.*?)\\end\{quote\}', lambda m: store_block(f'<blockquote class="kindle-quote">{m.group(1).strip()}</blockquote>'), tex, flags=re.S)

    BOX_NAMES = [('keyconcept', 'Conceito-Chave'), ('warningbox', 'Atenção'), ('examplebox', 'Exemplo'), ('notebox', 'Nota')]
    for b_env, b_def_title in BOX_NAMES:
        def make_repl(title_default):
            def _repl(m):
                opt_title = m.group(1) or title_default
                body = m.group(2).strip()
                return store_block(f'<aside class="kindle-box"><h4 class="box-title">{opt_title}</h4>\n{body}\n</aside>')
            return _repl
        tex = re.sub(rf'\\begin\{{{b_env}\}}(?:\[([^\]]+)\])?(.*?)\\end\{{{b_env}\}}', make_repl(b_def_title), tex, flags=re.S)

    # Títulos e divisões
    def repl_part(m):
        title = m.group(1).strip()
        toc_entries.append(("part", title))
        return store_block(f'<h1 class="part-title">{title}</h1>')
    tex = re.sub(r'\\part\*?\{([^}]+)\}', repl_part, tex)

    def repl_h1(m):
        title = m.group(1).strip()
        toc_entries.append(("chapter", title))
        return store_block(f'<h1 class="chapter-title">{title}</h1>')
    tex = re.sub(r'\\chapter\*?\{([^}]+)\}', repl_h1, tex)

    def repl_h2(m):
        title = m.group(1).strip()
        toc_entries.append(("section", title))
        return store_block(f'<h2 class="section-title">{title}</h2>')
    tex = re.sub(r'\\section\*?\{([^}]+)\}', repl_h2, tex)

    def repl_h3(m):
        title = m.group(1).strip()
        toc_entries.append(("subsection", title))
        return store_block(f'<h3 class="subsection-title">{title}</h3>')
    tex = re.sub(r'\\subsection\*?\{([^}]+)\}', repl_h3, tex)

    def repl_h4(m):
        title = m.group(1).strip()
        return store_block(f'<h4 class="subsubsection-title">{title}</h4>')
    tex = re.sub(r'\\(?:subsubsection|paragraph)\*?\{([^}]+)\}', repl_h4, tex)

    # Wrappers de alinhamento
    def repl_center(m):
        return store_block(f'<div class="kindle-center">\n{m.group(1).strip()}\n</div>')
    tex = re.sub(r'\\begin\{(?:center|flushleft|flushright)\}(.*?)\\end\{(?:center|flushleft|flushright)\}', repl_center, tex, flags=re.S)

    # Parágrafos normais
    blocks = re.split(r'\n\s*\n|\\par\b', tex)
    out_blocks = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if re.match(r'^@@BLOCK_\d+@@$', b):
            out_blocks.append(b)
        else:
            b = re.sub(r'\\\\', '<br/>', b)
            if b.startswith('{') and b.endswith('}'):
                b = b[1:-1].strip()
            out_blocks.append(f'<p>{b}</p>')

    full_html = "\n\n".join(out_blocks)

    # Restaurar blocos hierarquicamente
    while '@@BLOCK_' in full_html:
        for idx in range(len(blocks_store) - 1, -1, -1):
            full_html = full_html.replace(f'@@BLOCK_{idx}@@', blocks_store[idx])

    # Limpeza final de tags vazias e chaves TeX residuais
    full_html = re.sub(r'<p>\s*</p>', '', full_html)
    full_html = re.sub(r'\{([a-zA-Z0-9\s.,;:()—–"\'áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ-]+)\}', r'\1', full_html)
    full_html = full_html.replace('@@LBRACE@@', '{').replace('@@RBRACE@@', '}')

    return full_html, toc_entries


KINDLE_CSS = """/* Kindle & E-Reader Optimized Stylesheet */
@namespace "http://www.w3.org/1999/xhtml";

body {
    margin: 4% 5%;
    line-height: 1.45;
    text-align: justify;
    color: #111111;
    font-size: 1.05em;
    font-family: "Bookerly", "Georgia", "Palatino", serif;
}

h1, h2, h3, h4, h5, h6 {
    font-family: sans-serif;
    line-height: 1.25;
    text-align: left;
    page-break-after: avoid;
    break-after: avoid;
    color: #000000;
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
    text-indent: 1.2em;
}

h1 + p, h2 + p, h3 + p, h4 + p, .titlepage-cover + p {
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

div.kindle-center {
    text-align: center;
    margin: 1em 0;
}

/* Listas */
ul.kindle-list, ol.kindle-list {
    margin: 0.6em 0 0.8em 1.5em;
    padding-left: 0;
}

li {
    margin-bottom: 0.35em;
}

dl.kindle-description {
    margin: 1em 0;
}

dl.kindle-description dt {
    font-weight: bold;
    margin-top: 0.8em;
}

dl.kindle-description dd {
    margin-left: 1.2em;
    margin-bottom: 0.6em;
}

/* Imagens */
figure.kindle-figure, div.figure-container, div.titlepage-cover {
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

figcaption, div.table-caption {
    font-size: 0.85em;
    margin-top: 0.4em;
    color: #333333;
    font-family: sans-serif;
    text-align: center;
}

/* Tabelas */
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

/* Matemática */
span.inline-math {
    font-family: "Cambria Math", "Latin Modern Math", serif;
}

div.math-block {
    margin: 1em 0;
    text-align: center;
    font-family: "Cambria Math", "Latin Modern Math", serif;
    font-size: 1.1em;
}

span.blank {
    letter-spacing: 0.1em;
}

/* Código */
code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.9em;
    background-color: #f2f2f2;
    padding: 1px 3px;
    border-radius: 2px;
}

pre.kindle-code {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 0.85em;
    line-height: 1.35;
    background-color: #f2f2f2;
    padding: 0.8em 1em;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 1.2em 0;
}

pre.kindle-code code {
    background-color: transparent;
    padding: 0;
}
"""


def build_epub_for_book(book_dir_or_slug, output_epub: Path = None, root_dir: Path = Path(".")) -> Path:
    """Gera edição EPUB 3 otimizada para Amazon Kindle a partir de fontes LaTeX."""
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

    title = manifest.get("bookTitleTranslated", manifest.get("bookTitleOriginal", manifest.get("title", book_slug)))
    author = manifest.get("author", "Autor Desconhecido")
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_DNS, book_slug)}"

    # Pasta de staging
    epub_staging = work_dir / "_epub_staging"
    if epub_staging.exists():
        shutil.rmtree(epub_staging)

    meta_inf = epub_staging / "META-INF"
    oebps = epub_staging / "OEBPS"
    oebps_images = oebps / "assets" / "images"
    oebps_images.mkdir(parents=True, exist_ok=True)
    meta_inf.mkdir(parents=True, exist_ok=True)

    # 1. mimetype
    (epub_staging / "mimetype").write_text("application/epub+zip", encoding="ascii")

    # 2. container.xml
    (meta_inf / "container.xml").write_text("""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>""", encoding="utf-8")

    # 3. CSS Kindle
    (oebps / "kindle.css").write_text(KINDLE_CSS, encoding="utf-8")

    # 4. Copiar imagens existentes
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
                is_cover = "cover" in img_file.name.lower() or "capa" in img_file.name.lower()
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
    xhtml_docs: Dict[str, str] = {}

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

    if not chapters and chapters_dir.exists():
        for p in sorted(chapters_dir.glob("*.tex")):
            chapters.append({"id": p.stem, "titleTranslated": p.stem.replace("-", " ").title(), "_resolved_path": p})

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

        body_xhtml = html_to_xhtml_fragment(html_body)
        doc = xhtml_document(
            title=doc_title,
            body=f'<section class="chapter-content">\n{body_xhtml}\n</section>',
            css_href="kindle.css",
            body_attrs='epub:type="bodymatter"'
        )
        (oebps / xhtml_filename).write_text(doc, encoding="utf-8")
        xhtml_docs[xhtml_filename] = doc

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
    nav_xhtml = xhtml_document(
        title="Sumário",
        body=f"""    <nav epub:type="toc" id="toc">
        <h1>Sumário</h1>
        <ol>
            {"".join(nav_toc_items)}
        </ol>
    </nav>""",
        css_href="kindle.css"
    )
    (oebps / "nav.xhtml").write_text(nav_xhtml, encoding="utf-8")
    xhtml_docs["nav.xhtml"] = nav_xhtml
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

    # Validação XML e verificação de vazamento
    errors = [err for err in (validate_xhtml(c, n) for n, c in xhtml_docs.items()) if err]
    if errors:
        shutil.rmtree(epub_staging, ignore_errors=True)
        raise RuntimeError("XHTML inválido gerado para o EPUB:\n  " + "\n  ".join(errors[:10]))
    report_leaks(xhtml_docs, tag="LATEX-EPUB")

    # 8. content.opf
    cover_meta = f'<meta name="cover" content="{cover_image_id}"/>' if cover_image_id else ""
    manifest_str = "\n        ".join(manifest_items + image_manifest_entries)
    spine_str = "\n        ".join(spine_items)

    modified = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0" xml:lang="pt-BR">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">{book_id}</dc:identifier>
        <dc:title>{html.escape(title)}</dc:title>
        <dc:creator>{html.escape(author)}</dc:creator>
        <dc:language>pt-BR</dc:language>
        <meta property="dcterms:modified">{modified}</meta>
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

    # 9. Compactar para arquivo .epub
    if output_epub:
        final_epub = Path(output_epub)
        final_epub.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = work_dir / "dist"
        output_dir.mkdir(parents=True, exist_ok=True)
        final_epub = output_dir / f"{book_slug}-kindle.epub"

    write_epub_zip(epub_staging, final_epub)
    shutil.rmtree(epub_staging)

    sz_mb = final_epub.stat().st_size / (1024 * 1024)
    print(f"EPUB Kindle gerado com sucesso: {final_epub.name} ({sz_mb:.2f} MB, {len(chapters)} capítulos)")
    return final_epub

if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "ai-native-software-engineering"
    build_epub_for_book(slug)
