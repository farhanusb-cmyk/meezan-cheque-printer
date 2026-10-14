"""Shared cheque layout, calibration output, and printer submission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
from typing import Any

from reportlab.lib.colors import black, grey
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .settings import AppSettings, FieldTemplate

MM_TO_PT = 72.0 / 25.4
FIELD_ORDER = ("date", "payee", "amount_words", "amount")


def mm_to_points(value: float) -> float:
    return value * MM_TO_PT


def paper_size(settings: AppSettings) -> tuple[float, float]:
    if settings.width_mm is None or settings.height_mm is None:
        raise ValueError("Measure and enter the cheque width and height before previewing or printing.")
    if not (80 <= settings.width_mm <= 350 and 40 <= settings.height_mm <= 250):
        raise ValueError("Cheque dimensions are outside the supported safe range.")
    if settings.orientation not in {"Landscape", "Portrait"}:
        raise ValueError("Select Landscape or Portrait orientation.")
    width, height = settings.width_mm, settings.height_mm
    if settings.orientation == "Landscape" and width < height:
        raise ValueError("For landscape orientation, enter the long edge as width.")
    if settings.orientation == "Portrait" and width > height:
        raise ValueError("For portrait orientation, enter the short edge as width.")
    return width, height


def _pdf_font_name(family: str) -> str:
    names = {
        "Arial": ("Arial", "arial.ttf"),
        "Helvetica": ("Helvetica", "arial.ttf"),
        "Times New Roman": ("TimesNewRoman", "times.ttf"),
        "Courier New": ("CourierNew", "cour.ttf"),
    }
    registered, filename = names.get(family, names["Arial"])
    if registered in pdfmetrics.getRegisteredFontNames():
        return registered
    font_path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / filename
    if font_path.is_file():
        pdfmetrics.registerFont(TTFont(registered, str(font_path)))
        return registered
    return {"Arial": "Helvetica", "TimesNewRoman": "Times-Roman", "CourierNew": "Courier"}.get(
        registered, "Helvetica"
    )


def _split_lines(text: str, template: FieldTemplate, key: str) -> tuple[str, ...]:
    if len(text) <= template.max_chars:
        return (text,)
    if not template.second_line:
        raise ValueError(
            f"The {key.replace('_', ' ')} is longer than its configured limit. "
            "Adjust the text or allow a second line in template settings."
        )
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= template.max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(current) > template.max_chars:
                raise ValueError(f"A word in {key.replace('_', ' ')} exceeds the configured line length.")
    if current:
        lines.append(current)
    if len(lines) > 2:
        raise ValueError(
            f"The {key.replace('_', ' ')} needs more than two lines. Shorten it or increase "
            "the configured maximum characters."
        )
    return tuple(lines)


@dataclass(frozen=True)
class PositionedField:
    key: str
    text: str
    x_pt: float
    y_pt: float
    font_family: str
    font_size_pt: float
    alignment: str
    second_line: bool
    lines: tuple[str, ...]


def make_layout(record: dict[str, Any], settings: AppSettings) -> tuple[float, float, list[PositionedField]]:
    width_mm, height_mm = paper_size(settings)
    width_pt, height_pt = mm_to_points(width_mm), mm_to_points(height_mm)
    parsed_date = datetime.strptime(record["cheque_date"], "%Y-%m-%d")
    date_format = settings.date_format
    for source, target in (("yyyy", "%Y"), ("MM", "%m"), ("dd", "%d")):
        date_format = date_format.replace(source, target)
    values = {
        "date": parsed_date.strftime(date_format),
        "payee": record["payee"],
        "amount_words": record["amount_words"],
        "amount": f"{settings.currency_symbol} {record['amount']}",
    }
    fields: list[PositionedField] = []
    for key in FIELD_ORDER:
        template: FieldTemplate = settings.fields[key]
        x_pt = mm_to_points(template.x_mm)
        y_pt = height_pt - mm_to_points(template.y_mm)
        if not (0 <= template.x_mm <= width_mm and 0 <= template.y_mm <= height_mm):
            raise ValueError(f"The {key.replace('_', ' ')} field position is outside the cheque.")
        if not (6 <= template.font_size_pt <= 36):
            raise ValueError(f"The {key.replace('_', ' ')} font size must be between 6 and 36 points.")
        lines = _split_lines(str(values[key]), template, key)
        font_name = _pdf_font_name(template.font_family)
        max_width = (
            width_pt - x_pt if template.alignment == "left"
            else x_pt if template.alignment == "right"
            else 2 * min(x_pt, width_pt - x_pt)
        )
        if any(stringWidth(line, font_name, template.font_size_pt) > max_width for line in lines):
            raise ValueError(
                f"The {key.replace('_', ' ')} does not fit between its position and the paper edge."
            )
        ascent = pdfmetrics.getAscent(font_name, template.font_size_pt)
        descent = pdfmetrics.getDescent(font_name, template.font_size_pt)
        first_baseline_from_top = mm_to_points(template.y_mm)
        last_baseline_from_top = (
            first_baseline_from_top + (len(lines) - 1) * template.font_size_pt * 1.2
        )
        if first_baseline_from_top < ascent or height_pt - last_baseline_from_top < -descent:
            raise ValueError(
                f"The {key.replace('_', ' ')} text does not fit vertically on the cheque."
            )
        fields.append(PositionedField(
            key, str(values[key]), x_pt, y_pt,
            template.font_family, template.font_size_pt,
            template.alignment, template.second_line, lines,
        ))
    return width_pt, height_pt, fields


def _draw_text(target: Any, field: PositionedField) -> None:
    target.setFont(_pdf_font_name(field.font_family), field.font_size_pt)
    for index, line in enumerate(field.lines):
        y = field.y_pt - index * field.font_size_pt * 1.2
        if field.alignment == "right":
            target.drawRightString(field.x_pt, y, line)
        elif field.alignment == "center":
            target.drawCentredString(field.x_pt, y, line)
        else:
            target.drawString(field.x_pt, y, line)


def generate_pdf(record: dict[str, Any], settings: AppSettings, destination: Path) -> Path:
    width, height, fields = make_layout(record, settings)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(destination), pagesize=(width, height), pageCompression=1)
    pdf.setFillColor(black)
    for field in fields:
        _draw_text(pdf, field)
    pdf.save()
    return destination


def generate_calibration_pdf(
    settings: AppSettings,
    destination: Path,
    a4: bool = True,
    on_cheque: bool = False,
) -> Path:
    """Generate a labelled pattern; cheque marks require an explicit opt-in."""
    width, height = paper_size(settings) if on_cheque else A4
    if on_cheque and not settings.calibration_marks_on_cheque:
        raise ValueError("Enable calibration marks on a cheque in Settings before using this option.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(destination), pagesize=(width, height))
    pdf.setStrokeColor(grey)
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(20, height - 20, "CALIBRATION ONLY - NOT A CHEQUE")
    pdf.rect(18, 18, width - 36, height - 36)
    pdf.line(width / 2, 18, width / 2, height - 18)
    pdf.line(18, height / 2, width - 18, height / 2)
    for key in FIELD_ORDER:
        item = settings.fields[key]
        x = mm_to_points(item.x_mm) if on_cheque else 36 + (FIELD_ORDER.index(key) * 24)
        y = height - mm_to_points(item.y_mm) if on_cheque else height - 80 - FIELD_ORDER.index(key) * 60
        pdf.circle(x, y, 2.5, stroke=1, fill=0)
        pdf.drawString(x + 5, y + 3, f"{key} X={item.x_mm:.1f} Y={item.y_mm:.1f} mm")
    pdf.save()
    return destination


def preview_lines(record: dict[str, Any], settings: AppSettings) -> tuple[float, float, list[PositionedField]]:
    return make_layout(record, settings)


def fit_text(text: str, max_width_pt: float, font: str, size: float) -> str:
    """Shorten preview/print text to its available width without clipping."""
    if stringWidth(text, font, size) <= max_width_pt:
        return text
    suffix = "..."
    result = text
    while result and stringWidth(result + suffix, font, size) > max_width_pt:
        result = result[:-1]
    return result + suffix if result else suffix


def installed_printers() -> list[str]:
    from PySide6.QtPrintSupport import QPrinterInfo
    return [printer.printerName() for printer in QPrinterInfo.availablePrinters()]
