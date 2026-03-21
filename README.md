# \# Payday Bill App

# 

# A desktop payday bill tracker built with Python + CustomTkinter.

# 

# \## Features

# 

# \- Payday date and paycheck amount tracking.

# \- Alternating biweekly cycle (Paycheck Cycle 1 / 2).

# \- Bill templates with default amounts, notes, and optional links.

# \- Per-payday bill list with include checkboxes and editable amounts.

# \- Remaining balance summary.

# \- Per-bill \*\*Push Forward\*\* behavior with two options:

# &#x20; - Cascade next payday bills forward.

# &#x20; - Add only the selected bill to next payday.

# \- \*\*Free Check Review\*\* flow that:

# &#x20; - walks all bills,

# &#x20; - asks whether each bill can wait,

# &#x20; - adds selected bills to the free-check payday,

# &#x20; - flips future cycle parity for subsequent paydays.

# \- Next free-check indicator (defaults to payday #13 and #24 each year).

# \- Read-only \*\*Spreadsheet Simulation View\*\* to visualize upcoming payday columns with cycle colors and free-check highlights.

# \- Local JSON persistence.

# 

# \## Run (global Python install)

# 

# ```bash

# pip install -r requirements.txt

# python app.py

# ```

# 

# App data is stored in `payday\_data.json` next to `app.py`.

# 

