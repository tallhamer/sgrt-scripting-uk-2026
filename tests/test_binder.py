"""Binder's files: pinned from the lock, and starting the emulator the same way as everywhere else."""

import os
import shutil
import subprocess
import sys

import pytest

from conftest import ROOT

BINDER = ROOT / "binder"


@pytest.mark.skipif(shutil.which("uv") is None, reason="needs uv (the monorepo checks it; a mirror's CI has only pip)")
def test_requirements_match_the_lock():
    command = [sys.executable, str(ROOT / "scripts" / "export_requirements.py"), "--check"]
    result = subprocess.run(command, capture_output=True, text=True)  # audit: allow subprocesses - sys.executable
    assert result.returncode == 0, result.stdout + result.stderr


def test_requirements_pin_the_published_emulator_and_client_and_leave_out_the_tests():
    lines = (BINDER / "requirements.txt").read_text(encoding="utf-8").splitlines()
    import tomllib

    pins = [d for d in tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
            if d.startswith(("maprt-emulator==", "maprt-client=="))]
    assert len(pins) == 2 and all(pin in lines for pin in pins), pins  # Binder installs exactly what is pinned
    assert any(line.startswith("jupyterlab==") for line in lines)
    # Locked together: Binder's base image has its own `notebook`, which an unpinned JupyterLab
    # left broken (a repo2docker build, 2026-11-10).
    assert any(line.startswith("notebook==") for line in lines)
    assert not any(line.startswith(("pytest==", "sgrt-scripting-uk-2026")) for line in lines)


def test_python_312():
    assert (BINDER / "runtime.txt").read_text(encoding="utf-8").strip() == "python-3.12"


@pytest.mark.parametrize("name", ["postBuild", "start"])
def test_scripts_are_executable_bash(name):
    path = BINDER / name
    assert os.name == "nt" or os.access(path, os.X_OK)
    if shutil.which("bash"):
        bash = [shutil.which("bash"), "-n", str(path)]
        assert subprocess.run(bash).returncode == 0  # audit: allow subprocesses - bash syntax check only


def test_post_build_fetches_the_packs_and_start_uses_the_shared_emulator_command():
    post_build = (BINDER / "postBuild").read_text(encoding="utf-8")
    start = (BINDER / "start").read_text(encoding="utf-8")
    assert "set -euo pipefail" in post_build and "python -m sgrt_workshop.packs" in post_build
    assert "python -m sgrt_workshop.emulator start" in start and 'exec "$@"' in start
    commands = [line.strip() for line in start.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    assert not [c for c in commands if c.startswith("set -e")]  # Jupyter must start even if the emulator doesn't
