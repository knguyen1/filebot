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

"""Core providers package."""

from __future__ import annotations

from filebot.core.providers.acoustid import AcoustIDClient
from filebot.core.providers.anidb import AniDBClient
from filebot.core.providers.base import (
    ArtworkProvider,
    BaseDatasource,
    Datasource,
    EpisodeListProvider,
    MovieIdentificationService,
    MusicIdentificationService,
    SubtitleProvider,
)
from filebot.core.providers.fanarttv import FanartTVClient
from filebot.core.providers.omdb import OMDbClient
from filebot.core.providers.opensubtitles import OpenSubtitlesClient
from filebot.core.providers.tmdb import TMDbClient
from filebot.core.providers.tvdb import TheTVDBClient
from filebot.core.providers.tvmaze import TVMazeClient

__all__ = [
    "AcoustIDClient",
    "AniDBClient",
    "ArtworkProvider",
    "BaseDatasource",
    "Datasource",
    "EpisodeListProvider",
    "FanartTVClient",
    "MovieIdentificationService",
    "MusicIdentificationService",
    "OMDbClient",
    "OpenSubtitlesClient",
    "SubtitleProvider",
    "TMDbClient",
    "TVMazeClient",
    "TheTVDBClient",
]
