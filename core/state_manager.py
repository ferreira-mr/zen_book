"""
state_manager.py — Gerenciador de Estado, Manifesto e Progresso dos Livros
Mantém manifest.json, PROGRESS.md e estatísticas de cada obra em library/<slug>/state/
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple

def load_manifest(book_dir: Path) -> Dict[str, Any]:
    manifest_path = Path(book_dir) / "state" / "manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"total_pages": 0, "completed_pages": 0, "pages": [], "chapters": []}

def get_manifest_stats(manifest: Dict[str, Any]) -> Tuple[int, int]:
    """
    Normaliza a contagem de (total, concluídos) suportando múltiplos formatos de manifesto.
    """
    # 1. Total explícito de páginas
    total = manifest.get("total_pages") or manifest.get("total_pdf_pages")
    completed = manifest.get("completed_pages")

    # 2. Se há lista de páginas
    pages = manifest.get("pages", [])
    if pages:
        if total is None:
            total = len(pages)
        if completed is None:
            completed = len([p for p in pages if isinstance(p, dict) and p.get("status") in ["done", "completed", "verified"]])

    # 3. Se há lista de capítulos
    chapters = manifest.get("chapters", [])
    if chapters and (total is None or total == 0):
        total = len(chapters)
        completed = len([c for c in chapters if isinstance(c, dict) and c.get("status") in ["verified", "completed", "done"]])

    # 4. Se há lista de partes (ex: história da computação)
    parts = manifest.get("parts", [])
    if parts and (total is None or total == 0):
        total = len(parts)
        completed = len([p for p in parts if isinstance(p, dict) and p.get("status") in ["done", "verified", "completed"]])
        if completed == 0 and manifest.get("book"):  # Livro 100% concluído
            completed = total

    # 5. Se há lista de unidades (ex: writing-guide-with-handbook)
    units = manifest.get("units", [])
    if units and (total is None or total == 0):
        total = len(units)
        completed = len([u for u in units if isinstance(u, dict) and u.get("status") in ["verified", "completed", "done"]])

    total = total or 0
    completed = completed if completed is not None else (total if manifest.get("status") == "completed" else 0)
    return (total, completed)

def save_manifest(book_dir: Path, manifest: Dict[str, Any]):
    manifest_path = Path(book_dir) / "state" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

def update_progress_md(book_dir: Path, title: str, author: str = "", engine: str = "typst"):
    manifest = load_manifest(book_dir)
    total, done = get_manifest_stats(manifest)
    pct = (done / total * 100) if total > 0 else 0.0

    lines = [
        f"# Progresso Editorial: *{title}*",
        f"- **Autor**: {author or 'Não informado'}",
        f"- **Motor de Editoração**: `{engine}`",
        f"- **Total de Unidades**: {total}",
        f"- **Concluídos**: {done} ({pct:.1f}%)",
        "",
        "## Status dos Entregáveis em `dist/`:",
    ]

    dist_dir = Path(book_dir) / "dist"
    if dist_dir.exists():
        for f in sorted(dist_dir.iterdir()):
            if f.is_file() and f.suffix in [".pdf", ".epub"]:
                sz_mb = f.stat().st_size / (1024 * 1024)
                lines.append(f"- `dist/{f.name}` ({sz_mb:.2f} MB)")
    else:
        lines.append("- *(Nenhum entregável gerado ainda)*")

    prog_file = Path(book_dir) / "state" / "PROGRESS.md"
    prog_file.parent.mkdir(parents=True, exist_ok=True)
    prog_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
