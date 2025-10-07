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

"""Rename panel view.

This module contains the `RenamePanel` widget rendering the central two-pane
layout with a middle control column to visually match FileBot's Rename screen.
Only UI elements are scaffolded; no behaviors are connected.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from filebot.ui.components.file_list import FileList
from filebot.ui.icons import get_icon


class RenamePanel(QWidget):
    """Two-column list view with central action buttons.

    Parameters
    ----------
    parent:
        Parent widget for normal Qt ownership.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Compose the two-pane layout and controls."""
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(16, 8, 16, 8)
        root_layout.setSpacing(16)

        left_box = self._create_list_group(title="Original Files")
        right_box = self._create_list_group(title="New Names")

        center_controls = self._create_center_controls()

        root_layout.addWidget(left_box, 1)
        root_layout.addLayout(center_controls)
        root_layout.addWidget(right_box, 1)

        self.setLayout(root_layout)

    def _create_list_group(self, *, title: str) -> QGroupBox:
        """Create a group box containing a list and a bottom toolbar.

        Parameters
        ----------
        title:
            Title displayed at the top of the group.

        Returns
        -------
        QGroupBox
            Configured group box with internal layout placeholders.
        """
        group = QGroupBox(title, self)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(8, 24, 8, 8)
        vbox.setSpacing(8)

        # Left panel should accept file drops, right panel stays a plain list for now.
        if title == "Original Files":
            list_widget = FileList(group)
            list_widget.setAcceptDrops(True)
        else:
            from PyQt6.QtWidgets import QListWidget

            list_widget = QListWidget(group)
        list_widget.setObjectName(f"list_{title.lower().replace(' ', '_')}")
        vbox.addWidget(list_widget, 1)

        toolbar = self._create_bottom_toolbar()
        vbox.addLayout(toolbar)

        group.setLayout(vbox)
        return group

    def _create_center_controls(self) -> QVBoxLayout:
        """Create the central vertical controls with Match and Rename buttons."""
        center = QVBoxLayout()
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(16)

        center.addStretch(1)

        match_btn = QPushButton("Match", self)
        match_btn.setObjectName("btn_match")
        match_btn.setIcon(get_icon("match"))
        match_btn.setMinimumWidth(96)
        center.addWidget(match_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        rename_btn = QPushButton("Rename", self)
        rename_btn.setObjectName("btn_rename")
        rename_btn.setIcon(get_icon("rename_action"))
        rename_btn.setMinimumWidth(96)
        center.addWidget(rename_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        center.addStretch(1)
        return center

    def _create_bottom_toolbar(self) -> QHBoxLayout:
        """Create a row of tool buttons for list actions.

        The specific icons are placeholders; only buttons are required now.
        """
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)

        # Left-side trio
        toolbar.addWidget(self._tool_button("Down", icon_key="move_down"))
        toolbar.addWidget(self._tool_button("Up", icon_key="move_up"))
        toolbar.addWidget(self._tool_button("Swap", icon_key="swap"))

        toolbar.addStretch(1)

        # Right-side trio
        toolbar.addWidget(self._tool_button("Fetch Data", icon_key="fetch"))
        toolbar.addWidget(self._tool_button("Copy", icon_key="copy"))
        toolbar.addWidget(self._tool_button("Tools", icon_key="tools"))

        return toolbar

    def _tool_button(self, text: str, *, icon_key: str | None = None) -> QToolButton:
        """Create a small tool button used in list toolbars."""
        btn = QToolButton(self)
        btn.setText(text)
        if icon_key:
            btn.setIcon(get_icon(icon_key))
        btn.setObjectName(f"tool_{text.lower().replace(' ', '_')}")
        btn.setAutoRaise(True)
        return btn
