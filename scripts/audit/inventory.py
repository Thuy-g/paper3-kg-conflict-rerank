"""Read-only inventory of third-party repositories (stdlib only).

For each repository directory given on the command line this script reports:
licence file(s) and a best-effort licence identification, the HEAD commit, a
directory tree (depth-limited, with file counts), lines of code per Python
file, and an index of every ``def``/``class`` with its line number.

Upstream code is never imported or executed: Python files are only parsed
with :func:`ast.parse`. Run with ``python -I`` from the project root, e.g.::

    python3.11 -I scripts/audit/inventory.py third_party/* --out logs/audit
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import Counter
from pathlib import Path

# Ordered (identifier, required substrings) pairs; the first fully matching entry wins.
LICENSE_SIGNATURES: list[tuple[str, tuple[str, ...]]] = [
    ("Apache-2.0", ("apache license", "version 2.0")),
    ("MIT", ("permission is hereby granted, free of charge",)),
    ("GPL-3.0", ("gnu general public license", "version 3")),
    ("GPL-2.0", ("gnu general public license", "version 2")),
    ("AGPL-3.0", ("gnu affero general public license",)),
    ("LGPL", ("gnu lesser general public license",)),
    ("BSD-3-Clause", ("redistribution and use in source and binary forms", "neither the name")),
    ("BSD-2-Clause", ("redistribution and use in source and binary forms",)),
    ("CC-BY-4.0", ("creative commons attribution 4.0",)),
    ("CC-BY-SA-4.0", ("attribution-sharealike 4.0",)),
    ("CC-BY-NC-4.0", ("attribution-noncommercial 4.0",)),
]

SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints"}


def identify_license(text: str) -> str:
    """Return a best-effort licence identifier for a licence text."""
    low = " ".join(text.lower().split())
    for ident, needles in LICENSE_SIGNATURES:
        if all(n in low for n in needles):
            return ident
    return "UNKNOWN"


def copyright_lines(text: str, limit: int = 3) -> list[str]:
    """Return up to ``limit`` lines that look like copyright statements."""
    out = [
        ln.strip()
        for ln in text.splitlines()
        if "copyright" in ln.lower() and any(c.isdigit() for c in ln)
    ]
    return out[:limit]


def git_head(repo: Path) -> dict[str, str]:
    """Return HEAD hash, date and subject (git is called read-only)."""
    fmt = "%H%n%ad%n%an%n%s"
    try:
        res = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", f"--format={fmt}", "--date=iso"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    parts = res.stdout.strip().split("\n")
    keys = ["hash", "date", "author", "subject"]
    return dict(zip(keys, parts, strict=False))


def iter_files(repo: Path):
    """Yield files below ``repo`` skipping VCS and cache directories."""
    for path in sorted(repo.rglob("*")):
        if any(part in SKIP_DIRS for part in path.relative_to(repo).parts):
            continue
        if path.is_file():
            yield path


def tree(repo: Path, max_depth: int) -> list[str]:
    """Return an indented directory listing with file counts per directory."""
    lines: list[str] = []

    def walk(d: Path, depth: int) -> None:
        entries = sorted(p for p in d.iterdir() if p.name not in SKIP_DIRS)
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        for f in files:
            lines.append(f"{'  ' * depth}{f.name}  ({f.stat().st_size:,} B)")
        for sub in dirs:
            n_files = sum(1 for _ in iter_files(sub))
            lines.append(f"{'  ' * depth}{sub.name}/  [{n_files} files]")
            if depth + 1 < max_depth:
                walk(sub, depth + 1)

    walk(repo, 0)
    return lines


def python_symbols(path: Path) -> tuple[int, list[tuple[int, str, str]], str | None]:
    """Parse a Python file; return (non-empty LOC, [(line, kind, qualname)], parse_error)."""
    src = path.read_text(encoding="utf-8", errors="replace")
    loc = sum(1 for ln in src.splitlines() if ln.strip())
    try:
        mod = ast.parse(src)
    except SyntaxError as exc:  # report, never execute
        return loc, [], f"SyntaxError: {exc}"
    symbols: list[tuple[int, str, str]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                name = f"{prefix}{child.name}"
                symbols.append((child.lineno, "class", name))
                visit(child, name + ".")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                symbols.append((child.lineno, "def", name))
                visit(child, name + ".")

    visit(mod, "")
    return loc, sorted(symbols), None


def inventory(repo: Path, max_depth: int) -> dict:
    """Build the inventory record for one repository."""
    lic_files = sorted(
        p
        for p in repo.iterdir()
        if p.is_file() and p.name.upper().startswith(("LICENSE", "LICENCE", "COPYING"))
    )
    licenses = []
    for lf in lic_files:
        text = lf.read_text(encoding="utf-8", errors="replace")
        licenses.append(
            {
                "file": lf.name,
                "id_guess": identify_license(text),
                "copyright": copyright_lines(text),
            }
        )
    ext_counts: Counter[str] = Counter()
    py: dict[str, dict] = {}
    for f in iter_files(repo):
        ext_counts[f.suffix.lower() or "<none>"] += 1
        if f.suffix == ".py":
            loc, syms, err = python_symbols(f)
            py[str(f.relative_to(repo))] = {"loc": loc, "symbols": syms, "parse_error": err}
    return {
        "repo": repo.name,
        "head": git_head(repo),
        "licenses": licenses,
        "file_types": dict(ext_counts.most_common()),
        "python_loc_total": sum(v["loc"] for v in py.values()),
        "python_files": py,
        "tree": tree(repo, max_depth),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repos", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True, help="output directory for JSON/TSV files")
    ap.add_argument("--depth", type=int, default=3)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for repo in args.repos:
        if not repo.is_dir():
            continue
        inv = inventory(repo, args.depth)
        (args.out / f"{repo.name}.inventory.json").write_text(
            json.dumps(inv, indent=1, ensure_ascii=False)
        )
        with (args.out / f"{repo.name}.symbols.tsv").open("w", encoding="utf-8") as fh:
            for rel, info in sorted(inv["python_files"].items()):
                for line, kind, name in info["symbols"]:
                    fh.write(f"{rel}\t{line}\t{kind}\t{name}\n")
        lic = (
            ", ".join(f"{x['file']}={x['id_guess']}" for x in inv["licenses"]) or "NO LICENSE FILE"
        )
        print(
            f"{repo.name:20s} head={inv['head'].get('hash', '?')[:12]} licence=[{lic}] "
            f"py_files={len(inv['python_files'])} py_loc={inv['python_loc_total']} "
            f"types={inv['file_types']}"
        )


if __name__ == "__main__":
    main()
