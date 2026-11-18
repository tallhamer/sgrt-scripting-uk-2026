"""Start, stop and restart the workshop's MapRT emulator — the same way on a laptop, Binder and Colab.

    python -m sgrt_workshop.emulator start [--scenario NAME]   # Binder's start, the Colab bootstrap
    python -m sgrt_workshop.emulator stop
    python -m sgrt_workshop.emulator status

In a notebook::

    from sgrt_workshop import emulator
    emulator.restart(scenario="slow")    # notebook 07: the appliance misbehaving on purpose
    emulator.restart()                   # back to normal

The emulator runs in the background, detached from whatever started it, so it outlives Binder's
start script and a notebook kernel restart. Its process id, port and scenario are kept in
``.maprt_emulator/workshop.json``, so any later process (another notebook, a terminal) can stop it.
It listens on port 8000, or the next free one in :data:`config.PORTS` if something else holds 8000;
the emulator writes its URL to ``.maprt_emulator/server.json``, where :func:`config.api_url` reads it.
Its log, with the banner it prints at start, is ``.maprt_emulator/emulator.log``. It mints a fresh
token every time it starts and writes it to ``.maprt_emulator/token``; :func:`config.token` reads it.
"""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from sgrt_workshop import config

#: Seconds a map takes to "compute". An appliance takes several; one keeps the wait visible
#: without making a room of students sit through it.
MAP_SECONDS = 1


class EmulatorError(Exception):
    """The emulator could not be started or stopped; the message says why."""


def _state_file(root=None):
    return config.state_dir(root) / "workshop.json"


def _log_file(root=None):
    return config.state_dir(root) / "emulator.log"


def command(scenario=None, root=None, port=None):
    """The command line the emulator is started with, from the workshop folder (:func:`start` runs
    it there). Relative paths, so its banner shows ``Token file  .maprt_emulator/token`` in full."""
    args = [sys.executable, "-m", "maprt_emulator",
            "--host", config.HOST, "--port", str(port or config.PORT),
            "--packs-dir", "packs",
            "--state-dir", ".maprt_emulator",
            "--map-seconds", str(MAP_SECONDS)]
    if scenario:
        args += ["--scenario", scenario]
    return args


