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

"""Test RenamePanel widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QGroupBox, QListWidget

from filebot.ui.views.rename_panel import RenamePanel


def test_rename_panel_layout_and_groups(qapp: QApplication) -> None:
    panel = RenamePanel()
    groups = panel.findChildren(QGroupBox)
    titles = {g.title() for g in groups}
    assert {"Original Files", "New Names"}.issubset(titles)

    # Left group uses custom FileList; right is a plain QListWidget
    left = next(g for g in groups if g.title() == "Original Files")
    right = next(g for g in groups if g.title() == "New Names")
    left_list = left.findChild(QListWidget)
    right_list = right.findChild(QListWidget)
    assert left_list is not None
    assert right_list is not None
