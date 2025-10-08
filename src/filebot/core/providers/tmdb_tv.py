# Copyright (c) 2025 knguyen1

"""TMDb TV episode list provider.

Fetches series, seasons, and episodes from TMDb v3 API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from filebot.core.models import Episode, SearchResult, SeriesInfo
from filebot.core.providers.base import (
    BaseDatasource,
    EpisodeListProvider,
    RestClientMixin,
)

# Reuse language normalization from movie client
from filebot.core.providers.tmdb import _normalize_language

# TMDb TV API URLs
_TMDB_TV_BASE_URL = "https://api.themoviedb.org/3/"
_TMDB_TV_PUBLIC_URL = "https://www.themoviedb.org/tv/"

if TYPE_CHECKING:
    from cachetools import TTLCache

    from filebot.core.providers.utils import RateLimiter


@dataclass(slots=True)
class TMDbTVClient(BaseDatasource, RestClientMixin, EpisodeListProvider):
    """TMDb TV client.

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
        """Initialize caches and rate limiter for TMDb TV client."""
        self._init_rest(
            short_ttl=24 * 60 * 60,
            long_ttl=7 * 24 * 60 * 60,
            rate=(35, 10),
        )

    # --- BaseDatasource ---
    @property
    def identifier(self) -> str:
        """Return unique provider identifier for TMDb TV."""
        return "TheMovieDB::TV"

    # --- EpisodeListProvider ---
    def has_season_support(self) -> bool:
        """Return True; TMDb TV supports seasons."""
        return True

    def search(self, query: str, locale: str) -> list[SearchResult]:
        """Search TV series by name and optional starting year in the query.

        Notes
        -----
        If the query contains a 4-digit year suffix, it will be used as
        ``first_air_date_year`` to improve result quality.
        """
        name, year = _split_name_and_year(query)
        params: dict[str, Any] = {"query": name}
        if year is not None:
            params["first_air_date_year"] = year
        data = self._request_json("search/tv", params, locale)
        results = data.get("results") or []
        out: list[SearchResult] = []
        for it in results:
            try:
                sid = int(it["id"])  # KeyError/ValueError handled below
                title = (it.get("name") or it.get("original_name") or "").strip()
                out.append(SearchResult(id=sid, name=title, alias_names=[]))
            except (KeyError, ValueError, TypeError):
                continue
        return out

    def get_episode_list(
        self, series: SearchResult | int, order: str, locale: str
    ) -> list[Episode]:
        """Fetch all episodes for a series by iterating seasons."""
        sid = series.id if isinstance(series, SearchResult) else int(series)
        tv = self._request_json(f"tv/{sid}", {}, locale)
        name = (tv.get("name") or tv.get("original_name") or "").strip()

        # List seasons, then fetch each season's episodes
        seasons = [s.get("season_number") for s in tv.get("seasons", [])]
        seasons = [int(s) for s in seasons if isinstance(s, int)]

        info = SeriesInfo(id=sid, name=name or None, alias_names=[])

        episodes: list[Episode] = []
        specials: list[Episode] = []

        for s in seasons:
            season = self._request_json(f"tv/{sid}/season/{s}", {}, locale)
            for ep in season.get("episodes", []) or []:
                try:
                    eid = int(ep.get("id")) if ep.get("id") is not None else None
                except (ValueError, TypeError):
                    eid = None
                season_num = ep.get("season_number")
                try:
                    season_num = (
                        int(season_num) if season_num not in (None, "") else None
                    )
                except (ValueError, TypeError):
                    season_num = None
                ep_num = ep.get("episode_number")
                try:
                    ep_num = int(ep_num) if ep_num not in (None, "") else None
                except (ValueError, TypeError):
                    ep_num = None
                title = (ep.get("name") or "").strip() or None
                airdate = ep.get("air_date") or None

                if s > 0:
                    episodes.append(
                        Episode(
                            series_name=name,
                            season=season_num,
                            episode=ep_num,
                            title=title,
                            absolute=None,
                            special_number=None,
                            airdate=airdate,
                            id=eid,
                            series_info=info,
                        )
                    )
                else:
                    specials.append(
                        Episode(
                            series_name=name,
                            season=None,
                            episode=None,
                            title=title,
                            absolute=None,
                            special_number=ep_num,
                            airdate=airdate,
                            id=eid,
                            series_info=info,
                        )
                    )

        # Append specials after regular episodes
        episodes.extend(specials)
        return episodes

    def get_series_info(self, series: SearchResult | int, locale: str) -> SeriesInfo:
        """Fetch basic series info for the given series id."""
        sid = series.id if isinstance(series, SearchResult) else int(series)
        tv = self._request_json(f"tv/{sid}", {}, locale)
        name = (tv.get("name") or tv.get("original_name") or "").strip() or None
        # Build alias names: original name if different, and any from season names (optional)
        aliases: list[str] = []
        original = (tv.get("original_name") or "").strip()
        if original and original != name:
            aliases.append(original)
        # Populate SeriesInfo metadata similar to Java
        status = tv.get("status") or None
        runtime = None
        runtimes = tv.get("episode_run_time") or []
        if isinstance(runtimes, list) and runtimes:
            rt0 = runtimes[0]
            if isinstance(rt0, int):
                runtime = rt0
            elif isinstance(rt0, str) and rt0.isdigit():
                runtime = int(rt0)
        genres = [
            g.get("name")
            for g in (tv.get("genres") or [])
            if isinstance(g, dict) and g.get("name")
        ]
        network = None
        nets = tv.get("networks") or []
        if isinstance(nets, list) and nets:
            nn = nets[0]
            if isinstance(nn, dict):
                network = nn.get("name") or None
        return SeriesInfo(
            id=sid,
            name=name,
            alias_names=aliases,
            status=status,
            runtime=runtime,
            genres=genres,
            network=network,
        )

    def get_episode_list_link(self, series: SearchResult) -> str:
        """Return public TMDb TV page URL for the series."""
        return f"{_TMDB_TV_PUBLIC_URL}{series.id}"

    # --- internal helpers ---
    def _request_json(
        self, path: str, params: dict[str, Any], locale: str
    ) -> dict[str, Any]:
        base = _TMDB_TV_BASE_URL
        query = {"api_key": self.apikey}
        if locale:
            query["language"] = _normalize_language(locale)
        query.update(params)
        url = base + path + "?" + urlencode(query)
        # Use mixin for HTTPS + caching + rate limiting
        return self._http_get_json(
            url, timeout=15, long_ttl=not path.startswith("search/"), require_https=True
        )


def _split_name_and_year(query: str) -> tuple[str, int | None]:
    """Split TV query into name and optional start year.

    Examples
    --------
    "The Office 2005" -> ("The Office", 2005)
    "Breaking Bad" -> ("Breaking Bad", None)
    """
    import re as _re

    m = _re.match(r"(.+?)\s+(19\d{2}|20\d{2})$", query.strip())
    if m:
        try:
            return m.group(1).strip(), int(m.group(2))
        except ValueError:
            return query.strip(), None
    return query.strip(), None
