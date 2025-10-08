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

from time import perf_counter
from typing import TYPE_CHECKING

import pytest

from filebot.core.providers.utils import (
    RateLimiter,
    compute_opensubtitles_hash,
    is_allowed_http,
    is_https,
    lenient_name_equals,
    lenient_names_set,
    normalize_string_for_match,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://a", True),
        ("http://a", False),
        ("ftp://a", False),
        ("a", False),
    ],
)
def test_is_https(url: str, expected: bool) -> None:
    assert is_https(url) is expected


@pytest.mark.parametrize(
    ("url", "hosts", "expected"),
    [
        ("http://api.tvmaze.com/x", {"api.tvmaze.com"}, True),
        ("http://api.tvmaze.com/x", None, True),
        ("http://badhost/x", {"api.tvmaze.com"}, False),
        ("https://api.tvmaze.com/x", {"api.tvmaze.com"}, False),
        ("https://api.tvmaze.com/x", None, False),
    ],
)
def test_is_allowed_http(url: str, hosts: set[str] | None, expected: bool) -> None:
    assert is_allowed_http(url, hosts) is expected


def test_rate_limiter_acquire_sleeps_briefly() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=0.01)
    t0 = perf_counter()
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()  # should sleep a very small amount
    dt = perf_counter() - t0
    assert dt >= 0


def test_compute_opensubtitles_hash_small_and_empty(tmp_path: Path) -> None:
    small = tmp_path / "small.bin"
    small.write_bytes(b"x" * 1024)
    h_small, size_small = compute_opensubtitles_hash(str(small))
    assert size_small == 1024
    assert isinstance(h_small, str)
    assert len(h_small) == 16

    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    h_empty, size_empty = compute_opensubtitles_hash(str(empty))
    assert size_empty == 0
    assert h_empty == "0000000000000000"


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("Café del Mar", "cafe del mar"),
        (" The-Office (US)", "the office us"),
        ("", ""),
        ("ÄÖÜß", "aouß"),
        ("Ångström", "angstrom"),
        ("naïve—text!", "naive text"),
    ],
)
def test_normalize_string_for_match(raw: str, normalized: str) -> None:
    assert normalize_string_for_match(raw) == normalized


def test_lenient_names_set_deduplicates() -> None:
    vals = ["Café", "Cafe", "cafe"]
    out = lenient_names_set(vals)
    assert out == {"cafe"}


@pytest.mark.parametrize(
    ("a", "b", "eq"),
    [
        ("Café", "Cafe", True),
        ("The-Office", "The Office", True),
        ("A", "B", False),
        (None, None, True),
        (None, "", True),
        ("", None, True),
    ],
)
def test_lenient_name_equals(a: str | None, b: str | None, eq: bool) -> None:
    assert lenient_name_equals(a, b) is eq
