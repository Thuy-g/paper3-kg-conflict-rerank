"""Verify `path:line` code citations in Markdown reports (stdlib only).

A citation is a backticked span such as ``third_party/Repo/pkg/mod.py:120`` or
``third_party/Repo/pkg/mod.py:120-135``. For each citation the checker verifies
that (1) the file exists, (2) the line range exists, and (3) a symbol named in
the same Markdown line is present in the cited range. The symbol that is tested
first is the nearest backticked identifier *before* the citation (falling back
to the nearest one after it); if that fails, any other identifier on the line
is tried and the result is reported as WEAK.

Statuses: OK, WEAK (only a non-adjacent identifier matched), EXISTS (no
identifier on the line to test), MISSING_FILE, OUT_OF_RANGE, SYMBOL_NOT_FOUND.

Usage (from the project root)::

    python3.11 -I scripts/audit/check_citations.py reports/01_*.md reports/02_*.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BACKTICK = re.compile(r"`([^`]+)`")
CITATION = re.compile(r"^(third_party/[^\s:`]+):(\d+)(?:[-–](\d+))?$")
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(\(\))?$")


@dataclass
class Result:
    report: str
    lineno: int
    citation: str
    status: str
    detail: str = ""


def candidate_symbols(spans: list[str], idx: int) -> list[str]:
    """Return identifiers on the line ordered by proximity (preceding first)."""
    ids = [(i, s) for i, s in enumerate(spans) if IDENTIFIER.match(s) and "/" not in s]
    before = [s for i, s in reversed(ids) if i < idx]
    after = [s for i, s in ids if i > idx]
    ordered = before[:1] + after[:1] + before[1:] + after[1:]
    seen: list[str] = []
    for s in ordered:
        if s not in seen:
            seen.append(s)
    return seen


def check_line(report: str, lineno: int, text: str, root: Path) -> list[Result]:
    spans = BACKTICK.findall(text)
    out: list[Result] = []
    for idx, span in enumerate(spans):
        m = CITATION.match(span.strip())
        if not m:
            continue
        rel, start, end = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
        path = root / rel
        if not path.is_file():
            out.append(Result(report, lineno, span, "MISSING_FILE"))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if start < 1 or end > len(lines) or end < start:
            out.append(Result(report, lineno, span, "OUT_OF_RANGE", f"file has {len(lines)} lines"))
            continue
        cited = "\n".join(lines[start - 1 : end])
        symbols = candidate_symbols(spans, idx)
        if not symbols:
            out.append(Result(report, lineno, span, "EXISTS"))
            continue
        names = [s.removesuffix("()").split(".")[-1] for s in symbols]
        if names[0] in cited:
            out.append(Result(report, lineno, span, "OK", symbols[0]))
        elif any(n in cited for n in names[1:]):
            hit = next(s for s, n in zip(symbols[1:], names[1:], strict=True) if n in cited)
            out.append(Result(report, lineno, span, "WEAK", hit))
        else:
            out.append(Result(report, lineno, span, "SYMBOL_NOT_FOUND", ", ".join(symbols[:4])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    results: list[Result] = []
    for rep in args.reports:
        for lineno, text in enumerate(rep.read_text(encoding="utf-8").splitlines(), 1):
            results.extend(check_line(str(rep), lineno, text, args.root))
    bad = {"MISSING_FILE", "OUT_OF_RANGE", "SYMBOL_NOT_FOUND"}
    counts: dict[str, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
        if r.status in bad or (args.verbose and r.status != "OK"):
            print(f"{r.status:17s} {r.report}:{r.lineno}  {r.citation}  {r.detail}")
    print("summary:", dict(sorted(counts.items())), "total:", len(results))
    return 1 if any(r.status in bad for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
