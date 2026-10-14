from pathlib import Path

from app.database import Database
from app.settings import AppSettings


def test_draft_search_duplicate_and_protected_submitted_records(tmp_path: Path):
    database = Database(tmp_path / "records.sqlite3")
    record_id = database.save_draft(
        "2026-10-14", "Example Payee", "1000.00",
        "One Thousand Rupees Only", "INV-1", "Private note",
    )
    assert database.search_cheques("Example")[0]["id"] == record_id
    duplicate_id = database.duplicate_as_draft(record_id)
    assert duplicate_id != record_id
    database.set_print_status(record_id, "Submitted")
    try:
        database.save_draft(
            "2026-10-14", "Edited", "1.00", "One Rupee Only",
            cheque_id=record_id,
        )
    except ValueError as error:
        assert "cannot be edited" in str(error)
    else:
        raise AssertionError("Submitted history must be read-only.")


def test_settings_persist_and_backup_restore(tmp_path: Path):
    path = tmp_path / "records.sqlite3"
    database = Database(path)
    settings = AppSettings(width_mm=200, height_mm=90, calibration_complete=True)
    settings.save(database)
    assert AppSettings.load(database).calibration_complete
    backup = tmp_path / "backup.sqlite3"
    database.backup_to(backup)
    database.set_setting("test", "modified")
    database.restore_from(backup)
    assert database.get_setting("test") is None
    assert AppSettings.load(database).width_mm == 200
