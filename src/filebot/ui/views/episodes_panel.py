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

"""Episodes panel view.

This widget renders a header title, a centered search bar with provider
dropdown, query input, season selector, sort-order dropdown, language dropdown,
and a Find button, followed by a large content area that will later show a
history table. Only UI composition is implemented here to adhere to SOC.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:  # type-only imports
    from filebot.core.providers.base import EpisodeListProvider

from filebot.core.registry import provider_registry
from filebot.ui.flag_icons import get_flag_icon
from filebot.ui.icons import get_icon
from filebot.ui.languages import get_language_options


class SortOrder(StrEnum):
    """Episode sort/display orders as user-visible strings.

    Values follow the labels used in FileBot.
    """

    AIRDATE = "Airdate"
    DVD = "DVD"
    ABSOLUTE = "Absolute"
    DIGITAL = "Digital"
    STORY_ARC = "Story Arc"
    PRODUCTION = "Production"
    OFFICIAL = "Official"
    DATE_AND_TITLE = "Date and Title"


class EpisodesPanel(QWidget):
    """Episodes search panel.

    Notes
    -----
    Public widget intended for composition in the main window. No network
    behavior is wired yet; the UI is ready for future controllers.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Title
        title = QLabel("Episodes", self)
        title.setObjectName("episodes_title")
        title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        title.setMargin(4)
        root.addWidget(title)

        # Search bar wrapper to center the controls
        search_row = self._create_search_bar()
        root.addLayout(search_row)

        # Content area: tabbed search results with History as the first tab
        results_group = QGroupBox("Search Results", self)
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(8, 16, 8, 8)
        results_layout.setSpacing(8)

        tabs = QTabWidget(results_group)
        tabs.setObjectName("episodes_results_tabs")

        # History tab with goggles/binoculars icon and 3 columns
        history_table = QTableWidget(0, 3, tabs)
        history_table.setObjectName("episodes_history_table")
        history_table.setHorizontalHeaderLabels([
            "TV Series",
            "Number of Episodes",
            "Duration",
        ])
        header = history_table.horizontalHeader()
        if header is not None:
            # Set column resize modes and initial proportions
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(2, 250)
        tabs.addTab(history_table, get_icon("find"), "History")

        results_layout.addWidget(tabs, 1)
        results_group.setLayout(results_layout)
        root.addWidget(results_group, 1)

        # Hold references for later updates
        self._results_tabs = tabs
        self._history_table = history_table

        self.setLayout(root)

    def _create_search_bar(self) -> QHBoxLayout:
        """Create the centered search bar as shown in FileBot screenshots.

        Returns
        -------
        QHBoxLayout
            A horizontally centered layout containing all search widgets.
        """
        outer = QHBoxLayout()
        outer.addStretch(1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        # (1) Provider dropdown with small tv icon prefix
        provider_combo = QComboBox(self)
        provider_combo.setObjectName("episodes_provider_combo")
        for p in self._episode_providers():
            provider_combo.addItem(str(p.name), userData=p.identifier)
        grid.addWidget(provider_combo, 0, 0)

        # (2) Search input
        search_input = QLineEdit(self)
        search_input.setObjectName("episodes_search_input")
        search_input.setPlaceholderText("Search shows…")
        grid.addWidget(search_input, 0, 1, 1, 2)

        # (3) Season integer input (with label prefix)
        season_spin = QSpinBox(self)
        season_spin.setObjectName("episodes_season_spin")
        season_spin.setMinimum(0)  # 0 means All Seasons consistent with FileBot
        season_spin.setMaximum(1000)
        season_spin.setSpecialValueText("All Seasons")
        season_spin.setPrefix("Season ")
        grid.addWidget(season_spin, 0, 3)

        # (4) Sort order dropdown
        order_combo = QComboBox(self)
        order_combo.setObjectName("episodes_order_combo")
        for order in SortOrder:
            order_combo.addItem(order.value, userData=order.name)
        grid.addWidget(order_combo, 0, 4)

        # (5) Language dropdown with flag prefix
        language_combo = QComboBox(self)
        language_combo.setObjectName("episodes_language_combo")
        for opt in get_language_options():
            language_combo.addItem(opt.label, userData=opt.code)
            idx = language_combo.count() - 1
            icon = get_flag_icon(opt.code)
            if icon is not None:
                language_combo.setItemIcon(idx, icon)
        # Default to English (🇬🇧)
        default_index = next(
            (
                i
                for i in range(language_combo.count())
                if language_combo.itemData(i) == "en"
            ),
            0,
        )
        language_combo.setCurrentIndex(default_index)
        grid.addWidget(language_combo, 0, 5)

        # (6) Find button with binoculars icon
        find_btn = QPushButton("Find", self)
        find_btn.setObjectName("episodes_find_button")
        find_btn.setIcon(get_icon("find"))
        grid.addWidget(find_btn, 0, 6)

        outer.addLayout(grid)
        outer.addStretch(1)
        return outer

    def _episode_providers(self) -> list[EpisodeListProvider]:
        """Return available episode providers from the registry.

        Returns
        -------
        list[EpisodeListProvider]
            List of providers for the provider dropdown.
        """
        return provider_registry.get_episode_list_providers()

    # --- Public helpers for controllers -------------------------------------------------
    def add_history_entry(
        self, series: str, num_episodes: int, duration_ms: int
    ) -> None:
        """Append a row to the History table.

        Parameters
        ----------
        series:
            Series title.
        num_episodes:
            Number of episodes returned by the search.
        duration_ms:
            Search duration in milliseconds.
        """
        table = self._history_table
        row = table.rowCount()
        table.insertRow(row)

        table.setItem(row, 0, QTableWidgetItem(series))

        episodes_item = QTableWidgetItem(str(num_episodes))
        episodes_item.setTextAlignment(
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        )
        table.setItem(row, 1, episodes_item)

        duration_str = f"{duration_ms:,} ms"
        duration_item = QTableWidgetItem(duration_str)
        duration_item.setTextAlignment(
            int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        )
        table.setItem(row, 2, duration_item)

    def add_search_results_tab(self, label: str) -> int:
        """Create an empty results tab for a search and return its index.

        Parameters
        ----------
        label:
            Title of the tab, typically the series name.

        Returns
        -------
        int
            Index of the newly created tab.
        """
        table = QTableWidget(0, 4, self._results_tabs)
        table.setObjectName(f"episodes_results_table_{label}")
        table.setHorizontalHeaderLabels(["Episode", "Airdate", "Number", "Duration"])
        header = table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        return self._results_tabs.addTab(table, get_icon("episodes"), label)
