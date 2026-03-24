# Grid Finder: Search US cities/states and world capitals by city, state/country, or Maidenhead grid
# Requirements: pip install pandas PyQt5
# On Linux: sudo apt install python3-pyqt5 (Ubuntu/Debian) or equivalent
# CSV file: gridsearchdata.csv (columns: City, State, MGrid)

import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem,
    QStatusBar, QCompleter, QMenu, QAction, QMessageBox, QPushButton
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

class AppTheme:
    COLORS = {
        'primary': '#4CAF50',
        'primary_hover': '#66BB6A',
        'primary_pressed': '#388E3C',
        'container_bg': '#F8F7F2',
        'content_bg': '#FFFFFF',
        'border': '#666666',
        'flash_red': '#FF0000',
        'text': '#000000',
        'text_table': '#000000',
        'placeholder': '#E0E0E0',
    }

    @staticmethod
    def get_stylesheet():
        return f"""
            QLineEdit, QPushButton {{
                background-color: {AppTheme.COLORS['primary']};
                color: {AppTheme.COLORS['text']};
                font-family: DejaVu Sans, Helvetica, Arial, sans-serif;
                font-size: 11pt;
                font-weight: bold;
                border: 3px solid {AppTheme.COLORS['border']};
                border-radius: 5px;
            }}
            QLineEdit {{
                padding: 4px 8px;
            }}
            QPushButton {{
                padding: 4px 16px;
                min-width: 90px;
                text-align: center;
            }}
            QLineEdit:hover, QPushButton:hover {{
                background-color: {AppTheme.COLORS['primary_hover']};
            }}
            QLineEdit:focus {{
                border: 5px solid #1B5E20;             /* thicker + dark green border */
                background-color: #A5D6A7;             /* lighter green background */
                color: #000000;
            }}
            QPushButton:focus {{
                border: 4px solid #388E3C;
                background-color: {AppTheme.COLORS['primary']};
            }}
            QPushButton:pressed {{
                background-color: {AppTheme.COLORS['primary_pressed']};
            }}
            QLineEdit::placeholder {{
                color: {AppTheme.COLORS['placeholder']};
                font-weight: normal;
            }}
            QTableWidget {{
                font-family: DejaVu Sans, Helvetica, Arial, sans-serif;
                font-size: 11pt;
                background-color: {AppTheme.COLORS['content_bg']};
                color: {AppTheme.COLORS['text_table']};
                border: 1px solid {AppTheme.COLORS['border']};
                border-radius: 5px;
            }}
            QTableWidget::item {{
                padding: 2px;
            }}
            QHeaderView::section {{
                background-color: {AppTheme.COLORS['container_bg']};
                color: {AppTheme.COLORS['text_table']};
                border: 1px solid {AppTheme.COLORS['border']};
                padding: 4px;
            }}
        """

class GridFinderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GridFinder2 - US Cities + World Capitals v1.0")
        self.setGeometry(200, 200, 600, 450)
        self.setMinimumSize(600, 450)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(AppTheme.COLORS['container_bg']))
        self.setPalette(palette)

        self.data = self.load_data()

        # Pre-compute lowercase versions once for faster filtering
        self.data['City_lower']   = self.data['City'].str.lower().str.strip()
        self.data['State_lower']  = self.data['State'].str.lower().str.strip()
        self.data['MGrid_lower']  = self.data['MGrid'].str.lower().str.strip()

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.filter_data)
        self.debounce_delay = 400

        self.initUI()

    def load_data(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_name = "gridsearchdata.csv"
            file_path = os.path.join(script_dir, file_name)

            if not os.path.exists(file_path):
                for f in os.listdir(script_dir):
                    if f.lower() == file_name.lower():
                        file_path = os.path.join(script_dir, f)
                        break
                else:
                    raise FileNotFoundError(f"CSV file '{file_name}' not found")

            data = pd.read_csv(file_path, encoding='utf-8')
            data['MGrid'] = data['MGrid'].astype(str).str.strip().str.upper()
            data['City'] = data['City'].astype(str).str.strip()
            data['State'] = data['State'].astype(str).str.strip()

            print(f"Data loaded successfully: {len(data)} rows")
            return data

        except FileNotFoundError:
            self._show_error_dialog("Error", f"CSV file '{file_name}' not found in the same folder.")
            return pd.DataFrame()
        except Exception as e:
            self._show_error_dialog("Error", f"Error loading data: {str(e)}")
            return pd.DataFrame()

    def _show_error_dialog(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet(
            f"border: 1px solid {AppTheme.COLORS['border']}; border-radius: 4px; "
            f"background-color: {AppTheme.COLORS['container_bg']};"
        )

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        self.central_widget.setLayout(layout)

        # Top row: City input + Clear button
        city_layout = QHBoxLayout()
        city_layout.setSpacing(10)

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter City")
        self.city_input.setToolTip("Enter city name (partial match, case-insensitive)")
        self.city_input.textChanged.connect(self.on_text_changed)
        self.city_input.textChanged.connect(self.validate_inputs)

        if not self.data.empty:
            completer = QCompleter(self.data['City'].unique(), self)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            self.city_input.setCompleter(completer)

        city_layout.addWidget(self.city_input, stretch=4)

        self.clear_button = QPushButton("Clear")
        self.clear_button.setToolTip("Clear all input fields")
        self.clear_button.clicked.connect(self.clear_fields)
        self.clear_button.setFixedHeight(self.city_input.sizeHint().height())
        city_layout.addWidget(self.clear_button, stretch=0)

        layout.addLayout(city_layout)

        # Middle row: State/Country + Grid
        lower_input_layout = QHBoxLayout()
        lower_input_layout.setSpacing(10)

        self.state_input = QLineEdit()
        self.state_input.setPlaceholderText("State (US) or Country")
        self.state_input.setToolTip("US: 2-letter state code (e.g. IN) | World: country name (partial ok)")
        self.state_input.textChanged.connect(self.on_text_changed)
        self.state_input.textChanged.connect(self.validate_inputs)
        lower_input_layout.addWidget(self.state_input, stretch=2)

        self.grid_input = QLineEdit()
        self.grid_input.setPlaceholderText("Grid")
        self.grid_input.setToolTip("Enter Maidenhead grid (partial or full, up to 6 chars)")
        self.grid_input.textChanged.connect(self.on_text_changed)
        self.grid_input.textChanged.connect(self.validate_inputs)
        lower_input_layout.addWidget(self.grid_input, stretch=1)

        layout.addLayout(lower_input_layout)

        # Explicit tab order: only the three input fields, loop back
        self.setTabOrder(self.city_input, self.state_input)
        self.setTabOrder(self.state_input, self.grid_input)
        self.setTabOrder(self.grid_input, self.city_input)

        # Prevent Clear button from being tabbed to
        self.clear_button.setFocusPolicy(Qt.NoFocus)

        # Results table — prevent tab from reaching it
        self.results = QTableWidget()
        self.results.setFocusPolicy(Qt.NoFocus)
        self.results.setColumnCount(3)
        self.results.setHorizontalHeaderLabels(["City", "State / Country", "Grid"])
        self.results.setSelectionBehavior(QTableWidget.SelectRows)
        self.results.setSelectionMode(QTableWidget.SingleSelection)
        self.results.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results.setSortingEnabled(True)
        self.results.setColumnWidth(0, 220)
        self.results.setColumnWidth(1, 160)
        self.results.setColumnWidth(2, 100)
        self.results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results.customContextMenuRequested.connect(self.show_table_context_menu)
        self.results.selectionModel().currentChanged.connect(self.on_row_selected)

        layout.addWidget(self.results)

        # Status bar
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet(f"""
            QStatusBar {{
                background: #D6E4FF;
                border: 1px solid {AppTheme.COLORS['border']};
                font-family: DejaVu Sans, Helvetica, Arial, sans-serif;
                font-size: 11pt;
                font-weight: bold;
                color: {AppTheme.COLORS['text_table']};
            }}
        """)
        self.statusBar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.statusBar.customContextMenuRequested.connect(self._create_status_context_menu)
        self.setStatusBar(self.statusBar)

        if self.data.empty:
            self.show_styled_message("Error: Failed to load gridsearchdata.csv", 15000, "#CC0000")

        self.validate_inputs()

        # ── NEW: Set initial focus to City field on launch ───────────────────────────────
        self.city_input.setFocus()

    def clear_fields(self):
        self.city_input.clear()
        self.state_input.clear()
        self.grid_input.clear()
        self.city_input.setFocus()
        self.show_styled_message("Fields cleared", 4000, "#006600")

    def on_row_selected(self, current, previous):
        if not current.isValid():
            return

        row = current.row()
        if row < 0 or row >= self.results.rowCount():
            return

        city  = self.results.item(row, 0).text() if self.results.item(row, 0) else ""
        state = self.results.item(row, 1).text() if self.results.item(row, 1) else ""
        grid  = self.results.item(row, 2).text() if self.results.item(row, 2) else ""

        self.city_input.textChanged.disconnect(self.on_text_changed)
        self.state_input.textChanged.disconnect(self.on_text_changed)
        self.grid_input.textChanged.disconnect(self.on_text_changed)

        self.city_input.setText(city)
        self.state_input.setText(state)
        self.grid_input.setText(grid)

        self.city_input.textChanged.connect(self.on_text_changed)
        self.state_input.textChanged.connect(self.on_text_changed)
        self.grid_input.textChanged.connect(self.on_text_changed)

        if grid.strip():
            QApplication.clipboard().setText(grid)
            self.grid_input.selectAll()
            self.show_styled_message("Grid copied to the clipboard", 5000, "#006600")
        else:
            self.show_styled_message("No grid value in selected row", 8000, "#CC6600")

    def show_table_context_menu(self, position):
        if self.results.rowCount() == 0:
            return
        row = self.results.rowAt(position.y())
        if row == -1:
            return

        menu = QMenu()
        copy_grid_action = QAction("Copy Grid")
        copy_grid_action.triggered.connect(lambda: self.copy_selected_grid(row))
        menu.addAction(copy_grid_action)

        copy_row_action = QAction("Copy Full Row")
        copy_row_action.triggered.connect(lambda: self.copy_selected_row(row))
        menu.addAction(copy_row_action)

        menu.exec_(self.results.viewport().mapToGlobal(position))

    def copy_selected_grid(self, row):
        grid = self.results.item(row, 2).text()
        QApplication.clipboard().setText(grid)
        self.show_styled_message(f"Copied grid: {grid}", 5000, "#000000")

    def copy_selected_row(self, row):
        city = self.results.item(row, 0).text()
        state = self.results.item(row, 1).text()
        grid = self.results.item(row, 2).text()
        full = f"{city}, {state}, {grid}"
        QApplication.clipboard().setText(full)
        self.show_styled_message(f"Copied: {full}", 5000, "#000000")

    def show_styled_message(self, text, timeout, color):
        self.statusBar.setStyleSheet(f"""
            QStatusBar {{
                background: #D6E4FF;
                border: 1px solid {AppTheme.COLORS['border']};
                font-family: DejaVu Sans, Helvetica, Arial, sans-serif;
                font-size: 11pt;
                font-weight: bold;
                color: {color};
            }}
        """)
        self.statusBar.showMessage(text, timeout)

    def _create_status_context_menu(self, position):
        menu = QMenu()
        copy_action = menu.addAction("Copy Status Message")
        copy_action.triggered.connect(self._copy_status_message)
        menu.exec_(self.statusBar.mapToGlobal(position))

    def _copy_status_message(self):
        clipboard = QApplication.clipboard()
        message = self.statusBar.currentMessage()
        if message:
            clipboard.setText(message)
            self.show_styled_message("Status message copied", 8000, "#000000")
        else:
            self.show_styled_message("No status message to copy", 8000, "#CC0000")

    def on_text_changed(self, text):
        self.debounce_timer.start(self.debounce_delay)

    def validate_inputs(self):
        def set_input_style(widget, valid, tooltip=""):
            border_color = AppTheme.COLORS['border'] if valid else AppTheme.COLORS['flash_red']
            widget.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {AppTheme.COLORS['primary']};
                    color: {AppTheme.COLORS['text']};
                    font-family: DejaVu Sans, Helvetica, Arial, sans-serif;
                    font-size: 11pt;
                    font-weight: bold;
                    border: 3px solid {border_color};
                    padding: 2px 8px;
                    border-radius: 5px;
                }}
                QLineEdit:hover {{
                    background-color: {AppTheme.COLORS['primary_hover']};
                }}
                QLineEdit:focus {{
                    border: 5px solid #1B5E20;
                    background-color: #A5D6A7;
                    color: #000000;
                }}
                QLineEdit::placeholder {{
                    color: {AppTheme.COLORS['placeholder']};
                    font-weight: normal;
                }}
            """)
            if tooltip:
                widget.setToolTip(tooltip)

        set_input_style(self.city_input, True)
        set_input_style(self.state_input, True)

        grid_text = self.grid_input.text().strip()
        set_input_style(self.grid_input, len(grid_text) <= 6)

    def filter_data(self):
        self.show_styled_message("Filtering...", 2000, "#000000")

        city_query  = self.city_input.text().strip().lower()
        state_query = self.state_input.text().strip().lower()
        grid_query  = self.grid_input.text().strip().lower()

        if not any([city_query, state_query, grid_query]):
            self.display_results(pd.DataFrame())
            return

        filtered = self.data

        if city_query:
            filtered = filtered[filtered['City_lower'].str.contains(city_query, na=False)]
        if state_query:
            filtered = filtered[filtered['State_lower'].str.contains(state_query, na=False)]
        if grid_query:
            filtered = filtered[filtered['MGrid_lower'].str.contains(grid_query, na=False)]

        self.display_results(filtered)

    def display_results(self, filtered):
        self.results.clearContents()
        self.results.setRowCount(0)

        if filtered.empty:
            self.results.setRowCount(1)
            self.results.setItem(0, 0, QTableWidgetItem("No matches found"))
            self.show_styled_message("No results found", 8000, "#CC0000")
            return

        self.results.setRowCount(len(filtered))
        for i, (_, row) in enumerate(filtered.iterrows()):
            self.results.setItem(i, 0, QTableWidgetItem(row['City']))
            self.results.setItem(i, 1, QTableWidgetItem(row['State']))
            self.results.setItem(i, 2, QTableWidgetItem(row['MGrid']))

        self.results.resizeColumnsToContents()

        # Ensure no row is selected after filtering
        self.results.clearSelection()
        self.results.setCurrentCell(-1, -1)

        self.show_styled_message(
            f"Found {len(filtered)} results. Click row to fill fields & copy grid.",
            6000, "#000000"
        )

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setFont(QFont("DejaVu Sans, Helvetica, Arial, sans-serif", 11))
    app.setStyle('Fusion')

    window = GridFinderApp()
    window.show()

    sys.exit(app.exec_())