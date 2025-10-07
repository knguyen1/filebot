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

"""Centralized Qt stylesheets.

This module provides reusable stylesheet helpers to adhere to DRY/SRP and keep
style concerns separate from widget composition.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # type-only import
    from PyQt6.QtWidgets import QWidget


def sidebar_stylesheet() -> str:
    """Return stylesheet for sidebar navigation buttons.

    Notes
    -----
    Applies to buttons with dynamic property ``sidebarRole="nav"`` only, to
    avoid impacting other tool buttons in the app. The checked state uses a
    vertical gradient from ``#5096C3`` to ``#396A8C`` as requested.
    """
    return """
        QToolButton[sidebarRole="nav"] {
            padding: 6px 4px;
            border: 1px solid transparent; /* reserve space to avoid layout jump */
            border-radius: 6px;
        }
        QToolButton[sidebarRole="nav"]:hover {
            background: rgba(255, 255, 255, 0.06);
        }
        QToolButton[sidebarRole="nav"]:checked {
            color: #ffffff;
            border: 1px solid #000000; /* selected item border */
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 #5096C3, stop:1 #396A8C
            );
        }
        """


def apply_sidebar_styles(root: QWidget) -> None:
    """Apply sidebar stylesheet to the given container widget.

    Parameters
    ----------
    root:
        Sidebar container widget. The stylesheet is set on this root so it
        affects only descendants.
    """
    root.setStyleSheet(sidebar_stylesheet())
