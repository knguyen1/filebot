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

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from filebot.core.models import Episode, Movie, SearchResult, SeriesInfo


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
