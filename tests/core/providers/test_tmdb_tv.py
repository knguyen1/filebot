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

from filebot.core.models import SearchResult
from filebot.core.providers.tmdb_tv import TMDbTVClient, _split_name_and_year


def test_identifier_and_season_support() -> None:
    c = TMDbTVClient(apikey="k")
    assert c.identifier == "TheMovieDB::TV"
    assert c.has_season_support() is True


@pytest.mark.parametrize(
    ("query", "expected_name", "expected_year"),
    [
        ("The Office 2005", "The Office", 2005),
        ("Breaking Bad", "Breaking Bad", None),
        ("Show 20x5", "Show 20x5", None),
        ("  Extra spaces 1999 ", "Extra spaces", 1999),
    ],
)
def test_split_name_and_year(
    query: str, expected_name: str, expected_year: int | None
) -> None:
    name, year = _split_name_and_year(query)
    assert name == expected_name
    assert year == expected_year


def test_tmdb_tv_search_parses_results(mock_http_json) -> None:
    mock_http_json({"search/tv": {"results": [{"id": 5, "name": "N"}, {"id": "x"}]}})
    c = TMDbTVClient(apikey="k")
    out = c.search("Show 2005", "en-US")
    assert [r.id for r in out] == [5]
    assert [r.name for r in out] == ["N"]


def test_tmdb_tv_search_uses_language_and_year(
    monkeypatch: pytest.MonkeyPatch, mock_http_json
) -> None:
    # Ensure language normalization is applied and year filter is used
    # The mock only needs to return an empty results to validate request path mapping
    mock_http_json({"api.themoviedb.org/3/search/tv": {"results": []}})
    called_urls: list[str] = []

    def fake_http(self, url: str, **kwargs):  # type: ignore[override]
        called_urls.append(url)
        return {"results": []}

    monkeypatch.setattr(TMDbTVClient, "_http_get_json", fake_http, raising=True)
    c = TMDbTVClient(apikey="k")
    c.search("Name 2010", "en-US")
    assert called_urls
    assert "language=en-US" in called_urls[0]
    assert "first_air_date_year=2010" in called_urls[0]


def test_tmdb_tv_get_episode_list_and_info(mock_http_json) -> None:
    mock_http_json({
        "tv/100/season/0": {
            "episodes": [
                {
                    "id": 1,
                    "episode_number": 1,
                    "season_number": 0,
                    "name": "Sp1",
                    "air_date": "2020-01-01",
                }
            ]
        },
        "tv/100/season/1": {
            "episodes": [
                {
                    "id": 2,
                    "episode_number": 1,
                    "season_number": 1,
                    "name": "E1",
                    "air_date": "2020-01-02",
                }
            ]
        },
        "tv/100?": {
            "name": "S",
            "original_name": "S",
            "seasons": [{"season_number": 0}, {"season_number": 1}],
        },
        "tv/100": {
            "name": "S",
            "original_name": "S",
            "seasons": [{"season_number": 0}, {"season_number": 1}],
        },
    })
    c = TMDbTVClient(apikey="k")
    eps = c.get_episode_list(100, "Airdate", "en")
    # Episodes of season > 0 first, then specials (season 0) appended at end
    assert len(eps) == 2
    assert eps[0].season == 1
    assert eps[0].episode == 1
    assert eps[0].title == "E1"
    assert eps[1].special_number == 1
    assert eps[1].title == "Sp1"


def test_tmdb_tv_get_episode_list_parsing_edge_cases(mock_http_json) -> None:
    # Mix invalid numbers, missing ids, empty seasons, and None values
    mock_http_json({
        "tv/200/season/1": {
            "episodes": [
                {
                    "id": None,
                    "episode_number": "x",
                    "season_number": "1",
                    "name": "E?",
                    "air_date": None,
                },
                {
                    "id": "3",
                    "episode_number": 2,
                    "season_number": 1,
                    "name": "E2",
                    "air_date": "2020-02-02",
                },
            ]
        },
        "tv/200/season/0": {
            "episodes": [
                {
                    "id": "bad",
                    "episode_number": "not-int",
                    "season_number": 0,
                    "name": "Sp?",
                    "air_date": "2020-01-01",
                }
            ]
        },
        "tv/200?": {
            "name": "S2",
            "original_name": "S2",
            "seasons": [{"season_number": 1}, {"season_number": 0}],
        },
        "tv/200": {
            "name": "S2",
            "original_name": "S2",
            "seasons": [{"season_number": 1}, {"season_number": 0}],
        },
    })
    c = TMDbTVClient(apikey="k")
    eps = c.get_episode_list(200, "Airdate", "en")
    # Expect three: invalid-number episode (episode None), valid regular, and one special
    assert len(eps) == 3
    reg_invalid, reg_valid, sp = eps[0], eps[1], eps[2]
    assert reg_invalid.season == 1
    assert reg_invalid.episode is None
    assert reg_invalid.id is None
    assert reg_valid.season == 1
    assert reg_valid.episode == 2
    assert reg_valid.id == 3
    assert reg_valid.title == "E2"
    assert sp.season is None
    assert sp.episode is None
    assert sp.special_number is None


def test_tmdb_tv_get_series_info_parsing(mock_http_json) -> None:
    mock_http_json({
        "tv/300": {
            "name": "Name",
            "original_name": "Original",
            "status": "Returning Series",
            "episode_run_time": ["45"],
            "genres": [{"name": "Drama"}, {"name": None}, "bad"],
            "networks": [{"name": "HBO"}, "bad"],
        }
    })
    c = TMDbTVClient(apikey="k")
    info = c.get_series_info(300, "en")
    assert info.name == "Name"
    assert info.alias_names == ["Original"]
    assert info.status == "Returning Series"
    assert info.runtime == 45
    assert info.genres == ["Drama"]
    assert info.network == "HBO"


def test_tmdb_tv_public_link() -> None:
    c = TMDbTVClient(apikey="k")
    s = SearchResult(id=7, name="S")
    assert c.get_episode_list_link(s) == "https://www.themoviedb.org/tv/7"
