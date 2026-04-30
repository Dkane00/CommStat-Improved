# Copyright (c) 2025, 2026 Manuel Ochoa
# This file is part of CommStat.
# Licensed under the GNU General Public License v3.0.
"""help.py - Help dialog for CommStat"""

import os
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from constants import DEFAULT_COLORS, ICON_FILE


_PROG_BG  = DEFAULT_COLORS.get("program_background", "#000000")
_PROG_FG  = DEFAULT_COLORS.get("program_foreground", "#FFFFFF")
_PANEL_BG = DEFAULT_COLORS.get("module_background",  "#FFFFFF")


class HelpDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setFixedSize(300, 200)
        self.setWindowFlags(
            Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint
        )
        if os.path.exists(ICON_FILE):
            self.setWindowIcon(QtGui.QIcon(ICON_FILE))
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.setStyleSheet(f"background-color: {_PANEL_BG};")

        title = QtWidgets.QLabel("HELP")
        title.setStyleSheet(
            f"font-family: 'Roboto Slab'; font-size: 16px; font-weight: 900;"
            f"background-color: {_PROG_BG}; color: {_PROG_FG}; padding: 9px 0px;"
        )
        title.setAlignment(Qt.AlignLeft)
        layout.addWidget(title)

        rows = [
            ("Apr-28 02:40", False),
            ("W5TTA",        True),
            ("@MAGNET",      False),
            ("My Location",  False),
        ]
        for text, bold in rows:
            lbl = QtWidgets.QLabel(text)
            weight = "bold" if bold else "normal"
            lbl.setStyleSheet(
                f"font-family: Roboto; font-size: 13px; font-weight: {weight};"
                f"color: #333333; background: transparent;"
            )
            lbl.setAlignment(Qt.AlignLeft)
            layout.addWidget(lbl)

        layout.addStretch()