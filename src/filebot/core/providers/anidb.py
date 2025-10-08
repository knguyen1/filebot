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

"""AniDB episode list provider.

Implements minimal search via the AniDB anime titles index and episode list
retrieval via the AniDB HTTP API.
"""

from __future__ import annotations

import gzip
import io
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET  # noqa: S405 - trusted XML from AniDB API

from filebot.core.models import Episode, SearchResult, SeriesInfo
from filebot.core.providers.base import (
    BaseDatasource,
    EpisodeListProvider,
    RestClientMixin,
)
from filebot.core.providers.utils import is_allowed_http

if TYPE_CHECKING:
    from cachetools import TTLCache

_ANIDB_TITLES_URL = "http://anidb.net/api/anime-titles.dat.gz"
_ANIDB_HTTP_API = (
    "http://api.anidb.net:9001/httpapi?request=anime&client={client}"
    "&clientver={clientver}&protover=1&aid={aid}"
)
_ANIDB_PUBLIC_URL = "http://anidb.net"
_ALLOWED_HOSTS = {"anidb.net", "api.anidb.net:9001", "api.anidb.net"}


@dataclass(slots=True)
class AniDBClient(BaseDatasource, RestClientMixin, EpisodeListProvider):
    """AniDB episode provider.

    Parameters
    ----------
    client:
        Registered AniDB client identifier.
    clientver:
        Client version integer.
    """

    client: str
    clientver: int

    # simple in-memory cache for anime titles index
    _titles_cache: list[SearchResult] | None = None
    _cache_short: TTLCache | None = None
    _cache_long: TTLCache | None = None

    def __post_init__(self) -> None:
        """Initialize caches for AniDB client."""
        self._init_rest(
            short_ttl=24 * 60 * 60,
            long_ttl=7 * 24 * 60 * 60,
        )

    @property
    def identifier(self) -> str:
        """Return the unique provider identifier.

        Returns
        -------
        str
            Provider identifier.
        """
        return "AniDB"

    # --- EpisodeListProvider ---
    def has_season_support(self) -> bool:
        """Return False; AniDB uses absolute numbering."""
        return False

    def search(self, query: str, locale: str) -> list[SearchResult]:
        """Search anime titles locally using the AniDB titles index.

        Parameters
        ----------
        query:
            Free-form query.
        locale:
            Unused for index search.

        Returns
        -------
        list[SearchResult]
            Matching series search results.
        """
        titles = self._load_titles_index()
        q = query.strip().lower()
        if not q:
            return []
        matches: list[SearchResult] = []
        for it in titles:
            names = [n.lower() for n in it.effective_names()]
            if any(q in n for n in names):
                matches.append(it)
        return matches

    def get_episode_list(
        self, series: SearchResult | int, order: str, locale: str
    ) -> list[Episode]:
        """Fetch episode list from AniDB HTTP API.

        Parameters
        ----------
        series:
            Series search result or AniDB numeric ID.
        order:
            Sort order (supports "Absolute" and "AbsoluteAirdate").
        locale:
            Preferred language; used for episode titles.

        Returns
        -------
        list[Episode]
            Episodes for the series, sorted.
        """
        sid = series.id if isinstance(series, SearchResult) else int(series)
        lang = _normalize_language(locale)
        xml_data = self._request_xml(sid)

        # Parse error node
        if xml_data.find("error") is not None and (xml_data.findtext("error") or ""):
            # expose message if present
            raise RuntimeError(xml_data.findtext("error") or "AniDB error")

        series_name = self._select_text(xml_data, "anime/titles/title[@type='main']")
        official_name = self._select_text(
            xml_data, f"anime/titles/title[@type='official' and @lang='{lang}']"
        )
        if not official_name:
            official_name = series_name

        episodes: list[Episode] = []
        for node in xml_data.findall("anime/episodes/episode"):
            ep = self._episode_from_node(
                node=node,
                lang=lang,
                order=order,
                series_name=series_name,
                official_name=official_name,
                sid=sid,
            )
            if ep is not None:
                episodes.append(ep)

        # sort: normal episodes first by episode number, then specials
        episodes.sort(
            key=lambda e: (
                0 if e.episode is not None else 1,
                e.episode if e.episode is not None else (e.special_number or 0),
            )
        )
        return episodes

    def _episode_from_node(
        self,
        node,  # xml element
        *,
        lang: str,
        order: str,
        series_name: str | None,
        official_name: str | None,
        sid: int,
    ) -> Episode | None:
        """Create an Episode object from an AniDB episode XML node.

        Returns None if the node is not a normal/special episode.
        """
        epno = node.find("epno")
        if epno is None or epno.text is None:
            return None
        number = int(re.sub(r"\D", "", epno.text))
        type_attr = epno.get("type")
        try:
            ep_type = int(type_attr) if type_attr is not None else 0
        except ValueError:
            ep_type = 0
        if ep_type not in (1, 2):  # normal or special
            return None

        try:
            eid = int(node.get("id")) if node.get("id") else None
        except ValueError:
            eid = None

        airdate = self._select_text(node, "airdate") or None
        title = self._select_text(node, f".//title[@lang='{lang}']") or ""
        if not title:
            title = self._select_text(node, ".//title[@lang='en']") or ""

        series_display = official_name or series_name or ""

        if ep_type == 1:  # normal episode
            abs_num = number
            if (
                order == "AbsoluteAirdate"
                and airdate
                and re.match(r"\d{4}-\d{2}-\d{2}", airdate)
            ):
                y, m, d = airdate.split("-")
                abs_num = int(y) * 10000 + int(m) * 100 + int(d)
            return Episode(
                series_name=series_display,
                season=None,
                episode=number,
                title=title or None,
                absolute=abs_num,
                special_number=None,
                airdate=airdate,
                id=eid,
                series_info=SeriesInfo(id=sid, name=series_display),
            )

        # special
        return Episode(
            series_name=series_display,
            season=None,
            episode=None,
            title=title or None,
            absolute=None,
            special_number=number,
            airdate=airdate,
            id=eid,
            series_info=SeriesInfo(id=sid, name=series_display),
        )

    def get_series_info(self, series: SearchResult | int, locale: str) -> SeriesInfo:
        """Fetch basic series info using the anime XML data.

        Parameters
        ----------
        series:
            Series search result or AniDB numeric ID.
        locale:
            Preferred language.

        Returns
        -------
        SeriesInfo
            Series info with localized name and aliases when available.
        """
        sid = series.id if isinstance(series, SearchResult) else int(series)
        xml_data = self._request_xml(sid)
        series_name = self._select_text(xml_data, "anime/titles/title[@type='main']")
        return SeriesInfo(id=sid, name=series_name or None)

    def get_episode_list_link(self, series: SearchResult) -> str:
        """Return AniDB public series page URL."""
        return f"{_ANIDB_PUBLIC_URL}/a{series.id}"

    # --- internal helpers ---
    def _load_titles_index(self) -> list[SearchResult]:
        if self._titles_cache is not None:
            return self._titles_cache

        url = _ANIDB_TITLES_URL
        if not is_allowed_http(url, _ALLOWED_HOSTS):
            return []
        raw = self._http_get_bytes(
            url,
            timeout=30,
            long_ttl=True,
            require_https=False,
            allowed_http_hosts=_ALLOWED_HOSTS,
        )
        if raw is None:
            return []
        data = gzip.decompress(raw)
        # parse
        lines = io.BytesIO(data).read().decode("utf-8", errors="ignore").splitlines()
        pattern = re.compile(r"^(?!#)(\d+)[|](\d)[|]([\w-]+)[|](.+)$")

        # language and type priority
        language_order = ["x-jat", "en", "ja"]
        type_order = ["1", "4", "2", "3"]

        by_aid: dict[int, list[tuple[int, int, str]]] = {}
        for line in lines:
            m = pattern.match(line)
            if not m:
                continue
            aid = int(m.group(1))
            typ = m.group(2)
            lang = m.group(3)
            title = _html_unescape(m.group(4))
            if aid > 0 and title and typ in type_order and lang in language_order:
                if typ == "3" and (
                    len(title) < 5 or not title[:1].isupper() or title[-1:].isupper()
                ):
                    continue
                by_aid.setdefault(aid, []).append((
                    type_order.index(typ),
                    language_order.index(lang),
                    title,
                ))

        results: list[SearchResult] = []
        for aid, entries in by_aid.items():
            entries_sorted = sorted(entries, key=lambda t: (t[0], t[1]))
            names = [title for _, _, title in entries_sorted]
            if not names:
                continue
            primary = names[0]
            aliases = names[1:]
            results.append(SearchResult(id=aid, name=primary, alias_names=aliases))

        self._titles_cache = results
        return results

    def _request_xml(self, aid: int) -> ET.Element:
        url = _ANIDB_HTTP_API.format(
            client=self.client, clientver=self.clientver, aid=aid
        )
        if not is_allowed_http(url, _ALLOWED_HOSTS):
            message = "AniDB: invalid scheme or host"
            raise RuntimeError(message)
        xml_bytes = self._http_get_bytes(
            url,
            timeout=30,
            long_ttl=False,
            require_https=False,
            allowed_http_hosts=_ALLOWED_HOSTS,
        )
        if xml_bytes is None:
            message = "AniDB: request failed"
            raise RuntimeError(message)
        return ET.fromstring(xml_bytes)  # noqa: S314 - trusted XML from AniDB API

    def _select_text(self, root: ET.Element, xpath: str) -> str:
        """Return first match text by simple XPath subset.

        Supports absolute paths without predicates except for attribute filter
        used in this module.
        """
        # very small subset: /a/b/c and filters like tag[@attr='val']
        segments = xpath.strip("/").split("/")
        current: list[ET.Element] = [root]
        for seg in segments:
            attr_name = attr_val = None
            if "[@" in seg:
                # e.g. title[@type='main']
                name, rest = seg.split("[@", 1)
                attr_name, attr_val = rest[:-1].split("=", 1)
                attr_val = attr_val.strip("'\"")
            else:
                name = seg
            next_nodes: list[ET.Element] = []
            for node in current:
                children = [
                    child
                    for child in node.findall(name)
                    if attr_name is None or child.get(attr_name) == attr_val
                ]
                next_nodes.extend(children)
            current = next_nodes
            if not current:
                return ""
        return (current[0].text or "").strip()


def _normalize_language(locale: str) -> str:
    code = (locale or "en").split(".")[0]
    return {"iw": "he", "in": "id"}.get(code, code)


def _html_unescape(text: str) -> str:
    # minimal HTML entity replacement for common cases
    try:
        return json.loads('"' + text.replace("\\", r"\\").replace('"', r"\"") + '"')
    except (
        json.JSONDecodeError,
        ValueError,
    ):  # narrow failures in best-effort unescape
        return text
