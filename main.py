#!/usr/bin/env python3
"""
Music Production Platform
A digital audio workstation built with Python and PyQt5

This is the main entry point for the application. It initializes the
logging system, sets up the user interface, and starts the application.
"""

import sys
import os
import traceback
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
import qdarkstyle

# Import the logger
from logger import get_logger

# Set up module logger
logger = get_logger(__name__)

# Import the main GUI
from enhanced_main_gui import EnhancedMainGUI
from integration import IntegratedControlPanel


class ApplicationError(Exception):
    """Base exception for application-level errors."""
    pass


def setup_exception_handling() -> None:
    """
    Set up global exception handling to catch and log unhandled exceptions.
    """
    def exception_hook(exctype, value, tb):
        """
        Custom exception hook that logs unhandled exceptions.

        Args:
            exctype: Exception type
            value: Exception value
            tb: Traceback object
        """
        # Log the error
        error_msg = ''.join(traceback.format_exception(exctype, value, tb))
        logger.critical(f"Unhandled exception: {error_msg}")

        # Show error dialog
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Application Error")
        error_dialog.setText("An unexpected error occurred.")
        error_dialog.setInformativeText(str(value))
        error_dialog.setDetailedText(error_msg)
        error_dialog.exec_()

        # Call the default exception hook
        sys.__excepthook__(exctype, value, tb)

    # Set the exception hook
    sys.excepthook = exception_hook


def check_dependencies() -> bool:
    """
    Check that all required dependencies are installed.

    Returns:
        True if all dependencies are installed, False otherwise
    """
    required_packages = [
        "PyQt5",
        "numpy",
        "pyaudio",
        "pygame",
        "pyqtgraph",
        "soundfile"
    ]

    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")

        # Show error dialog
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Missing Dependencies")
        error_dialog.setText("The following required packages are missing:")
        error_dialog.setInformativeText(', '.join(missing_packages))
        error_dialog.setDetailedText(
            "Please install the missing packages using pip:\n\n"
            f"pip install {' '.join(missing_packages)}"
        )
        error_dialog.exec_()
        return False

    return True


def setup_environment() -> bool:
    """
    Set up the application environment.

    Returns:
        True if setup was successful, False otherwise
    """
    # Create application directories if they don't exist
    app_dirs = [
        "logs",
        "samples",
        "presets",
        "projects"
    ]

    try:
        for directory in app_dirs:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        return True
    except Exception as e:
        logger.error(f"Error setting up environment: {str(e)}")
        return False


def main():
    """Main entry point for the application"""
    # Initialize logger
    logger.info("Starting Music Production Platform")

    # Set up global exception handling
    setup_exception_handling()

    # Check dependencies
    if not check_dependencies():
        logger.critical("Missing dependencies, exiting")
        return 1

    # Set up environment
    if not setup_environment():
        logger.critical("Failed to set up environment, exiting")
        return 1

    try:
        # Create application
        app = QApplication(sys.argv)

        # Set application style
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        logger.debug("Applied dark style")

        # Set application icon if available
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons', 'app_icon.png')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logger.debug("Applied application icon")

        # Set application name and organization
        app.setApplicationName("Music Production Platform")
        app.setOrganizationName("MusicProductionPlatform")

        # Create and show main window
        try:
            logger.debug("Creating main window")
            main_window = EnhancedMainGUI()
            main_window.show()

            # Create integration panel
            try:
                logger.debug("Creating integration panel")
                integration_panel = IntegratedControlPanel(main_window)
                main_window.central_widget.addTab(integration_panel, "Integration")
            except Exception as e:
                logger.error(f"Failed to create integration panel: {str(e)}")
                logger.debug(traceback.format_exc())
                QMessageBox.warning(
                    main_window,
                    "Integration Error",
                    "Failed to load the integration panel. Some features may not be available."
                )
        except Exception as e:
            logger.critical(f"Failed to create main window: {str(e)}")
            logger.debug(traceback.format_exc())
            QMessageBox.critical(
                None,
                "Application Error",
                "Failed to create the main application window."
            )
            return 1

        # Run application
        logger.info("Application started successfully")
        return app.exec_()

    except Exception as e:
        logger.critical(f"Unexpected error in main function: {str(e)}")
        logger.debug(traceback.format_exc())
        return 1
    finally:
        logger.info("Application shutting down")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
