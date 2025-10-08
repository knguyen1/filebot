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

"""Core providers TMDB module."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from filebot.core.models import MOVIE_DB_IDENTIFIER, Movie
from filebot.core.providers.base import (
    BaseDatasource,
    MovieIdentificationService,
    RestClientMixin,
)

# TMDb API URLs
_TMDB_BASE_URL = "https://api.themoviedb.org/3/"

if TYPE_CHECKING:
    from cachetools import TTLCache

    from filebot.core.providers.utils import RateLimiter


@dataclass(slots=True)
class TMDbClient(BaseDatasource, RestClientMixin, MovieIdentificationService):
    """Minimal TMDb client stub.

    Parameters
    ----------
    apikey:
        TMDb API key.
    """

    apikey: str
    _cache_short: TTLCache = field(init=False, repr=False)
    _cache_long: TTLCache = field(init=False, repr=False)
    _limiter: RateLimiter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize caches and rate limiter for TMDb client."""
        self._init_rest(
            short_ttl=24 * 60 * 60,
            long_ttl=7 * 24 * 60 * 60,
            rate=(35, 10),
        )

    @property
    def identifier(self) -> str:
        """Return the unique provider identifier.

        Returns
        -------
        str
            The Movie Database identifier.
        """
        return MOVIE_DB_IDENTIFIER

    # --- MovieIdentificationService ---
    def search_movie(self, query: str, locale: str) -> list[Movie]:
        """Search for movies by free-form query via TMDb v3 API.

        Parameters
        ----------
        query:
            Free-form query, optionally including a 4-digit year.
        locale:
            BCP-47 language tag (e.g., "en-US").

        Returns
        -------
        list[Movie]
            Candidate matches with TMDb IDs populated.
        """
        movie_name, movie_year = _split_name_and_year(query)
        params: dict[str, Any] = {"query": movie_name}
        if movie_year is not None:
            params["year"] = movie_year

        json_data = self._request_json("search/movie", params, locale)
        results = json_data.get("results") or []

        movies: list[Movie] = []
        for it in results:
            try:
                tmdb_id = int(it["id"])  # KeyError/ValueError handled below
                title = it.get("title") or it.get("original_title") or ""
                release_date = it.get("release_date") or ""
                year = int(release_date[:4]) if len(release_date) >= 4 else None
                movies.append(
                    Movie(
                        name=title,
                        alias_names=[],
                        year=year,
                        imdb_id=None,
                        tmdb_id=tmdb_id,
                        language=locale,
                    )
                )
            except (KeyError, ValueError, TypeError):
                # Skip malformed entries from API
                continue
        return movies

    def get_movie_descriptor(self, movie: Movie, locale: str) -> Movie | None:
        """Resolve a canonical TMDb movie descriptor from IDs.

        Parameters
        ----------
        movie:
            Movie with `tmdb_id` or `imdb_id` populated.
        locale:
            Preferred language.

        Returns
        -------
        Movie | None
            Canonicalized movie descriptor or None if not found.
        """
        tmdb_id = movie.tmdb_id
        if tmdb_id is None and movie.imdb_id is not None:
            # Resolve TMDb ID from IMDb ID first (tt-prefixed)
            imdb_code = f"tt{movie.imdb_id:07d}"
            data = self._request_json(
                "find/" + imdb_code,
                {"external_source": "imdb_id"},
                locale,
            )
            matches = data.get("movie_results") or []
            if matches:
                with_id = matches[0]
                try:
                    tmdb_id = int(with_id["id"])  # type: ignore[assignment]
                except (KeyError, ValueError, TypeError):
                    tmdb_id = None

        if tmdb_id is None:
            return None

        info = self._request_json(f"movie/{tmdb_id}", {}, locale)
        try:
            title = (info.get("title") or info.get("original_title") or "").strip()
            release_date = info.get("release_date") or ""
            year = int(release_date[:4]) if len(release_date) >= 4 else movie.year
            imdb_code = info.get("imdb_id")
            if (
                isinstance(imdb_code, str)
                and imdb_code.startswith("tt")
                and imdb_code[2:].isdigit()
            ):
                imdb_id_val = int(imdb_code[2:])
            else:
                imdb_id_val = movie.imdb_id
            return Movie(
                name=title,
                alias_names=[],
                year=year,
                imdb_id=imdb_id_val,
                tmdb_id=tmdb_id,
                language=locale,
            )
        except (ValueError, TypeError, AttributeError, KeyError):
            return None

    # --- Internal helpers ---
    def _request_json(
        self, path: str, params: dict[str, Any], locale: str
    ) -> dict[str, Any]:
        """Issue a GET request to TMDb v3 and return parsed JSON.

        Parameters
        ----------
        path:
            API path segment after `/3/` (e.g., `search/movie`).
        params:
            Query parameters to include with the request.
        locale:
            BCP-47 language to pass via `language` parameter.

        Returns
        -------
        dict[str, Any]
            Parsed JSON; empty dict on HTTP errors.
        """
        base = _TMDB_BASE_URL
        query = {"api_key": self.apikey}
        if locale:
            query["language"] = _normalize_language(locale)
        query.update(params)
        url = base + path + "?" + urlencode(query)

        return self._http_get_json(
            url,
            timeout=15,
            long_ttl=not path.startswith("search/"),
            require_https=True,
        )


def _split_name_and_year(query: str) -> tuple[str, int | None]:
    """Split free-form movie query into name and year if present.

    Parameters
    ----------
    query:
        Input query, e.g., "Serenity (2005)".

    Returns
    -------
    tuple[str, int | None]
        Name and optional year.
    """
    m = re.match(r"(.+?)\s*\(?((?:19|20)\d{2})\)?$", query.strip())
    if m:
        name = m.group(1).strip()
        try:
            return name, int(m.group(2))
        except ValueError:
            return query.strip(), None
    return query.strip(), None


def _normalize_language(locale: str) -> str:
    """Normalize locale to TMDb `language` parameter.

    Maps legacy codes and ensures a sensible default.
    """
    if not locale:
        return "en-US"
    code = locale.replace("_", "-")
    # Map legacy ISO-639-1 codes
    if code.startswith("iw"):
        return "he-IL"
    if code.startswith("in"):
        return "id-ID"
    return code
