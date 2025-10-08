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

from typing import TYPE_CHECKING

import pytest

from filebot.core.providers.fanarttv import FanartTVClient

if TYPE_CHECKING:  # type-only import to satisfy linter rule
    from filebot.core.models import Artwork


def test_identifier_and_name_properties() -> None:
    c = FanartTVClient(apikey="k")
    assert c.identifier == "FanartTV"
    # BaseDatasource.name defaults to identifier
    assert c.name == "FanartTV"


def test_get_artwork_https_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force is_https to False by patching the base URL to http
    from filebot.core.providers import fanarttv as mod

    monkeypatch.setattr(
        mod, "_FANARTTV_BASE_URL", "http://webservice.fanart.tv/v3/", raising=True
    )
    c = FanartTVClient(apikey="k")
    # Should early-return [] due to HTTPS requirement
    assert c.get_artwork(123, "movie", "en") == []


def test_get_artwork_non_dict_response(mock_http_json) -> None:
    mock_http_json({"webservice.fanart.tv/v3/": [1, 2, 3]})
    c = FanartTVClient(apikey="k")
    assert c.get_artwork(1, "movie", "en") == []


def test_get_artwork_parses_items_and_filters_invalid(mock_http_json) -> None:
    mock_http_json({
        "webservice.fanart.tv/v3/": {
            # valid list with dict items
            "posters": [
                {"url": "https://x/p1.jpg", "lang": "en", "likes": 5},
                {"url": "https://x/p2.jpg", "lang": None, "likes": "3"},
                {"url": "", "likes": "bad"},  # invalid url => filtered
            ],
            # non-list value => ignored
            "banners": {"url": "https://x/ignored.jpg"},
            # list with non-dict item => ignored item
            "thumb": [
                1,
                {"url": "https://x/t1.jpg", "lang": "es", "likes": 0},
            ],
            # category with extra fields for category composition
            "cdarts": [{"url": "https://x/c1.png", "disc_type": "cd1", "likes": "7"}],
            # season artwork should include season in category
            "seasonposter": [{"url": "https://x/s1.jpg", "season": "1", "likes": "2"}],
        }
    })

    c = FanartTVClient(apikey="k")
    out = c.get_artwork(1, "movie", "en")

    # Validate URLs filtered and collected
    urls = [a.url for a in out]
    assert "https://x/p1.jpg" in urls
    assert "https://x/p2.jpg" in urls
    assert "https://x/t1.jpg" in urls
    assert "https://x/c1.png" in urls
    assert "https://x/s1.jpg" in urls
    # invalid/empty url filtered
    assert "" not in urls

    # Validate rating parsing (int/str->float; invalid->None)
    by_url: dict[str, Artwork] = {a.url: a for a in out}
    assert by_url["https://x/p1.jpg"].rating == pytest.approx(5.0)
    assert by_url["https://x/p2.jpg"].rating == pytest.approx(3.0)
    assert by_url["https://x/t1.jpg"].rating == pytest.approx(0.0)
    assert by_url["https://x/c1.png"].rating == pytest.approx(7.0)
    assert by_url["https://x/s1.jpg"].rating == pytest.approx(2.0)

    # Validate language passthrough (None becomes None)
    assert by_url["https://x/p1.jpg"].language == "en"
    assert by_url["https://x/p2.jpg"].language is None

    # Validate category composition: key[,season][,disc_type]
    # posters -> "posters" (no extras)
    assert by_url["https://x/p1.jpg"].category == "posters"
    # cdarts + disc_type
    assert by_url["https://x/c1.png"].category in ("cdarts,cd1", "cdarts")
    # seasonposter + season
    assert by_url["https://x/s1.jpg"].category in ("seasonposter,1", "seasonposter")


def test_get_artwork_empty_category_list(mock_http_json) -> None:
    mock_http_json({"webservice.fanart.tv/v3/": {"posters": []}})
    c = FanartTVClient(apikey="k")
    assert c.get_artwork(1, "movie", "en") == []


def test_get_artwork_unknown_fields_do_not_crash(mock_http_json) -> None:
    mock_http_json({
        "webservice.fanart.tv/v3/": {
            "weird": [
                {"url": "https://x/w1.jpg", "likes": "not-a-number"},
                {"url": "https://x/w2.jpg", "likes": None},
                {"url": "https://x/w3.jpg", "extra": {"nested": True}},
            ]
        }
    })
    c = FanartTVClient(apikey="k")
    out = c.get_artwork(1, "movie", "en")
    urls = {a.url for a in out}
    assert urls == {"https://x/w1.jpg", "https://x/w2.jpg", "https://x/w3.jpg"}
    # All with None rating when likes is invalid/None
    assert all(a.rating is None for a in out)
