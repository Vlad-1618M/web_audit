"""Resolve human-readable test case text for pytest HTML reports."""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_ACRONYMS = {
    "api": "API",
    "asn": "ASN",
    "cli": "CLI",
    "csp": "CSP",
    "dns": "DNS",
    "html": "HTML",
    "http": "HTTP",
    "hsts": "HSTS",
    "json": "JSON",
    "pdf": "PDF",
    "seo": "SEO",
    "tls": "TLS",
    "txt": "TXT",
    "url": "URL",
    "wp": "WordPress",
}


def _apply_acronyms(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        word = match.group(0)
        lower = word.lower()
        if lower in _ACRONYMS:
            return _ACRONYMS[lower]
        if lower == "graphql":
            return "GraphQL"
        if lower == "openapi":
            return "OpenAPI"
        return word.capitalize()

    return re.sub(r"[A-Za-z]+", repl, text)


def humanize_test_name(name: str) -> str:
    """Turn ``test_foo_bar`` into ``Foo bar``."""
    base = name.split("[", 1)[0]
    if base.startswith("test_"):
        base = base[5:]
    phrase = base.replace("_", " ").strip()
    return _apply_acronyms(phrase)


def default_test_case_sentence(name: str) -> str:
    phrase = humanize_test_name(name)
    if phrase.startswith(("no ", "not ")):
        return f"Ensures {phrase}."
    return f"Ensures {phrase}."


def module_area(item: pytest.Item) -> str | None:
    """First line of the test module docstring, if any."""
    module = inspect.getmodule(item.obj)
    if module is None:
        return None
    doc = inspect.getdoc(module)
    if not doc:
        return None
    first = doc.strip().splitlines()[0].strip()
    return first.rstrip(".") if first else None


def resolve_test_case(item: pytest.Item) -> str:
    """QA-facing description: explicit marker > function docstring > generated fallback."""
    marker = item.get_closest_marker("test_case")
    if marker and marker.args:
        text = str(marker.args[0]).strip()
        if text:
            return text

    doc = inspect.getdoc(item.obj)
    if doc:
        return doc.strip().split("\n\n")[0].strip()

    lines: list[str] = []
    area = module_area(item)
    if area:
        lines.append(f"Area: {area}")

    case = default_test_case_sentence(item.name)
    if hasattr(item, "callspec") and item.callspec is not None:
        params = ", ".join(f"{k}={v!r}" for k, v in item.callspec.params.items())
        case = f"{case.rstrip('.')} (parameters: {params})."
    lines.append(f"Test case: {case}")
    return "\n".join(lines)


def _make_docstring(func_name: str) -> str:
    return default_test_case_sentence(func_name)


def add_missing_docstrings(tests_root: Path) -> int:
    """Add one-line docstrings to test functions that lack them. Returns count added."""
    added = 0
    for path in sorted(tests_root.rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        changed = False
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            if ast.get_docstring(node) is not None:
                continue
            doc = _make_docstring(node.name)
            node.body.insert(0, ast.Expr(value=ast.Constant(value=doc)))
            changed = True
            added += 1
        if changed:
            path.write_text(f"{ast.unparse(tree)}\n", encoding="utf-8")
    return added


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    count = add_missing_docstrings(root)
    print(f"Added docstrings to {count} test function(s).")
