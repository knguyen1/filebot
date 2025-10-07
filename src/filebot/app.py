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

"""Application entrypoint for the FileBot UI scaffold."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from filebot.ui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Launch the Qt application.

    Parameters
    ----------
    argv:
        Command-line arguments. If ``None``, ``sys.argv`` is used.

    Returns
    -------
    int
        Process exit code.
    """
    args = argv if argv is not None else sys.argv
    app = QApplication(args)
    window = MainWindow()
    window.resize(1200, 750)
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual launch convenience
    raise SystemExit(main())
