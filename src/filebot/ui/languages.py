# Copyright (c) 2025 knguyen1

"""Language options for UI components.

This module provides a small typed list of languages for the Episodes screen
language combo box while keeping the view code minimal. The list starts with
English to mirror FileBot and can be extended later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class LanguageOption:
    """Minimal language option descriptor.

    Parameters
    ----------
    code:
        ISO 639-1 language code (e.g., "en").
    label:
        Human-readable language name for display (e.g., "English").
    """

    code: str
    label: str


_LANG_OPTIONS: Final[list[LanguageOption]] = [
    LanguageOption("en", "English"),  # default / favorite
    # Partial list mirroring FileBot ordering; extend as needed
    LanguageOption("af", "Afrikaans"),
    LanguageOption("sq", "Albanian"),
    LanguageOption("ar", "Arabic"),
    LanguageOption("hy", "Armenian"),
    LanguageOption("bg", "Bulgarian"),
    LanguageOption("ca", "Catalan"),
    LanguageOption("hr", "Croatian"),
    LanguageOption("cs", "Czech"),
    LanguageOption("da", "Danish"),
    LanguageOption("nl", "Dutch"),
    LanguageOption("fi", "Finnish"),
    LanguageOption("fr", "French"),
    LanguageOption("de", "German"),
    LanguageOption("el", "Greek"),
    LanguageOption("he", "Hebrew"),
    LanguageOption("hu", "Hungarian"),
    LanguageOption("is", "Icelandic"),
    LanguageOption("it", "Italian"),
    LanguageOption("ja", "Japanese"),
    LanguageOption("ko", "Korean"),
    LanguageOption("no", "Norwegian"),
    LanguageOption("pl", "Polish"),
    LanguageOption("pt", "Portuguese"),
    LanguageOption("ro", "Romanian"),
    LanguageOption("ru", "Russian"),
    LanguageOption("sr", "Serbian"),
    LanguageOption("sk", "Slovak"),
    LanguageOption("sl", "Slovenian"),
    LanguageOption("es", "Spanish"),
    LanguageOption("sv", "Swedish"),
    LanguageOption("tr", "Turkish"),
    LanguageOption("uk", "Ukrainian"),
    LanguageOption("zh", "Chinese"),
]


def get_language_options() -> list[LanguageOption]:
    """Return language options for the UI combo box.

    The list is ordered with English first to match the Java UI. Callers may
    insert a separator after the first item to visually distinguish favorites.
    """
    return list(_LANG_OPTIONS)
