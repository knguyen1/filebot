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
from collections import deque
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
