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

from dataclasses import dataclass

from filebot.core.models import MOVIE_DB_IDENTIFIER, Movie
from filebot.core.providers.base import BaseDatasource, MovieIdentificationService


@dataclass(slots=True)
class TMDbClient(BaseDatasource, MovieIdentificationService):
    """Minimal TMDb client stub.

    Parameters
    ----------
    apikey:
        TMDb API key.
    """

    apikey: str

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
        """Search for movies by query. Stub implementation.

        Returns an empty list for now. Real HTTP implementation will be added
        in a later phase.
        """
        return []

    def get_movie_descriptor(self, movie: Movie, locale: str) -> Movie | None:
        """Resolve movie details. Stub implementation."""
        return None
