"""Helpers for the SGRT Scripting Workshop (UK, December 2026).

Only what a notebook shouldn't have to show: where the emulator is and how to start it, fetching
the session packs, and drawing. Every MapRT call in the notebooks is written out in the notebook
itself — first with plain ``httpx2``, then with ``maprt-client``.
"""

from sgrt_workshop.config import USER_AGENT, api_url, token
from sgrt_workshop.connect import connect, settings

__all__ = ["USER_AGENT", "api_url", "token", "connect", "settings"]
