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

"""Core registry module."""

from dataclasses import dataclass, field

from filebot.core.config import AppConfig, load_config_from_env
from filebot.core.providers.acoustid import AcoustIDClient
from filebot.core.providers.anidb import AniDBClient
from filebot.core.providers.base import (
    ArtworkProvider,
    EpisodeListProvider,
    MovieIdentificationService,
    MusicIdentificationService,
    SubtitleProvider,
)
from filebot.core.providers.fanarttv import FanartTVClient
from filebot.core.providers.omdb import OMDbClient
from filebot.core.providers.tmdb import TMDbClient
from filebot.core.providers.tvdb import TheTVDBClient
from filebot.core.providers.tvmaze import TVMazeClient


@dataclass(slots=True)
class ProviderRegistry:
    """Registry of configured provider clients.

    Parameters
    ----------
    movies:
        Movie identification services.
    episodes:
        Episode list providers.
    """

    movies: list[MovieIdentificationService] = field(default_factory=list)
    episodes: list[EpisodeListProvider] = field(default_factory=list)
    artworks: list[ArtworkProvider] = field(default_factory=list)
    music: list[MusicIdentificationService] = field(default_factory=list)
    subtitles: list[SubtitleProvider] = field(default_factory=list)

    def get_movie_identification_services(self) -> list[MovieIdentificationService]:
        """Return configured movie identification services."""
        return list(self.movies)

    def get_episode_list_providers(self) -> list[EpisodeListProvider]:
        """Return configured episode list providers."""
        return list(self.episodes)

    def get_artwork_providers(self) -> list[ArtworkProvider]:
        """Return configured artwork providers."""
        return list(self.artworks)

    def get_music_identification_services(self) -> list[MusicIdentificationService]:
        """Return configured music identification services."""
        return list(self.music)

    def get_subtitle_providers(self) -> list[SubtitleProvider]:
        """Return configured subtitle providers."""
        return list(self.subtitles)

    def get_service_by_identifier(self, identifier: str):
        """Find a provider by its identifier (case-insensitive)."""
        ident = identifier.lower()
        for svc in [*self.movies, *self.episodes]:
            if getattr(svc, "identifier", "").lower() == ident:
                return svc
        return None


def _build_registry(config: AppConfig) -> ProviderRegistry:
    movies: list[MovieIdentificationService] = []
    episodes: list[EpisodeListProvider] = []
    artworks: list[ArtworkProvider] = []
    music: list[MusicIdentificationService] = []
    subtitles: list[SubtitleProvider] = []

    if config.tmdb_api_key:
        tmdb = TMDbClient(apikey=config.tmdb_api_key)
        movies.append(tmdb)
        # TMDb can also serve TV data; include later when implemented

    if config.omdb_api_key:
        movies.append(OMDbClient(apikey=config.omdb_api_key))

    if config.tvdb_api_key:
        tvdb = TheTVDBClient(apikey=config.tvdb_api_key)
        episodes.append(tvdb)

    if config.anidb_client and config.anidb_clientver:
        anidb = AniDBClient(
            client=config.anidb_client, clientver=config.anidb_clientver
        )
        episodes.append(anidb)

    # TVmaze requires no keys; always available
    episodes.append(TVMazeClient())

    # Optional providers
    if config.fanarttv_api_key:
        artworks.append(FanartTVClient(apikey=config.fanarttv_api_key))
    if config.acoustid_api_key:
        music.append(AcoustIDClient(apikey=config.acoustid_api_key))
    # OpenSubtitles requires XML-RPC credentials; stub not added by default

    return ProviderRegistry(
        movies=movies,
        episodes=episodes,
        artworks=artworks,
        music=music,
        subtitles=subtitles,
    )


# Default, environment-based registry
provider_registry: ProviderRegistry = _build_registry(load_config_from_env())
