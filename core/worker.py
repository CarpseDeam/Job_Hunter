# core/worker.py
"""
To define the QObject worker that runs in a background QThread, handling all
scraping and AI analysis to keep the GUI responsive.
"""

import logging
from typing import Dict, Optional, List
import importlib

from PySide6.QtCore import QObject, Signal, Slot

import config
from core.agents.base_scout import BaseScout, JobLead
from core.agents.qualifier_agent import QualifierAgent

logger = logging.getLogger(__name__)


def _import_class_from_string(path: str) -> Optional[Type[BaseScout]]:
    """Dynamically imports a class from a string path."""
    try:
        module_name, class_name = path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError, ValueError) as e:
        logger.error(f"Failed to import scout class from path '{path}': {e}")
        return None


class Worker(QObject):
    """
    Handles long-running tasks in a separate thread.

    This worker is responsible for orchestrating the scraping and analysis agents
    to find and qualify job prospects. It communicates with the main GUI thread
    via signals to provide progress updates, results, and status changes without
    blocking the user interface.

    Attributes:
        job_found (Signal): Emits a dictionary with analyzed job data.
        progress_updated (Signal): Emits an integer percentage (0-100) of task completion.
        status_updated (Signal): Emits a string with the current status message.
        finished (Signal): Emitted when the entire task is complete.
        error_occurred (Signal): Emits an error message string if an exception occurs.
    """

    job_found = Signal(dict)
    progress_updated = Signal(int)
    status_updated = Signal(str)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """
        Initializes the worker instance.

        Args:
            parent (Optional[QObject]): The parent QObject, if any.
        """
        super().__init__(parent)
        self._is_running = False
        self._scouts: List[BaseScout] = []
        self._qualifier_agent: Optional[QualifierAgent] = None

    @Slot()
    def stop(self) -> None:
        """
        Stops the current running task gracefully.

        Sets a flag that is checked during the processing loop, allowing the
        worker to terminate its current operation cleanly.
        """
        logger.info("Stop signal received. Attempting to halt worker process.")
        self._is_running = False

    @Slot(str)
    def run_scan(self, resume_content: str) -> None:
        """
        The main entry point for the worker's task, designed to be run in a QThread.

        This method initializes the agents, scrapes for job leads from configured
        sources, analyzes each lead with the AI qualifier, and emits signals
        with the results.

        Args:
            resume_content (str): The text content of the user's resume, used by
                                  the QualifierAgent for analysis.
        """
        if self._is_running:
            logger.warning("Scan is already in progress. Ignoring new request.")
            self.error_occurred.emit("A scan is already in progress.")
            return

        self._is_running = True
        scan_cancelled = False
        logger.info("Worker scan started.")
        self.status_updated.emit("Starting scan...")
        self.progress_updated.emit(0)

        try:
            # Step 1: Initialize Agents
            self.status_updated.emit("Initializing agents...")
            self._qualifier_agent = QualifierAgent()
            self._scouts = []
            for scout_path in config.SCOUTS_TO_USE:
                ScoutClass = _import_class_from_string(scout_path)
                if ScoutClass:
                    self._scouts.append(ScoutClass())

            if not self._scouts:
                raise RuntimeError("No valid scouts were initialized. Check config.py and logs.")

            logger.info(f"{len(self._scouts)} scout(s) and Qualifier agent initialized.")

            # Step 2: Find Leads from all sources
            self.status_updated.emit("Searching for job leads from all sources...")
            all_leads: List[JobLead] = []
            for scout in self._scouts:
                if not self._is_running:
                    raise InterruptedError("Scan cancelled during lead search.")
                self.status_updated.emit(f"Asking {scout.__class__.__name__} for leads...")
                all_leads.extend(scout.find_leads())

            if not self._is_running:
                raise InterruptedError("Scan cancelled during lead search.")

            if not all_leads:
                logger.info("No new leads found from any source.")
                self.status_updated.emit("No new job leads found.")
                self.progress_updated.emit(100)
                self._is_running = False
                self.finished.emit()
                return

            logger.info(f"Found {len(all_leads)} potential leads in total. Starting analysis.")
            total_leads = len(all_leads)

            # Step 3: Analyze Leads
            for i, lead in enumerate(all_leads):
                if not self._is_running:
                    scan_cancelled = True
                    logger.info("Worker process was stopped externally during analysis.")
                    break

                status_msg = f"Analyzing lead {i + 1}/{total_leads}: {lead.title[:50]}..."
                self.status_updated.emit(status_msg)
                logger.debug(status_msg)

                analyzed_job = self._qualifier_agent.analyze_and_qualify(
                    lead, resume_content
                )

                if analyzed_job:
                    logger.info(
                        f"Job '{lead.title}' qualified with score "
                        f"{analyzed_job.get('score')}."
                    )
                    self.job_found.emit(analyzed_job)
                else:
                    logger.info(f"Job '{lead.title}' was not qualified or failed analysis.")

                progress = int(((i + 1) / total_leads) * 100)
                self.progress_updated.emit(progress)

        except InterruptedError as e:
            scan_cancelled = True
            logger.warning(str(e))
        except Exception as e:
            error_message = f"An error occurred during the scan: {e}"
            logger.error(error_message, exc_info=True)
            self.error_occurred.emit(error_message)
        finally:
            logger.info("Worker scan finished or was terminated.")
            self._is_running = False
            if scan_cancelled:
                self.status_updated.emit("Scan cancelled.")
            else:
                self.status_updated.emit("Scan complete.")
            self.progress_updated.emit(100)
            self.finished.emit()