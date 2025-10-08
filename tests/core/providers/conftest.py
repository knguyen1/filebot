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

"""Provider-scoped pytest fixtures.

These fixtures are only imported for provider tests under tests/core/providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from filebot.core.providers.acoustid import AcoustIDClient
from filebot.core.providers.base import RestClientMixin

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def noop_limiter() -> object:
    """Limiter object with a no-op acquire method for tests."""

    class _NoopLimiter:
        calls: int = 0

        def acquire(self) -> None:  # pragma: no cover - trivial
            self.__class__.calls += 1

    return _NoopLimiter()


@pytest.fixture
def mock_http_json(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, object]], None]:
    """Factory to mock `RestClientMixin._http_get_json`.

    Parameters
    ----------
    mapping:
        Dict mapping substring match (typically path) to return value.
    """

    def _apply(mapping: dict[str, object]) -> None:
        def _fake(self: RestClientMixin, url: str, **_: object) -> object:  # type: ignore[override]
            for key, value in mapping.items():
                if key in url:
                    return value
            return {}

        monkeypatch.setattr(RestClientMixin, "_http_get_json", _fake, raising=True)

    return _apply


@pytest.fixture
def mock_http_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, bytes | None]], None]:
    """Factory to mock `RestClientMixin._http_get_bytes`.

    Parameters
    ----------
    mapping:
        Dict mapping substring match (typically path) to bytes to return.
    """

    def _apply(mapping: dict[str, bytes | None]) -> None:
        def _fake(self: RestClientMixin, url: str, **_: object) -> bytes | None:  # type: ignore[override]
            for key, value in mapping.items():
                if key in url:
                    return value
            return None

        monkeypatch.setattr(RestClientMixin, "_http_get_bytes", _fake, raising=True)

    return _apply


@pytest.fixture
def acoustid_client(monkeypatch: pytest.MonkeyPatch) -> AcoustIDClient:
    """Return an `AcoustIDClient` with in-memory cache and no-op limiter.

    Notes
    -----
    The production `__post_init__` relies on a mixin not used by `AcoustIDClient`.
    We override the initializer to set required attributes for unit testing.
    """

    from cachetools import TTLCache as _TTLCache

    def _init(self: AcoustIDClient) -> None:  # type: ignore[override]
        self._cache_day = _TTLCache(maxsize=128, ttl=60)  # type: ignore[attr-defined]

        class _Limiter:
            def __init__(self) -> None:
                self.calls = 0

            def acquire(self) -> None:  # pragma: no cover - trivial
                self.calls += 1

        self._limiter = _Limiter()  # type: ignore[attr-defined]

    monkeypatch.setattr(AcoustIDClient, "__post_init__", _init, raising=True)
    return AcoustIDClient(apikey="test-key")
