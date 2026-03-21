# Payday Bill App

A desktop payday bill tracker built with Python + CustomTkinter.

## Features

- Payday date and paycheck amount tracking.
- Alternating biweekly cycle (Paycheck Cycle 1 / 2).
- Bill templates with default amounts, notes, and optional links.
- Per-payday bill list with include checkboxes and editable amounts.
- Remaining balance summary.
- Per-bill **Push Forward** behavior with two options:
  - Cascade next payday bills forward.
  - Add only the selected bill to next payday.
- **Free Check Review** flow that:
  - walks all bills,
  - asks whether each bill can wait,
  - adds selected bills to the free-check payday,
  - flips future cycle parity for subsequent paydays.
- Next free-check indicator (defaults to payday #13 and #24 each year).
- Local JSON persistence.

## Run (global Python install)

```bash
pip install -r requirements.txt
python app.py
```

App data is stored in `payday_data.json` next to `app.py`.
