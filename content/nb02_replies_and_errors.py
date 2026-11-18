"""02 · Replies and errors: the envelope by hand, then maprt-client."""

from ._common import exercise, header

CELLS = [
    *header(2, "Replies and errors",
            "How MapRT says yes and no, and a library that handles the plumbing for you."),
    ("md", """\
## The reply envelope

Every MapRT reply (all but one, as notebook 05 shows) comes wrapped in the same five fields:

| Field | Meaning |
|---|---|
| `success` | `True` if the request worked |
| `data` | the answer, when it worked |
| `errorCode` | what went wrong, when it didn't (e.g. `InvalidClientToken`) |
| `errorCodeType` | the family the error belongs to (e.g. `AuthErrorCodes`) |
| `errorData` | more detail; in practice always `null` |

Let's ask for the list of treatment rooms, by hand with `httpx2` as in notebook 01:"""),
    ("code", """\
import httpx2
from sgrt_workshop import settings

s = settings()
headers = {"Authorization": f"Bearer {s.token}", "User-Agent": s.user_agent}

reply = httpx2.get(f"{s.url}/integration/rooms", headers=headers).json()

print("success:", reply["success"])
print("rooms:  ", len(reply["data"]))
reply["data"][0]"""),
    ("md", """\
## When it doesn't work

Now ask for the surfaces of a patient who doesn't exist:"""),
    ("code", """\
reply = httpx2.get(f"{s.url}/integration/patients/ANON-999/surfaces", headers=headers).json()
reply"""),
    ("md", """\
Notice there's **no `data` at all**, and the HTTP status was still 200. `errorCode` says what
happened (`PatientNotFoundInDatabase`) and `errorCodeType` the kind of problem
(`PatientErrorCodes`).

So every call needs the same check: *did it work?* before *what's in it?*. A small function does
that once, for every call:"""),
    ("code", """\
def get_data(path):
    \"\"\"GET a MapRT endpoint and return its data, or raise an error saying what went wrong.\"\"\"
    reply = httpx2.get(f"{s.url}{path}", headers=headers).json()
    if not reply["success"]:
        raise RuntimeError(f"{reply['errorCodeType']}: {reply['errorCode']}")
    return reply["data"]


print(len(get_data("/integration/rooms")), "rooms")

try:
    get_data("/integration/patients/ANON-999/surfaces")
except RuntimeError as error:
    print("MapRT said no:", error)"""),
    ("md", """\
That is the heart of every MapRT client: add the headers, send the request, check `success`, turn
the reply into something useful. A real one also checks the HTTP status (an overloaded server
answers `503`, notebook 07) and parses each endpoint's data.

## maprt-client: the same, done for you

**`maprt-client`** is a small library that does all of that for every MapRT endpoint. From now on
we'll use it, so the notebooks can be about MapRT rather than HTTP. `connect()` makes a client set
up for the emulator: it's the same three settings as before."""),
    ("code", """\
from sgrt_workshop import connect

client = connect()

print(client.get_status())
rooms = client.get_treatment_rooms()
rooms[:3]"""),
    ("md", """\
Each room comes back as a plain Python *tuple*: `(name, id, coordinate system)`. Nothing about it
is magic; `connect()` is just this:"""),
    ("code", """\
from maprt_client import MapRTClient

same_client = MapRTClient(api_url=s.url, token=s.token, user_agent=s.user_agent)
print(same_client.get_status())
same_client.close()"""),
    ("md", """\
## Errors, typed

When MapRT says no, `maprt-client` raises a **`MapRTApiError`**. It carries the error code, its
family, and a `category` that tells your code what kind of problem it is:"""),
    ("code", """\
from maprt_client import MapRTApiError

try:
    client.get_patient_surfaces("ANON-999")
except MapRTApiError as error:
    print("message:      ", error)
    print("error code:   ", error.error_code)
    print("category:     ", error.category)"""),
    ("md", """\
| `category` | Means | What a script should do |
|---|---|---|
| `auth` | bad or expired token, or wrong User-Agent | stop, and fix the settings |
| `license` | the appliance isn't licensed for this feature | report it: it is *not* a "no" |
| `client` | the request was wrong (unknown patient, bad data) | fix the request |
| `server` | the appliance failed or is busy | wait and try again (notebook 07) |

`try` / `except` is how Python lets you decide what happens when something goes wrong, instead of
the notebook stopping with a red error."""),
    *exercise(
        """\
        Write a function `surfaces_or_none(client, patient_id)` that returns the patient's surfaces,
        or `None` if MapRT says the patient doesn't exist (`error_code == "PatientNotFoundInDatabase"`).
        Any other error should still be raised. Try it with `"ANON-005"` and `"ANON-999"`.""",
        """\
        def surfaces_or_none(client, patient_id):
            try:
                return client.get_patient_surfaces(patient_id)
            except MapRTApiError as error:
                if error.error_code == "PatientNotFoundInDatabase":
                    return None
                raise

        print(surfaces_or_none(client, "ANON-005"))   # one surface
        print(surfaces_or_none(client, "ANON-999"))   # None""",
    ),
]
