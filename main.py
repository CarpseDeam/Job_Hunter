# main.py
"""
Main entry point for the Project Prospector application.

This script initializes the Qt application, sets up the main window, applies the
application theme, and starts the event loop. It serves as the bootstrap for
the entire GUI application.
"""

import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

try:
    from PySide6.QtWidgets import QApplication
    from ui.main_window import MainWindow
    from ui.dark_theme import apply_dark_theme
except ImportError as e:
    # This will help diagnose issues if PySide6 or other modules are not installed.
    logger.critical(f"Failed to import a critical module: {e}")
    logger.critical(
        "Please ensure all dependencies from requirements.txt are installed."
    )
    sys.exit(1)


def main() -> int:
    """
    Initializes and runs the Project Prospector application.

    This function sets up the QApplication, creates the main window,
    applies the visual theme, shows the window, and starts the Qt event loop.

    Returns:
        int: The exit code of the application.
    """
    logger.info("Starting Project Prospector application...")

    try:
        app = QApplication(sys.argv)
        logger.info("QApplication instance created.")

        window = MainWindow()
        logger.info("MainWindow instance created.")

        apply_dark_theme(app)
        logger.info("Dark theme applied.")

        window.show()
        logger.info("Main window shown. Entering event loop.")

        exit_code = app.exec()
        logger.info(f"Application exiting with code {exit_code}.")
        return exit_code

    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())