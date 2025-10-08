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
import re
from dataclasses import dataclass, field
from time import monotonic
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cachetools import TTLCache

from filebot.core.models import (
    TV_DB_IDENTIFIER,
    Artwork,
    Episode,
    SearchResult,
    SeriesInfo,
)
from filebot.core.providers.base import (
    BaseDatasource,
    EpisodeListProvider,
    RestClientMixin,
)
from filebot.core.providers.utils import (
    RateLimiter,
    is_https,
    lenient_name_equals,
)

# TVDB API URLs
_TVDB_BASE_URL = "https://api.thetvdb.com/"
_TVDB_LOGIN_URL = "https://api.thetvdb.com/login"
_TVDB_PUBLIC_URL = "https://www.thetvdb.com/"


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
                # Filter clearly invalid items by lenient name match if possible
                if query and not lenient_name_equals(query, name, locale):
                    # allow if any alias matches leniently
                    if not any(lenient_name_equals(query, a, locale) for a in aliases):
                        # keep but deprioritize by appending later if desired
                        out.append(SearchResult(id=sid, name=name, alias_names=aliases))
                    else:
                        out.append(SearchResult(id=sid, name=name, alias_names=aliases))
                else:
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
        specials: list[Episode] = []
        for node in self._iter_episode_nodes(series_id, locale):
            try:
                eid = int(node["id"])  # episode id
                title = node.get("episodeName") or None
                airdate = node.get("firstAired") or None
                absolute_num = self._parse_int(node.get("absoluteNumber"))

                season_num, episode_num = self._derive_numbering(
                    order, node, absolute_num, airdate
                )

                is_regular = season_num is None or (
                    isinstance(season_num, int) and season_num > 0
                )

                if is_regular:
                    episodes.append(
                        Episode(
                            series_name=s_info.name or "",
                            season=season_num,
                            episode=episode_num,
                            title=title,
                            absolute=absolute_num,
                            special_number=None,
                            airdate=airdate,
                            id=eid,
                            series_info=s_info,
                        )
                    )
                else:
                    specials.append(
                        Episode(
                            series_name=s_info.name or "",
                            season=None,
                            episode=None,
                            title=title,
                            absolute=absolute_num,
                            special_number=episode_num,
                            airdate=airdate,
                            id=eid,
                            series_info=s_info,
                        )
                    )
            except (KeyError, ValueError, TypeError):
                continue

        # Sort episodes by season / episode number and append specials at the end
        episodes.sort(key=lambda e: ((e.season or 0), (e.episode or 0)))
        episodes.extend(specials)
        return episodes

    def _iter_episode_nodes(self, series_id: int, locale: str):
        """Yield raw episode nodes across all pages."""
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
            yield from data.get("data", [])
            page += 1

    def _parse_int(self, value: Any) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def _derive_numbering(
        self,
        sort_order: str,
        node: dict[str, Any],
        absolute_number: int | None,
        airdate_str: str | None,
    ) -> tuple[int | None, int | None]:
        season_number = self._parse_int(node.get("airedSeason"))
        episode_number = self._parse_int(node.get("airedEpisodeNumber"))

        if sort_order == "DVD":
            dvd_season = self._parse_int(node.get("dvdSeason"))
            dvd_episode = self._parse_int(node.get("dvdEpisodeNumber"))
            if dvd_season is not None and dvd_episode is not None:
                return dvd_season, dvd_episode

        if sort_order == "Absolute" and (absolute_number or 0) > 0:
            return None, absolute_number

        if (
            sort_order == "AbsoluteAirdate"
            and isinstance(airdate_str, str)
            and re.match(r"^\d{4}-\d{2}-\d{2}$", airdate_str)
        ):
            y, m, d = airdate_str.split("-")
            return None, int(y) * 10000 + int(m) * 100 + int(d)

        return season_number, episode_number

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
        return f"{_TVDB_PUBLIC_URL}?tab=seasonall&id={series.id}"

    # --- Extras ---
    def get_languages(self) -> list[str]:
        """Return list of TheTVDB language abbreviations.

        Returns
        -------
        list[str]
            Language abbreviations, e.g., "en", "de", "es".
        """
        data = self._request_json("languages", {}, "")
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        langs: list[str] = []
        for it in items:
            if isinstance(it, dict):
                abbr = it.get("abbreviation")
                if isinstance(abbr, str) and abbr:
                    langs.append(abbr)
        return langs

    def get_actors(self, series_id: int, locale: str) -> list[dict[str, object]]:
        """Return actor credits for a series.

        Parameters
        ----------
        series_id:
            TheTVDB numeric series identifier.
        locale:
            Preferred language (BCP-47) for localized fields when available.

        Returns
        -------
        list[dict[str, object]]
            List of actor dictionaries with keys: "name", "character", "order", "image".
        """
        path = f"series/{series_id}/actors"
        data = self._request_json(path, {}, locale)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        actors: list[dict[str, object]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            name = it.get("name")
            character = it.get("role")
            order = it.get("sortOrder")
            image = self._resolve_image(it.get("image"))
            actors.append({
                "name": name if isinstance(name, str) else None,
                "character": character if isinstance(character, str) else None,
                "order": int(order)
                if isinstance(order, (int, str)) and str(order).isdigit()
                else None,
                "image": image,
            })
        actors.sort(key=lambda a: (a.get("order") is None, a.get("order") or 0))
        return actors

    def get_episode_info(self, episode_id: int, locale: str) -> dict[str, object]:
        """Return extra episode information.

        Parameters
        ----------
        episode_id:
            TheTVDB numeric episode identifier.
        locale:
            Preferred language (BCP-47).

        Returns
        -------
        dict[str, object]
            Dictionary with keys: "series_id", "overview", "rating", "votes",
            and "people" (list of credit dictionaries).
        """
        data = self._request_json(f"episodes/{episode_id}", {}, locale)
        node = data.get("data") if isinstance(data, dict) else None
        if not isinstance(node, dict):
            return {}
        series_id = node.get("seriesId")
        overview = node.get("overview")
        rating = node.get("siteRating")
        votes = node.get("siteRatingCount")

        def _as_people(key: str, role: str) -> list[dict[str, object]]:
            vals = node.get(key)
            out: list[dict[str, object]] = []
            if isinstance(vals, list):
                out.extend(
                    {"name": v, "role": role} for v in vals if isinstance(v, str) and v
                )
            return out

        people: list[dict[str, object]] = []
        people.extend(_as_people("directors", "Director"))
        people.extend(_as_people("writers", "Writer"))
        people.extend(_as_people("guestStars", "Guest Star"))

        return {
            "series_id": int(series_id)
            if isinstance(series_id, (int, str)) and str(series_id).isdigit()
            else None,
            "overview": overview if isinstance(overview, str) else None,
            "rating": float(rating)
            if isinstance(rating, (int, float, str))
            and str(rating).replace(".", "", 1).isdigit()
            else None,
            "votes": int(votes)
            if isinstance(votes, (int, str)) and str(votes).isdigit()
            else None,
            "people": people,
        }

    def get_artwork(self, series_id: int, category: str, locale: str) -> list[Artwork]:
        """Return artwork for a series and category.

        Parameters
        ----------
        series_id:
            TheTVDB numeric series identifier.
        category:
            TheTVDB image key type (e.g., "fanart", "poster", "season").
        locale:
            Preferred language (BCP-47).

        Returns
        -------
        list[Artwork]
            List of artwork assets.
        """
        path = f"series/{series_id}/images/query"
        data = self._request_json(path, {"keyType": category}, locale)
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        artworks: list[Artwork] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            sub_key = it.get("subKey") or None
            resolution = it.get("resolution") or None
            file_name = it.get("fileName") or None
            ratings_info = it.get("ratingsInfo") or {}
            rating = None
            if isinstance(ratings_info, dict):
                avg = ratings_info.get("average")
                if isinstance(avg, (int, float)):
                    rating = float(avg)
                elif isinstance(avg, str):
                    rating = float(avg) if avg.replace(".", "", 1).isdigit() else None
            url = self._resolve_image(file_name)
            cat = (
                ",".join([p for p in [category, sub_key, resolution] if p]) or category
            )
            if url:
                artworks.append(
                    Artwork(category=cat, url=url, language=None, rating=rating)
                )
        artworks.sort(key=lambda a: (a.rating is None, -(a.rating or 0.0)))
        return artworks

    def _resolve_image(self, path: object) -> str | None:
        """Resolve TheTVDB banner path to full URL."""
        if not isinstance(path, str) or not path:
            return None
        return f"https://thetvdb.com/banners/{path}"

    # --- Internal helpers ---
    def _request_json(
        self, path: str, params: dict[str, Any], locale: str
    ) -> dict[str, Any]:
        base = _TVDB_BASE_URL
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

        url = _TVDB_LOGIN_URL
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
