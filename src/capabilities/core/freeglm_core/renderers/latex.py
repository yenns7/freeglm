"""Render LaTeX (.tex) files by compiling to PDF then rendering pages.

Falls back to syntax-highlighted source on compilation failure.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

from shared.syscmd import which_tool


class _CompileError(RuntimeError):
    """Raised when LaTeX compilation fails, triggering source fallback."""


def _pdf_producer(tex_file: str, src_dir: str, compiler: str):
    """Build a produce(dest_pdf) closure that compiles `tex_file` to PDF."""

    def _compile(dest_pdf: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            shutil.copytree(src_dir, tmpdir, dirs_exist_ok=True)

            tex_basename = os.path.relpath(tex_file, src_dir)
            tex_in_tmp = os.path.join(tmpdir, tex_basename)
            if not os.path.isfile(tex_in_tmp):
                shutil.copy2(tex_file, tex_in_tmp)

            needs_bib = _needs_bibliography(tex_in_tmp)
            job_name = os.path.splitext(os.path.basename(tex_in_tmp))[0]
            work_dir = os.path.dirname(tex_in_tmp) or tmpdir

            # First pass; re-run after bibtex and once more for cross-refs.
            _run_compiler(compiler, tex_in_tmp, work_dir)
            if needs_bib:
                _run_bibtex(job_name, work_dir)
                _run_compiler(compiler, tex_in_tmp, work_dir)
            proc = _run_compiler(compiler, tex_in_tmp, work_dir)

            pdf_path = os.path.join(work_dir, job_name + ".pdf")
            if not os.path.isfile(pdf_path):
                raise _CompileError(_parse_log_errors(work_dir, job_name, proc))
            shutil.copy2(pdf_path, dest_pdf)

    return _compile


def to_pdf(path: str, **opts: Any) -> str:
    """Compile a LaTeX source/project to a cached intermediate PDF, returning its path."""
    from freeglm_core.renderers import cached_pdf

    tex_file, src_dir = _resolve_input(path)
    compiler = _find_compiler()
    if compiler is None:
        raise RuntimeError("No LaTeX compiler found (pdflatex/xelatex/lualatex)")
    return cached_pdf(tex_file, _pdf_producer(tex_file, src_dir, compiler), cache_inputs=_source_files(src_dir))


def render(path: str, **opts: Any) -> list:
    from freeglm_core.renderers import render_via_pdf

    tex_file, src_dir = _resolve_input(path)
    opts.setdefault("doc_type", "LaTeX")

    compiler = _find_compiler()
    if compiler is None:
        return _fallback(tex_file, "No LaTeX compiler found (pdflatex/xelatex/lualatex)")

    try:
        return render_via_pdf(
            tex_file, _pdf_producer(tex_file, src_dir, compiler), cache_inputs=_source_files(src_dir), **opts
        )
    except _CompileError as e:
        return _fallback(tex_file, f"LaTeX compilation failed:\n{e}")


# Extensions whose changes invalidate the compiled-PDF cache.
_SOURCE_EXTS = {".tex", ".bib", ".sty", ".cls", ".bst", ".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"}


def _source_files(src_dir: str) -> list[str]:
    """All LaTeX source/asset files under a project dir (for cache keying)."""
    found = []
    for root, _dirs, names in os.walk(src_dir):
        for name in names:
            if os.path.splitext(name)[1].lower() in _SOURCE_EXTS:
                found.append(os.path.join(root, name))
    return found


def _resolve_input(path: str) -> tuple[str, str]:
    """Resolve input path to (tex_file, source_directory).

    Accepts a .tex file or a directory containing .tex files.
    """
    path = os.path.abspath(path)

    if os.path.isfile(path):
        return path, os.path.dirname(path)

    if os.path.isdir(path):
        tex_file = _find_main_tex(path)
        if tex_file:
            return tex_file, path
        raise RuntimeError(f"No .tex file with \\documentclass found in: {path}")

    raise RuntimeError(f"Path does not exist: {path}")


_PREFERRED_NAMES = ("main.tex", "paper.tex", "thesis.tex", "document.tex", "article.tex")


def _find_main_tex(directory: str) -> str | None:
    """Find the main .tex file in a directory by looking for \\documentclass."""
    for name in _PREFERRED_NAMES:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and _has_documentclass(candidate):
            return candidate

    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".tex"):
            candidate = os.path.join(directory, fname)
            if _has_documentclass(candidate):
                return candidate

    return None


def _has_documentclass(path: str) -> bool:
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read(8192)
        return bool(re.search(r"\\documentclass", content))
    except Exception:
        return False


def _needs_bibliography(tex_path: str) -> bool:
    try:
        with open(tex_path, "r", errors="replace") as f:
            content = f.read()
        return bool(
            re.search(
                r"\\bibliography\b|\\addbibresource\b|\\printbibliography\b",
                content,
            )
        )
    except Exception:
        return False


def _find_compiler() -> str | None:
    for cmd in ("pdflatex", "xelatex", "lualatex"):
        path = which_tool(cmd)
        if path:
            return path
    return None


def _run_compiler(compiler: str, tex_path: str, work_dir: str):
    return subprocess.run(
        [compiler, "-interaction=nonstopmode", "-halt-on-error", "-output-directory", work_dir, tex_path],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=work_dir,
    )


def _run_bibtex(job_name: str, work_dir: str):
    bibtex = which_tool("bibtex")
    if not bibtex:
        return
    try:
        subprocess.run(
            [bibtex, job_name],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=work_dir,
        )
    except Exception:
        pass


def _parse_log_errors(work_dir: str, job_name: str, proc) -> str:
    log_path = os.path.join(work_dir, job_name + ".log")
    if os.path.isfile(log_path):
        try:
            with open(log_path, "r", errors="replace") as f:
                log = f.read()
            errors = [line for line in log.split("\n") if line.startswith("!")]
            if errors:
                return "\n".join(errors[:5])
        except Exception:
            pass
    return (proc.stdout or "")[-500:]


def _fallback(tex_path: str, error_msg: str) -> list:
    """Fall back to syntax-highlighted source code rendering."""
    header = {"type": "text", "text": f"[LaTeX render fallback] {error_msg}"}
    try:
        from freeglm_core.renderers.code import render as code_render

        images = code_render(tex_path)
        return [header] + images
    except Exception:
        try:
            with open(tex_path, "r", errors="replace") as f:
                source = f.read(5000)
            return [header, {"type": "text", "text": source}]
        except Exception:
            return [header]
