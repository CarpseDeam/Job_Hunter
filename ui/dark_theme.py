# ui/dark_theme.py
"""
To provide a QSS stylesheet for a professional dark theme, ensuring a
consistent and modern look and feel.

This module contains the Qt Style Sheet (QSS) string for the application's
dark theme and a function to apply it to the QApplication instance.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# A professional dark theme inspired by modern IDEs.
# Colors:
#   - Background: #2B2B2B
#   - Lighter Background / Controls: #3C3F41
#   - Borders: #555555
#   - Text: #BBBBBB
#   - Highlight/Accent: #007ACC (a vibrant blue)
#   - Highlight Text: #FFFFFF
#   - Disabled: #777777
DARK_THEME_QSS = """
QWidget {
    background-color: #2B2B2B;
    color: #BBBBBB;
    font-family: "Segoe UI", "Cantarell", "Helvetica Neue", sans-serif;
    font-size: 10pt;
}

QMainWindow {
    background-color: #2B2B2B;
}

QMenuBar {
    background-color: #3C3F41;
    color: #BBBBBB;
}

QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}

QMenuBar::item:selected {
    background-color: #007ACC;
    color: #FFFFFF;
}

QMenu {
    background-color: #3C3F41;
    border: 1px solid #555555;
}

QMenu::item:selected {
    background-color: #007ACC;
    color: #FFFFFF;
}

QToolTip {
    background-color: #3C3F41;
    color: #BBBBBB;
    border: 1px solid #555555;
    padding: 4px;
}

QLabel {
    color: #BBBBBB;
}

QPushButton {
    background-color: #3C3F41;
    color: #BBBBBB;
    border: 1px solid #555555;
    padding: 5px 10px;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #4A4D4F;
    border: 1px solid #666666;
}

QPushButton:pressed {
    background-color: #007ACC;
    color: #FFFFFF;
    border: 1px solid #007ACC;
}

QPushButton:disabled {
    background-color: #353535;
    color: #777777;
    border-color: #444444;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #3C3F41;
    color: #BBBBBB;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 4px;
    selection-background-color: #007ACC;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #007ACC;
}

QTableView {
    background-color: #3C3F41;
    border: 1px solid #555555;
    gridline-color: #555555;
    selection-background-color: #007ACC;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #4A4D4F;
    color: #BBBBBB;
    padding: 4px;
    border: 1px solid #555555;
    font-weight: bold;
}

QHeaderView::section:checked {
    background-color: #007ACC;
    color: #FFFFFF;
}

QProgressBar {
    border: 1px solid #555555;
    border-radius: 4px;
    text-align: center;
    color: #BBBBBB;
}

QProgressBar::chunk {
    background-color: #007ACC;
    border-radius: 3px;
    margin: 0.5px;
}

QScrollBar:vertical {
    background: #2B2B2B;
    width: 12px;
    margin: 0px 0px 0px 0px;
    border: 1px solid #555555;
}

QScrollBar::handle:vertical {
    background: #4A4D4F;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: #2B2B2B;
    height: 12px;
    margin: 0px 0px 0px 0px;
    border: 1px solid #555555;
}

QScrollBar::handle:horizontal {
    background: #4A4D4F;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QStatusBar {
    background-color: #3C3F41;
    color: #BBBBBB;
}

QGroupBox {
    border: 1px solid #555555;
    border-radius: 4px;
    margin-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
}

QSplitter::handle {
    background-color: #4A4D4F;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:hover {
    background-color: #007ACC;
}
"""


def apply_dark_theme(app: "QApplication") -> None:
    """
    Applies the dark theme stylesheet to the given QApplication instance.

    This function sets the global style for the entire application, ensuring
    all widgets conform to the defined dark theme.

    Args:
        app (QApplication): The main application instance to which the theme
                            will be applied.
    """
    logger.info("Applying dark theme QSS to the application.")
    try:
        app.setStyleSheet(DARK_THEME_QSS)
    except Exception as e:
        logger.error(f"Failed to apply stylesheet: {e}", exc_info=True)