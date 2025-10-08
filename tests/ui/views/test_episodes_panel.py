# Copyright (c) 2025 knguyen1

from __future__ import annotations

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTabWidget,
)

from filebot.ui.views.episodes_panel import EpisodesPanel


def test_episodes_panel_structure(qapp: QApplication) -> None:
    panel = EpisodesPanel()

    # Title label
    title = panel.findChild(QLabel, "episodes_title")
    assert title is not None
    assert title.text() == "Episodes"

    # Search bar widgets
    provider = panel.findChild(QComboBox, "episodes_provider_combo")
    search = panel.findChild(QLineEdit, "episodes_search_input")
    season = panel.findChild(QSpinBox, "episodes_season_spin")
    order = panel.findChild(QComboBox, "episodes_order_combo")
    language = panel.findChild(QComboBox, "episodes_language_combo")
    find_btn = panel.findChild(QPushButton, "episodes_find_button")

    assert provider is not None
    assert provider.count() >= 1
    assert search is not None
    assert season is not None
    assert season.minimum() == 0
    assert order is not None
    assert order.count() >= 3
    assert language is not None
    assert language.count() >= 1
    assert find_btn is not None
    assert find_btn.text() == "Find"

    # Results tabs and History table
    tabs = panel.findChild(QTabWidget, "episodes_results_tabs")
    assert tabs is not None
    assert tabs.count() >= 1
    assert tabs.tabText(0) == "History"

    table = panel.findChild(QTableWidget, "episodes_history_table")
    assert table is not None
    assert table.columnCount() == 3
    assert [table.horizontalHeaderItem(i).text() for i in range(3)] == [
        "TV Series",
        "Number of Episodes",
        "Duration",
    ]

    # Public helpers
    panel.add_history_entry("Neon Genesis Evangelion", 32, 1819)
    assert table.rowCount() == 1
    assert table.item(0, 0).text() == "Neon Genesis Evangelion"
    assert table.item(0, 1).text() == "32"
    assert table.item(0, 2).text().endswith(" ms")

    idx = panel.add_search_results_tab("Cowboy Bebop (2021)")
    assert idx >= 1
    assert tabs.tabText(idx) == "Cowboy Bebop (2021)"
