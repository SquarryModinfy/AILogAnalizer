"""
Main file for AI Log Analyzer application
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.constants import logger
from core.vectorizer import Vectorizer
from ui.main_window import MainWindow

def main():
    """Application entry point"""
    logger.debug("Application startup")
    app = QApplication(sys.argv)
    main_window = MainWindow(None)
    main_window.show_loading()

    def init_vectorizer():
        try:
            logger.debug("Starting vectorizer initialization...")
            vectorizer = Vectorizer()
            logger.debug("Vectorizer created successfully, updating main window")
            success = main_window.set_vectorizer(vectorizer)
            if not success:
                logger.error("Failed to set vectorizer in main window")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(main_window, "Warning", 
                              "Vectorizer was not fully initialized.\nSome features may be unavailable.")
            main_window.hide_loading()
            main_window.show()
            logger.debug("Main window shown")
        except Exception as e:
            logger.error(f"Vectorizer initialization error: {str(e)}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(main_window, "Error", 
                             f"Failed to initialize vectorizer: {str(e)}\n\nThe application may not work correctly.")
            main_window.hide_loading()
            main_window.show()

    QTimer.singleShot(100, init_vectorizer)
    logger.debug("Application started")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()