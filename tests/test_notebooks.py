"""The notebooks: up to date with ``content/``, shaped as the course needs, and every one runs —
with each exercise's solution pasted into the student's empty cell, so a wrong answer can't ship."""

import re
import subprocess
import sys

import nbformat
import pytest
from nbclient import NotebookClient

from conftest import ROOT

NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))
SOLUTION = re.compile(r"\A<details>\n<summary><b>Solution</b>.*?</summary>\n\n```python\n(.*?)\n```\n\n</details>\Z",
                      re.S)
EXERCISE = re.compile(r"\A## Exercise (\d+ )?\(optional\)")


def read(path):
    return nbformat.read(path, as_version=4)


def test_there_are_notebooks():
    assert [p.name[:2] for p in NOTEBOOKS] == [f"{i:02d}" for i in range(len(NOTEBOOKS))]


def test_the_notebooks_match_their_source():
    build = [sys.executable, str(ROOT / "scripts" / "build_notebooks.py"), "--check"]
    result = subprocess.run(build, capture_output=True, text=True)  # audit: allow subprocesses - sys.executable
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_shape(path):
    cells = read(path).cells
    assert not [c for c in cells if c.cell_type == "code" and (c.outputs or c.execution_count)], "saved outputs"
    assert cells[0].cell_type == "markdown" and cells[0].source.startswith(f"# {path.name[:2]} · ")
    assert cells[1].cell_type == "code" and "COLAB_RELEASE_TAG" in cells[1].source, "the setup cell"
    starts = [i for i, c in enumerate(cells) if c.cell_type == "markdown" and EXERCISE.match(c.source)]
    assert starts and starts[-1] == len(cells) - 3, "the notebook ends with an exercise"
    numbers = [EXERCISE.match(cells[i].source).group(1) for i in starts]
    assert numbers == ([None] if len(starts) == 1 else [f"{n} " for n in range(1, len(starts) + 1)]), numbers
    for i in starts:
        exercise, empty, solution = cells[i:i + 3]
        assert empty.cell_type == "code" and empty.source == "", "an empty cell for the student"
        assert solution.cell_type == "markdown" and SOLUTION.match(solution.source), "a collapsed solution"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_runs_with_its_solutions(path, running_emulator):
    notebook = read(path)
    for i, cell in enumerate(notebook.cells):
        if cell.cell_type == "markdown" and (solution := SOLUTION.match(cell.source)):
            notebook.cells[i - 1].source = solution.group(1)
    NotebookClient(notebook, timeout=180, kernel_name="python3",
                   resources={"metadata": {"path": str(ROOT / "notebooks")}}).execute()
    errors = [o for c in notebook.cells if c.cell_type == "code" for o in c.outputs if o.output_type == "error"]
    assert not errors
