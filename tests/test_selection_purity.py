"""The ordering is derived from a frozen graph, and that is checked, not promised.

ordering.py must reach no network library, no model SDK and no subprocess, directly
or transitively. The reason is not tidiness. A pure selector means the order can be
re-derived from stored state, which is what makes the prefix property testable and
what makes tuning the order cost nothing. If someone later imports `requests` into
the scorer to "just check one thing", this fails.

Same shape as outbound-sourcing/tests/test_send_path_purity.py, for the same reason.
"""
from __future__ import annotations

import ast
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

FORBIDDEN_PREFIXES = (
    "anthropic", "openai", "google.generativeai", "google.genai", "cohere",
    "mistralai", "ollama", "litellm", "langchain", "llama_index", "transformers",
    "claude", "subprocess", "requests", "httpx", "aiohttp", "urllib.request",
    "socket", "http.client",
)

PURE_ENTRIES = ["ordering"]


def module_file(name: str) -> Path | None:
    rel = name.replace(".", "/")
    for c in (SCRIPTS / f"{rel}.py", SCRIPTS / rel / "__init__.py"):
        if c.exists():
            return c
    return None


def imports_of(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out.update(f"{node.module}.{a.name}" for a in node.names)
    return out


def reachable(entries) -> dict[str, list[str]]:
    """Every module reachable from the entries, with the chain that got there."""
    seen: dict[str, list[str]] = {}
    stack = [(e, [e]) for e in entries]
    while stack:
        name, chain = stack.pop()
        if name in seen:
            continue
        seen[name] = chain
        f = module_file(name)
        if f is None:
            continue
        for imp in imports_of(f):
            local = imp.split(".")[-1] if imp.startswith("scripts.") else imp
            if module_file(local) and local not in seen:
                stack.append((local, chain + [local]))
            elif local not in seen:
                seen[local] = chain + [local]
    return seen


def test_selection_reaches_no_network_or_model():
    offenders = []
    for name, chain in reachable(PURE_ENTRIES).items():
        if any(name == p or name.startswith(p + ".") for p in FORBIDDEN_PREFIXES):
            offenders.append(f"{name} via {' -> '.join(chain)}")
    assert not offenders, "selection is no longer pure:\n" + "\n".join(offenders)
