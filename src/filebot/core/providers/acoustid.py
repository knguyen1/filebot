# Copyright (c) 2025 knguyen1

"""AcoustID music identification client (fingerprint lookup only)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from filebot.core.providers.base import BaseDatasource, MusicIdentificationService
from filebot.core.providers.utils import RateLimiter, is_allowed_http

if TYPE_CHECKING:
    from cachetools import TTLCache


@dataclass(slots=True)
class AcoustIDClient(BaseDatasource, MusicIdentificationService):
    """AcoustID client.

    Parameters
    ----------
    apikey:
        AcoustID API key.
    """

    apikey: str
    _cache_day: TTLCache = field(init=False, repr=False)
    _limiter: RateLimiter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize cache and rate limiter for AcoustID client."""
        # Use short cache for 1 day; no long-lived cache usage here
        self._init_rest(
            short_ttl=24 * 60 * 60,
            long_ttl=24 * 60 * 60,
            maxsize_short=2048,
            maxsize_long=2048,
            rate=(5, 1),
        )

    @property
    def identifier(self) -> str:
        """Return the AcoustID provider identifier."""
        return "AcoustID"

    def lookup(self, duration: int, fingerprint: str) -> dict:
        """Lookup recordings by Chromaprint fingerprint and duration."""
        if duration < 1 or not fingerprint:
            return {}
        url = "http://api.acoustid.org/v2/lookup?" + urlencode({
            "client": self.apikey,
            "meta": "recordings+releases+releasegroups+tracks+compress",
            "duration": duration,
            "fingerprint": fingerprint,
        })
        if not is_allowed_http(url, {"api.acoustid.org"}):
            return {}

        cached = self._cache_day.get(url)
        if cached is not None:
            return cached

        self._limiter.acquire()

        req = Request(url, headers={"Accept-Encoding": "gzip"})  # noqa: S310
        try:
            with urlopen(req, timeout=20) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
                self._cache_day[url] = data
                return data
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return {}
