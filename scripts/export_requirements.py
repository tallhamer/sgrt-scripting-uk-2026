"""Write ``binder/requirements.txt`` from ``uv.lock``.

    uv run python scripts/export_requirements.py           # write it
    uv run python scripts/export_requirements.py --check   # fail if it is out of date (the tests run this)

Binder builds with repo2docker, which reads ``requirements.txt`` and knows nothing of uv. Exporting
the lock gives a Binder session exactly the versions ``uv sync`` installs and the tests ran:
the runtime dependencies and the ``lab`` group (Jupyter), without ``dev`` (the tests) and without
the workshop itself, which ``binder/postBuild`` installs from the checkout.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # audit: allow writable-locations - the workshop folder
TARGET = ROOT / "binder" / "requirements.txt"

HEADER = """\
# GENERATED, do not edit. Run: uv run python scripts/export_requirements.py
# The locked versions `uv sync` installs, for Binder (repo2docker reads requirements.txt, not uv).
# The workshop itself is installed by binder/postBuild.
"""


def export():
    command = ["uv", "export", "--format", "requirements-txt", "--no-hashes", "--no-emit-project",
               "--no-default-groups", "--group", "lab", "--no-header", "--frozen"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)  # audit: allow subprocesses - uv, maintainer-only
    if result.returncode != 0:
        raise SystemExit(f"export_requirements: uv export failed\n{result.stderr}")
    return HEADER + result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    content = export()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
        if current != content:
            raise SystemExit(f"{TARGET.name} is out of date with uv.lock. Run this script without --check.")
        print("binder/requirements.txt is up to date.")
        return
    TARGET.write_text(content, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)} ({content.count(chr(10))} lines)")


if __name__ == "__main__":
    sys.exit(main())
