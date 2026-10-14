"""Template measurement and per-field positioning editor."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .printer_service import installed_printers
from .settings import AppSettings

FIELD_LABELS = {
    "date": "Date",
    "payee": "Payee",
    "amount_words": "Amount in words",
    "amount": "Numeric amount",
}


class TemplateEditor(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Printer and cheque template settings")
        self.resize(760, 620)
        self.settings = settings
        self._field_controls: dict[str, dict[str, QWidget]] = {}

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.printer = QComboBox()
        self.printer.setEditable(True)
        self.printer.addItems(installed_printers())
        if settings.default_printer:
            self.printer.setCurrentText(settings.default_printer)
        form.addRow("Default printer", self.printer)

        self.width = self._decimal(0, 350, 1)
        self.height = self._decimal(0, 250, 1)
        self.width.setValue(settings.width_mm or 0)
        self.height.setValue(settings.height_mm or 0)
        dimensions = QHBoxLayout()
        dimensions.addWidget(QLabel("Width (mm)"))
        dimensions.addWidget(self.width)
        dimensions.addWidget(QLabel("Height (mm)"))
        dimensions.addWidget(self.height)
        form.addRow("Measured cheque size", dimensions)

        self.orientation = QComboBox()
        self.orientation.addItems(["Landscape", "Portrait"])
        self.orientation.setCurrentText(settings.orientation)
        form.addRow("Orientation", self.orientation)

        self.date_format = QLineEdit(settings.date_format)
        form.addRow("Date format", self.date_format)
        self.currency = QLineEdit(settings.currency_symbol)
        self.currency.setMaxLength(12)
        form.addRow("Currency prefix", self.currency)
        self.confirm_print = QCheckBox("Ask before submitting each cheque")
        self.confirm_print.setChecked(settings.confirm_before_print)
        form.addRow("Print confirmation", self.confirm_print)
        self.allow_cheque_marks = QCheckBox("Allow calibration marks on a real cheque (not recommended)")
        self.allow_cheque_marks.setChecked(settings.calibration_marks_on_cheque)
        form.addRow("Calibration marks", self.allow_cheque_marks)
        self.calibration_complete = QCheckBox(
            "Calibration confirmed against a blank cheque using ordinary paper"
        )
        self.calibration_complete.setChecked(settings.calibration_complete)
        form.addRow("Alignment status", self.calibration_complete)
        root.addLayout(form)

        instructions = QLabel(
            "Measure a blank cheque before entering dimensions or coordinates. X is measured "
            "from the left edge; Y is measured from the top edge to the text baseline. "
            "No bank cheque dimensions or field positions are assumed."
        )
        instructions.setWordWrap(True)
        root.addWidget(instructions)

        fields_group = QGroupBox("Field positions (millimetres from top-left; Y is baseline)")
        fields_layout = QVBoxLayout(fields_group)
        for key, label in FIELD_LABELS.items():
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            field_settings = settings.fields[key]
            x = self._decimal(0, 350, 1)
            y = self._decimal(0, 250, 1)
            size = self._decimal(6, 36, 1)
            x.setValue(field_settings.x_mm)
            y.setValue(field_settings.y_mm)
            size.setValue(field_settings.font_size_pt)
            alignment = QComboBox()
            alignment.addItems(["left", "center", "right"])
            alignment.setCurrentText(field_settings.alignment)
            family = QComboBox()
            family.setEditable(True)
            family.addItems(["Arial", "Helvetica", "Times New Roman", "Courier New"])
            family.setCurrentText(field_settings.font_family)
            max_chars = QSpinBox()
            max_chars.setRange(1, 240)
            max_chars.setValue(field_settings.max_chars)
            second_line = QCheckBox("Allow second line")
            second_line.setChecked(field_settings.second_line)
            for title, widget in (
                ("X", x), ("Y", y), ("pt", size), ("Font", family),
                ("Align", alignment), ("Max chars", max_chars), ("", second_line),
            ):
                if title:
                    row.addWidget(QLabel(title))
                row.addWidget(widget)
            adjust = QHBoxLayout()
            adjust.addWidget(QLabel("Fine adjust"))
            for dx, dy, icon in ((-0.1, 0, "←"), (0.1, 0, "→"), (0, -0.1, "↑"), (0, 0.1, "↓")):
                button = QPushButton(icon)
                button.setMaximumWidth(36)
                button.clicked.connect(
                    lambda checked=False, x=x, y=y, dx=dx, dy=dy:
                    (x.setValue(x.value() + dx), y.setValue(y.value() + dy))
                )
                adjust.addWidget(button)
            fields_layout.addLayout(row)
            fields_layout.addLayout(adjust)
            self._field_controls[key] = {
                "x": x, "y": y, "size": size, "alignment": alignment,
                "font": family, "max_chars": max_chars, "second_line": second_line,
            }
        root.addWidget(fields_group)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _decimal(minimum: float, maximum: float, decimals: int) -> QDoubleSpinBox:
        control = QDoubleSpinBox()
        control.setRange(minimum, maximum)
        control.setDecimals(decimals)
        control.setSingleStep(0.1)
        return control

    def apply_to(self, settings: AppSettings) -> None:
        settings.default_printer = self.printer.currentText().strip()
        settings.width_mm = self.width.value() or None
        settings.height_mm = self.height.value() or None
        settings.orientation = self.orientation.currentText()
        settings.date_format = self.date_format.text().strip() or "dd/MM/yyyy"
        settings.currency_symbol = self.currency.text().strip() or "Rs."
        settings.confirm_before_print = self.confirm_print.isChecked()
        settings.calibration_marks_on_cheque = self.allow_cheque_marks.isChecked()
        settings.calibration_complete = self.calibration_complete.isChecked()
        for key, controls in self._field_controls.items():
            target = settings.fields[key]
            target.x_mm = controls["x"].value()
            target.y_mm = controls["y"].value()
            target.font_size_pt = controls["size"].value()
            target.font_family = controls["font"].currentText().strip() or "Arial"
            target.alignment = controls["alignment"].currentText()
            target.max_chars = controls["max_chars"].value()
            target.second_line = controls["second_line"].isChecked()
