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

from typing import cast

import pytest

from filebot.core.providers.tvdb import TheTVDBClient, _normalize_language


@pytest.fixture(autouse=True)
def _patch_token(monkeypatch: pytest.MonkeyPatch) -> None:
    # Avoid real network login for token
    monkeypatch.setattr(TheTVDBClient, "_get_token", lambda self: "tok", raising=True)


def test_identifier_and_season_support() -> None:
    c = TheTVDBClient(apikey="k")
    assert c.identifier == "TheTVDB"
    assert c.has_season_support() is True
    # language normalization
    assert _normalize_language("") == "en"
    assert _normalize_language("en_US") == "en-US"
    assert _normalize_language("iw") == "he"
    assert _normalize_language("in_ID") == "id"


def test_request_headers_and_ttl(
    monkeypatch: pytest.MonkeyPatch, mock_http_json
) -> None:
    # Map any URL to empty dict to satisfy mock matcher
    mock_http_json({"api.thetvdb.com/series/1": {}})
    captured: dict[str, object] = {}

    def fake_http(self, url: str, **kwargs):  # type: ignore[override]
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["long_ttl"] = kwargs.get("long_ttl")
        return {}

    monkeypatch.setattr(TheTVDBClient, "_http_get_json", fake_http, raising=True)
    c = TheTVDBClient(apikey="k")
    # non-episodes path => long_ttl True and Accept-Language set
    c._request_json("series/1", {}, "en-US")
    assert captured.get("long_ttl") is True
    headers = captured.get("headers") or {}
    assert headers.get("Authorization") == "Bearer tok"
    assert headers.get("Accept-Language") == "en-US"
    # episodes path => long_ttl False
    c._request_json("series/1/episodes", {"page": 1}, "en-US")
    assert captured.get("long_ttl") is False


def test_search_series_and_series_info(mock_http_json) -> None:
    mock_http_json({
        "api.thetvdb.com/search/series": {
            "data": [
                {"id": 1, "seriesName": "S", "aliases": ["A"]},
                {"id": "bad"},
            ]
        },
        "api.thetvdb.com/series/1": {"data": {"seriesName": "S", "aliases": ["A"]}},
    })
    c = TheTVDBClient(apikey="k")
    res = c.search("S", "en")
    assert len(res) == 1
    assert res[0].name == "S"
    info = c.get_series_info(1, "en")
    assert info.name == "S"
    assert info.alias_names == ["A"]


def test_tvdb_episode_list_and_info(mock_http_json) -> None:
    mock_http_json({
        "series/10/episodes": {
            "links": {"last": 1},
            "data": [
                {
                    "id": 100,
                    "episodeName": "E1",
                    "firstAired": "2020-01-01",
                    "absoluteNumber": 1,
                    "airedSeason": 1,
                    "airedEpisodeNumber": 1,
                },
                {
                    "id": 101,
                    "episodeName": "Special",
                    "firstAired": "2020-01-02",
                    "absoluteNumber": 2,
                    "airedSeason": 0,
                    "airedEpisodeNumber": 1,
                },
            ],
        },
        "episodes/100": {
            "data": {
                "seriesId": 10,
                "overview": "",
                "siteRating": 7.5,
                "siteRatingCount": 10,
                "directors": ["D"],
                "writers": ["W"],
                "guestStars": ["G"],
            }
        },
        "series/10?": {"data": {"seriesName": "S", "aliases": []}},
        "series/10": {"data": {"seriesName": "S", "aliases": []}},
    })
    c = TheTVDBClient(apikey="k")
    eps = c.get_episode_list(10, "Airdate", "en")
    assert len(eps) == 2
    assert eps[0].season == 1
    assert eps[1].special_number == 1
    info = c.get_episode_info(100, "en")
    assert info.get("series_id") == 10
    assert isinstance(info.get("people"), list)


