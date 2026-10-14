"""Main window for cheque entry, preview, local history, and safe printing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QFont, QIcon, QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication, QDateEdit, QDialog, QFileDialog, QGraphicsScene, QGraphicsTextItem,
    QGraphicsView, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from .amount_words import amount_to_words
from .branding import DEVELOPER_CREDIT, DEVELOPER_ROLE, create_logo
from .cheque_form import ChequeForm
from .database import Database
from .printer_service import FIELD_ORDER, MM_TO_PT, generate_pdf, installed_printers, make_layout, paper_size
from .settings import AppSettings
from .template_editor import TemplateEditor
from .validation import ValidationError, validate_cheque

_PASSWORD_ITERATIONS = 310_000


def _password_hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS).hex()


def _check_password(settings: AppSettings, password: str) -> bool:
    if not settings.app_password_hash or not settings.app_password_salt:
        return True
    try:
        candidate = _password_hash(password, bytes.fromhex(settings.app_password_salt))
    except ValueError:
        return False
    return hmac.compare_digest(candidate, settings.app_password_hash)


class MainWindow(QMainWindow):
    def __init__(self, database: Database):
        super().__init__()
        self.database = database
        self.settings = AppSettings.load(database)
        self.active_record_id: int | None = None
        self._printing = False
        self.setWindowTitle("Meezan Cheque Printer | Farhan Sami")
        self.setWindowIcon(QIcon(create_logo()))
        self.resize(1000, 720)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.form = ChequeForm()
        self.tabs.addTab(self._entry_tab(), "Cheque entry")
        self.tabs.addTab(self._preview_tab(), "Preview")
        self.tabs.addTab(self._history_tab(), "Cheque history")
        self.tabs.addTab(self._settings_tab(), "Settings")
        self._refresh_history()
        self.statusBar().showMessage("Cheque data stays on this computer.")
        self.statusBar().addPermanentWidget(QLabel(f"{DEVELOPER_CREDIT} | {DEVELOPER_ROLE}"))
        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About", self)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)

    def _entry_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.form)
        row = QHBoxLayout()
        for title, callback in (("New", self.new_cheque), ("Save draft", self.save_draft),
                                ("Preview", self.refresh_preview), ("Export PDF", self.export_pdf),
                                ("Print test page", self.print_test_page), ("Print cheque", self.print_cheque)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            if title == "Print cheque":
                self.print_button = button
            row.addWidget(button)
        layout.addLayout(row)
        return page

    def _preview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Layout guide only. Calibrate on ordinary paper against a blank cheque."))
        self.preview = QGraphicsView()
        self.preview_scene = QGraphicsScene(self.preview)
        self.preview.setScene(self.preview_scene)
        layout.addWidget(self.preview)
        return page

    def _history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search payee, date, amount, or memo")
        self.search.textChanged.connect(self._refresh_history)
        layout.addWidget(self.search)
        self.history = QTableWidget(0, 6)
        self.history.setHorizontalHeaderLabels(["ID", "Date", "Payee", "Amount", "Status", "Memo"])
        self.history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history)
        row = QHBoxLayout()
        for title, callback in (("Open draft", self.load_selected), ("Duplicate", self.duplicate_selected),
                                ("Export CSV", self.export_history)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)
        return page

    def _settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.settings_summary = QLabel()
        self.settings_summary.setWordWrap(True)
        layout.addWidget(self.settings_summary)
        for title, callback in (("Printer and cheque template settings", self.edit_template),
                                ("Back up database", self.backup_database),
                                ("Restore database", self.restore_database),
                                ("Set or change application password", self.change_password),
                                ("Remove application password", self.remove_password)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            layout.addWidget(button)
        self._update_settings_summary()
        layout.addStretch(1)
        return page

    def show_about(self) -> None:
        QMessageBox.about(self, "About Meezan Cheque Printer",
            "<h2>Meezan Cheque Printer</h2><p>Local Windows cheque preparation and printing utility.</p>"
            "<p><b>Developed by Farhan Sami</b><br>IT Network and System Engineer</p>"
            "<p>Categories: Finance &amp; Accounting · Cheque Printing · Windows Desktop Productivity</p>"
            "<p>Independent utility; not affiliated with Meezan Bank.</p>")

    def _update_settings_summary(self) -> None:
        dimensions = (f"{self.settings.width_mm:g} x {self.settings.height_mm:g} mm"
                      if self.settings.width_mm and self.settings.height_mm else "Not measured")
        self.settings_summary.setText(
            f"Printer: {self.settings.default_printer or 'Not selected'}\nMeasured cheque: {dimensions}\n"
            f"Orientation: {self.settings.orientation}\nCalibration confirmed: {self.settings.calibration_complete}\n"
            f"Application password: {'Enabled' if self.settings.app_password_hash else 'Disabled'}")

    def _record(self) -> dict[str, str]:
        values = self.form.values()
        values["cheque_date"], values["payee"], values["amount"], values["memo"], values["internal_remarks"] = validate_cheque(
            values["cheque_date"], values["payee"], values["amount"], values["memo"], values["internal_remarks"])
        values["amount_words"] = amount_to_words(values["amount"])
        return values

    def save_draft(self) -> None:
        try:
            record = self._record()
            self.active_record_id = self.database.save_draft(
                record["cheque_date"], record["payee"], record["amount"], record["amount_words"],
                record["memo"], record["internal_remarks"], self.active_record_id)
        except (ValidationError, ValueError, OSError) as error:
            QMessageBox.warning(self, "Cannot save draft", str(error))
            return
        self._refresh_history()
        self.statusBar().showMessage(f"Draft {self.active_record_id} saved locally.", 5000)

    def new_cheque(self) -> None:
        self.active_record_id = None
        self.form.clear()
        self.tabs.setCurrentIndex(0)

    def refresh_preview(self) -> None:
        try:
            record = self._record()
            width, height, fields = make_layout(record, self.settings)
        except (ValidationError, ValueError) as error:
            QMessageBox.warning(self, "Preview unavailable", str(error))
            return
        self.preview_scene.clear()
        self.preview_scene.setSceneRect(0, 0, width, height)
        for item in fields:
            text = QGraphicsTextItem("\n".join(item.lines))
            text.setFont(QFont(item.font_family, max(6, round(item.font_size_pt))))
            text.setDefaultTextColor(QColor("#111827"))
            x = item.x_pt
            if item.alignment == "right":
                x -= text.boundingRect().width()
            elif item.alignment == "center":
                x -= text.boundingRect().width() / 2
            text.setPos(x, height - item.y_pt - text.boundingRect().height())
            self.preview_scene.addItem(text)
        self.tabs.setCurrentIndex(1)

    def export_pdf(self) -> None:
        try:
            record = self._record()
            make_layout(record, self.settings)
        except (ValidationError, ValueError) as error:
            QMessageBox.warning(self, "PDF unavailable", str(error))
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save overlay PDF", "cheque-overlay.pdf", "PDF (*.pdf)")
        if not filename:
            return
        try:
            generate_pdf(record, self.settings, Path(filename))
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, "PDF generation failed", str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(filename))

    def _printer(self, cheque: bool) -> QPrinter:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setResolution(72)
        if self.settings.default_printer:
            printer.setPrinterName(self.settings.default_printer)
        if cheque:
            from PySide6.QtGui import QPageLayout, QPageSize
            from PySide6.QtCore import QSizeF
            width, height = paper_size(self.settings)
            orientation = QPageLayout.Orientation.Landscape if self.settings.orientation == "Landscape" else QPageLayout.Orientation.Portrait
            size = QPageSize(QSizeF(width, height), QPageSize.Unit.Millimeter, "Measured cheque")
            printer.setPageSize(size)
            printer.setPageOrientation(orientation)
        printer.setFullPage(True)
        return printer

    def print_test_page(self) -> None:
        if not self.settings.default_printer and not installed_printers():
            QMessageBox.warning(self, "No printer", "Install or select a Windows printer first.")
            return
        printer = self._printer(False)
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return
        painter = QPainter()
        if not painter.begin(printer):
            QMessageBox.critical(self, "Test print failed", "Windows could not start the print job.")
            return
        rect = printer.pageRect(QPrinter.Unit.Point)
        painter.drawText(QPointF(rect.left() + 24, rect.top() + 32), "CALIBRATION ONLY - ORDINARY A4 PAPER")
        painter.drawRect(rect.adjusted(18, 18, -18, -18))
        for i, key in enumerate(FIELD_ORDER):
            field = self.settings.fields[key]
            painter.drawText(QPointF(rect.left() + 36, rect.top() + 80 + i * 52),
                             f"{key}: x={field.x_mm:.1f} mm, y={field.y_mm:.1f} mm")
        if not painter.end():
            QMessageBox.critical(self, "Test print failed", "The calibration job could not be finalized.")
            return
        QMessageBox.information(self, "Test page submitted", "Windows accepted the A4 test job; compare it with a blank cheque. This does not confirm physical printing.")

    def print_cheque(self) -> None:
        if self._printing:
            return
        if not self.settings.calibration_complete:
            QMessageBox.warning(self, "Calibration required", "Calibrate against a blank cheque using ordinary paper before printing.")
            return
        try:
            record = self._record()
            _, height, fields = make_layout(record, self.settings)
            if self.active_record_id is None:
                self.save_draft()
            if self.active_record_id is None:
                return
        except (ValidationError, ValueError) as error:
            QMessageBox.warning(self, "Cannot print", str(error))
            return
        answer = QMessageBox.warning(self, "Confirm cheque print", "Submit one print job? The app cannot verify the physical result and will not automatically retry.", QMessageBox.StandardButton.Print | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if answer != QMessageBox.StandardButton.Print:
            return
        if not self.settings.default_printer and not installed_printers():
            QMessageBox.warning(self, "No printer", "Install or select a Windows printer first.")
            return
        try:
            printer = self._printer(True)
        except ValueError as error:
            QMessageBox.warning(self, "Printer setup incomplete", str(error))
            return
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return
        painter = QPainter()
        self._printing = True
        self.print_button.setEnabled(False)
        started = False
        error = None
        try:
            if not painter.begin(printer):
                raise RuntimeError("The print job could not be started.")
            started = True
            painter.setClipRect(printer.pageRect(QPrinter.Unit.Point))
            for item in fields:
                painter.setFont(QFont(item.font_family, round(item.font_size_pt)))
                metrics = painter.fontMetrics()
                for line_index, line in enumerate(item.lines):
                    x = item.x_pt
                    if item.alignment == "right":
                        x -= metrics.horizontalAdvance(line)
                    elif item.alignment == "center":
                        x -= metrics.horizontalAdvance(line) / 2
                    painter.drawText(QPointF(x, height - item.y_pt + line_index * item.font_size_pt * 1.2), line)
        except (RuntimeError, OSError, ValueError) as exc:
            error = exc
        finally:
            if painter.isActive() and not painter.end():
                error = error or RuntimeError("The print job could not be finalized.")
        try:
            self.database.set_print_status(self.active_record_id, "Uncertain" if error and started else "Submitted")
        except (ValueError, OSError) as exc:
            error = error or exc
        self._printing = False
        self.print_button.setEnabled(True)
        self._refresh_history()
        if error:
            QMessageBox.critical(self, "Print result uncertain", f"{error}\nThe job may have reached the printer. Verify output before any retry.")
        else:
            QMessageBox.information(self, "Print job submitted", "Windows accepted the job; physical printing is not verified. No automatic reprint was made.")

    def _selected_id(self) -> int | None:
        rows = self.history.selectionModel().selectedRows()
        if not rows:
            return None
        return int(self.history.item(rows[0].row(), 0).text())

    def _refresh_history(self, *_args) -> None:
        if not hasattr(self, "history"):
            return
        records = self.database.search_cheques(self.search.text())
        self.history.setRowCount(len(records))
        for row, record in enumerate(records):
            for col, value in enumerate((record["id"], record["cheque_date"], record["payee"], record["amount"], record["print_status"], record["memo"])):
                self.history.setItem(row, col, QTableWidgetItem(str(value)))
        self.history.resizeColumnsToContents()

    def load_selected(self) -> None:
        record_id = self._selected_id()
        record = self.database.get_cheque(record_id) if record_id else None
        if not record or record["print_status"] != "Draft":
            QMessageBox.information(self, "Read-only history", "Select one draft. Submitted records cannot be edited.")
            return
        self.active_record_id = record["id"]
        self.form.set_values(record)
        self.tabs.setCurrentIndex(0)

    def duplicate_selected(self) -> None:
        record_id = self._selected_id()
        if not record_id:
            QMessageBox.information(self, "Select a record", "Select one record to duplicate.")
            return
        try:
            new_id = self.database.duplicate_as_draft(record_id)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Cannot duplicate", str(error))
            return
        record = self.database.get_cheque(new_id)
        self.active_record_id = new_id
        self.form.set_values(record)
        self.tabs.setCurrentIndex(0)
        self._refresh_history()

    def export_history(self) -> None:
        ids = [int(item.text()) for item in self.history.selectedItems() if item.column() == 0]
        if not ids:
            QMessageBox.information(self, "Select records", "Select one or more history rows to export.")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Export history", "cheque-history.csv", "CSV (*.csv)")
        if filename:
            try:
                self.database.export_csv(ids, Path(filename))
            except (OSError, ValueError) as error:
                QMessageBox.critical(self, "Export failed", str(error))

    def edit_template(self) -> None:
        dialog = TemplateEditor(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        dialog.apply_to(self.settings)
        try:
            if self.settings.width_mm and self.settings.height_mm:
                paper_size(self.settings)
            self.settings.save(self.database)
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, "Settings not saved", str(error))
            return
        self._update_settings_summary()

    def backup_database(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Back up database", "cheques-backup.sqlite3", "SQLite (*.sqlite3)")
        if filename:
            try:
                self.database.backup_to(Path(filename))
            except (OSError, ValueError) as error:
                QMessageBox.critical(self, "Backup failed", str(error))

    def restore_database(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Restore database", "", "SQLite (*.sqlite3 *.db)")
        if not filename:
            return
        if QMessageBox.question(self, "Confirm restore", "Replace local history? A safety backup is created first.") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.restore_from(Path(filename))
            self.settings = AppSettings.load(self.database)
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Restore failed", str(error))
            return
        self._refresh_history()
        self._update_settings_summary()

    def change_password(self) -> None:
        if self.settings.app_password_hash:
            current, ok = QInputDialog.getText(self, "Verify password", "Current password", QLineEdit.EchoMode.Password)
            if not ok or not _check_password(self.settings, current):
                QMessageBox.warning(self, "Password unchanged", "Current password was not verified.")
                return
        password, ok = QInputDialog.getText(self, "Set password", "New password (at least 10 characters)", QLineEdit.EchoMode.Password)
        if not ok:
            return
        if len(password) < 10:
            QMessageBox.warning(self, "Password too short", "Use at least 10 characters.")
            return
        confirmation, ok = QInputDialog.getText(self, "Confirm password", "Re-enter password", QLineEdit.EchoMode.Password)
        if not ok or not hmac.compare_digest(password, confirmation):
            QMessageBox.warning(self, "Password unchanged", "The passwords did not match.")
            return
        salt = secrets.token_bytes(16)
        self.settings.app_password_salt = salt.hex()
        self.settings.app_password_hash = _password_hash(password, salt)
        self.settings.save(self.database)
        self._update_settings_summary()

    def remove_password(self) -> None:
        if not self.settings.app_password_hash:
            return
        password, ok = QInputDialog.getText(self, "Verify password", "Current password", QLineEdit.EchoMode.Password)
        if not ok or not _check_password(self.settings, password):
            QMessageBox.warning(self, "Password unchanged", "Current password was not verified.")
            return
        self.settings.app_password_hash = ""
        self.settings.app_password_salt = ""
        self.settings.save(self.database)
        self._update_settings_summary()


def authenticate_startup(database: Database, settings: AppSettings) -> bool:
    del database
    if not settings.app_password_hash:
        return True
    for _ in range(3):
        password, ok = QInputDialog.getText(None, "Meezan Cheque Printer", "Application password", QLineEdit.EchoMode.Password)
        if not ok:
            return False
        if _check_password(settings, password):
            return True
        QMessageBox.warning(None, "Incorrect password", "The application password is incorrect.")
    return False
