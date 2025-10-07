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

"""Drop-enabled file list with extension pill rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QFont,
    QPainter,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QWidget,
)

EXT_ROLE: Final[int] = Qt.ItemDataRole.UserRole + 1
PATH_ROLE: Final[int] = Qt.ItemDataRole.UserRole + 2


def _split_name_and_ext(path: Path) -> tuple[str, str]:
    """Return (stem, ext) for display. Ext defaults to 'File' without leading dot."""
    name = path.name
    if name.startswith(".") and path.suffix == "":
        # Hidden files without an explicit suffix
        return name, "File"
    stem = path.stem
    ext = path.suffix[1:] if path.suffix else "File"
    return stem if stem else name, ext if ext else "File"


class ExtensionPillDelegate(QStyledItemDelegate):
    """Render item text with a trailing muted yellow-orange pill for extension."""

    PADDING_X = 8
    PADDING_Y = 4
    PILL_H_PAD = 8
    PILL_V_PAD = 2

    def paint(self, painter: QPainter, option, index) -> None:  # type: ignore[no-untyped-def]
        """Render filename and an extension pill.

        Parameters
        ----------
        painter:
            Active painter used by Qt's delegate pipeline.
        option:
            Style options provided by the view. Kept untyped per Qt API.
        index:
            Model index for the item to render. Kept untyped per Qt API.
        """
        painter.save()

        # Selection background
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if is_selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Base text (filename without extension)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        rect = option.rect
        font: QFont = option.font
        painter.setFont(font)
        painter.setPen(
            option.palette.highlightedText().color()
            if is_selected
            else QColor("#e0e0e0")
        )

        text_rect = QRect(
            rect.left() + self.PADDING_X,
            rect.top() + self.PADDING_Y,
            rect.width() - 2 * self.PADDING_X,
            rect.height() - 2 * self.PADDING_Y,
        )

        # Compute pill size using font metrics
        ext = index.data(EXT_ROLE) or "File"
        fm = painter.fontMetrics()
        ext_width = fm.horizontalAdvance(ext) + 2 * self.PILL_H_PAD
        ext_height = fm.height() + 2 * self.PILL_V_PAD

        # Draw text, leaving space for pill on the right
        text_rect.setWidth(text_rect.width() - (ext_width + self.PADDING_X))
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine),
            text,
        )

        # Draw extension pill on the right
        pill_rect = QRect(
            rect.right() - ext_width - self.PADDING_X,
            rect.top() + (rect.height() - ext_height) // 2,
            ext_width,
            ext_height,
        )
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor("#C28F2C"))  # muted yellow-orange
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(pill_rect, 6, 6)

        # Pill text
        painter.setPen(QColor("#ffffff") if is_selected else QColor("#1e1e1e"))
        painter.drawText(
            pill_rect,
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextSingleLine),
            ext,
        )

        painter.restore()

    def sizeHint(self, option, index) -> QSize:  # noqa: N802 - Qt API; type: ignore[no-untyped-def]
        """Return height accommodating text and the extension pill.

        Parameters
        ----------
        option:
            Style options provided by the view. Kept untyped per Qt API.
        index:
            Model index for the item to measure. Kept untyped per Qt API.

        Returns
        -------
        QSize
            Suggested size for the item; width is ignored by the view.
        """
        fm = option.fontMetrics
        return QSize(0, fm.height() + 2 * self.PADDING_Y + 6)


class FileList(QListWidget):
    """List widget that accepts file drops and renders extension pills.

    Notes
    -----
    - Only adds files (skips directories); silently ignores duplicates.
    - Stores absolute path in ``PATH_ROLE`` and extension in ``EXT_ROLE``.
    - Displays filename without extension as the main text.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Enable external OS drag-and-drop
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        # Enable multi-selection (Shift/Ctrl)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setItemDelegate(ExtensionPillDelegate(self))

    # Drag & Drop events
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt API
        """Accept drags that contain URLs (files).

        Parameters
        ----------
        event:
            Qt drag-enter event carrying potential file URLs.
        """
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # noqa: N802 - Qt API
        """Continue accepting drags that contain URLs (files)."""
        mime = event.mimeData()
        if mime is not None and mime.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt API
        """Add dropped file paths to the list, skipping directories and dups.

        Parameters
        ----------
        event:
            Qt drop event containing the final set of file URLs.
        """
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            event.ignore()
            return

        added = False
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            local_path = url.toLocalFile()
            if not local_path:
                continue
            path = Path(local_path)
            if not path.is_file():
                continue
            self._add_path(path)
            added = True

        if added:
            event.acceptProposedAction()
        else:
            event.ignore()

    # Public API
    def add_paths(self, paths: list[Path]) -> None:
        """Add a list of filesystem paths to the widget.

        Parameters
        ----------
        paths:
            List of paths to add. Non-files are ignored.
        """
        for p in paths:
            if p.is_file():
                self._add_path(p)

    # Internal helpers
    def _add_path(self, path: Path) -> None:
        stem, ext = _split_name_and_ext(path)
        # Skip duplicates by absolute path
        for i in range(self.count()):
            if self.item(i).data(PATH_ROLE) == str(path):
                return
        item = QListWidgetItem(stem)
        item.setData(EXT_ROLE, ext)
        item.setData(PATH_ROLE, str(path))
        self.addItem(item)
