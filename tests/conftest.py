import os
import shutil
from pathlib import Path

import pytest

from sgrt_workshop import config, emulator, packs

ROOT = Path(__file__).resolve().parents[1]  # audit: allow writable-locations - the workshop folder, read only


@pytest.fixture(scope="session")
def running_emulator():
    """The workshop's emulator on its packs, as a student has it. Packs are fetched once (or copied
    from ``SGRT_WORKSHOP_PACKS_FROM``, a folder holding the same zips, to avoid the download)."""
    dest = config.packs_dir(ROOT)
    source = os.environ.get("SGRT_WORKSHOP_PACKS_FROM")
    if source:
        dest.mkdir(exist_ok=True)
        for name in config.PACKS:
            if not packs.is_present(name, dest):
                shutil.copyfile(Path(source) / f"{name}.zip", dest / f"{name}.zip")
    packs.fetch_all(dest)
    started_here = not emulator.running(ROOT)
    emulator.start(root=ROOT)
    yield
    if started_here:
        emulator.stop(root=ROOT)
