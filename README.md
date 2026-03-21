# Payday Bill App

A desktop payday bill tracker built with Python + CustomTkinter.

## Features

- Payday date and paycheck amount tracking.
- Alternating biweekly cycle (Paycheck 1 / Paycheck 2).
- Bill templates with default amounts, notes, and optional links.
- Per-payday bill list with include checkboxes and editable amounts.
- Remaining balance summary.
- Per-bill **Push Forward** behavior with two options:
  - Cascade next payday bills forward.
  - Add only the selected bill to next payday.
- Local JSON persistence.

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

App data is stored in `payday_data.json` next to `app.py`.
