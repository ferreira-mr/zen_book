"""
azw3_converter.py — Conversor EPUB para AZW3 (Amazon KF8) local para BookForge
Utiliza o motor local do Calibre (`ebook-convert`) para gerar arquivos AZW3 100%
compatíveis com e-readers Kindle para transferência direta via USB.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

# Configurar encoding UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_ebook_convert() -> Optional[Path]:
    """
    Localiza o binário 'ebook-convert' do Calibre no sistema operacional.
    Verifica no PATH do sistema e em diretórios padrão comuns no Windows, macOS e Linux.
    """
    # 1. Verifica no PATH
    which_cmd = shutil.which("ebook-convert") or shutil.which("ebook-convert.exe")
    if which_cmd:
        return Path(which_cmd).resolve()

    # 2. Caminhos padrão no Windows
    if os.name == "nt":
        candidates = [
            Path(r"C:\Program Files\Calibre2\ebook-convert.exe"),
            Path(r"C:\Program Files (x86)\Calibre2\ebook-convert.exe"),
        ]
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidates.append(Path(local_app) / "Programs" / "Calibre2" / "ebook-convert.exe")
        program_files = os.environ.get("ProgramFiles")
        if program_files:
            candidates.append(Path(program_files) / "Calibre2" / "ebook-convert.exe")
        for cand in candidates:
            if cand.is_file():
                return cand.resolve()

    # 3. Caminhos padrão no macOS / Linux
    else:
        unix_candidates = [
            Path("/Applications/calibre.app/Contents/MacOS/ebook-convert"),
            Path("/usr/bin/ebook-convert"),
            Path("/usr/local/bin/ebook-convert"),
            Path.home() / ".local/bin/ebook-convert",
        ]
        for cand in unix_candidates:
            if cand.is_file():
                return cand.resolve()

    return None


def convert_epub_to_azw3(
    epub_path: Path,
    azw3_path: Optional[Path] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    cover_path: Optional[Path] = None,
    no_inline_toc: bool = True,
    output_profile: str = "kindle_pw3",
    verbose: bool = False,
) -> Tuple[bool, Optional[Path], str]:
    """
    Converte um arquivo EPUB para AZW3 (KF8) localmente usando o Calibre.

    Args:
        epub_path: Caminho do arquivo .epub de origem.
        azw3_path: Caminho do arquivo .azw3 de destino (opcional; se omitido, usa mesmo nome com .azw3).
        title: Título do livro para sobrescrever/garantir metadados (opcional).
        author: Autor do livro (opcional).
        cover_path: Caminho de imagem de capa dedicada (opcional).
        no_inline_toc: Se True, não gera índice HTML duplicado no fim do livro (o Kindle usa o sumário nativo).
        output_profile: Perfil de dispositivo do Calibre (padrão: 'kindle_pw3').
        verbose: Exibe saída detalhada do processo de conversão.

    Returns:
        (sucesso: bool, caminho_azw3: Optional[Path], mensagem: str)
    """
    epub_path = Path(epub_path).resolve()
    if not epub_path.is_file():
        msg = f"Arquivo EPUB não encontrado: {epub_path}"
        print(f"[AZW3] Erro: {msg}", file=sys.stderr)
        return False, None, msg

    converter_bin = find_ebook_convert()
    if not converter_bin:
        msg = (
            "Calibre ('ebook-convert') não foi encontrado no sistema.\n"
            "Instale o Calibre (https://calibre-ebook.com) ou verifique se está no PATH."
        )
        print(f"[AZW3] Erro: {msg}", file=sys.stderr)
        return False, None, msg

    if azw3_path is None:
        azw3_path = epub_path.with_suffix(".azw3")
    else:
        azw3_path = Path(azw3_path).resolve()

    azw3_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(converter_bin),
        str(epub_path),
        str(azw3_path),
        f"--output-profile={output_profile}",
    ]

    if no_inline_toc:
        cmd.append("--no-inline-toc")

    if cover_path is None:
        book_dir = epub_path.parent.parent if epub_path.parent.name == "dist" else epub_path.parent
        for cand in [
            book_dir / "assets" / "figures" / "capa.jpg",
            book_dir / "assets" / "figures" / "cover.jpg",
            book_dir / "assets" / "figures" / "capa.png",
            book_dir / "assets" / "figures" / "cover_1.jpeg",
        ]:
            if cand.is_file():
                cover_path = cand
                break

    if title:
        cmd.extend(["--title", title])
    if author:
        cmd.extend(["--authors", author])
    if cover_path and Path(cover_path).is_file():
        cmd.extend(["--cover", str(cover_path)])

    print(f"[AZW3] Convertendo EPUB para AZW3 (KF8 nativo)...")
    print(f"       Origem:  {epub_path.name} ({epub_path.stat().st_size / (1024*1024):.2f} MB)")
    print(f"       Destino: {azw3_path.name}")
    print(f"       Motor:   {converter_bin}")

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if res.returncode == 0 and azw3_path.exists() and azw3_path.stat().st_size > 0:
            size_mb = azw3_path.stat().st_size / (1024 * 1024)
            print(f"[AZW3] ✓ Conversão concluída com sucesso: {azw3_path.name} ({size_mb:.2f} MB)")
            return True, azw3_path, "Conversão concluída com sucesso."
        else:
            err_msg = res.stderr.strip() or res.stdout.strip()
            print(f"[AZW3] Falha na conversão (código {res.returncode}):\n{err_msg}", file=sys.stderr)
            return False, None, f"Falha na conversão: {err_msg}"

    except Exception as e:
        msg = f"Exceção ao executar conversão: {e}"
        print(f"[AZW3] {msg}", file=sys.stderr)
        return False, None, msg
