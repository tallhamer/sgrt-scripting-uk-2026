"""The README is the course handout: its links must match the release and the notebooks."""

import re
import tomllib

from conftest import ROOT

README = (ROOT / "README.md").read_text(encoding="utf-8")
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
TAG = f"v{VERSION}"
REPO = "tallhamer/sgrt-scripting-uk-2026"


def test_every_link_to_the_workshop_is_pinned_to_this_release():
    refs = re.findall(rf"{REPO}(?:\.git)?(?:/(?:blob|tree|releases/tag)/|/)([^/?#)\s]+)", README)
    refs += re.findall(r"--branch (\S+)", README)
    assert refs and set(refs) == {TAG}, set(refs)


def test_every_notebook_is_in_the_table_with_a_colab_link_and_nothing_else_is():
    notebooks = sorted(p.name for p in (ROOT / "notebooks").glob("*.ipynb"))
    linked = re.findall(rf"colab\.research\.google\.com/github/{REPO}/blob/{TAG}/notebooks/([^)\s]+)", README)
    assert linked == notebooks


def test_the_binder_badge_opens_notebook_00_on_the_tag():
    binder = f"mybinder.org/v2/gh/{REPO}/{TAG}?urlpath=lab/tree/notebooks/00_start_here.ipynb"  # audit: allow path-construction - a URL
    assert binder in README


def test_the_setup_cell_clones_the_same_tag():
    from content import _common  # the notebooks' shared source

    assert _common.TAG == TAG and _common.REPO_URL == f"https://github.com/{REPO}"
