"""Application entry point."""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from app.branding import create_logo, create_splash_pixmap
from app.database import Database
from app.main_window import MainWindow, authenticate_startup
from app.settings import AppSettings


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("Meezan Cheque Printer")
    application.setOrganizationName("Local")
    application.setWindowIcon(QIcon(create_logo()))
    splash = QSplashScreen(create_splash_pixmap())
    splash.show()
    application.processEvents()
    try:
        database = Database()
        settings = AppSettings.load(database)
    except (OSError, ValueError) as error:
        splash.close()
        QMessageBox.critical(None, "Application startup failed", str(error))
        return 1
    splash.close()
    if not authenticate_startup(database, settings):
        return 0
    window = MainWindow(database)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
