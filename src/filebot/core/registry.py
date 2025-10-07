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
from filebot.core.providers.base import (
    EpisodeListProvider,
    MovieIdentificationService,
)
from filebot.core.providers.tmdb import TMDbClient
from filebot.core.providers.tvdb import TheTVDBClient


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

    def get_movie_identification_services(self) -> list[MovieIdentificationService]:
        """Return configured movie identification services."""
        return list(self.movies)

    def get_episode_list_providers(self) -> list[EpisodeListProvider]:
        """Return configured episode list providers."""
        return list(self.episodes)

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

    if config.tmdb_api_key:
        tmdb = TMDbClient(apikey=config.tmdb_api_key)
        movies.append(tmdb)
        # TMDb can also serve TV data; include later when implemented

    if config.tvdb_api_key:
        tvdb = TheTVDBClient(apikey=config.tvdb_api_key)
        episodes.append(tvdb)

    return ProviderRegistry(movies=movies, episodes=episodes)


# Default, environment-based registry
provider_registry: ProviderRegistry = _build_registry(load_config_from_env())
