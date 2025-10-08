# Copyright (c) 2025 knguyen1

"""Flag icon helpers.

Provides helpers to map ISO language codes to flag icons. We render Unicode
emoji flags into small pixmaps so we don't depend on specific icon fonts.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Final

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont, QIcon, QPainter, QPixmap

_LANG_TO_FLAG_EMOJI: Final[dict[str, str]] = {
    "en": "🇬🇧",
    "af": "🇿🇦",
    "sq": "🇦🇱",
    "ar": "🇸🇦",
    "hy": "🇦🇲",
    "bg": "🇧🇬",
    "ca": "🇪🇸",
    "hr": "🇭🇷",
    "cs": "🇨🇿",
    "da": "🇩🇰",
    "nl": "🇳🇱",
    "fi": "🇫🇮",
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "el": "🇬🇷",
    "he": "🇮🇱",
    "hu": "🇭🇺",
    "is": "🇮🇸",
    "it": "🇮🇹",
    "ja": "🇯🇵",
    "ko": "🇰🇷",
    "no": "🇳🇴",
    "pl": "🇵🇱",
    "pt": "🇵🇹",
    "ro": "🇷🇴",
    "ru": "🇷🇺",
    "sr": "🇷🇸",
    "sk": "🇸🇰",
    "sl": "🇸🇮",
    "es": "🇪🇸",
    "sv": "🇸🇪",
    "tr": "🇹🇷",
    "uk": "🇺🇦",
    "zh": "🇨🇳",
}


def _render_emoji_icon(emoji: str, size: QSize = QSize(20, 16)) -> QIcon:
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        font = QFont()
        font.setPointSize(int(size.height() * 0.9))
        font.setFamily("Apple Color Emoji")
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
    finally:
        painter.end()
    return QIcon(pixmap)


@lru_cache(maxsize=128)
def get_flag_icon(code: str):
    """Return a QIcon of a flag emoji for the given ISO 639-1 language code.

    Returns None if the mapping is unknown.
    """
    emoji = _LANG_TO_FLAG_EMOJI.get(code.lower())
    if not emoji:
        return None
    return _render_emoji_icon(emoji)
