"""Build ``notebooks/*.ipynb`` from their sources in ``content/``.

    uv run python scripts/build_notebooks.py           # write the notebooks
    uv run python scripts/build_notebooks.py --check   # fail if a notebook is out of date

**The notebooks are generated: edit ``content/``, not the ``.ipynb``.** Generating them keeps
every notebook free of outputs (clean diffs, small files), keeps the prose editable as plain text,
and lets ``--check`` (run by the tests) catch a notebook edited by hand.

``content/__init__.py`` lists the notebooks; each content module defines ``CELLS``, a list of
``("md", text)`` and ``("code", text)`` pairs, ending with :func:`content._common.exercise`.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # audit: allow writable-locations - the workshop folder, read only
CONTENT = ROOT / "content"
NOTEBOOKS = ROOT / "notebooks"


def load_notebooks():
    """``content/`` → its ``NOTEBOOKS`` list of ``(filename, cells)``."""
    spec = importlib.util.spec_from_file_location("content", CONTENT / "__init__.py",
                                                  submodule_search_locations=[str(CONTENT)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # before exec_module, so its relative imports resolve
    spec.loader.exec_module(module)
    return module.NOTEBOOKS


def _lines(text):
    """nbformat's list of lines, each keeping its newline but the last: a one-line prose fix is a
    one-line diff."""
    return text.strip("\n").splitlines(keepends=True) or [""]


def build(cells):
    built = []
    for index, (kind, text) in enumerate(cells):
        # Sequential ids, so an unchanged notebook rebuilds byte-identical.
        cell = {"id": f"cell-{index:03d}", "cell_type": "markdown" if kind == "md" else "code",
                "metadata": {}, "source": _lines(text)}
        if kind != "md":
            cell.update(execution_count=None, outputs=[])
        built.append(cell)
    return {
        "cells": built,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def render(cells):
    return json.dumps(build(cells), indent=1, ensure_ascii=False) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if a notebook differs from its source")
    args = parser.parse_args(argv)
    NOTEBOOKS.mkdir(exist_ok=True)
    stale = []
    notebooks = load_notebooks()
    for name, cells in notebooks:
        path = NOTEBOOKS / name
        content = render(cells)
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(name)
        else:
            path.write_text(content, encoding="utf-8")
            print(f"notebooks/{name}: {len(cells)} cells")
    extra = sorted({p.name for p in NOTEBOOKS.glob("*.ipynb")} - {name for name, _ in notebooks})
    if args.check:
        if stale or extra:
            raise SystemExit("Out of date: " + ", ".join(stale + [f"{e} (no source)" for e in extra])
                             + "\nRun: uv run python scripts/build_notebooks.py")
        print(f"{len(notebooks)} notebooks are up to date.")
    elif extra:
        print(f"warning: notebooks with no source in content/: {', '.join(extra)}", file=sys.stderr)


if __name__ == "__main__":
    main()
