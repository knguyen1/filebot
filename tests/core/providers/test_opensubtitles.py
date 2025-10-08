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

from filebot.core.providers.opensubtitles import OpenSubtitlesClient

if TYPE_CHECKING:  # pragma: no cover - types only
    from pathlib import Path


def test_opensubtitles_search_and_hash(mock_http_json, tmp_path: Path) -> None:
    mock_http_json({
        "/search/query-": [
            {
                "SubFileName": "A.srt",
                "SubLanguageID": "en",
                "IDMovieImdb": "123",
                "ZipDownloadLink": "https://x",
            }
        ]
    })
    c = OpenSubtitlesClient(app_name="App", app_version="1.0")
    res = c.search("A")
    assert len(res) == 1
    assert res[0].imdb_id == 123
    assert res[0].url == "https://x"

    # hash search
    video = tmp_path / "v.bin"  # type: ignore[name-defined]
    video.write_bytes(b"A" * (70 * 1024))
    mock_http_json({
        "/search/moviebytesize-": [
            {
                "SubFileName": "B.srt",
                "SubLanguageID": "en",
                "IDMovieImdb": 321,
                "ZipDownloadLink": "https://y",
            }
        ]
    })
    res2 = c.search_by_hash(str(video))
    assert len(res2) == 1
    assert res2[0].imdb_id == 321
    assert res2[0].url == "https://y"


def test_opensubtitles_search_best(tmp_path: Path, mock_http_json) -> None:
    c = OpenSubtitlesClient(app_name="App", app_version="1.0")
    # no hash results -> fallback
    mock_http_json({
        "/search/moviebytesize-": [],
        "/search/query-": [{"SubFileName": "C.srt"}],
    })
    video = tmp_path / "v.bin"  # type: ignore[name-defined]
    video.write_bytes(b"A" * (70 * 1024))
    out = c.search_best(str(video), tag="C")
    assert out
    assert out[0].name == "C.srt"
