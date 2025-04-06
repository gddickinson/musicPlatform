#!/usr/bin/env python3
"""
Music Production Platform
A digital audio workstation built with Python and PyQt5
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import qdarkstyle

# Import the main GUI
from enhanced_main_gui import EnhancedMainGUI
from integration import IntegratedControlPanel

def main():
    """Main entry point for the application"""
    # Create application
    app = QApplication(sys.argv)

    # Set application style
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    # Set application icon
    # app.setWindowIcon(QIcon('icons/app_icon.png'))

    # Set application name and organization
    app.setApplicationName("Music Production Platform")
    app.setOrganizationName("MusicProductionPlatform")

    # Create and show main window
    main_window = EnhancedMainGUI()
    main_window.show()

    integration_panel = IntegratedControlPanel(main_window)
    main_window.central_widget.addTab(integration_panel, "Integration")

    # Run application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
