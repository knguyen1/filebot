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

"""Configuration for UI tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

import pytest
from PyQt6.QtWidgets import QApplication

if TYPE_CHECKING:  # type-only imports
    from pathlib import Path


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a QApplication for UI tests.

    Ensures a single app instance for the test session. Uses offscreen mode if
    not already configured.
    """

    if os.environ.get("QT_QPA_PLATFORM") is None:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    # Ensure static type is QApplication, not QCoreApplication | QApplication
    return cast("QApplication", app)


@pytest.fixture
def tmp_files(tmp_path: Path) -> list[Path]:
    """Create a small set of files for drag/drop-style tests."""

    names = [
        "movie.mp4",
        "show.s01e01.mkv",
        "archive.tar.gz",
        ".env",
        "README",
    ]
    files: list[Path] = []
    for name in names:
        p = tmp_path / name
        p.write_text("x")
        files.append(p)
    return files
