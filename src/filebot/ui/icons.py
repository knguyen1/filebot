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

"""Icon utilities for the UI.

This module provides a small registry for resolving semantic icon names to
platform-appropriate `QIcon` instances using Qt's standard pixmaps. This keeps
widget code clean and adheres to SRP/DRY.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Final

import qtawesome as qta

if TYPE_CHECKING:  # type-only import
    from PyQt6.QtGui import QIcon

# Mapping from semantic names to one or more Font Awesome 5 icon keys.
_ICON_MAP: Final[dict[str, tuple[str, ...]]] = {
    # Sidebar
    "rename": ("fa5s.folder", "fa5s.folder-open"),
    "episodes": ("fa5s.tv", "fa5s.film"),
    "subtitles": ("fa5s.closed-captioning", "fa5s.comment-dots"),
    "sfv": ("fa5s.check-circle", "fa5s.check"),
    "filter": ("fa5s.filter",),
    "list": ("fa5s.list", "fa5s.stream"),
    # Center controls
    "match": ("fa5s.arrows-alt-h", "fa5s.exchange-alt"),
    "rename_action": ("fa5s.angle-right", "fa5s.arrow-right"),
    # Bottom toolbars
    "move_down": ("fa5s.arrow-down", "fa5s.chevron-down"),
    "move_up": ("fa5s.arrow-up", "fa5s.chevron-up"),
    "swap": ("fa5s.exchange-alt", "fa5s.sync-alt", "fa5s.sync"),
    "fetch": ("fa5s.download", "fa5s.cloud-download-alt"),
    "copy": ("fa5s.copy",),
    "tools": ("fa5s.tools", "fa5s.wrench"),
    # Search specific
    "find": ("fa5s.binoculars", "fa5s.search"),
}

# Default colors for icons to avoid grayscale look.
_ICON_COLOR_MAP: Final[dict[str, str]] = {
    # Sidebar
    "rename": "#f39c12",  # orange
    "episodes": "#3498db",  # blue
    "subtitles": "#9b59b6",  # purple
    "sfv": "#28a745",  # green
    "filter": "#6c757d",  # gray
    "list": "#17a2b8",  # teal
    # Center controls
    "match": "#2ecc71",  # green
    "rename_action": "#1abc9c",  # turquoise
    # Bottom toolbars
    "move_down": "#e67e22",  # orange
    "move_up": "#28a745",  # green
    "swap": "#e67e22",  # orange
    "fetch": "#007bff",  # primary blue
    "copy": "#95a5a6",  # muted gray
    "tools": "#7f8c8d",  # dark gray
    # Search specific
    "find": "#2c3e50",  # dark blue-gray
}


@lru_cache(maxsize=128)
def get_icon(
    name: str, *, _use_app_style: bool = True, color: str | None = None
) -> QIcon:
    """Return a `QIcon` for the given semantic icon name.

    Parameters
    ----------
    name:
        Semantic icon key. See `_ICON_MAP` for available keys.
    _use_app_style:
        Unused. Kept for API compatibility.
    color:
        Optional color string (e.g., "#ffffff") to tint the icon.

    Returns
    -------
    QIcon
        The resolved icon. If the key is unknown or loading fails, a generic
        file icon is returned.
    """
    candidates = _ICON_MAP.get(name, ("fa5s.file",))
    # Pick the first candidate deterministically to avoid broad exception handling.
    key = candidates[0] if candidates else "fa5s.file"
    tint = color if color is not None else _ICON_COLOR_MAP.get(name)
    return qta.icon(key, color=tint) if tint else qta.icon(key)
