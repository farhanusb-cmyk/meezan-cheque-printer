# Meezan Cheque Printer

**Developed by Farhan Sami — IT Network and System Engineer**

**Software categories:** Finance & Accounting · Cheque Printing · Windows Desktop Productivity

A local Windows desktop application for preparing cheque overlays, calibrating positions against a blank cheque, saving drafts, and submitting print jobs. It does not draw the bank's background, logo, cheque number, account number, MICR line, or other pre-printed content. Cheque details remain in a local SQLite database; the app has no telemetry, cloud sync, or network API calls.

The application opens with a custom branded launch screen and shows the developer credit in the main window and About dialog. It is an independent utility and is not affiliated with Meezan Bank.

## Important safety notes

- This software does not verify that a cheque physically printed. It only reports when Windows accepted a print submission.
- Never automatically retry an uncertain cheque print. Check the physical output first.
- Do not print a real cheque until you have measured and calibrated a blank cheque using ordinary paper.
- The cheque database contains sensitive financial information. Protect your Windows account and secure backups.
- The cheque dimensions, orientation, field positions, and P1102 feed behavior are not assumed by the application.

## Requirements

- Windows 10/11
- Python 3.12 or newer
- A supported installed Windows printer driver. The HP LaserJet Pro P1102 driver is not bundled and must be installed separately by the user.

Runtime dependencies are in `requirements.txt`; development/test/build tools are in `requirements-dev.txt`.

## Install and run

In PowerShell, open this project folder and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python main.py
```

If script execution is restricted, use the venv interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

The database is created in `%LOCALAPPDATA%\MeezanChequePrinter\cheques.sqlite3`. No real cheque details should be placed in a shared or cloud-synced folder.

## Calibrate an actual cheque

1. In **Settings**, select the installed printer and measure the blank cheque in millimetres. Enter its physical width, height, and orientation. Do not use example dimensions from another cheque.
2. Enter each field's X coordinate from the left edge and Y coordinate from the top edge to the text baseline. Adjust font, size, alignment, maximum characters, and whether the field may use a second line.
3. Select **Print Test Page** and print the calibration pattern on ordinary A4 paper. Place the blank cheque over the output to compare the positions. Do not feed the cheque itself during calibration.
4. Adjust the field positions with the fine adjustment controls, print another A4 sheet, and compare again.
5. Once the measured positions look correct, return to template settings and enable **Calibration confirmed against a blank cheque using ordinary paper**.
6. Review **Preview** and verify the printer driver paper-size and orientation options. Print a real cheque only after confirming the selected printer and feed method.

The preview is a layout guide. Actual print alignment varies with the printer, driver, paper feed, and printable area. The app does not scale the cheque to fit a different page size; unsupported custom media sizes may be rejected or altered by a driver.

## HP LaserJet Pro P1102 setup and feed checks

- Install the correct HP driver and confirm the P1102 appears in **Settings → Printer and cheque template settings**.
- Confirm the driver accepts the measured custom paper size. If it does not, do not try to force the cheque through an unrelated page size.
- Use ordinary A4 for the calibration pattern. Keep paper guides snug; avoid curled, damp, stapled, or damaged stock.
- Verify orientation and disable driver options such as **Fit to page**, **Scale to fit**, or **Shrink oversized pages**.
- Check the HP manual for the supported media types, dimensions, and feed path. Test feed behavior with sacrificial paper before using a real cheque.
- If the printer status or physical output is uncertain, inspect both the printer and cheque before deciding whether to retry.

## Features

- Cheque date, payee, amount, automatically generated words, optional printed memo, and private internal remarks.
- Numeric amount and words share one conversion path; amounts must be non-negative and have no more than two decimal places.
- Local draft database, history search, date filters, duplicate-as-draft, read-only submitted/uncertain records, CSV export, and audit entries for draft/print status.
- Printer selection, measured custom page size, alignment preview, overlay PDF export, A4 test page, print confirmation, and a no-automatic-retry policy.
- Local database backup/restore with backup integrity checking and a pre-restore backup.
- Optional application password stored as a salted PBKDF2-HMAC-SHA256 verifier.

## Tests

Run:

```powershell
python -m pytest -q
```

Tests cover number conversion, decimal validation, dates and form validation, template coordinate conversion, settings persistence, database operations, and PDF layout generation without a physical printer. Automated tests never submit print jobs.

## Build a standalone executable

After installing `requirements-dev.txt`, run:

```powershell
python -m PyInstaller --noconfirm --clean --windowed --name MeezanChequePrinter `
  --collect-all PySide6 --collect-all reportlab main.py
```

The executable is written under `dist\MeezanChequePrinter`. Review the generated application on a clean Windows machine and install the target printer driver separately. The application database is still stored under the current user's `%LOCALAPPDATA%`.

## Limitations

- No Meezan cheque dimensions or field positions are supplied. They must be measured on the actual cheque stock.
- Printer queue acceptance is not physical print confirmation.
- Windows printer drivers differ; a custom cheque page size or feed path may not be supported by the P1102 or another printer.
- A password on the app is an additional local access check, not encryption of the SQLite database. Use Windows account protection and full-disk encryption.
- A print error after a job starts is recorded as **Uncertain**; verify the paper before taking further action.
