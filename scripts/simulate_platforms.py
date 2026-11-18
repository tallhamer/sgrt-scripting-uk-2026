"""Run the workshop the way Binder and Colab will, before anything is published.

    uv run python scripts/simulate_platforms.py binder   # a real repo2docker build (needs Docker running)
    uv run python scripts/simulate_platforms.py colab    # a fresh 3.12 env, the setup cell does the rest
    uv run python scripts/simulate_platforms.py all

Both work on a **clean copy** of this folder (the files git tracks or would add; never ``packs/``,
``.venv/`` or saved notebook outputs) in a temporary folder, and both execute **every notebook**,
reporting each one's errors. Nothing here is touched.

* **binder:** ``repo2docker`` (run with ``uvx``) builds the image exactly as mybinder.org would, then
  each notebook runs inside it through the image's entry point, so ``binder/start`` runs first.
* **colab:** a bare Python 3.12 venv with only what Colab already has (a kernel, nbconvert, numpy,
  matplotlib). Each notebook is opened on its own, outside any checkout, with ``COLAB_RELEASE_TAG``
  set and the repository pointed at a local git copy (``SGRT_WORKSHOP_REPO``/``_REF``/``_DIR``), so
  the setup cell has to clone, install, fetch the packs and start the emulator by itself.

Maintainer tool: it needs ``uv``, ``git`` and (for binder) Docker on PATH.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # audit: allow writable-locations - the workshop folder, read only
IMAGE = "sgrt-workshop-simulated-binder"
COLAB_HAS = ["ipykernel", "nbconvert", "numpy", "matplotlib"]


def run(command, **kwargs):
    """Run a maintainer tool (uv, git, docker); fail loudly."""
    return subprocess.run(command, check=True, **kwargs)  # audit: allow subprocesses - maintainer tools


def clean_copy(dest):
    """The files git tracks or would add, as they are now (never packs, .venv or ignored files)."""
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,  # audit: allow subprocesses - git
                            check=True, capture_output=True, text=True).stdout.splitlines()
    for name in listed:
        source = ROOT / name
        if source.is_file():
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return dest


def notebook_errors(path):
    notebook = json.loads(Path(path).read_text(encoding="utf-8"))
    return [f"{o.get('ename')}: {o.get('evalue')}" for c in notebook["cells"] if c["cell_type"] == "code"
            for o in c.get("outputs", []) if o.get("output_type") == "error"]


def notebooks():
    return sorted(p.name for p in (ROOT / "notebooks").glob("*.ipynb"))


def binder(scratch):
    repo = clean_copy(scratch / "repo")
    run(["docker", "image", "rm", "-f", IMAGE], capture_output=True)  # repo2docker would reuse an old image
    print("Building with repo2docker (a few minutes)...", flush=True)
    run(["uvx", "--from", "jupyter-repo2docker", "repo2docker", "--no-run", "--image-name", IMAGE,
         "--user-id", "1000", "--user-name", "jovyan", str(repo)],
        stdout=open(scratch / "build.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    log = (scratch / "build.log").read_text(encoding="utf-8")
    if "dependency conflicts" in log:
        print("WARNING: pip reported dependency conflicts in the image; see the build log")
    out = scratch / "out"
    out.mkdir()
    script = "cd notebooks && " + " && ".join(
        f"jupyter nbconvert --to notebook --execute --allow-errors --ExecutePreprocessor.timeout=600 --output /out/{n} {n}"
        for n in notebooks())
    run(["docker", "run", "--rm", "-v", f"{out}:/out", IMAGE, "bash", "-c", script],
        capture_output=True)
    return {n: notebook_errors(out / n) for n in notebooks()}


def colab(scratch):
    repo = clean_copy(scratch / "repo")
    git = ["git", "-c", "user.name=simulation", "-c", "user.email=simulation@example.invalid"]
    run([*git, "init", "-q", "-b", "main"], cwd=repo)
    run([*git, "add", "-A"], cwd=repo)
    run([*git, "commit", "-qm", "simulated release"], cwd=repo)
    venv = scratch / "venv"
    run(["uv", "venv", "-q", "--seed", "--python", "3.12", str(venv)])
    bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
    run([str(bin_dir / "python"), "-m", "pip", "install", "-q", *COLAB_HAS])
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env.update(PATH=f"{bin_dir}{os.pathsep}{env['PATH']}", COLAB_RELEASE_TAG="simulated",
               SGRT_WORKSHOP_REPO=str(repo), SGRT_WORKSHOP_REF="main",
               SGRT_WORKSHOP_DIR=str(scratch / "content" / "sgrt-scripting-uk-2026"))
    opened = scratch / "opened"  # Colab opens a notebook on its own, outside any checkout
    opened.mkdir()
    results = {}
    try:
        for name in notebooks():
            shutil.copy2(repo / "notebooks" / name, opened / name)
            run([str(bin_dir / "jupyter"), "nbconvert", "--to", "notebook", "--execute",
                 "--allow-errors", "--ExecutePreprocessor.timeout=600", "--output", f"out-{name}", name],
                cwd=opened, env=env, capture_output=True)
            results[name] = notebook_errors(opened / f"out-{name}")
    finally:
        installed = scratch / "content" / "sgrt-scripting-uk-2026"
        if installed.is_dir():
            subprocess.run([str(bin_dir / "python"), "-m", "sgrt_workshop.emulator", "stop"],  # audit: allow subprocesses - the venv's python
                           cwd=installed, env=env, capture_output=True)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("platform", choices=["binder", "colab", "all"])
    args = parser.parse_args(argv)
    failed = False
    for platform in (["binder", "colab"] if args.platform == "all" else [args.platform]):
        with tempfile.TemporaryDirectory(prefix=f"sgrt-{platform}-") as scratch:
            print(f"\n== {platform} ==", flush=True)
            try:
                results = (binder if platform == "binder" else colab)(Path(scratch))
            except subprocess.CalledProcessError as error:
                print(f"{platform}: {' '.join(map(str, error.cmd[:4]))}… failed (exit {error.returncode})")
                failed = True
                continue
            for name, errors in results.items():
                print(f"  {name}: {'ok' if not errors else 'ERRORS: ' + '; '.join(errors)}")
                failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
