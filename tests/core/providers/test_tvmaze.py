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

from typing import TYPE_CHECKING, cast

from filebot.core.models import SearchResult
from filebot.core.providers.tvmaze import TVMazeClient

if TYPE_CHECKING:
    import pytest


def test_identifier_and_season_support_and_public_link() -> None:
    c = TVMazeClient()
    assert c.identifier == "TVmaze"
    assert c.has_season_support() is True
    s = SearchResult(id=9, name="S")
    assert c.get_episode_list_link(s) == "http://www.tvmaze.com/shows/9"


def test_request_params_and_allowed_host(
    monkeypatch: pytest.MonkeyPatch, mock_http_json
) -> None:
    mock_http_json({"api.tvmaze.com/search/shows?q=Name": []})
    captured: dict[str, object] = {}

    def fake_http(self, url: str, **kwargs):  # type: ignore[override]
        captured["url"] = url
        captured["require_https"] = kwargs.get("require_https")
        captured["allowed_http_hosts"] = kwargs.get("allowed_http_hosts")
        captured["long_ttl"] = kwargs.get("long_ttl")
        return []

    monkeypatch.setattr(TVMazeClient, "_http_get_json", fake_http, raising=True)
    c = TVMazeClient()
    c.search("Name", "")
    assert captured.get("url") == "http://api.tvmaze.com/search/shows?q=Name"
    assert captured.get("require_https") is False
    assert captured.get("long_ttl") is False
    set_hosts = captured.get("allowed_http_hosts")
    assert isinstance(set_hosts, set)
    hosts_set = cast("set[str]", set_hosts)
    assert "api.tvmaze.com" in hosts_set


def test_tvmaze_search_parsing_and_trim(mock_http_json) -> None:
    mock_http_json({
        "search/shows?": [
            {"show": {"id": 3, "name": "  A  "}},
            {"show": {"id": "x"}},
            {"notshow": {"id": 4}},
            1,
        ]
    })
    c = TVMazeClient()
    res = c.search("A", "")
    assert [r.id for r in res] == [3]
    assert res[0].name == "A"


def test_get_series_info_and_episodes_parsing(mock_http_json) -> None:
    mock_http_json({
        "shows/3/episodes": [
            {
                "id": 1,
                "season": 1,
                "number": 1,
                "name": "Pilot",
                "airdate": "2020-01-01",
            },
            {"id": "bad", "season": "2", "number": "x", "name": 5, "airdate": None},
            {"id": 2, "season": "2", "number": "10", "name": "E", "airdate": ""},
            "bad",
        ],
        "shows/3": {"id": 3, "name": "  A  "},
    })
    c = TVMazeClient()
    info = c.get_series_info(3, "")
    assert info.id == 3
    assert info.name == "A"
    eps = c.get_episode_list(3, "ignored", "")
    # Order will be as listed for valid dicts; the invalid-number episode will have None fields
    assert [e.id for e in eps] == [1, None, 2]
    assert [e.season for e in eps] == [1, 2, 2]
    assert [e.episode for e in eps] == [1, None, 10]
    assert [e.title for e in eps] == ["Pilot", None, "E"]
    assert [e.airdate for e in eps] == ["2020-01-01", None, None]
