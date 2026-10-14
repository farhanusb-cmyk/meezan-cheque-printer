from pathlib import Path

from app.printer_service import generate_pdf
from app.settings import AppSettings


def test_overlay_pdf_generates_without_physical_printer(tmp_path: Path):
    settings = AppSettings(width_mm=200, height_mm=90)
    for field in settings.fields.values():
        field.x_mm = 10
        field.y_mm = 12
    settings.fields["amount"].x_mm = 190
    record = {
        "cheque_date": "2026-10-14",
        "payee": "Payee",
        "amount_words": "One Thousand Rupees Only",
        "amount": "1000.00",
    }
    output = generate_pdf(record, settings, tmp_path / "overlay.pdf")
    assert output.is_file()
    assert output.read_bytes().startswith(b"%PDF-")