def ping(timeout=1.0, root=None):
    """The emulator's ping reply (a dict), or None if nothing answers. Any JSON reply counts as
    answering: just after a restart the token file may still be the previous run's."""
    request = urllib.request.Request(
        f"{config.api_url(root)}/integration/ping",
        headers={"Authorization": f"Bearer {config.token(root, required=False)}",
                 "User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):  # refused, timed out, or not JSON
        return None


def listening(timeout=0.5, port=None, root=None):
    """Whether something (this workshop's emulator or not) accepts connections on ``port``: by
    default the port this workshop's emulator was last started on (8000 if it never was).

    Readiness is checked this way, never with an API call: a scenario can make every call slow
    (``slow``), refuse it (``bad-token``) or use up a limited number of failures (``throttle``), and
    a check that called the API would hang, fail, or spend those failures before the student saw them.
    """
    try:
        with socket.create_connection((config.HOST, port or _port(root)), timeout=timeout):
            return True
    except OSError:
        return False


def _server_pid(root=None):
    """The process id in the ``server.json`` the emulator writes when it starts (or None)."""
    return config.server_info(root).get("pid")


def _port(root=None):
    """The port this workshop's emulator was last started on (the first of :data:`config.PORTS` if
    it never was)."""
    return _read_state(root).get("port") or config.PORT


def running(root=None):
    """Whether *this workshop's* emulator is up: the process it started is the one that wrote
    ``server.json``, and its port answers. Something else on the port doesn't count."""
    pid = _read_state(root).get("pid")
    return bool(pid) and pid == _server_pid(root) and listening(root=root)


def status(root=None):
    """``{"running": bool, "scenario": str | None, "pid": int | None, "port": int}``."""
    state = _read_state(root)
    return {"running": listening(root=root), "scenario": state.get("scenario"), "pid": state.get("pid"),
            "port": _port(root)}


def _read_state(root=None):
    try:
        return json.loads(_state_file(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def start(scenario=None, root=None, wait=60.0, port=None):
    """Start the emulator in the background and wait until it answers.

    If this workshop's emulator is already running (say, left behind by a closed terminal), it is
    used as it is (use :func:`restart` to change its scenario). Otherwise it starts on ``port``
    (default 8000), or, if something else holds that port, on the next free one in
    :data:`config.PORTS`: a busy port never stops the class. Notebooks find the port through
    :func:`config.api_url`. Only when every port in the range is taken does this fail, and it says so.
    """
    if running(root):
        return status(root)
    packs = config.packs_dir(root)
    if not any(packs.glob("*.zip")):
        raise EmulatorError(f"no packs in {packs}: run `python -m sgrt_workshop.packs` first")
    config.state_dir(root).mkdir(parents=True, exist_ok=True)
    preferred = port or config.PORTS[0]
    for candidate in [preferred, *(p for p in config.PORTS if p != preferred)]:
        if listening(port=candidate):
            continue  # held by something else: try the next
        process = _launch(scenario, root, candidate)
        if _wait_until_up(process, candidate, root, wait):
            return status(root)
        if not listening(port=candidate):  # it failed for its own reasons, not a busy port
            raise EmulatorError(f"the emulator stopped at once (exit {process.returncode}):\n{_tail(root)}")
        # Something took the port between the check and the emulator's start: try the next.
    raise EmulatorError(f"ports {config.PORTS[0]}–{config.PORTS[-1]} are all in use by other programs "
                        "(or emulators started from other folders). Close some, then run this again.")


def _launch(scenario, root, port):
    log = open(_log_file(root), "w", encoding="utf-8")  # the child keeps its own handle
    detach = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
              if os.name == "nt" else {"start_new_session": True})
    process = subprocess.Popen(command(scenario, root, port), stdout=log, stderr=subprocess.STDOUT,  # audit: allow subprocesses - sys.executable
                               stdin=subprocess.DEVNULL, cwd=root or config.workshop_root(),
                               **detach)
    log.close()
    _state_file(root).write_text(json.dumps({"pid": process.pid, "port": port, "scenario": scenario}),
                                 encoding="utf-8")
    return process


def _wait_until_up(process, port, root, wait):
    """True once the emulator is up; False if it exited first."""
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        # Up when it has written this run's server.json (and token) and accepts connections.
        if _server_pid(root) == process.pid and listening(port=port):
            return True
        time.sleep(0.25)
    raise EmulatorError(f"the emulator did not answer within {wait:.0f} s:\n{_tail(root)}")


def stop(root=None, wait=15.0):
    """Stop the emulator this workshop started. Never touches anything else: if this workshop's
    emulator isn't running, whatever holds its port is left alone and this just tidies up."""
    port = _port(root)
    if not running(root):
        _state_file(root).unlink(missing_ok=True)
        return
    pid = _read_state(root)["pid"]
    try:
        os.kill(pid, signal.SIGTERM)  # Windows: terminates the process
    except OSError:
        pass
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline and listening(port=port):
        time.sleep(0.25)
    if listening(port=port):
        raise EmulatorError(f"the emulator (process {pid}) did not stop within {wait:.0f} s")
    _state_file(root).unlink(missing_ok=True)


def restart(scenario=None, root=None):
    """Stop the emulator and start it again, with ``scenario`` armed (None: normal operation).

    It comes back on the same port, so a client built before the restart still reaches it."""
    port = _read_state(root).get("port")
    stop(root)
    result = start(scenario, root, port=port)
    print(f"Emulator restarted{f' with the {scenario!r} scenario' if scenario else ''}.")
    return result


def banner(root=None):
    """The banner the emulator printed when it started (its address, the packs, the token)."""
    try:
        text = _log_file(root).read_text(encoding="utf-8")
    except OSError:
        return ""
    end = text.find("Press Ctrl+C to stop the server.")
    return text[:end].rstrip() if end >= 0 else ""


def _tail(root=None, lines=15):
    try:
        return "\n".join(_log_file(root).read_text(encoding="utf-8").splitlines()[-lines:])
    except OSError:
        return "(no log)"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m sgrt_workshop.emulator", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="action", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--scenario")
    sub.add_parser("stop")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    try:
        if args.action == "start":
            start(args.scenario)
            print(f"The emulator is up on {config.api_url()}.")
        elif args.action == "stop":
            stop()
            print("The emulator is stopped.")
        else:
            print(json.dumps(status()))
    except EmulatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
