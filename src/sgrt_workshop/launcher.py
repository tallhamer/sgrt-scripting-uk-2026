"""``sgrt-workshop``: the one command for a local install.

    uv run sgrt-workshop

Fetches the session packs (once), starts the MapRT emulator, then opens Jupyter Lab in
``notebooks/``. Ctrl+C (or closing Jupyter) stops both.

The emulator runs in the background, as an appliance would, so the notebooks talk to it over HTTP
exactly as they would talk to a real one.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from sgrt_workshop import config, emulator, packs


def main():
    root = config.workshop_root()
    notebooks = root / "notebooks"
    if not notebooks.is_dir():
        sys.exit(f"sgrt-workshop: no notebooks/ folder at or above {root}; run this from the workshop's folder.")
    jupyter = shutil.which("jupyter", path=str(Path(sys.executable).parent)) or shutil.which("jupyter")
    if jupyter is None:
        sys.exit("sgrt-workshop: Jupyter isn't installed here. Run `uv sync` in the workshop's folder first.")
    try:
        packs.fetch_all(config.packs_dir(root))
        port = emulator.start(root=root)["port"]
    except (packs.PackError, emulator.EmulatorError) as error:
        sys.exit(f"sgrt-workshop: {error}")
    print("\n" + emulator.banner(root) + "\n", flush=True)
    if port != config.PORT:
        print(f"The emulator is on port {port}: port {config.PORT} was in use by another program when it "
              "started.\nNothing to change: the notebooks find it by themselves.\n", flush=True)
    print("The notebooks read the token from the token file for you: there's nothing to copy.\n"
          "Opening JupyterLab. Close it (or press Ctrl+C here) to stop the emulator too.\n", flush=True)
    try:
        subprocess.run([jupyter, "lab", str(notebooks)], check=False)  # audit: allow subprocesses - the venv's jupyter
    except KeyboardInterrupt:
        pass
    finally:
        try:
            emulator.stop(root)
        except emulator.EmulatorError as error:
            print(f"sgrt-workshop: {error}", file=sys.stderr)
        print("\nThe emulator is stopped.", flush=True)
