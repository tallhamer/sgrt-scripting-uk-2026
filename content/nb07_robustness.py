"""07 · Robustness: slow replies, a busy server, refusals, a cut-off map, and recording a session."""

from ._common import exercise, header

CELLS = [
    *header(7, "Robustness", "What to do when the appliance is slow, busy, refuses, or sends half an answer."),
    ("md", """\
A script that only works when everything goes right isn't finished. A real appliance is sometimes
slow, sometimes busy, may not be licensed for every feature, and a network can drop a reply
halfway through. You can't make that happen on a real system when you want to, but you can on the
emulator: it has scenarios, and this notebook restarts it with one at a time.

**Restarting the emulator gives it a new token**, so after each restart we make a new client with
`connect()`, which reads the new token."""),
    ("code", """\
import time

from maprt_client import MapRTApiError, build_map_request
from sgrt_workshop import connect, emulator"""),
    ("md", """\
## 1. A slow reply: timeouts

A client waits a limited time for each reply: its **timeout**. Too short, and a working appliance
looks broken. A GetMap call against a real appliance may take many seconds to over a minute. The
`slow` scenario adds 8 seconds to every reply:"""),
    ("code", """\
import httpx2

emulator.restart(scenario="slow")

impatient = connect(timeout=3)          # waits 3 seconds
try:
    impatient.get_treatment_rooms()
except httpx2.ReadTimeout:
    print("Gave up after 3 seconds: the reply hadn't arrived.")"""),
    ("code", """\
patient = connect(timeout=30)           # waits 30 seconds
start = time.monotonic()
rooms = patient.get_treatment_rooms()
print(f"{len(rooms)} rooms after {time.monotonic() - start:.0f} seconds.")"""),
    ("md", """\
`maprt-client` waits 120 seconds by default. Choose a timeout from how long the appliance really
takes, not from how long you'd like to wait.

## 2. A busy server: try again, a little later

A server that can't take a request right now answers HTTP **503**, often with a `Retry-After`
header saying how many seconds to wait. The `throttle` scenario does that twice, then recovers:"""),
    ("code", """\
emulator.restart(scenario="throttle")
client = connect()

for attempt in range(1, 6):
    try:
        rooms = client.get_treatment_rooms()
        print(f"Attempt {attempt}: {len(rooms)} rooms.")
        break
    except MapRTApiError as error:
        if error.http_status != 503:
            raise
        wait = 2 ** (attempt - 1)               # 1, 2, 4, 8... seconds
        print(f"Attempt {attempt}: busy (HTTP 503). Waiting {wait} s.")
        time.sleep(wait)"""),
    ("md", """\
Waiting longer each time (*exponential backoff*) gives a busy server room to recover, and a limit
on the attempts stops a script from trying forever.

## 3. "Not licensed" is not "no"

Some MapRT features are licensed separately. Without the license, the appliance refuses with
`FeatureNotLicensed`, in the `license` category:"""),
    ("code", """\
emulator.restart(scenario="unlicensed-map")
client = connect()

room_name, room_id, _ = client.get_treatment_rooms()[0]
surface_id, _ = client.get_patient_surfaces("ANON-001-SLIM")[0]
_, (_, request) = build_map_request(
    isocenter=[0.0, 98.6, -1.71],
    couch_buffer=2,      # cm
    patient_buffer=2,    # cm
    surface_id=surface_id,
    room_id=room_id,
    room_scale="IEC_61217",
    patient_orientation="HFS",
)

try:
    client.get_map(request)
except MapRTApiError as error:
    print(error.category, error.error_code)"""),
    ("md", """\
A script must report this as "MapRT won't say", **never** as "collision" or "unsafe". The same goes
for GetBeamDeliveryStatus: a withheld verdict is not a failed one.

## 4. Half a map

The `truncate-map` scenario cuts the map off before its last line, as a dropped connection would.
Ask for the map:"""),
    ("code", """\
from maprt_client import IncompleteMapError

emulator.restart(scenario="truncate-map")
client = connect()

try:
    client.get_map(request)
except IncompleteMapError as error:
    print("Refused:", error)"""),
    ("md", """\
`maprt-client` refuses it. Here is why. A complete map ends with a line saying `DONE`; this reply
just stops:"""),
    ("code", """\
text = client.send("POST", "/integration/GetMap", request).text

print("Ends with DONE?", text.rstrip().endswith("DONE"))
print("Last characters:", repr(text[-30:]))"""),
    ("md", """\
Without that check, the reply would still look like a map: about half the gantry angles would
simply be missing, and a script reading them would treat them as collisions, or worse, read the
wrong angle. (Older versions of `maprt-client` did exactly that.) If you ever parse MapRT's map
text yourself, check for `DONE` first."""),
    ("md", """\
## 5. Recording a session

When something goes wrong with a real appliance, the most useful thing you can send to whoever
helps you is **exactly what was asked and answered**. `maprt-client` can record every call to a
folder: set the client's `recorder`. The token is never written to the recording."""),
    ("code", """\
import uuid
from datetime import date

from maprt_client import SessionRecorder
from sgrt_workshop import config

emulator.restart()                      # back to normal
client = connect()

client.recorder = SessionRecorder(config.workshop_root() / "recordings", uuid.uuid4(), date.today())
client.get_status()
client.get_treatment_rooms()
client.get_patient_surfaces("ANON-005")
client.recorder.write_readme()

print("Recorded in", client.recorder.session_dir)
for path in sorted(client.recorder.session_dir.iterdir()):
    print("  ", path.name)"""),
    ("md", """\
One request file and one response file per call, plus a README describing the session. The folder
is `recordings` in the workshop folder (on Binder and Colab, in the file panel)."""),
    *exercise(
        """\
        Write a function `with_retry(call, attempts=5)` that runs `call()` and, whenever it raises a
        `MapRTApiError` with `http_status` 503, waits (1, 2, 4... seconds) and tries again, up to
        `attempts` times. Any other error should be raised at once.

        Test it under the `throttle` scenario with `with_retry(client.get_treatment_rooms)`, then
        put the emulator back to normal with `emulator.restart()`.""",
        """\
        def with_retry(call, attempts=5):
            for attempt in range(attempts):
                try:
                    return call()
                except MapRTApiError as error:
                    if error.http_status != 503 or attempt == attempts - 1:
                        raise
                    time.sleep(2 ** attempt)

        emulator.restart(scenario="throttle")
        client = connect()
        print(len(with_retry(client.get_treatment_rooms)), "rooms")
        emulator.restart()""",
    ),
]
