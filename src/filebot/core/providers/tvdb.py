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

"""Core providers TheTVDB module."""

import json
from dataclasses import dataclass, field
from time import monotonic
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cachetools import TTLCache

from filebot.core.models import TV_DB_IDENTIFIER, Episode, SearchResult, SeriesInfo
from filebot.core.providers.base import (
    BaseDatasource,
    EpisodeListProvider,
    RestClientMixin,
)
from filebot.core.providers.utils import RateLimiter, is_https


@dataclass(slots=True)
class TheTVDBClient(BaseDatasource, RestClientMixin, EpisodeListProvider):
    """Minimal TheTVDB client stub.

    Parameters
    ----------
    apikey:
        TheTVDB API key.
    """

    apikey: str
    _token: str | None = None
    _token_expire_ts: float | None = None  # monotonic seconds deadline
    _cache_short: TTLCache = field(init=False, repr=False)
    _cache_long: TTLCache = field(init=False, repr=False)
    _limiter: RateLimiter = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize caches and rate limiter for TheTVDB client."""
        self._cache_short = TTLCache(maxsize=4096, ttl=24 * 60 * 60)
        self._cache_long = TTLCache(maxsize=4096, ttl=7 * 24 * 60 * 60)
        # Typical limits allow ~20-40/10s; use conservative 30/10s
        self._limiter = RateLimiter(max_requests=30, window_seconds=10)

    @property
    def identifier(self) -> str:
        """Return the unique provider identifier.

        Returns
        -------
        str
            The TV Database identifier.
        """
        return TV_DB_IDENTIFIER

    # --- EpisodeListProvider ---
    def has_season_support(self) -> bool:
        """Return True; TheTVDB supports seasons."""
        return True

    def search(self, query: str, locale: str) -> list[SearchResult]:
        """Search for series using TheTVDB v2 API."""
        data = self._request_json(
            "search/series",
            {"name": query},
            locale,
        )
        results = data.get("data") or []
        out: list[SearchResult] = []
        for it in results:
            try:
                sid = int(it["id"])  # KeyError/ValueError handled below
                name = it.get("seriesName") or ""
                aliases = list(it.get("aliases") or [])
                out.append(SearchResult(id=sid, name=name, alias_names=aliases))
            except (KeyError, ValueError, TypeError):
                continue
        return out

    def get_episode_list(
        self, series: SearchResult | int, order: str, locale: str
    ) -> list[Episode]:
        """Fetch episodes for a series with pagination."""
        series_id = series.id if isinstance(series, SearchResult) else int(series)

        # Fetch series info to capture series-level context with English fallback
        s_info = self.get_series_info(series_id, locale)
        if not s_info.name and locale and not locale.startswith("en"):
            # Fallback to English if preferred language returns no title
            s_info = self.get_series_info(series_id, "en")

        episodes: list[Episode] = []
        page = 1
        last = None
        while last is None or page <= last:
            data = self._request_json(
                f"series/{series_id}/episodes",
                {"page": page},
                locale,
            )
            last = (data.get("links") or {}).get("last")
            try:
                last = int(last) if last is not None else page
            except (TypeError, ValueError):
                last = page

            for it in data.get("data", []):
                try:
                    eid = int(it["id"])  # episode id
                    title = it.get("episodeName") or None
                    airdate = it.get("firstAired") or None
                    absolute = it.get("absoluteNumber")
                    absolute_num = (
                        int(absolute)
                        if isinstance(absolute, int)
                        or (isinstance(absolute, str) and absolute.isdigit())
                        else None
                    )
                    season_num = it.get("airedSeason")
                    season_num = (
                        int(season_num) if season_num not in (None, "") else None
                    )
                    episode_num = it.get("airedEpisodeNumber")
                    episode_num = (
                        int(episode_num) if episode_num not in (None, "") else None
                    )

                    episodes.append(
                        Episode(
                            series_name=s_info.name or "",
                            season=season_num,
                            episode=episode_num,
                            title=title,
                            absolute=absolute_num,
                            special_number=it.get("dvdEpisodeNumber")
                            if season_num == 0
                            else None,
                            airdate=airdate,
                            id=eid,
                            series_info=s_info,
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    continue
            page += 1

        return episodes

    def get_series_info(self, series: SearchResult | int, locale: str) -> SeriesInfo:
        """Fetch basic series info."""
        sid = series.id if isinstance(series, SearchResult) else int(series)
        data = self._request_json(f"series/{sid}", {}, locale)
        d = data.get("data") or {}
        name = d.get("seriesName") or None
        aliases = list(d.get("aliases") or [])
        return SeriesInfo(id=sid, name=name, alias_names=aliases)

    def get_episode_list_link(self, series: SearchResult) -> str:
        """Return the public episode list link."""
        return f"https://www.thetvdb.com/?tab=seasonall&id={series.id}"

    # --- Internal helpers ---
    def _request_json(
        self, path: str, params: dict[str, Any], locale: str
    ) -> dict[str, Any]:
        base = "https://api.thetvdb.com/"
        token = self._get_token()
        query = urlencode(params) if params else ""
        url = base + path + ("?" + query if query else "")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        if locale:
            headers["Accept-Language"] = _normalize_language(locale)

        if not is_https(url):
            return {}
        long_ttl = not (path.startswith("series/") and path.endswith("/episodes"))
        cache_key = url + "|" + headers.get("Accept-Language", "")
        return self._http_get_json(
            url,
            headers=headers,
            timeout=15,
            cache_key=cache_key,
            long_ttl=long_ttl,
            require_https=True,
        )

    def _get_token(self) -> str:
        # Refresh token every ~23 hours similar to Java client behavior
        now = monotonic()
        if self._token and self._token_expire_ts and now < self._token_expire_ts:
            return self._token

        url = "https://api.thetvdb.com/login"
        payload = json.dumps({"apikey": self.apikey}).encode("utf-8")
        req = Request(  # noqa: S310
            url,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if not is_https(url):
            message = "TheTVDB: invalid scheme for token endpoint"
            raise RuntimeError(message)
        with urlopen(req, timeout=15) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("token")
            if not token:
                message = "TheTVDB: missing token in response"
                raise RuntimeError(message)
            self._token = token
            # 23 hours from now using monotonic time base
            self._token_expire_ts = now + 23 * 60 * 60
            return token


def _normalize_language(locale: str) -> str:
    """Normalize to TheTVDB Accept-Language semantics.

    Maps legacy codes, returns two-letter language or language-country code.
    """
    if not locale:
        return "en"
    code = locale.split(".")[0]
    code = code.replace("_", "-")
    if code.startswith("iw"):
        return "he"
    if code.startswith("in"):
        return "id"
    return code
