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

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from filebot.core.providers.acoustid import AcoustIDClient


def test_acoustid_identifier(acoustid_client: AcoustIDClient) -> None:
    c = acoustid_client
    assert c.identifier == "AcoustID"


def test_acoustid_lookup_happy_path(
    monkeypatch: pytest.MonkeyPatch, acoustid_client: AcoustIDClient
) -> None:
    # AcoustIDClient uses its own urlopen name from module import
    import json as _json

    def _fake_urlopen(req, timeout=0):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return _json.dumps({"status": "ok", "results": []}).encode()

        return _Resp()

    monkeypatch.setattr(
        "filebot.core.providers.acoustid.urlopen", _fake_urlopen, raising=True
    )

    c = acoustid_client
    out = c.lookup(10, "fingerprint")
    assert isinstance(out, dict)


@pytest.mark.parametrize(("duration", "fingerprint"), [(0, "f"), (10, ""), (0, "")])
def test_acoustid_invalid_input_early_return(
    monkeypatch: pytest.MonkeyPatch,
    acoustid_client: AcoustIDClient,
    duration: int,
    fingerprint: str,
) -> None:
    def _boom(
        req: Any, timeout: int = 0
    ) -> None:  # pragma: no cover - should not be called
        msg = "network should not be called for invalid args"
        raise AssertionError(msg)

    monkeypatch.setattr("filebot.core.providers.acoustid.urlopen", _boom, raising=True)
    c = acoustid_client
    assert c.lookup(duration, fingerprint) == {}


def test_acoustid_disallowed_host(
    monkeypatch: pytest.MonkeyPatch, acoustid_client: AcoustIDClient
) -> None:
    # Disallow host to force early return
    monkeypatch.setattr(
        "filebot.core.providers.acoustid._ACOUSTID_ALLOWED_HOSTS",
        set(),
        raising=True,
    )
    c = acoustid_client
    assert c.lookup(10, "fp") == {}


def test_acoustid_caching_and_limiter(
    monkeypatch: pytest.MonkeyPatch, acoustid_client: AcoustIDClient
) -> None:
    calls = {"n": 0}

    def _ok(req: Any, timeout: int = 0):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                calls["n"] += 1
                return b"{}"

        return _Resp()

    monkeypatch.setattr("filebot.core.providers.acoustid.urlopen", _ok, raising=True)

    c = acoustid_client
    out1 = c.lookup(10, "fp")
    out2 = c.lookup(10, "fp")
    assert out1 == out2 == {}
    # One network call due to cache
    assert calls["n"] == 1


def test_acoustid_json_error_returns_empty(
    monkeypatch: pytest.MonkeyPatch, acoustid_client: AcoustIDClient
) -> None:
    def _bad(req: Any, timeout: int = 0):
        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return b"not-json"

        return _Resp()

    monkeypatch.setattr("filebot.core.providers.acoustid.urlopen", _bad, raising=True)
    c = acoustid_client
    assert c.lookup(10, "fp") == {}


def test_acoustid_http_error_returns_empty(
    monkeypatch: pytest.MonkeyPatch, acoustid_client: AcoustIDClient
) -> None:
    from urllib.error import URLError

    def _raise(req: Any, timeout: int = 0):
        err = URLError("fail")
        raise err

    monkeypatch.setattr("filebot.core.providers.acoustid.urlopen", _raise, raising=True)
    c = acoustid_client
    assert c.lookup(10, "fp") == {}


def test_acoustid_request_contains_params(
    monkeypatch: pytest.MonkeyPatch, acoustid_client: AcoustIDClient
) -> None:
    captured = {"url": "", "headers": {}}

    # Ensure allowed host and clean cache
    monkeypatch.setattr(
        "filebot.core.providers.acoustid._ACOUSTID_ALLOWED_HOSTS",
        {"api.acoustid.org"},
        raising=True,
    )

    def _ok(req: Any, timeout: int = 0):
        # Robustly extract URL and headers from urllib Request
        url_val = getattr(req, "full_url", None)
        if not url_val and hasattr(req, "get_full_url"):
            try:
                url_val = req.get_full_url()
            except Exception:  # pragma: no cover - defensive  # noqa: BLE001
                url_val = ""
        captured["url"] = url_val or ""

        hdrs = dict(getattr(req, "headers", {}))
        if not hdrs and hasattr(req, "header_items"):
            try:
                hdrs = dict(req.header_items())
            except Exception:  # pragma: no cover - defensive  # noqa: BLE001
                hdrs = {}
        captured["headers"] = hdrs

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return b"{}"

        return _Resp()

    monkeypatch.setattr("filebot.core.providers.acoustid.urlopen", _ok, raising=True)
    c = acoustid_client
    c._cache_day.clear()  # type: ignore[attr-defined]
    out = c.lookup(99, "abcdef")
    assert isinstance(out, dict)
    # Fixture uses test-key; replace for loose check
    assert "client=k" in captured["url"].replace("test-key", "k")
    assert "duration=99" in captured["url"]
    assert "fingerprint=abcdef" in captured["url"]
    # Normalize header keys for case-insensitive comparison
    norm_headers = {k.lower(): v for k, v in captured["headers"].items()}
    assert norm_headers.get("accept-encoding") == "gzip"
