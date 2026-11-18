"""01 · Setup and token: the three things every call needs, and a first call with plain httpx2."""

from ._common import exercise, header

CELLS = [
    *header(1, "Setup and token", "The three things every MapRT call needs, and your first call."),
    ("md", """\
## Three things every call needs

Every request to the MapRT API carries the same three things:

1. **The address** of the appliance (its *base URL*). Every endpoint hangs off it: the ping is at
   `<base URL>/integration/ping`.
2. **A token**, sent in the `Authorization` header as `Bearer <token>`. It is how the appliance
   knows the caller is allowed in. On a real appliance it is issued to you (see *Where the token
   comes from*, below) and is a **secret**, like a password: never paste it into a notebook you
   share or email.
3. **A User-Agent**, a header naming the client. MapRT only answers clients that say they speak
   its API version: `VisionRT.Integration.Saturn/2.0.0`.

## Where the token comes from

On a real appliance, the token is set in MapRT's API configuration. It is given to you by the
Vision RT installer, a Vision RT Field Service Engineer (FSE), or your IT system administrator.

The emulator makes a **new token every time it starts**. It prints it when it starts, and writes
it to a file, `.maprt_emulator/token`, in the workshop's folder:"""),
    ("code", """\
from sgrt_workshop import config

print(config.token_file())"""),
    ("md", """\
`settings()` reads that file each time it's called, so it always has the token of the emulator
that is running now. Here are the three settings:"""),
    ("code", """\
from sgrt_workshop import settings

s = settings()
print("Base URL:  ", s.url)
print("Token:     ", s.token[:6] + "…")   # never print a real token in full
print("User-Agent:", s.user_agent)"""),
    ("md", """\
**Never type a token into your code.** This one changes every time the emulator restarts, so a
copied token stops working; and a real appliance's token is a secret, which a notebook you share
or email would give away. Read it from somewhere instead: a file, as here, or an environment
variable. On a real appliance only the values change: the URL is the appliance's address (and
starts with `https://`), and the token is the one you were given by the Vision RT installer, a
Vision RT Field Service Engineer (FSE), or your IT system administrator."""),
    ("md", """\
## Choosing your own token (running the emulator yourself)

When you run the emulator on your own laptop, after the course for instance, you can give it a
**fixed token** instead of a new one each time: handy while you write your own scripts. There are
two ways, both typed in a terminal in the workshop folder.

**Start the emulator directly**, with `--token`:

```console
uv run maprt-emulator --packs-dir packs --token my-workshop-token
```

**Or set the `MAPRT_EMULATOR_TOKEN` environment variable** before starting the workshop. The
emulator uses it as its token, and the notebooks read the same variable, so they still match:

```console
export MAPRT_EMULATOR_TOKEN=my-workshop-token        # macOS and Linux
$env:MAPRT_EMULATOR_TOKEN = "my-workshop-token"      # Windows PowerShell
uv run sgrt-workshop
```

A fixed token is fine for an emulator on your own computer, which nothing else can reach. A real
appliance's token still comes from its API configuration (see *Where the token comes from*),
and is still a secret.

## Your first call

`httpx2` is a Python library for HTTP, the protocol web browsers use. We'll use it directly, so
you see exactly what goes over the wire. The **ping** endpoint answers "I'm here, and this is my
API version":"""),
    ("code", """\
import httpx2

headers = {
    "Authorization": f"Bearer {s.token}",
    "User-Agent": s.user_agent,
}

response = httpx2.get(f"{s.url}/integration/ping", headers=headers)

print("HTTP status:", response.status_code)
print(response.text)"""),
    ("md", """\
**200** is HTTP's "OK". The reply itself is **JSON**, a text format for data, which Python turns
into a dictionary:"""),
    ("code", """\
reply = response.json()
reply"""),
    ("code", """\
print("Did it work?", reply["success"])
print("API version:", reply["data"])"""),
    ("md", """\
Every MapRT reply is wrapped like this: `success` says whether it worked, `data` holds the answer,
and the `error…` fields say what went wrong when it didn't. Notebook 02 is all about that wrapper.

## What happens when something is missing

Leave out the User-Agent, and see what the appliance says:"""),
    ("code", """\
no_user_agent = {"Authorization": f"Bearer {s.token}"}

response = httpx2.get(f"{s.url}/integration/ping", headers=no_user_agent)
print("HTTP status:", response.status_code)
response.json()"""),
    ("md", """\
Look closely: the HTTP status is still **200**, but `success` is `False`, and `errorCode` says
why: `VersionMismatch`. MapRT reports most problems this way, *inside* a successful HTTP reply. A
script that only checks the status code would think this worked.

Now a wrong token:"""),
    ("code", """\
wrong_token = {"Authorization": "Bearer not-the-right-token", "User-Agent": s.user_agent}

httpx2.get(f"{s.url}/integration/ping", headers=wrong_token).json()"""),
    ("md", """\
`InvalidClientToken`: the appliance won't talk to you. On a real system that's what an expired or
mistyped token looks like.

## A note on real appliances

A real appliance uses `https://` with a certificate the hospital made itself, which Python won't
trust by default. Clients for MapRT therefore switch certificate checking off
(`httpx2.Client(verify=False)`); the `maprt-client` library in the next notebook does it for you.
That is one more reason to use the API only on the hospital network the appliance lives on."""),
    *exercise(
        """\
        Write a function `ping(url, token, user_agent)` that calls the ping endpoint and returns
        `True` if the reply's `success` is `True`, and `False` otherwise. Then call it twice: once
        with the emulator's settings, and once with a wrong token.""",
        """\
        def ping(url, token, user_agent):
            headers = {"Authorization": f"Bearer {token}", "User-Agent": user_agent}
            reply = httpx2.get(f"{url}/integration/ping", headers=headers).json()
            return reply["success"]

        print(ping(s.url, s.token, s.user_agent))        # True
        print(ping(s.url, "wrong", s.user_agent))        # False""",
    ),
]
