"""The workshop's fixed settings: where the emulator listens, what it is called with, and the data.

One place, so the launcher, Binder's ``start``, the Colab bootstrap and every notebook agree.
"""

import json
import os
from pathlib import Path

#: The emulator listens here on every platform. Local only: nothing outside this machine (or this
#: Binder/Colab container) can reach it.
HOST = "127.0.0.1"

#: The ports it may use, tried in order. 8000 is the usual one; if something else holds it (an
#: emulator left running from another folder, another program), the next free one is taken, so
#: nobody in the room loses time to a busy port. The port actually used is in ``server.json``
#: (:func:`api_url` reads it), and a restart keeps it.
PORTS = tuple(range(8000, 8020))
PORT = PORTS[0]

#: What a MapRT client must send as its User-Agent: the appliance (and the emulator) refuse any
#: other with ``VersionMismatch``. Notebook 01 shows that refusal.
USER_AGENT = "VisionRT.Integration.Saturn/2.0.0"

#: The session packs: recordings of a real appliance, anonymized, published as release assets of
#: the emulator's repository (CC BY 4.0). Each is at most 25 MB, so Binder and Colab fetch them
#: quickly. Name -> (sha256, size in bytes), pinned from the published release: a download that
#: doesn't match is refused.
#:
#: Downloaded straight from each asset's URL, never through the GitHub API: unauthenticated API
#: calls are limited to 60 an hour per address, and a classroom on one network (or Colab, whose
#: machines share addresses) would run out at the start of the session.
PACKS_RELEASE = "packs-v1"
PACKS_URL = f"https://github.com/tallhamer/maprt-emulator/releases/download/{PACKS_RELEASE}"
PACKS = {
    "hfdr-phantom": ("d6eff91994bc44fd200c968f1677cd3d7a95e73c10987ff20bdce6856bfa52bd", 4206738),
    "hfs-phantom-slim": ("7411034e9cdfc2e26496801549afcf5734e44de2bbad286514553f7a8a1ecc56", 7966799),
    "2-surface-patient": ("50c01e54d6e817f8e671a85ab552085b7f42111d8f2953e60fb228bd9120e827", 24653031),
    "lt-lung-sbrt-patient": ("f3a5a712553d74d47a4115f914a31937960c1569783c18dea647a1827a75f505", 11651470),
    "srs-patient": ("d46bdbd080efa72d41311c36d5d823fd81779887cb04879bedd6d52ab9caa4c7", 12680094),
}

#: The pack license and citation, shown wherever the packs are introduced.
PACKS_CREDIT = (
    "Session packs: Tallhamer, M. J. (2026). *MapRT Emulator session packs* (packs-v1) [Data set]. "
    "AdventHealth. https://github.com/tallhamer/maprt-emulator — licensed CC BY 4.0."
)

PROJECT_NAME = "sgrt-scripting-uk-2026"


def token_file(root=None):
    """Where the running emulator wrote its token: ``.maprt_emulator/token`` in the workshop folder."""
    return state_dir(root) / "token"


def token(root=None, required=True):
    """The API token of the emulator that is running now.

    The emulator mints a **fresh token every time it starts** (a real appliance's token, too, can
    be changed by its administrator), prints it, and writes it to :func:`token_file`. This reads
    that file at the moment it is called, so code never holds a token from an earlier run.
    ``MAPRT_EMULATOR_TOKEN`` overrides it. With ``required=False`` a missing file gives ``""``.
    """
    if os.environ.get("MAPRT_EMULATOR_TOKEN"):
        return os.environ["MAPRT_EMULATOR_TOKEN"]
    try:
        return token_file(root).read_text(encoding="utf-8").strip()
    except OSError:
        if not required:
            return ""
        raise RuntimeError(f"no token file at {token_file(root)}: the emulator isn't running. "
                           "Run the setup cell at the top of the notebook (or `uv run sgrt-workshop`).") from None


def server_file(root=None):
    """What the running emulator wrote about itself when it started: ``.maprt_emulator/server.json``
    (its URL, token and process id)."""
    return state_dir(root) / "server.json"


def server_info(root=None):
    """The contents of :func:`server_file` as a dict (empty if there is none yet)."""
    try:
        info = json.loads(server_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return info if isinstance(info, dict) else {}


def api_url(root=None):
    """The emulator's base URL, e.g. ``http://127.0.0.1:8000``.

    Read from :func:`server_file` at the moment it is called, like the token: the emulator may be on
    another port than 8000 if that one was busy when it started. ``MAPRT_EMULATOR_URL`` overrides it.
    """
    return (os.environ.get("MAPRT_EMULATOR_URL") or server_info(root).get("url")
            or f"http://{HOST}:{PORT}")


def workshop_root(start=None):
    """The workshop's folder: ``SGRT_WORKSHOP_HOME``, else the nearest folder at or above ``start``
    (the working directory) whose ``pyproject.toml`` is this project's, else ``start`` itself.

    Walking up means a notebook in ``notebooks/`` and a terminal at the top both find the same
    ``packs/`` and the same emulator state.
    """
    if os.environ.get("SGRT_WORKSHOP_HOME"):
        return Path(os.environ["SGRT_WORKSHOP_HOME"]).resolve()
    here = Path(start or Path.cwd()).resolve()
    for folder in [here, *here.parents]:
        pyproject = folder / "pyproject.toml"
        if pyproject.is_file() and f'name = "{PROJECT_NAME}"' in pyproject.read_text(encoding="utf-8"):
            return folder
    return here


def packs_dir(root=None):
    return (root or workshop_root()) / "packs"


def state_dir(root=None):
    """The emulator's state, its log and the process id of the one this workshop started."""
    return (root or workshop_root()) / ".maprt_emulator"
