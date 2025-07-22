# ui/main_window.py
"""
To define the main GUI window, its layout, widgets, and signal/slot connections
for user interaction.
"""

import logging
import os
from typing import Any, Dict, Optional

from PySide6.QtCore import (
    QItemSelection,
    QSortFilterProxyModel,
    Qt,
    QThread,
    Signal,
    Slot,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import config
from core.worker import Worker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    The main application window for Project Prospector.

    This class sets up the entire user interface, including widgets for controls,
    a table for job results, and a detail view. It also manages the background
    worker thread for non-blocking operations.
    """

    # Signal to start the worker's scan process, carrying the resume content.
    start_worker_scan = Signal(str)

    # Column indices for the results table for easier access
    COL_SCORE = 0
    COL_TITLE = 1
    COL_COMPANY = 2
    COL_SOURCE = 3

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the MainWindow.

        Args:
            parent (Optional[QWidget]): The parent widget, if any.
        """
        super().__init__(parent)
        logger.info("Initializing MainWindow.")

        self.setWindowTitle("Project Prospector")
        self.setGeometry(100, 100, 1400, 800)

        self._worker: Optional[Worker] = None
        self._worker_thread: Optional[QThread] = None

        self._init_ui()
        self._init_worker()
        self._connect_signals()
        self._load_initial_settings()

        logger.info("MainWindow initialization complete.")

    def _init_ui(self) -> None:
        """Initializes the user interface, creating and arranging all widgets."""
        logger.debug("Initializing UI components.")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Controls ---
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout()
        controls_group.setLayout(controls_layout)

        self.start_scan_button = QPushButton("Start Scan")
        self.start_scan_button.setToolTip("Begin searching for new job prospects.")
        self.stop_scan_button = QPushButton("Stop Scan")
        self.stop_scan_button.setToolTip("Cancel the currently running scan.")
        self.stop_scan_button.setEnabled(False)

        self.resume_path_edit = QLineEdit()
        self.resume_path_edit.setPlaceholderText("Path to your resume file (.md, .txt)")
        self.browse_resume_button = QPushButton("Browse...")

        controls_layout.addWidget(self.start_scan_button)
        controls_layout.addWidget(self.stop_scan_button)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(QLabel("Resume File:"))
        controls_layout.addWidget(self.resume_path_edit, 1)
        controls_layout.addWidget(self.browse_resume_button)

        # --- Main Content Area (Splitter) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Panel: Results Table ---
        results_group = QGroupBox("Prospects")
        results_layout = QVBoxLayout()
        results_group.setLayout(results_layout)

        self.job_table_view = QTableView()
        self.job_table_model = QStandardItemModel(0, 4)
        self.job_table_model.setHorizontalHeaderLabels(
            ["Score", "Title", "Company", "Source"]
        )

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.job_table_model)

        self.job_table_view.setModel(self.proxy_model)
        self.job_table_view.setSortingEnabled(True)
        self.job_table_view.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.job_table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.job_table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.job_table_view.horizontalHeader().setStretchLastSection(True)
        self.job_table_view.sortByColumn(self.COL_SCORE, Qt.SortOrder.DescendingOrder)

        results_layout.addWidget(self.job_table_view)
        splitter.addWidget(results_group)

        # --- Right Panel: Details View ---
        details_group = QGroupBox("Details")
        details_layout = QVBoxLayout()
        details_group.setLayout(details_layout)

        details_form_layout = QFormLayout()
        self.title_label = QLabel("N/A")
        self.title_label.setWordWrap(True)
        self.url_label = QLabel('<a href="#">N/A</a>')
        self.url_label.setOpenExternalLinks(True)
        self.company_label = QLabel("N/A")
        self.contact_label = QLabel("N/A")

        details_form_layout.addRow("<b>Title:</b>", self.title_label)
        details_form_layout.addRow("<b>URL:</b>", self.url_label)
        details_form_layout.addRow("<b>Company:</b>", self.company_label)
        details_form_layout.addRow("<b>Contact:</b>", self.contact_label)

        self.justification_edit = QTextEdit()
        self.justification_edit.setReadOnly(True)
        self.cover_letter_edit = QTextEdit()
        self.cover_letter_edit.setReadOnly(False) # Allow user to edit

        details_layout.addLayout(details_form_layout)
        details_layout.addWidget(QLabel("<b>Justification:</b>"))
        details_layout.addWidget(self.justification_edit)
        details_layout.addWidget(QLabel("<b>Draft Cover Letter:</b>"))
        details_layout.addWidget(self.cover_letter_edit)

        splitter.addWidget(details_group)
        splitter.setSizes([600, 800])

        # --- Status Bar ---
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Ready.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # --- Final Layout Assembly ---
        main_layout.addWidget(controls_group)
        main_layout.addWidget(splitter)

    def _init_worker(self) -> None:
        """Initializes the background worker and its thread."""
        logger.debug("Initializing worker thread.")
        self._worker_thread = QThread()
        self._worker = Worker()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.start()
        logger.info("Worker thread started.")

    def _connect_signals(self) -> None:
        """Connects all signals and slots for the application."""
        if not self._worker or not self._worker_thread:
            logger.error("Worker not initialized, cannot connect signals.")
            return

        # UI controls to main window slots
        self.start_scan_button.clicked.connect(self.start_scan)
        self.stop_scan_button.clicked.connect(self._worker.stop)
        self.browse_resume_button.clicked.connect(self.browse_for_resume)

        # Main window to worker
        self.start_worker_scan.connect(self._worker.run_scan)

        # Worker to main window slots
        self._worker.job_found.connect(self.add_job_to_table)
        self._worker.progress_updated.connect(self.update_progress)
        self._worker.status_updated.connect(self.update_status)
        self._worker.finished.connect(self.scan_finished)
        self._worker.error_occurred.connect(self.handle_error)

        # Table view selection
        self.job_table_view.selectionModel().selectionChanged.connect(
            self.display_job_details
        )
        logger.debug("Signal connections established.")

    def _load_initial_settings(self) -> None:
        """Loads initial settings from the config file."""
        if config.RESUME_FILE_PATH:
            self.resume_path_edit.setText(config.RESUME_FILE_PATH)
            logger.info(f"Loaded default resume path: {config.RESUME_FILE_PATH}")

    def _read_resume_content(self) -> str:
        """
        Reads the content of the resume file specified in the UI.

        Returns:
            str: The content of the resume file, or an empty string if the
                 path is invalid or the file cannot be read.
        """
        resume_path = self.resume_path_edit.text()
        if not resume_path or not os.path.exists(resume_path):
            logger.warning(f"Resume file not found at: {resume_path}")
            self.handle_error(
                "Resume file not found. Analysis will proceed without it."
            )
            return ""
        try:
            with open(resume_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading resume file {resume_path}: {e}")
            self.handle_error(f"Could not read resume file: {e}")
            return ""

    @Slot()
    def start_scan(self) -> None:
        """Prepares for and starts a new scan."""
        logger.info("'Start Scan' button clicked.")
        self.start_scan_button.setEnabled(False)
        self.stop_scan_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.job_table_model.removeRows(0, self.job_table_model.rowCount())
        self.update_status("Starting scan...")

        resume_content = self._read_resume_content()
        self.start_worker_scan.emit(resume_content)

    @Slot()
    def scan_finished(self) -> None:
        """Handles the completion of a scan."""
        logger.info("Scan finished signal received.")
        self.start_scan_button.setEnabled(True)
        self.stop_scan_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.update_status("Scan complete.")

    @Slot(dict)
    def add_job_to_table(self, job_data: Dict[str, Any]) -> None:
        """
        Adds a new job prospect to the results table.

        Args:
            job_data (Dict[str, Any]): A dictionary containing the analyzed job data.
        """
        logger.debug(f"Adding job to table: {job_data.get('title')}")
        score_item = QStandardItem(str(job_data.get("score", 0)))
        score_item.setData(job_data, Qt.ItemDataRole.UserRole) # Store full dict

        title_item = QStandardItem(job_data.get("title", "N/A"))
        company_item = QStandardItem(job_data.get("company_name", "N/A"))
        source_item = QStandardItem(job_data.get("source", "N/A"))

        self.job_table_model.appendRow(
            [score_item, title_item, company_item, source_item]
        )

    @Slot(int)
    def update_progress(self, value: int) -> None:
        """
        Updates the progress bar.

        Args:
            value (int): The progress value (0-100).
        """
        self.progress_bar.setValue(value)

    @Slot(str)
    def update_status(self, message: str) -> None:
        """
        Updates the status label in the status bar.

        Args:
            message (str): The new status message to display.
        """
        self.status_label.setText(message)

    @Slot(str)
    def handle_error(self, error_message: str) -> None:
        """
        Displays an error message to the user.

        Args:
            error_message (str): The error message to display.
        """
        logger.error(f"Displaying error to user: {error_message}")
        QMessageBox.warning(self, "Error", error_message)
        self.update_status("An error occurred.")

    @Slot(QItemSelection, QItemSelection)
    def display_job_details(
        self, selected: QItemSelection, deselected: QItemSelection
    ) -> None:
        """
        Displays the details of the selected job in the right-hand panel.

        Args:
            selected (QItemSelection): The newly selected items.
            deselected (QItemSelection): The previously selected items.
        """
        if not selected.indexes():
            return

        source_index = selected.indexes()[0]
        proxy_index = self.proxy_model.mapToSource(source_index)
        item = self.job_table_model.itemFromIndex(proxy_index)

        if not item:
            return

        job_data: Dict[str, Any] = item.data(Qt.ItemDataRole.UserRole)
        logger.debug(f"Displaying details for: {job_data.get('title')}")

        self.title_label.setText(job_data.get("title", "N/A"))
        url = job_data.get("url", "#")
        self.url_label.setText(f'<a href="{url}">{url}</a>')
        self.company_label.setText(job_data.get("company_name", "N/A"))
        self.contact_label.setText(job_data.get("contact_info", "N/A"))
        self.justification_edit.setText(job_data.get("justification", ""))
        self.cover_letter_edit.setText(job_data.get("cover_letter", ""))

    @Slot()
    def browse_for_resume(self) -> None:
        """Opens a file dialog to select a resume file."""
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Text files (*.md *.txt)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if file_dialog.exec():
            filenames = file_dialog.selectedFiles()
            if filenames:
                self.resume_path_edit.setText(filenames[0])
                logger.info(f"User selected new resume file: {filenames[0]}")

    def closeEvent(self, event: Any) -> None:
        """
        Handles the window close event to ensure the worker thread is shut down.

        Args:
            event (Any): The close event.
        """
        logger.info("Close event triggered. Shutting down worker thread.")
        if self._worker_thread and self._worker_thread.isRunning():
            if self._worker:
                self._worker.stop()
            self._worker_thread.quit()
            if not self._worker_thread.wait(3000):  # Wait 3 seconds
                logger.warning("Worker thread did not terminate gracefully. Forcing.")
                self._worker_thread.terminate()
        event.accept()