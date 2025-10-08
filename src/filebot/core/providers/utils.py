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

"""Shared utilities for provider modules.

This module provides helpers for URL validation and a simple sliding-window
rate limiter to protect external API calls.
"""

from __future__ import annotations

import threading
import time
import unicodedata
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit


def is_https(url: str) -> bool:
    """Check if URL uses HTTPS scheme.

    Parameters
    ----------
    url : str
        URL to check.

    Returns
    -------
    bool
        True if URL uses HTTPS scheme, False otherwise.
    """
    parts = urlsplit(url)
    return parts.scheme == "https"


def is_allowed_http(url: str, allowed_hosts: set[str] | None = None) -> bool:
    """Check if URL uses HTTP scheme and is from an allowed host.

    Parameters
    ----------
    url : str
        URL to check.
    allowed_hosts : set[str] | None
        Set of allowed hosts for HTTP URLs. If None, only checks for HTTP scheme.

    Returns
    -------
    bool
        True if URL uses HTTP scheme and is from an allowed host (if specified).
    """
    parts = urlsplit(url)
    if parts.scheme != "http":
        return False

    if allowed_hosts is None:
        return True

    return parts.netloc in allowed_hosts


class RateLimiter:
    """Simple sliding-window rate limiter.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed per window.
    window_seconds:
        Duration of the sliding window in seconds.

    Methods
    -------
    acquire:
        Blocks briefly if necessary to respect the configured rate.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = int(max_requests)
        self._window = float(window_seconds)
        self._events: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Acquire permission to proceed, sleeping if required.

        Notes
        -----
        Uses a sliding window over the last ``window_seconds``. If the number
        of recorded events reaches ``max_requests``, this call will sleep until
        the oldest event falls out of the current window.
        """
        now = time.monotonic()
        with self._lock:
            # purge old events
            cutoff = now - self._window
            while self._events and self._events[0] < cutoff:
                self._events.popleft()

            if len(self._events) < self._max_requests:
                self._events.append(now)
                return

            # need to wait until earliest event leaves window
            sleep_for = self._events[0] + self._window - now
        if sleep_for > 0:
            time.sleep(sleep_for)
        # record event after sleeping
        with self._lock:
            self._events.append(time.monotonic())


def compute_opensubtitles_hash(file_path: str) -> tuple[str, int]:
    """Compute OpenSubtitles movie hash and file size.

    Parameters
    ----------
    file_path:
        Absolute path to the video file.

    Returns
    -------
    tuple[str, int]
        A tuple of (hash_hex, size_bytes). The hash is a 16-character
        lowercase hexadecimal string as expected by OpenSubtitles.

    Notes
    -----
    Algorithm: sum of 64-bit little-endian unsigned integers over the
    first and last 64 KiB of the file plus the file size, reduced modulo
    2^64.
    """
    block_size = 64 * 1024
    p = Path(file_path)
    size = p.stat().st_size

    def _sum_64k(fh, length: int) -> int:
        total = 0
        buf = fh.read(length)
        mv = memoryview(buf)
        n = (len(mv) // 8) * 8
        # sum 8-byte little-endian chunks
        for i in range(0, n, 8):
            chunk = int.from_bytes(mv[i : i + 8], "little", signed=False)
            total = (total + chunk) & 0xFFFFFFFFFFFFFFFF
        # handle remaining tail bytes (pad as little-endian)
        rem = len(mv) - n
        if rem:
            tail = int.from_bytes(mv[n:], "little", signed=False)
            total = (total + tail) & 0xFFFFFFFFFFFFFFFF
        return total

    with p.open("rb") as fh:
        head_sum = _sum_64k(fh, min(block_size, size))
        # seek to start of last 64 KiB (or 0 if file smaller)
        tail_offset = max(size - block_size, 0)
        fh.seek(tail_offset)
        tail_sum = _sum_64k(fh, min(block_size, size))

    # include size
    h = (head_sum + tail_sum + (size & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF
    hash_hex = f"{h:016x}"
    return hash_hex, size


def normalize_string_for_match(value: str, _locale: str | None = None) -> str:
    """Return a lenient-normalized string for name matching.

    Parameters
    ----------
    value:
        Input string to normalize.
    _locale:
        Reserved for future locale-aware normalization rules (unused).

    Returns
    -------
    str
        Normalized string with accents removed, lowercased, punctuation
        replaced by spaces, and collapsed whitespace.

    Notes
    -----
    Normalization strategy:
    - Unicode NFKD + strip diacritics
    - Lowercase
    - Replace non-alphanumeric with single spaces
    - Collapse whitespace
    """
    if not value:
        return ""
    # Decompose accents and remove combining marks
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = without_accents.lower()
    # Replace non-alphanumeric with spaces
    cleaned_chars = [ch if ch.isalnum() else " " for ch in lowered]
    cleaned = "".join(cleaned_chars)
    # Collapse whitespace
    tokens = cleaned.split()
    return " ".join(tokens)


def lenient_names_set(names: list[str], _locale: str | None = None) -> set[str]:
    """Return set of lenient-normalized names.

    Parameters
    ----------
    names:
        List of candidate names.
    _locale:
        Reserved for future locale-aware normalization rules (unused).

    Returns
    -------
    set[str]
        Normalized, deduplicated names.
    """
    return {normalize_string_for_match(n) for n in names if n}


def lenient_name_equals(
    a: str | None, b: str | None, _locale: str | None = None
) -> bool:
    """Compare two names leniently after normalization.

    Parameters
    ----------
    a:
        First name (may be None).
    b:
        Second name (may be None).
    _locale:
        Reserved for future locale-aware normalization rules (unused).

    Returns
    -------
    bool
        True if normalized names are equal, False otherwise.
    """
    return normalize_string_for_match(a or "") == normalize_string_for_match(b or "")
