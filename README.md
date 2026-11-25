# SGRT Scripting Workshop: the MapRT API

**United Kingdom, 3 December 2026.** Course materials and handout.

> **Teaching use only. Not a medical device.** Everything in this workshop talks to an emulator on
> your own machine, answering from sessions recorded on a real MapRT appliance and anonymized.
> Nothing here is for clinical use. Not affiliated with or endorsed by Vision RT.

In this workshop you'll script the **Vision RT MapRT API 2.0** from Python: list a site's
treatment rooms, find a patient's surfaces, ask for a collision clearance map, and check a
treatment plan's beams against it, ending with a plan QA report across every room.

**What you need:** a laptop with a web browser, and basic Python (variables, functions, loops).
Every notebook already contains all the code needed to follow along; each ends with an optional
exercise for when you want to write some yourself, in class or later.

## Start here: pick one way to run it

You don't need to install anything for the first two.

### 1. Binder (in your browser, nothing to sign in to)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/tallhamer/sgrt-scripting-uk-2026/v2026.12.2?urlpath=lab/tree/notebooks/00_start_here.ipynb)

Click the badge. The first start can take a few minutes while Binder prepares the session; then
JupyterLab opens on notebook 00, with the emulator already running.

* A Binder session is **temporary**: it closes after about 10 minutes without activity, and
  anything you changed is lost. To keep your work, right-click a notebook in the file panel and
  choose **Download**.

### 2. Google Colab (in your browser, with a Google account)

Open a notebook from the [table below](#the-notebooks) using its **Colab** link, then run its first
cell (the **setup cell**). Each notebook runs in its own Colab session, so the first time you run
the setup cell in a notebook, it installs the workshop, downloads the session packs and starts the
emulator, which takes about a minute; running it again in the same notebook is quick.

* Run the setup cell **first, in every notebook**. If Colab restarts (**Runtime → Restart
  session**), run it again.
* Open each notebook in its own browser tab: **Ctrl+click** its Colab link (**Cmd+click** on a
  Mac). A notebook opened from inside Colab can appear in a side panel instead.
* To keep your work, use **File → Save a copy in Drive**.

### 3. Your own laptop

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs Python for you),
then, in a terminal:

```console
git clone --branch v2026.12.2 https://github.com/tallhamer/sgrt-scripting-uk-2026.git
cd sgrt-scripting-uk-2026
uv run sgrt-workshop
```

