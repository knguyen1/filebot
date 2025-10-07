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

"""Test Sidebar widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication, QToolButton

from filebot.ui.components.sidebar import Sidebar

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_sidebar_renders_buttons(qapp: QApplication) -> None:
    labels: Sequence[str] = ("Rename", "Episodes", "Subtitles", "SFV", "Filter", "List")
    s = Sidebar(labels)
    buttons = s.findChildren(QToolButton)
    assert len(buttons) >= len(labels)
    names = {b.objectName() for b in buttons}
    for label in labels:
        assert f"sidebarButton_{label.lower()}" in names
