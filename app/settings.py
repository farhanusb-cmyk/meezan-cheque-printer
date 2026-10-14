"""Persistent printer, template, and security preferences."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .database import Database


@dataclass
class FieldTemplate:
    x_mm: float = 0.0
    y_mm: float = 0.0
    font_family: str = "Arial"
    font_size_pt: float = 11.0
    alignment: str = "left"
    max_chars: int = 120
    second_line: bool = False


@dataclass
class AppSettings:
    default_printer: str = ""
    width_mm: float | None = None
    height_mm: float | None = None
    orientation: str = "Landscape"
    calibration_complete: bool = False
    date_format: str = "dd/MM/yyyy"
    currency_symbol: str = "Rs."
    confirm_before_print: bool = True
    calibration_marks_on_cheque: bool = False
    app_password_salt: str = ""
    app_password_hash: str = ""
    fields: dict[str, FieldTemplate] = field(default_factory=lambda: {
        "date": FieldTemplate(max_chars=10),
        "payee": FieldTemplate(max_chars=120, second_line=True),
        "amount_words": FieldTemplate(max_chars=120, second_line=True),
        "amount": FieldTemplate(max_chars=18, alignment="right"),
    })

    @classmethod
    def load(cls, database: Database) -> "AppSettings":
        raw = database.get_setting("app_settings")
        if not raw:
            return cls()
        try:
            data = json.loads(raw)
            fields = {
                name: FieldTemplate(**values)
                for name, values in data.pop("fields", {}).items()
                if name in {"date", "payee", "amount_words", "amount"}
            }
            loaded = cls(**data)
            loaded.fields.update(fields)
            return loaded
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("Saved settings are invalid. Use Settings to reset them.") from error

    def save(self, database: Database) -> None:
        database.set_setting("app_settings", json.dumps(asdict(self), ensure_ascii=True))
