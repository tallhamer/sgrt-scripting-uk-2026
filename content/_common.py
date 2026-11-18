"""Pieces every notebook shares: the setup cell, the title block and the exercise."""

import textwrap

#: The public repository and the tag students use. The Colab setup clones it; the Binder badge and
#: the README link to it.
REPO_URL = "https://github.com/tallhamer/sgrt-scripting-uk-2026"
TAG = "v2026.12.0"

#: The first code cell of every notebook. On Colab it installs the workshop, fetches the session
#: packs and starts the emulator, once per runtime; everywhere else it does nothing, because
#: `sgrt-workshop` (local) or Binder's start script already did it. SGRT_WORKSHOP_REPO, _REF and
#: _DIR exist so it can be simulated against a local copy before anything is published.
SETUP = f'''\
# Setup. Run this cell first, in every notebook.
# On Google Colab it installs the workshop, downloads the session packs and starts the emulator
# (about a minute, the first time). Anywhere else it does nothing: that was done for you.
import os, subprocess, sys

if "COLAB_RELEASE_TAG" in os.environ:
    workshop = os.environ.get("SGRT_WORKSHOP_DIR", "/content/sgrt-scripting-uk-2026")
    if not os.path.isdir(workshop):
        repo = os.environ.get("SGRT_WORKSHOP_REPO", "{REPO_URL}")
        ref = os.environ.get("SGRT_WORKSHOP_REF", "{TAG}")
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", ref, repo, workshop], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", workshop], check=True)
    os.chdir(f"{{workshop}}/notebooks")
    subprocess.run([sys.executable, "-m", "sgrt_workshop.packs"], check=True)
    subprocess.run([sys.executable, "-m", "sgrt_workshop.emulator", "start"], check=True)

print("Ready.")'''

NOT_A_DEVICE = (
    "> **Teaching use only. Not a medical device.** Every call in this workshop goes to an emulator "
    "on your own machine, answering from sessions recorded on a real MapRT appliance and anonymized. "
    "Not affiliated with or endorsed by Vision RT."
)


def header(number, title, summary):
    """The title cell, then the setup cell."""
    return [
        ("md", f"# {number:02d} · {title}\n\n{summary}\n\n{NOT_A_DEVICE}"),
        ("code", SETUP),
    ]


def exercise(prompt, solution, number=None):
    """The three cells every notebook ends with: the exercise, an empty cell for the student's own
    code, and the solution, collapsed (an HTML ``<details>`` block, which starts closed in
    JupyterLab, Binder, Colab and GitHub's viewer alike). A notebook with more than one numbers them
    (``number=1``, ``number=2``: "Exercise 1 (optional)", …)."""
    solution = textwrap.dedent(solution).strip("\n")
    return [
        ("md", f"## Exercise {f'{number} ' if number else ''}(optional)\n\n" + textwrap.dedent(prompt).strip("\n")
         + "\n\nWrite your code in the empty cell below. The solution is under it, folded away: open it"
           " when you're done, or if you get stuck. There's no need to finish this in class."),
        ("code", ""),
        ("md", "<details>\n<summary><b>Solution</b> (click to open)</summary>\n\n"
               f"```python\n{solution}\n```\n\n</details>"),
    ]
