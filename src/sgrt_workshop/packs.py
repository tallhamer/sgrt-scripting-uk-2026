"""Fetch the workshop's session packs into ``packs/``, each checked against its pinned sha256.

    python -m sgrt_workshop.packs            # what Binder's postBuild and the Colab bootstrap run

A pack already present with the right sha256 is not downloaded again, so this is safe to run at
every start. A download goes to ``<name>.zip.part`` and is renamed only once its size and sha256
match, so an interrupted download never leaves a broken pack for the emulator to refuse.
"""

import hashlib
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from types import SimpleNamespace

from sgrt_workshop import config

CHUNK = 1 << 20


class PackError(Exception):
    """A pack could not be fetched or did not match its pinned sha256."""


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def is_present(name, dest):
    """Whether ``dest/<name>.zip`` is there and is exactly the pinned pack."""
    sha256, size = config.PACKS[name]
    path = Path(dest) / f"{name}.zip"
    return path.is_file() and path.stat().st_size == size and sha256_of(path) == sha256


def download(name, dest, opener=urllib.request.urlopen, base_url=None):
    """Download one pack into ``dest``; returns ``"present"`` or ``"downloaded"``."""
    if name not in config.PACKS:
        raise PackError(f"{name!r} is not one of this workshop's packs: {', '.join(config.PACKS)}")
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if is_present(name, dest):
        return "present"
    sha256, size = config.PACKS[name]
    url = f"{base_url or config.PACKS_URL}/{name}.zip"
    part = dest / f"{name}.zip.part"
    try:
        with opener(url, timeout=60) as response, open(part, "wb") as out:
            shutil.copyfileobj(response, out, CHUNK)
    except OSError as error:  # URLError and timeouts are OSErrors
        part.unlink(missing_ok=True)
        raise PackError(f"could not download {url}: {error}") from error
    got_size, got_sha = part.stat().st_size, sha256_of(part)
    if got_size != size or got_sha != sha256:
        part.unlink(missing_ok=True)
        raise PackError(f"{name}.zip does not match the published pack "
                        f"({got_size} bytes, sha256 {got_sha[:12]}…); not kept")
    part.replace(dest / f"{name}.zip")
    return "downloaded"


def fetch_all(dest=None, out=sys.stdout, **kwargs):
    """Every pack the workshop uses. Raises :class:`PackError` naming every one that failed."""
    dest = Path(dest or config.packs_dir())
    failed = []
    for name in config.PACKS:
        print(f"{name}.zip ... ", end="", file=out, flush=True)
        try:
            result = download(name, dest, **kwargs)
        except PackError as error:
            print("failed", file=out)
            failed.append(str(error))
            continue
        print("already here" if result == "present" else "done", file=out)
    if failed:
        raise PackError("\n".join(failed))
    print(f"{len(config.PACKS)} packs in {dest}", file=out)
    return dest


def extract_dicom(name, root=None):
    """Unpack a pack's DICOM (its RT Plan and RT Structure Set) and return where they are.

    Returns a namespace with ``.plan`` and ``.struct`` (full paths to the two ``.dcm`` files) and
    ``.folder`` (``packs/<name>-dicom/``). On Binder and Colab there is no file dialog to pick a
    file with, so the notebooks print these paths and use them directly; the same cell works on a
    laptop. Safe to call again: files already unpacked are left as they are.
    """
    zip_path = config.packs_dir(root) / f"{name}.zip"
    if not zip_path.is_file():
        raise PackError(f"{zip_path} is missing: run `python -m sgrt_workshop.packs` first")
    folder = config.packs_dir(root) / f"{name}-dicom"
    found = {}
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            parts = member.split("/")
            # A pack keeps its DICOM as dicom/plan/RP.<uid>.dcm and dicom/struct/RS.<uid>.dcm.
            if len(parts) == 3 and parts[0] == "dicom" and parts[2].lower().endswith(".dcm"):
                target = folder / parts[1] / parts[2]
                if not target.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(member))
                found[parts[1]] = target
    missing = {"plan", "struct"} - found.keys()
    if missing:
        raise PackError(f"{name} has no {' or '.join(sorted(missing))} DICOM file")
    return SimpleNamespace(folder=folder, plan=found["plan"], struct=found["struct"])


def recorded_rooms(name, root=None):
    """The room ids the pack's session recorded maps in.

    A real appliance computes a map for any room. The emulator can only replay what was recorded:
    for a room the session didn't record it substitutes a map recorded elsewhere, so the lessons
    that loop over rooms use these.
    """
    import json

    rooms = set()
    with zipfile.ZipFile(config.packs_dir(root) / f"{name}.zip") as archive:
        for member in archive.namelist():
            if "GetMap" in member and member.endswith("_request.json"):
                rooms.add(json.loads(archive.read(member))["body"]["TreatmentRoomId"])
    return sorted(rooms)


def main():
    try:
        fetch_all()
    except PackError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
