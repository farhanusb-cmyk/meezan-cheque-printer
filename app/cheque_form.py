"""Cheque entry form widgets."""

from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from .amount_words import AmountError, amount_to_words
from .validation import MAX_MEMO_LENGTH, MAX_PAYEE_LENGTH, MAX_REMARKS_LENGTH


class ChequeForm(QWidget):
    amount_words_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox("Cheque details")
        form = QFormLayout(group)

        self.cheque_date = QDateEdit()
        self.cheque_date.setCalendarPopup(True)
        self.cheque_date.setDisplayFormat("dd/MM/yyyy")
        self.cheque_date.setDate(QDate.currentDate())
        form.addRow("Cheque date", self.cheque_date)

        self.payee = QLineEdit()
        self.payee.setPlaceholderText("Name exactly as it should appear")
        form.addRow("Pay to", self.payee)

        self.amount = QLineEdit()
        self.amount.setPlaceholderText("e.g. 25000.00")
        self.amount.textChanged.connect(self._update_amount_words)
        form.addRow("Amount (rupees)", self.amount)

        self.amount_words = QLabel("Enter an amount to generate words.")
        self.amount_words.setWordWrap(True)
        self.amount_words.setTextInteractionFlags(self.amount_words.textInteractionFlags())
        form.addRow("Amount in words", self.amount_words)

        self.memo = QLineEdit()
        self.memo.setPlaceholderText("Optional; printed on the cheque")
        form.addRow("Memo / reference", self.memo)

        self.remarks = QPlainTextEdit()
        self.remarks.setPlaceholderText("Internal only; never printed")
        self.remarks.setMaximumHeight(90)
        form.addRow("Internal remarks", self.remarks)

        layout.addWidget(group)
        note = QLabel(
            "The amount in words is generated from the numeric amount and cannot be edited "
            "independently. Internal remarks are stored locally and never printed."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        self._amount_words_value = ""

    def _update_amount_words(self, text: str) -> None:
        try:
            words = amount_to_words(text)
        except AmountError:
            words = ""
        self._amount_words_value = words
        self.amount_words.setText(words or "Enter a valid non-negative amount.")
        self.amount_words_changed.emit(words)

    def values(self) -> dict[str, str]:
        return {
            "cheque_date": self.cheque_date.date().toString("yyyy-MM-dd"),
            "payee": self.payee.text(),
            "amount": self.amount.text(),
            "amount_words": self._amount_words_value,
            "memo": self.memo.text(),
            "internal_remarks": self.remarks.toPlainText(),
        }

    def set_values(self, record: dict) -> None:
        qdate = QDate.fromString(record["cheque_date"], "yyyy-MM-dd")
        self.cheque_date.setDate(qdate if qdate.isValid() else QDate.currentDate())
        self.payee.setText(record["payee"])
        self.amount.setText(record["amount"])
        self.memo.setText(record.get("memo", ""))
        self.remarks.setPlainText(record.get("internal_remarks", ""))

    def clear(self) -> None:
        self.cheque_date.setDate(QDate.currentDate())
        self.payee.clear()
        self.amount.clear()
        self.memo.clear()
        self.remarks.clear()
