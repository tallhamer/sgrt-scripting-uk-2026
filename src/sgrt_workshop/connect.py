"""What a notebook needs to talk to the emulator: its URL, the token and the User-Agent."""

from types import SimpleNamespace

from sgrt_workshop import config


def settings():
    """The three things every MapRT call needs, as ``.url``, ``.token`` and ``.user_agent``.

    On a real appliance the URL is its address, the token comes from its administrator, and the
    User-Agent is fixed by the API version. Here they point at the emulator on this machine.
    """
    return SimpleNamespace(url=config.api_url(), token=config.token(), user_agent=config.USER_AGENT)


def connect(**kwargs):
    """A :class:`maprt_client.MapRTClient` for the emulator (keyword arguments are passed on,
    e.g. ``timeout=``). Close it with ``client.close()``, or use it in a ``with`` block."""
    from maprt_client import MapRTClient

    s = settings()
    return MapRTClient(api_url=s.url, token=s.token, user_agent=s.user_agent, **kwargs)
