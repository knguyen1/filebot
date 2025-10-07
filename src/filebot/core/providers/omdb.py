# Copyright (c) 2025 knguyen1

"""OMDb movie identification service."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from filebot.core.models import Movie
from filebot.core.providers.base import (
    BaseDatasource,
    MovieIdentificationService,
    RestClientMixin,
)

if TYPE_CHECKING:
    from cachetools import TTLCache

    from filebot.core.providers.utils import RateLimiter


@dataclass(slots=True)
class OMDbClient(BaseDatasource, RestClientMixin, MovieIdentificationService):
    """OMDb client.

    Parameters
    ----------
    apikey:
        OMDb API key.
    """

    apikey: str
    _cache_short: TTLCache = field(init=False, repr=False)
    _limiter: RateLimiter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize cache and rate limiter for OMDb client."""
        # OMDb results change, but daily cache is fine for most workflows
        self._init_rest(
            short_ttl=24 * 60 * 60,
            long_ttl=24 * 60 * 60,
            maxsize_short=4096,
            maxsize_long=4096,
            rate=(2, 1),
        )

    @property
    def identifier(self) -> str:
        """Return the OMDb provider identifier."""
        return "OMDb"

    def search_movie(self, query: str, locale: str) -> list[Movie]:
        """Search movies by name and optional year suffix."""
        name, year = _split_name_year(query)
        params: dict[str, Any] = {"s": name, "type": "movie", "apikey": self.apikey}
        if year is not None:
            params["y"] = year
        data = self._request(params)
        out: list[Movie] = []
        for it in data.get("Search") or []:
            try:
                if (it.get("Type") or "").lower() != "movie":
                    continue
                title = it.get("Title") or ""
                year_str = it.get("Year") or ""
                imdbid = (it.get("imdbID") or "").replace("tt", "")
                out.append(
                    Movie(
                        name=title,
                        alias_names=[],
                        year=int(year_str) if year_str.isdigit() else None,
                        imdb_id=int(imdbid) if imdbid.isdigit() else None,
                        tmdb_id=None,
                        language=None,
                    )
                )
            except (TypeError, ValueError):
                continue
        return out

    def get_movie_descriptor(self, movie: Movie, locale: str) -> Movie | None:
        """Get canonical movie data by IMDb ID."""
        if not movie.imdb_id:
            return None
        params = {"i": f"tt{movie.imdb_id:07d}", "apikey": self.apikey}
        data = self._request(params)
        if (data.get("Response") or "").lower() != "true":
            return None
        title = (data.get("Title") or "").strip()
        year_str = data.get("Year") or ""
        return Movie(
            name=title,
            alias_names=[],
            year=int(year_str)
            if isinstance(year_str, str) and year_str.isdigit()
            else movie.year,
            imdb_id=movie.imdb_id,
            tmdb_id=None,
            language=locale or None,
        )

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        url = "https://www.omdbapi.com/?" + urlencode(params)
        return self._http_get_json(url, timeout=15, long_ttl=False, require_https=True)


def _split_name_year(query: str) -> tuple[str, int | None]:
    m = re.match(r"(.+?)\s+(19\d{2}|20\d{2})$", query.strip())
    if m:
        try:
            return m.group(1).strip(), int(m.group(2))
        except ValueError:
            return query.strip(), None
    return query.strip(), None
