# Copyright (c) 2025 knguyen1

"""OpenSubtitles provider (tokenless placeholders for now).

This implementation provides only the interface and a guarded stub for
searching by tag, intended to be expanded with XML-RPC in future phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from filebot.core.models import SubtitleSearchResult

from filebot.core.providers.base import BaseDatasource, SubtitleProvider


@dataclass(slots=True)
class OpenSubtitlesClient(BaseDatasource, SubtitleProvider):
    """OpenSubtitles client (stub for search)."""

    app_name: str
    app_version: str

    @property
    def identifier(self) -> str:
        """Return the OpenSubtitles provider identifier."""
        return "OpenSubtitles"

    def search(self, query: str) -> list[SubtitleSearchResult]:
        """Stub: OpenSubtitles XML-RPC search is restricted; return empty list."""
        return []
