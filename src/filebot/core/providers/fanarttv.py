# Copyright (c) 2025 knguyen1

"""FanartTV artwork provider."""

from __future__ import annotations

from dataclasses import dataclass, field

from cachetools import TTLCache

from filebot.core.models import Artwork
from filebot.core.providers.base import ArtworkProvider, BaseDatasource, RestClientMixin
from filebot.core.providers.utils import is_https


@dataclass(slots=True)
class FanartTVClient(BaseDatasource, RestClientMixin, ArtworkProvider):
    """FanartTV client.

    Parameters
    ----------
    apikey:
        FanartTV API key.
    """

    apikey: str
    _cache_week: TTLCache = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize cache for FanartTV client."""
        # Artwork sets are fairly static; cache for a week
        self._cache_week = TTLCache(maxsize=4096, ttl=7 * 24 * 60 * 60)

    @property
    def identifier(self) -> str:
        """Return the unique provider identifier."""
        return "FanartTV"

    def get_artwork(self, media_id: int, category: str, locale: str) -> list[Artwork]:
        """Return artwork items for a given media identifier and category."""
        url = f"https://webservice.fanart.tv/v3/{category}/{media_id}?api_key={self.apikey}"
        if not is_https(url):
            return []

        data = self._http_get_json(url, timeout=15, long_ttl=True, require_https=True)
        if not isinstance(data, dict):
            return []

        artworks: list[Artwork] = []
        if isinstance(data, dict):
            for key, value in data.items():
                if not isinstance(value, list):
                    continue
                for it in value:
                    if not isinstance(it, dict):
                        continue
                    url_val = it.get("url")
                    lang = it.get("lang") or None
                    likes = it.get("likes")
                    season = it.get("season")
                    disc_type = it.get("disc_type")
                    try:
                        rating = (
                            float(likes)
                            if isinstance(likes, (int, float, str))
                            else None
                        )
                    except ValueError:
                        rating = None
                    category_name = ",".join([p for p in [key, season, disc_type] if p])
                    if isinstance(url_val, str) and url_val:
                        artworks.append(
                            Artwork(
                                category=category_name or key,
                                url=url_val,
                                language=lang,
                                rating=rating,
                            )
                        )
        return artworks
