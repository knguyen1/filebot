# Copyright (c) 2025 knguyen1
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Core providers base module."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from filebot.core.models import (
        Artwork,
        Episode,
        Movie,
        SearchResult,
        SeriesInfo,
        SubtitleSearchResult,
    )


@runtime_checkable
class Datasource(Protocol):
    """Generic data source interface.

    Notes
    -----
    Pure typing protocol to decouple UI from provider implementations.
    """

    @property
    def identifier(self) -> str:
        """Unique provider identifier (e.g., "TheMovieDB")."""

    def get_icon(self) -> object | None:
        """Return optional icon handle for UI layers.

        Returns
        -------
        object | None
            UI-specific icon object if available; otherwise None.
        """


class BaseDatasource(ABC):
    """Minimal base class offering a default `name`.

    Subclasses should define `identifier` and may override `get_icon`.
    """

    @property
    @abstractmethod
    def identifier(self) -> str:  # pragma: no cover - abstract contract
        """Unique provider identifier."""

    def get_icon(self) -> object | None:  # pragma: no cover - UI concern
        """Return default icon (None) for base implementation.

        Returns
        -------
        None
            Base implementation returns None.
        """
        return None

    @property
    def name(self) -> str:
        """Human-readable provider name.

        Returns
        -------
        str
            Defaults to `identifier`.
        """
        return self.identifier


@runtime_checkable
class MovieIdentificationService(Datasource, Protocol):
    """Movie identification service contract.

    Implementations should map queries to `Movie` descriptors and enrich
    partial movie descriptors with canonical identifiers.
    """

    def search_movie(self, query: str, locale: str) -> list[Movie]:
        """Search for movies by free-form query.

        Parameters
        ----------
        query:
            Free-form user query, optionally including year.
        locale:
            BCP-47 language tag (e.g., "en-US").

        Returns
        -------
        list[Movie]
            Candidate matches.
        """

    def get_movie_descriptor(self, movie: Movie, locale: str) -> Movie | None:
        """Resolve a `Movie` to a canonical descriptor if possible.

        Parameters
        ----------
        movie:
            Movie with partial identifiers (e.g., TMDb ID, IMDb ID).
        locale:
            Preferred language.

        Returns
        -------
        Movie | None
            Canonical movie descriptor or None if not found.
        """


@runtime_checkable
class EpisodeListProvider(Datasource, Protocol):
    """Episode list provider contract for TV series data."""

    def has_season_support(self) -> bool:
        """Whether provider exposes explicit season structures."""

    def search(self, query: str, locale: str) -> list[SearchResult]:
        """Search for series by name."""

    def get_episode_list(
        self, series: SearchResult | int, order: str, locale: str
    ) -> list[Episode]:
        """Fetch episodes for a series (by `SearchResult` or numeric ID)."""

    def get_series_info(self, series: SearchResult | int, locale: str) -> SeriesInfo:
        """Fetch series information (by `SearchResult` or numeric ID)."""

    def get_episode_list_link(self, series: SearchResult) -> str:
        """Return public episode list URL for the given series."""


@runtime_checkable
class ArtworkProvider(Datasource, Protocol):
    """Artwork provider contract."""

    def get_artwork(self, media_id: int, category: str, locale: str) -> list[Artwork]:
        """Return artwork for the given id and category."""


@runtime_checkable
class MusicIdentificationService(Datasource, Protocol):
    """Music identification service contract (e.g., AcoustID)."""

    def lookup(self, duration: int, fingerprint: str) -> dict:
        """Lookup recording by Chromaprint fingerprint."""


@runtime_checkable
class SubtitleProvider(Datasource, Protocol):
    """Subtitle provider contract."""

    def search(self, query: str) -> list[SubtitleSearchResult]:
        """Search subtitles by free-form query."""


class RestClientMixin:
    """Shared REST client helper for JSON GET with caching and rate limiting.

    Attributes
    ----------
    _cache_short:
        Short-lived cache (e.g., 1 day) for search endpoints.
    _cache_long:
        Long-lived cache (e.g., 1 week) for descriptor endpoints.
    _limiter:
        Rate limiter to protect external APIs.
    """

    def _http_get_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 15,
        cache_key: str | None = None,
        long_ttl: bool = False,
        require_https: bool = True,
        allowed_http_hosts: set[str] | None = None,
    ) -> dict:
        """Perform a GET request and return parsed JSON with cache / rate limit.

        Parameters
        ----------
        url:
            Full request URL.
        headers:
            Optional request headers.
        timeout:
            Timeout in seconds.
        cache_key:
            Optional key for caching; defaults to the URL string.
        long_ttl:
            Use the long-lived cache if True, else the short-lived cache.
        require_https:
            If True, only allow HTTPS URLs.
        allowed_http_hosts:
            If set, allow HTTP only for hosts in this set.

        Returns
        -------
        dict
            Parsed JSON object or empty dict on error.
        """
        from filebot.core.providers.utils import is_allowed_http, is_https

        # Validate scheme
        if require_https and not is_https(url):
            return {}
        if not require_https and not (
            is_https(url) or is_allowed_http(url, allowed_http_hosts)
        ):
            return {}

        # Select cache
        cache = getattr(self, "_cache_long" if long_ttl else "_cache_short")
        key = cache_key or url
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Rate limit before network call
        limiter = getattr(self, "_limiter", None)
        if limiter is not None:
            limiter.acquire()

        # Only allow http(s) via earlier guards
        req = Request(url, headers=headers or {})  # noqa: S310
        try:
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
                cache[key] = data
                return data
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            ).warning(
                "http_json_request_failed",
                extra={
                    "url": url,
                    "require_https": require_https,
                    "long_ttl": long_ttl,
                },
                exc_info=True,
            )
            return {}

    def _http_get_bytes(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: int = 15,
        cache_key: str | None = None,
        long_ttl: bool = False,
        require_https: bool = True,
        allowed_http_hosts: set[str] | None = None,
    ) -> bytes | None:
        """Perform a GET request and return raw bytes with cache / rate limit."""
        from filebot.core.providers.utils import is_allowed_http, is_https

        if require_https and not is_https(url):
            return None
        if not require_https and not (
            is_https(url) or is_allowed_http(url, allowed_http_hosts)
        ):
            return None

        cache = getattr(self, "_cache_long" if long_ttl else "_cache_short")
        key = cache_key or url
        cached = cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        limiter = getattr(self, "_limiter", None)
        if limiter is not None:
            limiter.acquire()

        req = Request(url, headers=headers or {})  # noqa: S310
        try:
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310
                data = resp.read()
                cache[key] = data
                return data
        except (HTTPError, URLError, TimeoutError):
            logging.getLogger(
                f"{self.__class__.__module__}.{self.__class__.__name__}"
            ).warning(
                "http_bytes_request_failed",
                extra={
                    "url": url,
                    "require_https": require_https,
                    "long_ttl": long_ttl,
                },
                exc_info=True,
            )
            return None
