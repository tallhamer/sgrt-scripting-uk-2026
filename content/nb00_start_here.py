"""00 · Start here."""

from ._common import exercise, header

CELLS = [
    *header(0, "Start here", "What this workshop is, how the notebooks work, and what you're talking to."),
    ("md", """\
## What is MapRT and what does it do?

MapRT is Vision RT's clearance-mapping system for radiation therapy planning. It combines a 3D
surface model of the patient with a model of the treatment equipment, to help planners find the
gantry and couch angles that avoid collisions between the machine, the patient, the couch and any
immobilization devices.

### How it works

* At CT simulation, two wide-field cameras capture a 3D surface of the patient and their
  accessories in the treatment position. This includes areas outside the usual CT volume that can
  still collide, such as elbows and knees.
* MapRT combines that surface with models of the treatment couch and gantry to build a virtual
  treatment room.
* From that room it computes a **clearance map**: the predicted clearance for every combination
  of couch and gantry angle. Planners can also import a treatment plan to check its beams.

### Why it matters

A beam angle can be attractive dosimetrically yet impossible to deliver, because the machine would
collide with the patient or with itself. MapRT finds those limits during planning, rather than at
a physical clearance check on the treatment machine. It is particularly useful for non-coplanar
treatments, which rotate the couch to deliver beams from more directions; depending on the case,
those beams can improve the sparing of organs at risk.

MapRT's **API** lets a script, from within (or from outside of) a treatment planning system, ask
for that information directly: which treatment rooms are set up, which surfaces a patient has, the
clearance map for a particular setup, and whether an existing plan's beams can be delivered
safely."""),
    ("md", """\
## What you'll do

Over the next eight short notebooks you'll learn to script the MapRT API using Python:

| Notebook | You'll learn |
|---|---|
| 01 · Setup and token | the three things every call needs, and a first call |
| 02 · Replies and errors | how MapRT says yes and no, and a library that handles it for you |
| 03 · Treatment rooms | listing rooms and finding one by name |
| 04 · Patient surfaces | a patient's surfaces, and drawing one |
| 05 · Clearance maps | asking for a map and reading it |
| 06 · Beams and plans | checking a plan's beams against a map, and asking MapRT |
| 07 · Robustness | what to do when the appliance is slow, refuses, or fails |
| 08 · Capstone | a plan QA report across every room |

**You don't have to write any code during these lessons.** Every code cell is already written, so
you can focus on the topic. You can add a cell of your own at any time, to explore something that
comes up in discussion. Each notebook ends with a short, optional **Exercise** to practice what
you've learned, with one possible solution below it if you get stuck."""),
    ("md", """\
## How a notebook works

A notebook is a list of **cells**. Markdown cells (like this one) explain a topic or give
instructions; code cells run Python code.

* Click a code cell and press **Shift + Enter** to run it. Its output appears underneath.
* Run the cells **in order, from top to bottom**. A later cell often uses data and variables that
  an earlier cell created.
* If the notebook doesn't behave as expected, use **Kernel → Restart Kernel** (in Colab: **Runtime
  → Restart session**) and run it from the top again. Nothing is lost: the notebook is unchanged.

The **setup cell** at the top of every notebook makes sure everything is running. **Always run it
first.**"""),
    ("md", """\
## What you're talking to

A real MapRT appliance sits in a hospital network. You don't need one today: a **MapRT emulator**
is running on the same machine as this notebook. It answers the same API, in the same way, from
**session packs**: real conversations with a real appliance, recorded and then anonymized (the
patients are `ANON-…`, their dates shifted).

The MapRT emulator ("the emulator") used in this course is written in Python and needs Python to
run. You don't need to know how to set that up: it has been done for you. You don't need a real
MapRT appliance either, which makes the emulator a good place to learn the MapRT API and practice
your scripting. The emulator and its installation instructions are at
[github.com/tallhamer/maprt-emulator](https://github.com/tallhamer/maprt-emulator). It works with
any programming language, as long as you know how to make API calls from it.

Whether you are running this on your own laptop, on **Binder** or on **Google Colab**, the
emulator is at the same address, and the notebooks work the same way."""),
    ("code", """\
from sgrt_workshop import emulator

emulator.status()"""),
    ("md", """\
`'running': True` means the emulator is answering. If it says `False`, run the setup cell at the
top again.

The session packs it serves were downloaded into a folder called `packs`:"""),
    ("code", """\
from sgrt_workshop import config

for pack in sorted(config.packs_dir().glob("*.zip")):
    print(pack.name)"""),
    ("md", """\
> Session packs: Tallhamer, M. J. (2026). *MapRT Emulator session packs* (packs-v1) [Data set].
> AdventHealth. https://github.com/tallhamer/maprt-emulator. Licensed
> [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)."""),
    *exercise(
        """\
        Print how many session packs there are, and the size of the largest one in megabytes.

        *Hint:* `pack.stat().st_size` is a file's size in bytes, and there are 1,000,000 bytes in a
        megabyte.""",
        """\
        packs = sorted(config.packs_dir().glob("*.zip"))
        largest = max(pack.stat().st_size for pack in packs)
        print(f"{len(packs)} packs; the largest is {largest / 1_000_000:.1f} MB")""",
    ),
]
