# Copyright (c) 2025 knguyen1

"""OpenSubtitles provider with REST tag search.

Implements tag-based search via `rest.opensubtitles.org` with caching and
rate limiting. XML-RPC features (login, upload, language map) can be added in
future phases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from filebot.core.models import SubtitleSearchResult
from filebot.core.providers.base import (
    BaseDatasource,
    RestClientMixin,
    SubtitleProvider,
)
from filebot.core.providers.utils import RateLimiter, compute_opensubtitles_hash

if TYPE_CHECKING:
    from cachetools import TTLCache


@dataclass(slots=True)
class OpenSubtitlesClient(BaseDatasource, RestClientMixin, SubtitleProvider):
    """OpenSubtitles client (REST tag search)."""

    app_name: str
    app_version: str
    _cache_short: TTLCache = field(init=False, repr=False)
    _cache_long: TTLCache = field(init=False, repr=False)
    _limiter: RateLimiter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize caches and rate limiter."""
        self._init_rest(short_ttl=24 * 60 * 60, long_ttl=7 * 24 * 60 * 60, rate=(5, 1))

    @property
    def identifier(self) -> str:
        """Return the OpenSubtitles provider identifier."""
        return "OpenSubtitles"

    def search(self, query: str) -> list[SubtitleSearchResult]:
        """Search subtitles by free-form tag using the REST API.

        Parameters
        ----------
        query:
            Free-form tag (typically file name without extension).

        Returns
        -------
        list[SubtitleSearchResult]
            Subtitle results if any.
        """
        if not query.strip():
            return []

        # Build REST endpoint
        # Docs: https://trac.opensubtitles.org/projects/opensubtitles/wiki/DevReadFirst
        # Endpoint pattern: /search/query-<tag>
        tag = quote(query.strip())
        url = f"https://rest.opensubtitles.org/search/query-{tag}"

        headers = {
            # Required User-Agent format similar to Java client
            "User-Agent": f"{self.app_name} v{self.app_version}",
            "Accept": "application/json",
        }

        data: Any = self._http_get_json(
            url, headers=headers, timeout=20, long_ttl=False, require_https=True
        )
        if not isinstance(data, list):
            return []

        results: list[SubtitleSearchResult] = []
        for it in data:
            if not isinstance(it, dict):
                continue
            name = (it.get("SubFileName") or "").strip()
            lang = it.get("SubLanguageID") or None
            imdb_raw = it.get("IDMovieImdb")
            imdb_id = None
            if isinstance(imdb_raw, (int, str)) and str(imdb_raw).isdigit():
                imdb_id = int(imdb_raw)
            url_dl = it.get("ZipDownloadLink") or it.get("SubDownloadLink") or None
            score = None
            sr = SubtitleSearchResult(
                name=name or query,
                lang=lang,
                imdb_id=imdb_id,
                tmdb_id=None,
                score=score,
                url=url_dl,
            )
            results.append(sr)

        return results

    def search_by_hash(
        self, file_path: str, locale: str | None = None
    ) -> list[SubtitleSearchResult]:
        """Search subtitles by OpenSubtitles movie hash.

        Parameters
        ----------
        file_path:
            Absolute path to the target video file.
        locale:
            Optional language code; when provided, may bias results.
        """
        if not file_path:
            return []
        hash_hex, size = compute_opensubtitles_hash(file_path)
        # Endpoint: /search/moviebytesize-<size>/moviehash-<hash>
        url = f"https://rest.opensubtitles.org/search/moviebytesize-{size}/moviehash-{hash_hex}"
        headers = {
            "User-Agent": f"{self.app_name} v{self.app_version}",
            "Accept": "application/json",
        }
        data: Any = self._http_get_json(
            url, headers=headers, timeout=20, long_ttl=False, require_https=True
        )
        if not isinstance(data, list):
            return []
        out: list[SubtitleSearchResult] = []
        for it in data:
            if not isinstance(it, dict):
                continue
            name = (it.get("SubFileName") or "").strip()
            lang = it.get("SubLanguageID") or None
            imdb_raw = it.get("IDMovieImdb")
            imdb_id = None
            if isinstance(imdb_raw, (int, str)) and str(imdb_raw).isdigit():
                imdb_id = int(imdb_raw)
            url_dl = it.get("ZipDownloadLink") or it.get("SubDownloadLink") or None
            out.append(
                SubtitleSearchResult(
                    name=name or file_path,
                    lang=lang,
                    imdb_id=imdb_id,
                    tmdb_id=None,
                    score=None,
                    url=url_dl,
                )
            )
        return out
