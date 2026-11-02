"""
epub_utils.py — Utilitários compartilhados pelos geradores de EPUB do BookForge.

- Conversão de HTML5 (serialização do Typst) para XHTML bem-formado (exigido pelo EPUB 3).
- Validação XML de cada documento XHTML antes do empacotamento.
- Detecção de vazamento de marcação-fonte (comandos LaTeX / chamadas Typst) no texto visível.
- Empacotamento do arquivo .epub (mimetype sem compressão em primeiro lugar).
"""

from __future__ import annotations

import html
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

MATHML_NS = "http://www.w3.org/1998/Math/MathML"

_VOID_TAGS = ("area", "base", "br", "col", "embed", "hr", "img", "input",
              "link", "meta", "param", "source", "track", "wbr")
_VOID_RE = re.compile(r"<(" + "|".join(_VOID_TAGS) + r")\b((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)\s*/?>", re.I)
# Entidades nomeadas do HTML que não existem em XML puro
_NAMED_ENTITY_RE = re.compile(r"&(?!(?:amp|lt|gt|quot|apos);)([a-zA-Z][a-zA-Z0-9]*);")
_BARE_AMP_RE = re.compile(r"&(?!(?:[a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)")


def html_to_xhtml_fragment(fragment: str) -> str:
    """Converte um fragmento HTML5 em XHTML bem-formado."""
    # Elementos vazios precisam ser auto-fechados
    fragment = _VOID_RE.sub(lambda m: f"<{m.group(1)}{m.group(2).rstrip()}/>", fragment)
    # Entidades nomeadas HTML (&nbsp; etc.) -> caracteres reais
    fragment = _NAMED_ENTITY_RE.sub(lambda m: html.unescape(m.group(0)) if html.unescape(m.group(0)) != m.group(0) else "&amp;" + m.group(1) + ";", fragment)
    # E comercial solto
    fragment = _BARE_AMP_RE.sub("&amp;", fragment)
    # MathML precisa de namespace explícito em XHTML
    fragment = re.sub(r"<math(?![^>]*\bxmlns=)", f'<math xmlns="{MATHML_NS}"', fragment)
    return fragment


def xhtml_document(title: str, body: str, css_href: str = "kindle.css", body_attrs: str = "") -> str:
    """Monta um documento XHTML 5 completo para EPUB 3."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html>\n"
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
        'xml:lang="pt-BR" lang="pt-BR">\n'
        "<head>\n"
        '    <meta charset="UTF-8"/>\n'
        f"    <title>{html.escape(title)}</title>\n"
        f'    <link rel="stylesheet" type="text/css" href="{css_href}"/>\n'
        "</head>\n"
        f"<body{(' ' + body_attrs) if body_attrs else ''}>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def validate_xhtml(content: str, name: str = "") -> str | None:
    """Retorna None se o XHTML for XML bem-formado; caso contrário, a mensagem de erro."""
    try:
        ET.fromstring(content.encode("utf-8"))
        return None
    except ET.ParseError as e:
        line_no = e.position[0] if hasattr(e, "position") else 0
        lines = content.splitlines()
        ctx = lines[line_no - 1][:200] if 0 < line_no <= len(lines) else ""
        return f"{name}: {e} :: {ctx}"


# Padrões que indicam código-fonte vazado no texto visível pelo leitor
_LEAK_PATTERNS = {
    "comando LaTeX": re.compile(r"\\(?:begin|end|text[a-z]+|emph|section|chapter|item|frac|href|url|vspace|hspace|"
                                r"small|large|Large|Huge|bfseries|sffamily|itshape|centering|noindent|par\b|"
                                r"includegraphics|caption|label|ref|cite|footnote|quad|times|rightarrow)\b"),
    "chamada Typst": re.compile(r"#(?:text|align|block|box|grid|table|strong|emph|link|image|figure|place|rect|"
                                r"set|show|let|import|include|v|h|pad|stack|columns|par|smallcaps|underline|"
                                r"linebreak|pagebreak|context|for|if|sym)\b[\(\[\s.]"),
    "argumento nomeado Typst": re.compile(r"\b(?:fill|inset|stroke|weight|tracking|radius|columns|font):\s*"
                                          r"(?:rgb|\(|\d|\"|cor-|font-|white|black|none|auto)"),
}


def visible_text(xhtml: str) -> str:
    """Extrai o texto visível ao leitor (ignora <pre>/<code>/<math>, onde código é legítimo)."""
    s = re.sub(r"(?is)<head.*?</head>", " ", xhtml)
    s = re.sub(r"(?is)<(pre|code|math)\b.*?</\1>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(s)


def find_markup_leaks(xhtml: str, max_samples: int = 5) -> dict[str, list[str]]:
    """Procura sintaxe LaTeX/Typst remanescente no texto visível."""
    text = visible_text(xhtml)
    found: dict[str, list[str]] = {}
    for label, pat in _LEAK_PATTERNS.items():
        for m in pat.finditer(text):
            lst = found.setdefault(label, [])
            if len(lst) < max_samples:
                a, b = max(0, m.start() - 40), min(len(text), m.end() + 40)
                lst.append(re.sub(r"\s+", " ", text[a:b]).strip())
    return found


def report_leaks(docs: dict[str, str], tag: str = "EPUB") -> int:
    """Imprime um relatório de vazamentos de marcação; retorna o total de documentos afetados."""
    affected = 0
    for name, content in docs.items():
        leaks = find_markup_leaks(content)
        if leaks:
            affected += 1
            print(f"[{tag}] AVISO: possível marcação-fonte visível em {name}:")
            for label, samples in leaks.items():
                for s in samples:
                    print(f"         - {label}: …{s}…")
    return affected


def write_epub_zip(staging: Path, output_epub: Path) -> None:
    """Empacota a pasta de staging em .epub (mimetype sem compressão como primeira entrada)."""
    output_epub = Path(output_epub)
    output_epub.parent.mkdir(parents=True, exist_ok=True)
    if output_epub.exists():
        output_epub.unlink()
    with zipfile.ZipFile(output_epub, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for root, _, files in os.walk(staging):
            for file in sorted(files):
                full_path = Path(root) / file
                rel_path = full_path.relative_to(staging).as_posix()
                if rel_path == "mimetype":
                    continue
                zf.write(full_path, rel_path, compress_type=zipfile.ZIP_DEFLATED)
