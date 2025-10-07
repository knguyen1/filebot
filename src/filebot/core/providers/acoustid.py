# Copyright (c) 2025 knguyen1

"""AcoustID music identification client (fingerprint lookup only)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cachetools import TTLCache

from filebot.core.providers.base import BaseDatasource, MusicIdentificationService
from filebot.core.providers.utils import RateLimiter, is_allowed_http


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
        self._cache_day = TTLCache(maxsize=2048, ttl=24 * 60 * 60)
        # Public API docs suggest practical limits; be conservative
        self._limiter = RateLimiter(max_requests=5, window_seconds=1)

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
