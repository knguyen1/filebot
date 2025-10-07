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

"""Core models module."""

from dataclasses import dataclass, field
from typing import Final


@dataclass(slots=True)
class SearchResult:
    """A generic search result.

    Parameters
    ----------
    id:
        Provider-specific unique identifier.
    name:
        Primary display name.
    alias_names:
        Alternate names for fuzzy matching and display.
    """

    id: int
    name: str | None = None
    alias_names: list[str] = field(default_factory=list)

    def effective_names(self) -> list[str]:
        """Return primary name followed by aliases.

        Returns
        -------
        list[str]
            Primary name and aliases; empty if `name` is not set.
        """
        if not self.name:
            return []
        if not self.alias_names:
            return [self.name]
        return [self.name, *self.alias_names]


@dataclass(slots=True)
class Movie:
    """Lightweight movie descriptor.

    Parameters
    ----------
    name:
        Movie title.
    alias_names:
        Alternate titles.
    year:
        Release year if known.
    imdb_id:
        Numeric IMDb ID (without the "tt" prefix).
    tmdb_id:
        Numeric TMDb ID.
    language:
        BCP-47 language tag (e.g., "en", "en-US").
    """

    name: str
    alias_names: list[str] = field(default_factory=list)
    year: int | None = None
    imdb_id: int | None = None
    tmdb_id: int | None = None
    language: str | None = None


@dataclass(slots=True)
class SeriesInfo:
    """Series-level information for an episode provider.

    Parameters
    ----------
    id:
        Provider-specific series ID.
    name:
        Series title.
    alias_names:
        Alternate titles.
    order:
        Sort order hint (e.g., "Airdate", "DVD", "Absolute").
    """

    id: int
    name: str | None = None
    alias_names: list[str] = field(default_factory=list)
    order: str | None = None


@dataclass(slots=True)
class Episode:
    """Episode information used for formatting and renaming.

    Parameters
    ----------
    series_name:
        Name of the series for display.
    season:
        Season number; may be None for absolute numbering or specials.
    episode:
        Episode number; may represent absolute number depending on `order`.
    title:
        Episode title.
    absolute:
        Absolute episode number if available.
    special_number:
        Special episode number if this is a special.
    airdate:
        Airdate in ISO format (YYYY-MM-DD) if available.
    id:
        Provider-specific episode ID.
    series_info:
        Copy of series info snapshot at retrieval time.
    """

    series_name: str
    season: int | None
    episode: int | None
    title: str | None = None
    absolute: int | None = None
    special_number: int | None = None
    airdate: str | None = None
    id: int | None = None
    series_info: SeriesInfo | None = None


# Constants used across providers
MOVIE_DB_IDENTIFIER: Final[str] = "TheMovieDB"
TV_DB_IDENTIFIER: Final[str] = "TheTVDB"


@dataclass(slots=True)
class Artwork:
    """Artwork asset descriptor.

    Parameters
    ----------
    category:
        Artwork category (e.g., "poster", "fanart").
    url:
        Absolute URL of the image.
    language:
        Two-letter language code if applicable.
    rating:
        Provider-specific rating for the asset.
    """

    category: str
    url: str
    language: str | None = None
    rating: float | None = None


@dataclass(slots=True)
class SubtitleSearchResult:
    """Subtitle search result descriptor.

    Parameters
    ----------
    name:
        Display name or file name of the subtitle.
    lang:
        Language code.
    imdb_id:
        Associated IMDb ID if known.
    tmdb_id:
        Associated TMDb ID if known.
    score:
        Relevance score if available.
    url:
        Download URL if available.
    """

    name: str
    lang: str | None = None
    imdb_id: int | None = None
    tmdb_id: int | None = None
    score: int | None = None
    url: str | None = None
