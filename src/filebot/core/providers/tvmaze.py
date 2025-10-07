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

"""TVmaze episode list provider.

Implements search, series info, and episode listing via TVmaze API.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from filebot.core.models import Episode, SearchResult, SeriesInfo
from filebot.core.providers.base import BaseDatasource, EpisodeListProvider
from filebot.core.providers.utils import is_allowed_http

_TVMAZE_HOST = "api.tvmaze.com"


@dataclass(slots=True)
class TVMazeClient(BaseDatasource, EpisodeListProvider):
    """TVmaze episode provider.

    No API key required.
    """

    @property
    def identifier(self) -> str:
        """Return the unique provider identifier."""
        return "TVmaze"

    # --- EpisodeListProvider ---
    def has_season_support(self) -> bool:
        """Return True; TVmaze exposes seasons and numbers."""
        return True

    def search(self, query: str, locale: str) -> list[SearchResult]:
        """Search series by name using TVmaze search endpoint.

        Parameters
        ----------
        query:
            Free-form query.
        locale:
            Ignored; TVmaze responses are English.

        Returns
        -------
        list[SearchResult]
            Matching series.
        """
        params = urlencode({"q": query})
        data = self._request_json(f"search/shows?{params}")
        out: list[SearchResult] = []
        for item in data if isinstance(data, list) else []:
            show = item.get("show") if isinstance(item, dict) else None
            if not isinstance(show, dict):
                continue
            try:
                sid = int(show.get("id"))
                name = (show.get("name") or "").strip()
            except (TypeError, ValueError):
                continue
            out.append(SearchResult(id=sid, name=name))
        return out

    def get_episode_list(
        self, series: SearchResult | int, order: str, locale: str
    ) -> list[Episode]:
        """Fetch episode list for a show.

        Parameters
        ----------
        series:
            Series search result or numeric TVmaze ID.
        order:
            Ignored; TVmaze uses airdate ordering.
        locale:
            Ignored.
        """
        sid = series.id if isinstance(series, SearchResult) else int(series)
        info = self.get_series_info(sid, locale)
        data = self._request_json(f"shows/{sid}/episodes")
        episodes: list[Episode] = []
        for ep in data if isinstance(data, list) else []:
            if not isinstance(ep, dict):
                continue
            try:
                eid = int(ep.get("id"))
            except (TypeError, ValueError):
                eid = None
            season = ep.get("season")
            number = ep.get("number")
            title = (
                (ep.get("name") or None) if isinstance(ep.get("name"), str) else None
            )
            airdate = ep.get("airdate") or None
            season_num = (
                int(season)
                if isinstance(season, int)
                or (isinstance(season, str) and season.isdigit())
                else None
            )
            episode_num = (
                int(number)
                if isinstance(number, int)
                or (isinstance(number, str) and number.isdigit())
                else None
            )
            episodes.append(
                Episode(
                    series_name=info.name or "",
                    season=season_num,
                    episode=episode_num,
                    title=title,
                    absolute=None,
                    special_number=None,
                    airdate=airdate,
                    id=eid,
                    series_info=info,
                )
            )
        return episodes

    def get_series_info(self, series: SearchResult | int, locale: str) -> SeriesInfo:
        """Fetch basic series info.

        Parameters
        ----------
        series:
            Series search result or numeric TVmaze ID.
        locale:
            Ignored.

        Returns
        -------
        SeriesInfo
            Series info with name.
        """
        sid = series.id if isinstance(series, SearchResult) else int(series)
        data = self._request_json(f"shows/{sid}")
        name = data.get("name") if isinstance(data, dict) else None
        name_str = (name or "").strip() if isinstance(name, str) else None
        return SeriesInfo(id=sid, name=name_str)

    def get_episode_list_link(self, series: SearchResult) -> str:
        """Return TVmaze public series page URL."""
        return f"http://www.tvmaze.com/shows/{series.id}"

    # --- internal helpers ---
    def _request_json(self, resource: str) -> Any:
        url = f"http://{_TVMAZE_HOST}/{resource}"
        if not is_allowed_http(url, {_TVMAZE_HOST}):
            return {}
        req = Request(url)  # noqa: S310
        try:
            with urlopen(req, timeout=15) as resp:  # noqa: S310
                content = resp.read().decode("utf-8")
                return json.loads(content)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return {}
