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

"""Core business logic for FileBot (providers, models, registry).

Exposes high-level access to configured web service clients via
`provider_registry`.
"""

from filebot.core.config import AppConfig, load_config_from_env
from filebot.core.models import Episode, Movie, SearchResult, SeriesInfo
from filebot.core.providers.base import (
    BaseDatasource,
    Datasource,
    EpisodeListProvider,
    MovieIdentificationService,
)
from filebot.core.registry import ProviderRegistry, provider_registry

__all__ = [
    "AppConfig",
    "BaseDatasource",
    "Datasource",
    "Episode",
    "EpisodeListProvider",
    "Movie",
    "MovieIdentificationService",
    "ProviderRegistry",
    "SearchResult",
    "SeriesInfo",
    "load_config_from_env",
    "provider_registry",
]
