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

from typing import TYPE_CHECKING, Any, Self

from cachetools import TTLCache

from filebot.core.providers.base import RestClientMixin

if TYPE_CHECKING:
    import pytest


class DummyClient(RestClientMixin):
    def __init__(self) -> None:
        self._cache_short = TTLCache(maxsize=16, ttl=60)
        self._cache_long = TTLCache(maxsize=16, ttl=60)

        class _Limiter:
            def __init__(self) -> None:
                self.calls = 0

            def acquire(self) -> None:
                self.calls += 1

        self._limiter = _Limiter()


def _mock_urlopen(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    class _Resp:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:  # pragma: no cover - trivial
            return None

    def _factory(req: Any, timeout: int = 0) -> _Resp:
        return _Resp(body)

    monkeypatch.setattr("filebot.core.providers.base.urlopen", _factory, raising=True)


def test_http_get_json_https_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient()
    # http rejected when require_https=True
    out = client._http_get_json("http://example.com/x", require_https=True)
    assert out == {}

    # https accepted and parsed
    import json as _json

    _mock_urlopen(monkeypatch, _json.dumps({"ok": 1}).encode())
    out2 = client._http_get_json("https://example.com/x", require_https=True)
    assert out2 == {"ok": 1}


def test_http_get_json_cache_and_limiter(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient()
    calls = {"n": 0}

    class _Resp:
        def __init__(self) -> None:
            pass

        def read(self) -> bytes:
            calls["n"] += 1
            return b"{}"

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:  # pragma: no cover - trivial
            return None

    def _factory(req: Any, timeout: int = 0) -> _Resp:
        return _Resp()

    monkeypatch.setattr("filebot.core.providers.base.urlopen", _factory, raising=True)

    url = "https://example.com/a"
    out1 = client._http_get_json(url, cache_key="k1")
    out2 = client._http_get_json(url, cache_key="k1")
    assert out1 == {}
    assert out2 == {}
    assert calls["n"] == 1  # second call is cached


def test_http_get_json_allowed_http_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient()
    _mock_urlopen(monkeypatch, b"{}")
    out = client._http_get_json(
        "http://api.tvmaze.com/x",
        require_https=False,
        allowed_http_hosts={"api.tvmaze.com"},
    )
    assert out == {}


def test_http_get_bytes_behaviour(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient()
    _mock_urlopen(monkeypatch, b"abc")
    b1 = client._http_get_bytes("https://example.com/x")
    b2 = client._http_get_bytes("https://example.com/x")
    assert b1 == b"abc"
    assert b2 == b"abc"


def test_http_get_json_headers_and_cache_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient()
    calls = {"n": 0, "last_req": None}

    class _Resp:
        def read(self) -> bytes:
            calls["n"] += 1
            return b"{}"

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:  # pragma: no cover - trivial
            return None

    def _factory(req: Any, timeout: int = 0) -> _Resp:
        calls["last_req"] = req
        return _Resp()

    monkeypatch.setattr("filebot.core.providers.base.urlopen", _factory, raising=True)

    # First call stores under cache_key in long cache
    headers = {"X-Test": "1"}
    out1 = client._http_get_json(
        "https://example.com/a1",
        headers=headers,
        cache_key="same",
        long_ttl=True,
        require_https=True,
    )
    assert out1 == {}
    assert calls["n"] == 1
    assert "same" in client._cache_long  # type: ignore[attr-defined]
    # Headers propagated to Request
    req = calls["last_req"]
    assert getattr(req, "full_url", "").startswith("https://example.com/")
    rh = {k.lower(): v for k, v in dict(getattr(req, "headers", {})).items()}
    assert rh.get("x-test") == "1"

    # Second call with different URL but same cache_key hits cache (no network)
    out2 = client._http_get_json(
        "https://example.com/a2",
        headers=headers,
        cache_key="same",
        long_ttl=True,
        require_https=True,
    )
    assert out2 == {}
    assert calls["n"] == 1


def test_http_get_json_allowed_http_hosts_none_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = DummyClient()
    # HTTP URL with require_https False but no allowed_http_hosts -> blocked
    out = client._http_get_json(
        "http://api.tvmaze.com/x",
        require_https=False,
        allowed_http_hosts=None,
    )
    assert out == {}


def test_http_get_bytes_scheme_guards_and_identity_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = DummyClient()

    # Blocked due to HTTP with no allowed host
    out = client._http_get_bytes(
        "http://example.com/x",
        require_https=False,
        allowed_http_hosts=None,
    )
    assert out is None

    # Allowed host passes; identity cached in long vs short cache is per long_ttl flag
    class _Resp:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self) -> bytes:
            return self._data

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:  # pragma: no cover - trivial
            return None

    def _factory(req: Any, timeout: int = 0) -> _Resp:
        return _Resp(b"xyz")

    monkeypatch.setattr("filebot.core.providers.base.urlopen", _factory, raising=True)

    b1 = client._http_get_bytes(
        "http://api.tvmaze.com/x",
        require_https=False,
        allowed_http_hosts={"api.tvmaze.com"},
        long_ttl=False,
    )
    b2 = client._http_get_bytes(
        "http://api.tvmaze.com/x",
        require_https=False,
        allowed_http_hosts={"api.tvmaze.com"},
        long_ttl=False,
    )
    assert b1 == b"xyz"
    assert b2 is b1  # identity from cache


def test_http_get_json_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyClient()

    from email.message import Message
    from urllib.error import HTTPError, URLError

    # JSON decode error
    class _Bad:
        def read(self) -> bytes:
            return b"not-json"

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:  # pragma: no cover - trivial
            return None

    def _factory_bad(req: Any, timeout: int = 0) -> _Bad:
        return _Bad()

    monkeypatch.setattr(
        "filebot.core.providers.base.urlopen", _factory_bad, raising=True
    )
    out = client._http_get_json("https://example.com/x")
    assert out == {}

    # HTTPError
    def _raise_http(req: Any, timeout: int = 0) -> None:
        headers = Message()
        headers["Content-Type"] = "application/json"
        err = HTTPError(
            url="https://example.com/x", code=500, msg="err", hdrs=headers, fp=None
        )
        raise err

    monkeypatch.setattr(
        "filebot.core.providers.base.urlopen", _raise_http, raising=True
    )
    out = client._http_get_json("https://example.com/x")
    assert out == {}

    # URLError
    def _raise_url(req: Any, timeout: int = 0) -> None:
        err = URLError("fail")
        raise err

    monkeypatch.setattr("filebot.core.providers.base.urlopen", _raise_url, raising=True)
    out = client._http_get_json("https://example.com/x")
    assert out == {}


def test_init_rest_sets_attributes() -> None:
    class _C(RestClientMixin):
        pass

    c = _C()
    # without rate
    c._init_rest(short_ttl=1, long_ttl=2)
    assert hasattr(c, "_cache_short")
    assert hasattr(c, "_cache_long")
    # with rate
    c2 = _C()
    c2._init_rest(short_ttl=1, long_ttl=2, rate=(1, 0.1))
    assert hasattr(c2, "_limiter")
