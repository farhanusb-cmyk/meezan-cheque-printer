from app.printer_service import make_layout, mm_to_points, paper_size
from app.settings import AppSettings


def test_mm_to_points_and_baselines_use_measured_top_left_coordinates():
    assert round(mm_to_points(25.4), 4) == 72.0
    settings = AppSettings(width_mm=200, height_mm=90)
    for field in settings.fields.values():
        field.x_mm = 10
        field.y_mm = 12
    settings.fields["amount"].x_mm = 190
    settings.fields["date"].x_mm = 10
    settings.fields["date"].y_mm = 12
    record = {
        "cheque_date": "2026-10-14",
        "payee": "Payee",
        "amount_words": "One Rupee Only",
        "amount": "1.00",
    }
    _, height_pt, fields = make_layout(record, settings)
    date = next(field for field in fields if field.key == "date")
    assert round(date.x_pt, 4) == round(mm_to_points(10), 4)
    assert round(height_pt - date.y_pt, 4) == round(mm_to_points(12), 4)


def test_cheque_dimensions_must_be_measured_and_orientation_consistent():
    settings = AppSettings()
    try:
        paper_size(settings)
    except ValueError as error:
        assert "Measure" in str(error)
    else:
        raise AssertionError("Unmeasured cheque dimensions must not be accepted.")
    settings.width_mm, settings.height_mm = 90, 200
    try:
        paper_size(settings)
    except ValueError as error:
        assert "long edge" in str(error)
    else:
        raise AssertionError("Landscape dimensions must match the selected orientation.")


def test_long_text_requires_explicit_second_line():
    settings = AppSettings(width_mm=200, height_mm=90)
    for field in settings.fields.values():
        field.x_mm = 10
        field.y_mm = 12
    settings.fields["amount"].x_mm = 190
    settings.fields["payee"].max_chars = 8
    settings.fields["payee"].second_line = False
    record = {
        "cheque_date": "2026-10-14",
        "payee": "A long payee name",
        "amount_words": "One Rupee Only",
        "amount": "1.00",
    }
    try:
        make_layout(record, settings)
    except ValueError as error:
        assert "second line" in str(error)
    else:
        raise AssertionError("Long field must not be silently clipped.")


def test_text_baseline_must_keep_glyphs_inside_cheque():
    settings = AppSettings(width_mm=200, height_mm=90)
    for field in settings.fields.values():
        field.x_mm = 10
        field.y_mm = 12
    settings.fields["amount"].x_mm = 190
    settings.fields["date"].y_mm = 0
    record = {
        "cheque_date": "2026-10-14",
        "payee": "Payee",
        "amount_words": "One Rupee Only",
        "amount": "1.00",
    }
    try:
        make_layout(record, settings)
    except ValueError as error:
        assert "does not fit vertically" in str(error)
    else:
        raise AssertionError("Text must not be positioned beyond the paper edge.")
