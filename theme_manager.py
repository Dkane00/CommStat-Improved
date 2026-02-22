"""
Centralized theme manager for CommStat v3.

Provides system-theme-aware structural colors derived from the active
QPalette, while leaving all semantic/functional colors untouched.

Usage:
    from theme_manager import theme
    bg = theme.color('window')
    qss = theme.menu_style()
"""

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor


class ThemeManager:
    """Provides structural UI colors from the system QPalette.

    Structural colors (backgrounds, text, menus, inputs, table chrome)
    follow the OS/desktop theme.  Semantic colors (status indicators,
    alert severity, button accents, newsfeed, etc.) are NOT managed here
    — they stay hardcoded in the modules that own them.
    """

    # Default font settings — used as fallback everywhere
    font_family: str = "Arial"
    font_size: int = 12

    # -----------------------------------------------------------------
    # Palette helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _palette() -> QPalette:
        """Return the application palette (must be called after QApplication exists)."""
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("ThemeManager requires a QApplication instance")
        return app.palette()

    @staticmethod
    def _hex(color: QColor) -> str:
        """Convert a QColor to a hex string like '#rrggbb'."""
        return color.name()

    # -----------------------------------------------------------------
    # Individual palette color accessors
    # -----------------------------------------------------------------

    def color(self, role: str) -> str:
        """Return a hex color string for a named QPalette role.

        Supported role names (case-insensitive):
            window, windowtext, base, alternatebase, text,
            button, buttontext, highlight, highlightedtext,
            tooltipbase, tooltiptext, mid, dark, light,
            brighttext, link, linkvisited, shadow,
            midlight, placeholdertext
        """
        palette = self._palette()
        role_map = {
            'window':           QPalette.Window,
            'windowtext':       QPalette.WindowText,
            'base':             QPalette.Base,
            'alternatebase':    QPalette.AlternateBase,
            'text':             QPalette.Text,
            'button':           QPalette.Button,
            'buttontext':       QPalette.ButtonText,
            'highlight':        QPalette.Highlight,
            'highlightedtext':  QPalette.HighlightedText,
            'tooltipbase':      QPalette.ToolTipBase,
            'tooltiptext':      QPalette.ToolTipText,
            'mid':              QPalette.Mid,
            'dark':             QPalette.Dark,
            'light':            QPalette.Light,
            'brighttext':       QPalette.BrightText,
            'link':             QPalette.Link,
            'linkvisited':      QPalette.LinkVisited,
            'shadow':           QPalette.Shadow,
            'midlight':         QPalette.Midlight,
        }
        # PlaceholderText was added in Qt 5.12
        if hasattr(QPalette, 'PlaceholderText'):
            role_map['placeholdertext'] = QPalette.PlaceholderText

        qt_role = role_map.get(role.lower())
        if qt_role is None:
            raise ValueError(f"Unknown palette role: {role!r}")
        return self._hex(palette.color(qt_role))

    # -----------------------------------------------------------------
    # Structural color dict (replaces DEFAULT_COLORS structural keys)
    # -----------------------------------------------------------------

    def structural_colors(self) -> dict:
        """Return a dict of structural color keys mapped to palette values.

        These replace the hardcoded structural entries that were in
        DEFAULT_COLORS.  Semantic keys (newsfeed_*, condition_*) are NOT
        included — they stay as-is in DEFAULT_COLORS.
        """
        return {
            'program_background':    self.color('window'),
            'program_foreground':    self.color('windowtext'),
            'menu_background':       self.color('window'),
            'menu_foreground':       self.color('windowtext'),
            'title_bar_background':  self.color('highlight'),
            'title_bar_foreground':  self.color('highlightedtext'),
            'data_background':       self.color('base'),
            'data_foreground':       self.color('text'),
            'feed_background':       self.color('base'),
            'feed_foreground':       self.color('text'),
            'time_background':       self.color('window'),
            'time_foreground':       self.color('windowtext'),
        }

    # -----------------------------------------------------------------
    # QSS snippet generators
    # -----------------------------------------------------------------

    def menu_style(self) -> str:
        """Return QSS for QMenuBar and QMenu using palette colors."""
        bg = self.color('window')
        fg = self.color('windowtext')
        hl = self.color('highlight')
        hl_text = self.color('highlightedtext')
        mid = self.color('mid')
        return f"""
            QMenuBar {{
                background-color: {bg};
                color: {fg};
            }}
            QMenuBar::item {{
                padding: 4px 8px;
                background-color: transparent;
                color: {fg};
            }}
            QMenuBar::item:selected {{
                background-color: {hl};
                color: {hl_text};
            }}
            QMenu {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {mid};
            }}
            QMenu::item {{
                padding: 4px 20px 4px 20px;
                background-color: transparent;
                color: {fg};
            }}
            QMenu::item:selected {{
                background-color: {hl};
                color: {hl_text};
            }}
        """

    def table_style(self) -> str:
        """Return QSS for QTableWidget structural chrome using palette colors."""
        base = self.color('base')
        text = self.color('text')
        hl = self.color('highlight')
        hl_text = self.color('highlightedtext')
        return f"""
            QTableWidget {{
                background-color: {base};
                color: {text};
            }}
            QTableWidget QHeaderView::section {{
                background-color: {hl};
                color: {hl_text};
                font-weight: bold;
                padding: 4px;
                border: 1px solid {hl};
            }}
        """

    def header_style(self) -> str:
        """Return QSS for QHeaderView::section using palette colors."""
        hl = self.color('highlight')
        hl_text = self.color('highlightedtext')
        return f"""
            QHeaderView::section {{
                background-color: {hl};
                color: {hl_text};
                font-weight: bold;
                font-size: 10pt;
                padding: 4px;
            }}
        """

    def combo_style(self) -> str:
        """Return QSS for QComboBox structural chrome using palette colors."""
        bg = self.color('window')
        fg = self.color('windowtext')
        border = self.color('mid')
        return f"""
            QComboBox {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                padding: 2px 5px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """

    def combo_list_style(self) -> str:
        """Return QSS for the QListView popup inside a QComboBox."""
        bg = self.color('window')
        fg = self.color('windowtext')
        hl = self.color('highlight')
        hl_text = self.color('highlightedtext')
        return f"""
            QListView {{
                background-color: {bg};
                color: {fg};
                outline: none;
            }}
            QListView::item {{
                background-color: {bg};
                color: {fg};
                padding: 4px;
            }}
            QListView::item:selected {{
                background-color: {hl};
                color: {hl_text};
            }}
        """

    def header_button_style(self) -> str:
        """Return QSS for header-area buttons (e.g. 'Last 20') using palette."""
        bg = self.color('window')
        fg = self.color('windowtext')
        hl = self.color('highlight')
        hl_text = self.color('highlightedtext')
        border = self.color('mid')
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                padding: 2px 5px;
            }}
            QPushButton:hover {{
                background-color: {hl};
                color: {hl_text};
            }}
        """

    def input_readonly_style(self) -> str:
        """Return QSS for read-only input fields using palette colors."""
        bg = self.color('base')
        return f"background-color: {bg};"

    def dialog_title_style(self) -> str:
        """Return QSS for dialog title labels."""
        fg = self.color('windowtext')
        return f"color: {fg}; margin-bottom: 10px;"

    def dialog_title_style_compact(self) -> str:
        """Return QSS for dialog title labels (less margin)."""
        fg = self.color('windowtext')
        return f"color: {fg}; margin-bottom: 5px;"

    @staticmethod
    def button_style(accent_color: str) -> str:
        """Return QSS for an accent-colored button.

        The accent_color is a semantic color passed through unchanged
        (e.g. '#007bff' for primary, '#dc3545' for danger).
        """
        return f"""
            QPushButton {{
                background-color: {accent_color};
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                opacity: 0.8;
            }}
        """


# Module-level singleton — import as `from theme_manager import theme`
theme = ThemeManager()