No `git`? Download the ZIP from
[the v2026.12.2 release](https://github.com/tallhamer/sgrt-scripting-uk-2026/releases/tag/v2026.12.2),
unzip it, and run `uv run sgrt-workshop` inside the folder.

`sgrt-workshop` downloads the session packs (the first time only), starts the emulator and opens
JupyterLab. Close JupyterLab (or press **Ctrl+C** in the terminal) to stop both. Your notebooks,
and anything you change in them, stay in the folder. The next section shows what the terminal
prints, and where to find the emulator's token.

### A few practical notes for the course

* **Your own laptop**, set up with uv, is the recommended way to run the course: the most
  flexibility for the least effort, and your work stays in the folder.
* If you'd rather not install anything, **Binder** is the best choice for running the whole course
  in one sitting, with no runtimes to manage. **Colab** works well as a fallback, or for picking up
  a single notebook.
* Colab limits how many runtimes you can have running at once. Before moving on to the next
  notebook, use **Runtime → Disconnect and delete runtime** on the one you've finished, or close
  its tab. Otherwise idle runtimes can pile up and Colab may refuse to start a new one.

## On your own laptop: the terminal and your token

### What you'll see in the terminal

When you run `uv run sgrt-workshop`, the terminal prints this:

```text
hfdr-phantom.zip ... done
hfs-phantom-slim.zip ... done
2-surface-patient.zip ... done
lt-lung-sbrt-patient.zip ... done
srs-patient.zip ... done
5 packs in /Users/you/sgrt-scripting-uk-2026/packs

╭────────────────────────────────────────────────────────────────────────╮
│  MapRT Emulator  —  NOT a medical device. Teaching only.               │
│                                                                        │
│  Base URL    http://127.0.0.1:8000                                     │
│  Docs        http://127.0.0.1:8000/docs                                │
│              (Try it out needs --lenient-user-agent)                   │
│  Packs       5 packs, 5 patients, 6 surfaces, 16 rooms, 296 maps,      │
│              148 beam checks                                           │
│              packs                                                     │
│  Appliance   Saturn/1.3.217.2 (API 2.0.0)                              │
│  Token file  .maprt_emulator/token                                     │
╰────────────────────────────────────────────────────────────────────────╯

API token for this session (a new one each time the emulator starts):

    EXAMPLE-not-a-real-token-yours-is-43-random-characters

Read it in code from .maprt_emulator/token, or from MAPRT_EMULATOR_TOKEN if you set one.
Treat it like a password: never paste it into code or notebooks you share.

The notebooks read the token from the token file for you: there's nothing to copy.
Opening JupyterLab. Close it (or press Ctrl+C here) to stop the emulator too.
```

(The token above is a placeholder: yours is 43 random letters, digits, `-` and `_`, different on every run.)

* **The pack lines:** the five session packs, downloaded and checked. The next time you run
  `sgrt-workshop` they say `already here` instead.
* **Base URL:** the emulator's address. Every MapRT call starts with it, exactly as with a real
  appliance's address. Only your own computer can reach it.
* **Docs:** a web page describing the API's endpoints and replies. Its "Try it out" buttons are
  refused, as a real appliance would refuse them, because a browser can't send the User-Agent
  MapRT requires (notebook 01 explains).
* **Packs:** what the emulator is serving: the patients, their surfaces, the treatment rooms, and
  the recorded collision maps and beam checks.
* **Appliance:** the MapRT version the sessions were recorded on.
* **Token file** and **API token for this session:** this run's token, where it is kept, and how
  to use it safely (below).

### The token is new every time

The emulator makes a **new token every time it starts**, prints it, and writes it to a file:
**`.maprt_emulator/token`**, inside the workshop folder. Next to it, `.maprt_emulator/server.json`
holds the same token with the emulator's address. Both files can be read only by you.

**Don't copy the token into your code**, as the banner says: it stops working the next time the
emulator starts. Read it from the file instead, which is what the
notebooks do (`from sgrt_workshop import settings` reads it each time). In a script of your own:

```python
from pathlib import Path

token = Path(".maprt_emulator/token").read_text(encoding="utf-8").strip()   # from the workshop folder
```

The same habit matters more with a real appliance: its token is a secret, and a token typed into
a notebook travels with every copy of that notebook.

`.maprt_emulator` is a hidden folder (its name starts with a dot). To see it: on a Mac, press
**Cmd + Shift + .** in Finder; on Windows, choose **View → Show → Hidden items** in File Explorer.
On Binder and Colab the emulator works the same way inside your session, with a new token each
session, and the notebooks read it for you.

## The notebooks

Work through them in order: each builds on the one before.

| # | Notebook | You'll learn | Open in Colab |
|---|---|---|---|
| 00 | Start here | how the notebooks work, and what you're talking to | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/00_start_here.ipynb) |
| 01 | Setup and token | the three things every call needs, and a first call | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/01_setup_and_token.ipynb) |
| 02 | Replies and errors | how MapRT says yes and no; `maprt-client` | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/02_replies_and_errors.ipynb) |
| 03 | Treatment rooms | listing rooms, and finding one by machine name | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/03_treatment_rooms.ipynb) |
| 04 | Patient surfaces | a patient's surfaces, and a 3D view of one | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/04_patient_surfaces.ipynb) |
| 05 | Clearance maps | building a map request from the plan; reading the map | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/05_clearance_maps.ipynb) |
| 06 | Beams and plans | checking a plan's beams yourself, and asking MapRT | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/06_beams_and_plans.ipynb) |
| 07 | Robustness | timeouts, a busy server, refusals, half a map, recording a session | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/07_robustness.ipynb) |
| 08 | Capstone: plan QA across rooms | every beam of a plan in every room, and a report | [Colab](https://colab.research.google.com/github/tallhamer/sgrt-scripting-uk-2026/blob/v2026.12.2/notebooks/08_capstone_plan_qa.ipynb) |

**Exercises.** Each notebook ends with an optional exercise, an empty cell for your code, and the
solution, folded away under **Solution (click to open)**. Try it first; open the solution when
you're done or stuck. You won't need the exercise to follow the next notebook.

## What's in the box

* **The MapRT emulator** ([`maprt-emulator`](https://github.com/tallhamer/maprt-emulator) on PyPI):
  a stand-in for a MapRT appliance that answers the same API in the same way, on your own machine.
* **Session packs**: real conversations with a real appliance, recorded and anonymized (patients
  are `ANON-…`, dates shifted), including the patients' RT Plan and RT Structure Set. The emulator
  answers from them.
* **`maprt-client`** ([on PyPI](https://github.com/tallhamer/maprt-client)): a small Python client
  for the API. The first notebooks use plain HTTP so you see what goes over the wire; from
  notebook 02 on, this library does the plumbing.

## If something goes wrong

* **"The emulator isn't running" / connection refused:** run the notebook's setup cell again.
  Locally, check the terminal where `sgrt-workshop` is running.
* **A cell fails after you skipped some:** run the cells in order from the top. **Kernel → Restart
  Kernel and Run All Cells** (Colab: **Runtime → Restart session and run all**) starts clean.
* **Locally, "the emulator is on port 8001" (or another number):** port 8000 was in use by another
  program, so the emulator took the next free port. Nothing to do: the notebooks find it by
  themselves. Only if ports 8000–8019 are *all* in use does it stop and say so; then close some
  programs (or restart your laptop) and run `uv run sgrt-workshop` again.
* **Binder won't start:** Binder is a free, shared service and is sometimes busy. Use Colab
  instead; the notebooks are the same.

## After the course

Everything here keeps working on your own laptop (option 3). Against a **real** appliance, three
things change, and nothing else:

* the **URL** is the appliance's address, and starts with `https://`;
* the **token** comes from your system administrator, and is a secret: keep it out of notebooks
  you share;
* the appliance's certificate is one your hospital made, so clients turn certificate checking off
  (`maprt-client` does). Use the API only on the network the appliance lives on.

Talk to your physics and IT teams before pointing any script at a clinical system.

## Credits and licenses

* Workshop code and notebooks: MIT ([LICENSE](LICENSE)).
* Session packs: Tallhamer, M. J. (2026). *MapRT Emulator session packs* (packs-v1) [Data set].
  AdventHealth. <https://github.com/tallhamer/maprt-emulator>. Licensed
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
* MapRT is a product of Vision RT. This workshop is independent of Vision RT.
