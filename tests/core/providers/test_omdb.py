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

from __future__ import annotations

import pytest

from filebot.core.models import Movie
from filebot.core.providers.omdb import OMDbClient


def test_identifier_property() -> None:
    c = OMDbClient(apikey="k")
    assert c.identifier == "OMDb"


@pytest.mark.parametrize(
    ("query", "expected_name", "expected_year"),
    [
        ("The Matrix 1999", "The Matrix", 1999),
        ("Amélie 2001", "Amélie", 2001),
        ("Spirited Away", "Spirited Away", None),  # no year
        ("Title 20x1", "Title 20x1", None),  # not a year at the end
        ("  Leading and trailing  2000 ", "Leading and trailing", 2000),
    ],
)
def test_split_name_year_cases(
    query: str, expected_name: str, expected_year: int | None
) -> None:
    from filebot.core.providers.omdb import _split_name_year

    name, year = _split_name_year(query)
    assert name == expected_name
    assert year == expected_year


def test_search_movie_filters_and_parses(mock_http_json) -> None:
    mock_http_json({
        "omdbapi.com": {
            "Search": [
                # valid movie
                {"Type": "movie", "Title": "T", "Year": "2001", "imdbID": "tt0000123"},
                # non-movie types are skipped
                {"Type": "series", "Title": "S"},
                # malformed item still yielded by implementation (empty title)
                {"Type": "movie", "Title": None, "Year": "not-year", "imdbID": "bad"},
            ]
        }
    })
    c = OMDbClient(apikey="k")
    out = c.search_movie("T 2001", "en")
    names = [m.name for m in out]
    assert "T" in names
    truthy = [m for m in out if m.name]
    assert len(truthy) == 1
    assert truthy[0].year == 2001
    assert truthy[0].imdb_id == 123


def test_search_movie_without_year_suffix(mock_http_json) -> None:
    mock_http_json({
        "omdbapi.com": {
            "Search": [
                {"Type": "movie", "Title": "X", "Year": "1999", "imdbID": "tt0000009"}
            ]
        }
    })
    c = OMDbClient(apikey="k")
    out = c.search_movie("X", "en")
    assert len(out) == 1
    assert out[0].name == "X"
    assert out[0].year == 1999
    assert out[0].imdb_id == 9


def test_get_movie_descriptor_requires_imdb_id() -> None:
    c = OMDbClient(apikey="k")
    m = Movie(name="N")
    assert c.get_movie_descriptor(m, "en") is None


def test_get_movie_descriptor_bad_response(mock_http_json) -> None:
    mock_http_json({"omdbapi.com": {"Response": "False"}})
    c = OMDbClient(apikey="k")
    m = Movie(name="N", imdb_id=123)
    assert c.get_movie_descriptor(m, "en") is None


def test_get_movie_descriptor_success_parses_year_and_locale(mock_http_json) -> None:
    mock_http_json({
        "omdbapi.com": {"Response": "True", "Title": "Title", "Year": "2003"}
    })
    c = OMDbClient(apikey="k")
    m = Movie(name="?", imdb_id=123)
    out = c.get_movie_descriptor(m, "en-US")
    assert out is not None
    assert out.name == "Title"
    assert out.year == 2003
    assert out.imdb_id == 123
    assert out.language == "en-US"


def test_get_movie_descriptor_preserves_original_year_when_invalid(
    mock_http_json,
) -> None:
    mock_http_json({
        "omdbapi.com": {"Response": "True", "Title": "Title", "Year": "Year"}
    })
    c = OMDbClient(apikey="k")
    m = Movie(name="?", imdb_id=123, year=1999)
    out = c.get_movie_descriptor(m, "en")
    assert out is not None
    assert out.year == 1999