def test_episode_pagination_and_numbering_orders(mock_http_json) -> None:
    mock_http_json({
        # episodes pages (use substring match for both pages)
        "series/10/episodes?page=2": {
            "links": {"last": 2},
            "data": [
                {
                    "id": 102,
                    "episodeName": "E2",
                    "firstAired": "2020-01-03",
                    "absoluteNumber": 3,
                    "airedSeason": 1,
                    "airedEpisodeNumber": 2,
                },
                {
                    "id": 103,
                    "episodeName": "DVD",
                    "dvdSeason": 1,
                    "dvdEpisodeNumber": 5,
                    "absoluteNumber": 4,
                    "airedSeason": 99,
                    "airedEpisodeNumber": 99,
                },
            ],
        },
        "series/10/episodes": {
            "links": {"last": 2},
            "data": [
                {
                    "id": 100,
                    "episodeName": "E1",
                    "firstAired": "2020-01-01",
                    "absoluteNumber": 1,
                    "airedSeason": 1,
                    "airedEpisodeNumber": 1,
                },
                {
                    "id": 101,
                    "episodeName": "Sp",
                    "firstAired": "2020-01-02",
                    "absoluteNumber": 2,
                    "airedSeason": 0,
                    "airedEpisodeNumber": 1,
                },
            ],
        },
        # series info
        "series/10?": {"data": {"seriesName": "S", "aliases": []}},
        "series/10": {"data": {"seriesName": "S", "aliases": []}},
    })
    c = TheTVDBClient(apikey="k")

    eps_air = c.get_episode_list(10, "Airdate", "en")
    # Sorted by season/episode; specials appended last
    assert [e.id for e in eps_air] == [100, 102, 103, 101]

    eps_abs = c.get_episode_list(10, "Absolute", "en")
    assert [e.episode for e in eps_abs[:3]] == [1, 2, 3]

    eps_dvd = c.get_episode_list(10, "DVD", "en")
    dvd_ep = next(e for e in eps_dvd if e.id == 103)
    assert dvd_ep.season == 1
    assert dvd_ep.episode == 5


def test_get_languages_and_actors(mock_http_json) -> None:
    mock_http_json({
        "api.thetvdb.com/languages": {
            "data": [{"abbreviation": "en"}, {"abbreviation": ""}, "bad"]
        },
        "api.thetvdb.com/series/5/actors": {
            "data": [
                {"name": "N", "role": "R", "sortOrder": "2", "image": "x/y.jpg"},
                {"name": 1, "role": None, "sortOrder": "notnum", "image": None},
                "bad",
            ]
        },
    })
    c = TheTVDBClient(apikey="k")
    langs = c.get_languages()
    assert langs == ["en"]
    actors = c.get_actors(5, "en")
    assert [a["name"] for a in actors] == ["N", None]
    assert [a["order"] for a in actors] == [2, None]
    assert [a["image"] for a in actors] == ["https://thetvdb.com/banners/x/y.jpg", None]


def test_get_episode_info_parsing(mock_http_json) -> None:
    mock_http_json({
        "api.thetvdb.com/episodes/100": {
            "data": {
                "seriesId": "10",
                "overview": 5,  # invalid => None
                "siteRating": "7.5",
                "siteRatingCount": "10",
                "directors": ["D", 1],
                "writers": ["W"],
                "guestStars": [None, "G"],
            }
        }
    })
    c = TheTVDBClient(apikey="k")
    info = c.get_episode_info(100, "en")
    assert info["series_id"] == 10
    assert info["overview"] is None
    assert info["rating"] == pytest.approx(7.5)
    assert info["votes"] == 10
    people = info["people"]
    assert isinstance(people, list)
    roles: set[str] = set()
    for item in people:
        if isinstance(item, dict):
            d = cast("dict[str, object]", item)
            role_obj = d.get("role")
            if isinstance(role_obj, str):
                roles.add(role_obj)
    assert roles == {"Director", "Writer", "Guest Star"}


def test_get_artwork_parsing_and_sorting(mock_http_json) -> None:
    mock_http_json({
        "api.thetvdb.com/series/9/images/query?keyType=poster": {
            "data": [
                {
                    "subKey": "season",
                    "resolution": "500x750",
                    "fileName": "a.jpg",
                    "ratingsInfo": {"average": "8.5"},
                },
                {
                    "subKey": None,
                    "resolution": None,
                    "fileName": "b.jpg",
                    "ratingsInfo": {"average": 9},
                },
                {"fileName": "", "ratingsInfo": {"average": "bad"}},
                {"fileName": "c.jpg"},
            ]
        }
    })
    c = TheTVDBClient(apikey="k")
    out = c.get_artwork(9, "poster", "en")
    urls = [a.url for a in out]
    assert urls == [
        "https://thetvdb.com/banners/b.jpg",
        "https://thetvdb.com/banners/a.jpg",
        "https://thetvdb.com/banners/c.jpg",
    ]
    cats = [a.category for a in out]
    assert cats[0] == "poster"
    assert cats[1] == "poster,season,500x750"
