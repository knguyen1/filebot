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

from dataclasses import dataclass

from filebot.core.models import TV_DB_IDENTIFIER, Episode, SearchResult, SeriesInfo
from filebot.core.providers.base import BaseDatasource, EpisodeListProvider


@dataclass(slots=True)
class TheTVDBClient(BaseDatasource, EpisodeListProvider):
    """Minimal TheTVDB client stub.

    Parameters
    ----------
    apikey:
        TheTVDB API key.
    """

    apikey: str

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
        """Search series by query. Stub implementation."""
        return []

    def get_episode_list(
        self, series: SearchResult | int, order: str, locale: str
    ) -> list[Episode]:
        """Fetch episodes for series. Stub implementation."""
        return []

    def get_series_info(self, series: SearchResult | int, locale: str) -> SeriesInfo:
        """Fetch series info. Stub implementation."""
        sid = series.id if isinstance(series, SearchResult) else int(series)
        return SeriesInfo(id=sid)

    def get_episode_list_link(self, series: SearchResult) -> str:
        """Return the public episode list link."""
        return f"https://www.thetvdb.com/?tab=seasonall&id={series.id}"
