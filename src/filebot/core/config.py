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

"""Core config module."""

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    """Application configuration for web service clients.

    Parameters
    ----------
    tmdb_api_key:
        API key for TMDb (TheMovieDB) if configured.
    tvdb_api_key:
        API key for TheTVDB if configured.
    """

    tmdb_api_key: str | None = None
    tvdb_api_key: str | None = None


def load_config_from_env() -> AppConfig:
    """Load configuration from environment variables.

    Environment
    ----
    FILEBOT_API_TMDB:
        API key for TheMovieDB.
    FILEBOT_API_TVDB:
        API key for TheTVDB.

    Returns
    -------
    AppConfig
        Loaded configuration object.
    """
    return AppConfig(
        tmdb_api_key=os.getenv("FILEBOT_API_TMDB"),
        tvdb_api_key=os.getenv("FILEBOT_API_TVDB"),
    )
