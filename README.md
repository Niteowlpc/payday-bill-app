\# Payday Bill App



A desktop payday bill tracker built with Python + CustomTkinter.



\## Features



\- Payday date and paycheck amount tracking.

\- Alternating biweekly cycle (Paycheck Cycle 1 / 2).

\- Bill templates with default amounts, notes, and optional links.

\- Per-payday bill list with include checkboxes and editable amounts.

\- Bill notes are shown inline under each bill name (no popup click needed).

\- URL button only appears for bills that have a payment URL.

\- Bill setup/editing lives on a dedicated \*\*Bills\*\* tab.

\- Remaining balance summary.

\- \*\*Free Check Review\*\* flow that:

&#x20; - walks all bills,

&#x20; - asks whether each bill can wait,

&#x20; - adds selected bills to the free-check payday,

&#x20; - flips future cycle parity for subsequent paydays.

\- Next free-check indicator (defaults to payday #13 and #24 each year).

\- Read-only \*\*Spreadsheet Simulation View\*\* to visualize upcoming payday columns with cycle colors and free-check highlights.

\- Spreadsheet view always starts at the first payday of the selected year and shows the full year.

\- Due cells in spreadsheet view show bill amounts (color + amount).

\- Spreadsheet view includes per-payday \*\*Total Bills\*\* and \*\*Money Left\*\* rows.

\- Quick payday jump buttons (two previous, current, and two next paydays) to avoid manual date typing.

\- Local JSON persistence.



\## Run (global Python install)



```bash

pip install -r requirements.txt

python app.py

```



App data is stored in `payday\_data.json` next to `app.py`.



