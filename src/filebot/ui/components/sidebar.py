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

"""Sidebar UI components.

This module defines the `Sidebar` widget that renders the vertical navigation
buttons shown on the left side of the application window. The widget is kept
intentionally dumb and self-contained to adhere to SRP and SOC; it exposes no
behavior beyond rendering the buttons with stable object names so that other
layers can wire up interactions later via IoC.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QButtonGroup, QFrame, QToolButton, QVBoxLayout, QWidget

if TYPE_CHECKING:  # type-only imports
    from collections.abc import Iterable, Sequence

    from PyQt6.QtGui import QIcon

from filebot.ui.icons import get_icon
from filebot.ui.styles import apply_sidebar_styles


class Sidebar(QWidget):
    """Vertical navigation sidebar with icon-text buttons.

    Parameters
    ----------
    button_labels:
        Sequence of button labels to render from top to bottom. Defaults to
        FileBot-like sections.
    parent:
        Parent widget for normal Qt ownership.
    """

    DEFAULT_LABELS: Sequence[str] = (
        "Rename",
        "Episodes",
        "Subtitles",
        "SFV",
        "Filter",
        "List",
    )

    def __init__(
        self, button_labels: Iterable[str] | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._labels: list[str] = list(button_labels or self.DEFAULT_LABELS)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Compose the sidebar layout and create buttons."""
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(16)

        # Spacer frame at the top for visual breathing room
        top_spacer = QFrame(self)
        root_layout.addWidget(top_spacer)

        # Create navigation buttons (checkable & exclusive) and tag them
        # with a property used by the stylesheet for targeted styling.
        self.setProperty("sidebarRole", "container")
        self._buttons: list[QToolButton] = []
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        for label in self._labels:
            icon_key = label.lower().replace(" ", "_")
            button = self._create_nav_button(text=label, icon=get_icon(icon_key))
            # Object names allow external stylesheets and wiring without tight coupling
            button.setObjectName(f"sidebarButton_{label.lower()}")
            button.setProperty("sidebarRole", "nav")
            button.setCheckable(True)
            root_layout.addWidget(button)
            self._buttons.append(button)
            self._button_group.addButton(button)

        root_layout.addStretch(1)
        self.setLayout(root_layout)

        # Narrow fixed width similar to FileBot
        self.setFixedWidth(96)

        # Make buttons mutually exclusive selection similar to a tab list.
        if self._buttons:
            self._buttons[0].setChecked(True)

        # Apply sidebar-specific stylesheet (scoped to this widget).
        apply_sidebar_styles(self)

    def _create_nav_button(
        self, *, text: str, icon: QIcon | None = None
    ) -> QToolButton:
        """Create a styled navigation button.

        Parameters
        ----------
        text:
            Visible text label.
        icon:
            Optional icon to display above the text. Kept for future parity.

        Returns
        -------
        QToolButton
            Configured tool button instance.
        """
        button = QToolButton(self)
        if icon is not None:
            button.setIcon(icon)
            button.setIconSize(QSize(40, 40))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setText(text)
        button.setCheckable(False)
        button.setAutoRaise(True)
        button.setMinimumWidth(80)
        button.setMinimumHeight(72)
        return button
