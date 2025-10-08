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

from filebot.core.config import AppConfig
from filebot.core.providers.acoustid import AcoustIDClient
from filebot.core.providers.anidb import AniDBClient
from filebot.core.providers.fanarttv import FanartTVClient
from filebot.core.providers.omdb import OMDbClient
from filebot.core.providers.tmdb import TMDbClient
from filebot.core.providers.tmdb_tv import TMDbTVClient
from filebot.core.providers.tvdb import TheTVDBClient
from filebot.core.providers.tvmaze import TVMazeClient
from filebot.core.registry import ProviderRegistry, _build_registry


def test_build_registry_minimal_config() -> None:
    cfg = AppConfig()
    reg = _build_registry(cfg)

    assert isinstance(reg, ProviderRegistry)
    # Movies/music/artworks/subtitles empty with no keys
    assert reg.get_movie_identification_services() == []
    assert reg.get_artwork_providers() == []
    assert reg.get_music_identification_services() == []
    assert reg.get_subtitle_providers() == []

    # TVMaze is always present for episodes
    eps = reg.get_episode_list_providers()
    assert len(eps) == 1
    assert isinstance(eps[0], TVMazeClient)


def test_build_registry_with_all_keys(monkeypatch) -> None:
    # Avoid calling _init_rest in AcoustIDClient during registry construction
    monkeypatch.setattr(
        AcoustIDClient, "__post_init__", lambda self: None, raising=True
    )

    cfg = AppConfig(
        tmdb_api_key="t",
        tvdb_api_key="d",
        anidb_client="c",
        anidb_clientver=1,
        omdb_api_key="o",
        fanarttv_api_key="f",
        acoustid_api_key="a",
    )
    reg = _build_registry(cfg)

    movies = reg.get_movie_identification_services()
    movie_types = {type(m) for m in movies}
    assert TMDbClient in movie_types
    assert OMDbClient in movie_types

    episodes = reg.get_episode_list_providers()
    episode_types = {type(e) for e in episodes}
    assert TMDbTVClient in episode_types
    assert TheTVDBClient in episode_types
    assert AniDBClient in episode_types
    assert TVMazeClient in episode_types  # always present

    artworks = reg.get_artwork_providers()
    assert any(isinstance(a, FanartTVClient) for a in artworks)

    music = reg.get_music_identification_services()
    assert any(isinstance(m, AcoustIDClient) for m in music)

    # No subtitle providers by default
    assert reg.get_subtitle_providers() == []


def test_anidb_requires_both_client_and_version() -> None:
    cfg_missing_ver = AppConfig(anidb_client="c", anidb_clientver=None)
    reg1 = _build_registry(cfg_missing_ver)
    assert all(
        not isinstance(e, AniDBClient) for e in reg1.get_episode_list_providers()
    )

    cfg_missing_client = AppConfig(anidb_client=None, anidb_clientver=1)
    reg2 = _build_registry(cfg_missing_client)
    assert all(
        not isinstance(e, AniDBClient) for e in reg2.get_episode_list_providers()
    )


def test_getters_return_copies() -> None:
    cfg = AppConfig(tmdb_api_key="t")
    reg = _build_registry(cfg)

    original_eps = reg.get_episode_list_providers()
    assert original_eps  # TMDbTV + TVMaze
    # Mutate the returned list and ensure registry state is unaffected
    original_eps.append(TVMazeClient())
    again = reg.get_episode_list_providers()
    assert len(again) + 1 == len(original_eps)
    # Identity differs (returned list is a copy)
    assert again is not original_eps


def test_lookup_by_identifier_case_insensitive() -> None:
    cfg = AppConfig(tmdb_api_key="t", omdb_api_key="o")
    reg = _build_registry(cfg)

    svc1 = reg.get_service_by_identifier("themoviedb::tv")
    assert isinstance(svc1, TMDbTVClient)

    svc2 = reg.get_service_by_identifier("OMDb")
    assert isinstance(svc2, OMDbClient)

    # Non-movie/episode providers are not searched
    assert reg.get_service_by_identifier("FanartTV") is None
    assert reg.get_service_by_identifier("AcoustID") is None

    # Unknown returns None
    assert reg.get_service_by_identifier("unknown") is None
