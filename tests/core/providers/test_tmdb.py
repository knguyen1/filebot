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

from filebot.core.models import MOVIE_DB_IDENTIFIER, Movie
from filebot.core.providers.tmdb import (
    TMDbClient,
    _normalize_language,
    _split_name_and_year,
)


def test_identifier_and_language_normalization() -> None:
    c = TMDbClient(apikey="k")
    assert c.identifier == MOVIE_DB_IDENTIFIER
    assert _normalize_language("") == "en-US"
    assert _normalize_language("en_US") == "en-US"
    assert _normalize_language("iw") == "he-IL"
    assert _normalize_language("in_ID") == "id-ID"


@pytest.mark.parametrize(
    ("query", "expected_name", "expected_year"),
    [
        ("Serenity 2005", "Serenity", 2005),
        ("Spirited Away (2001)", "Spirited Away", 2001),
        ("Movie 20x1", "Movie 20x1", None),
        ("  Name (1999) ", "Name", 1999),
    ],
)
def test_split_name_and_year(
    query: str, expected_name: str, expected_year: int | None
) -> None:
    name, year = _split_name_and_year(query)
    assert name == expected_name
    assert year == expected_year


def test_search_movie_params_language_and_year(
    monkeypatch: pytest.MonkeyPatch, mock_http_json
) -> None:
    mock_http_json({"api.themoviedb.org/3/search/movie": {"results": []}})
    captured: dict[str, object] = {}

    def fake_http(self, url: str, **kwargs):  # type: ignore[override]
        captured["url"] = url
        captured["long_ttl"] = kwargs.get("long_ttl")
        return {"results": []}

    monkeypatch.setattr(TMDbClient, "_http_get_json", fake_http, raising=True)
    c = TMDbClient(apikey="k")
    c.search_movie("Name 2010", "en-US")
    assert "language=en-US" in str(captured.get("url"))
    assert "year=2010" in str(captured.get("url"))
    assert captured.get("long_ttl") is False


def test_tmdb_search_movie_parses_results(mock_http_json) -> None:
    mock_http_json({
        "api.themoviedb.org/3/search/movie": {
            "results": [
                {"id": 10, "title": "A", "release_date": "2001-01-01"},
                {"id": 11, "original_title": "B"},
                {"id": "x"},  # skipped
            ]
        }
    })
    c = TMDbClient(apikey="k")
    out = c.search_movie("A 2001", "en-US")
    assert [m.tmdb_id for m in out] == [10, 11]
    assert out[0].year == 2001
    assert out[0].language == "en-US"


def test_get_movie_descriptor_from_tmdb_id(mock_http_json) -> None:
    mock_http_json({
        "api.themoviedb.org/3/movie/42": {
            "title": "X",
            "release_date": "1999-12-31",
            "imdb_id": "tt0000123",
        }
    })
    c = TMDbClient(apikey="k")
    m = Movie(name="?", tmdb_id=42)
    out = c.get_movie_descriptor(m, "en")
    assert out is not None
    assert out.name == "X"
    assert out.year == 1999
    assert out.imdb_id == 123
    assert out.tmdb_id == 42


def test_get_movie_descriptor_via_imdb_find_then_fetch(mock_http_json) -> None:
    mock_http_json({
        "api.themoviedb.org/3/find/tt0000123": {"movie_results": [{"id": 77}]},
        "api.themoviedb.org/3/movie/77": {"title": "Z"},
    })
    c = TMDbClient(apikey="k")
    m = Movie(name="?", imdb_id=123)
    out = c.get_movie_descriptor(m, "en")
    assert out is not None
    assert out.tmdb_id == 77
    assert out.imdb_id == 123


def test_get_movie_descriptor_missing_ids_returns_none(mock_http_json) -> None:
    mock_http_json({})
    c = TMDbClient(apikey="k")
    m = Movie(name="?")
    assert c.get_movie_descriptor(m, "en") is None


def test_get_movie_descriptor_find_miss_or_invalid_id(mock_http_json) -> None:
    mock_http_json({
        # find returns no results => cannot resolve tmdb_id
        "api.themoviedb.org/3/find/tt0000123": {"movie_results": []}
    })
    c = TMDbClient(apikey="k")
    m = Movie(name="?", imdb_id=123)
    assert c.get_movie_descriptor(m, "en") is None


def test_request_json_long_ttl_for_non_search(
    monkeypatch: pytest.MonkeyPatch, mock_http_json
) -> None:
    mock_http_json({"api.themoviedb.org/3/movie/1": {}})
    captured: dict[str, object] = {}

    def fake_http(self, url: str, **kwargs):  # type: ignore[override]
        captured["url"] = url
        captured["long_ttl"] = kwargs.get("long_ttl")
        return {}

    monkeypatch.setattr(TMDbClient, "_http_get_json", fake_http, raising=True)
    c = TMDbClient(apikey="k")
    # Non-search path should set long_ttl True
    c._request_json("movie/1", {}, "en-US")
    assert captured.get("long_ttl") is True
