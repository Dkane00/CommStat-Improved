# Copyright (c) 2025, 2026 Manuel Ochoa
# This file is part of CommStat.
# Licensed under the GNU General Public License v3.0.
"""
ui_helpers.py - Shared UI helpers for CommStat dialogs.

Centralizes the styled QPushButton, QLineEdit, and centered-checkbox-cell
factories that were previously copy-pasted across every dialog module.
The canonical implementation comes from qrz_settings.py.
"""

from typing import Tuple

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QPushButton, QLineEdit, QCheckBox, QWidget, QHBoxLayout,
)

from constants import FONT_ROBOTO, FONT_MONO


# ── Button ─────────────────────────────────────────────────────────────────────

def make_button(label: str, color: str, min_w: int = 90) -> QPushButton:
    """Standard styled action button: Roboto Bold 15px, colored background."""
    b = QPushButton(label)
    b.setMinimumWidth(min_w)
    b.setStyleSheet(
        f"QPushButton {{ background-color:{color}; color:#ffffff; border:none;"
        f" padding:6px 14px; border-radius:4px; font-family:{FONT_ROBOTO}; font-size:15px;"
        f" font-weight:bold; }}"
        f"QPushButton:hover {{ background-color:{color}; opacity:0.9; }}"
        f"QPushButton:pressed {{ background-color:{color}; }}"
        f"QPushButton:disabled {{ background-color:#cccccc; color:#888888; }}"
    )
    return b


# ── Input ──────────────────────────────────────────────────────────────────────

def make_input(placeholder: str = "", default: str = "", max_len: int = 0) -> QLineEdit:
    """Standard styled QLineEdit: white background, Kode Mono 13px."""
    e = QLineEdit()
    if placeholder:
        e.setPlaceholderText(placeholder)
    if default:
        e.setText(default)
    if max_len:
        e.setMaxLength(max_len)
    e.setMinimumHeight(30)
    e.setStyleSheet(
        "QLineEdit { background-color:white; color:#333333; border:1px solid #cccccc;"
        f" border-radius:4px; padding:2px 6px; font-family:'{FONT_MONO}'; font-size:13px; }}"
        "QLineEdit:focus { border:1px solid #007bff; }"
    )
    return e


# ── Checkbox cell ──────────────────────────────────────────────────────────────

def make_checkbox_cell(checked: bool = False) -> Tuple[QWidget, QCheckBox]:
    """Return (container_widget, checkbox) with the checkbox centered in the cell."""
    container = QWidget()
    container.setStyleSheet("background-color: transparent;")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setAlignment(Qt.AlignCenter)
    cb = QCheckBox()
    cb.setChecked(checked)
    cb.setStyleSheet(
        "QCheckBox { background-color: transparent; }"
        "QCheckBox::indicator { width:16px; height:16px; }"
    )
    layout.addWidget(cb)
    return container, cb


# ── Fonts ──────────────────────────────────────────────────────────────────────

def label_font() -> QtGui.QFont:
    """Roboto Bold — for QLabel headings within dialogs."""
    return QtGui.QFont(FONT_ROBOTO, -1, QtGui.QFont.Bold)


def mono_font() -> QtGui.QFont:
    """Kode Mono — for table cells and data display."""
    return QtGui.QFont(FONT_MONO)
