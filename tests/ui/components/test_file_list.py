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

"""Test FileList widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PyQt6.QtCore import QItemSelectionModel, QMimeData, QPointF, Qt, QUrl
from PyQt6.QtGui import QDropEvent

from filebot.ui.components.file_list import EXT_ROLE, PATH_ROLE, FileList

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from PyQt6.QtWidgets import QApplication as QApplicationType


def _urls_for(paths: Iterable[Path]) -> list[QUrl]:
    return [QUrl.fromLocalFile(str(p)) for p in paths]


def test_add_paths_sets_display_and_roles(
    qapp: QApplicationType, tmp_files: list[Path]
) -> None:
    w = FileList()
    w.add_paths(tmp_files)
    assert w.count() == len(tmp_files)
    for i in range(w.count()):
        item = w.item(i)
        assert item is not None
        assert isinstance(item.data(PATH_ROLE), str)
        assert item.text()  # stem shown
        ext = item.data(EXT_ROLE)
        assert isinstance(ext, str)
        assert "." not in ext


@pytest.mark.parametrize(
    ("name", "expected_ext"),
    [
        ("movie.mp4", "mp4"),
        ("archive.tar.gz", "gz"),
        (".env", "File"),
        ("README", "File"),
    ],
)
def test_extension_pill_values(
    qapp: QApplicationType, tmp_path: Path, name: str, expected_ext: str
) -> None:
    w = FileList()
    p = tmp_path / name
    p.write_text("x")
    w.add_paths([p])
    item = w.item(0)
    assert item is not None
    assert item.data(EXT_ROLE) == expected_ext


def test_drag_drop_adds_only_files(qapp: QApplicationType, tmp_path: Path) -> None:
    w = FileList()
    files = [tmp_path / "a.mp3", tmp_path / "b"]
    (tmp_path / "dir").mkdir()
    for f in files:
        f.write_text("x")

    mime = QMimeData()
    mime.setUrls(_urls_for([files[0], tmp_path / "dir"]))

    # Simulate drop
    ev = QDropEvent(
        QPointF(w.rect().center()),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    w.dropEvent(ev)
    assert w.count() == 1


def test_multi_selection_with_shift_ctrl(
    qapp: QApplicationType, tmp_files: list[Path]
) -> None:
    w = FileList()
    w.add_paths(tmp_files)

    # Select first and third using selection flags
    w.setCurrentRow(0, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    w.setCurrentRow(2, QItemSelectionModel.SelectionFlag.Toggle)
    sel_rows = sorted([idx.row() for idx in w.selectedIndexes()])
    assert sel_rows == [0, 2]
