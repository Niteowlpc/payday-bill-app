from __future__ import annotations

import json
import uuid
import webbrowser
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from tkinter import ttk


DATA_FILE = Path(__file__).with_name("payday_data.json")
DATE_FMT = "%m/%d/%Y"
DEFAULT_FREE_CHECK_NUMBERS = [13, 24]


@dataclass
class BillRowWidgets:
    frame: ctk.CTkFrame
    include_var: tk.BooleanVar
    amount_var: tk.StringVar


class PaydayBillApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Payday Bill App")
        self.root.geometry("1260x780")

        self.data = self._load_data()
        self.bill_row_widgets: list[BillRowWidgets] = []
        self.selected_template_id: str | None = None

        self._build_ui()
        self._load_initial_state()

    # -------------------- Data layer --------------------
    def _default_data(self) -> dict:
        return {
            "anchor_date": None,
            "current_date": None,
            "templates": [],
            "sessions": {},
            "free_check_numbers": DEFAULT_FREE_CHECK_NUMBERS,
            "free_check_flips": [],
        }

    def _load_data(self) -> dict:
        if DATA_FILE.exists():
            try:
                with DATA_FILE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                merged = {**self._default_data(), **data}
                if not merged.get("free_check_numbers"):
                    merged["free_check_numbers"] = DEFAULT_FREE_CHECK_NUMBERS
                return merged
            except (json.JSONDecodeError, OSError):
                messagebox.showwarning(
                    "Data warning",
                    "Could not read payday_data.json. Starting with empty data.",
                )
        return self._default_data()

    def _save_data(self) -> None:
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def _parse_date(self, value: str) -> date:
        return datetime.strptime(value.strip(), DATE_FMT).date()

    def _fmt_date(self, d: date) -> str:
        return d.strftime(DATE_FMT)

    def _parse_money(self, value: str) -> Decimal:
        normalized = value.strip().replace("$", "")
        return Decimal(normalized)

    def _money_str(self, value: Decimal | float | str) -> str:
        return f"{Decimal(str(value)):.2f}"

    def _next_payday_str(self, payday_str: str) -> str:
        d = self._parse_date(payday_str)
        return self._fmt_date(d + timedelta(days=14))

    def _flip_dates(self) -> list[date]:
        return sorted(self._parse_date(d) for d in self.data.get("free_check_flips", []))

    def _base_slot_from_anchor(self, payday_date: date) -> int:
        anchor = self.data.get("anchor_date")
        if not anchor:
            self.data["anchor_date"] = self._fmt_date(payday_date)
            self._save_data()
            return 1

        anchor_date = self._parse_date(anchor)
        delta = (payday_date - anchor_date).days
        if delta % 14 != 0:
            raise ValueError("Payday must be exactly every 14 days from the anchor date.")
        index = delta // 14
        return 1 if index % 2 == 0 else 2

    def _slot_for_date(self, payday_date: date, pending_flip_date: date | None = None) -> int:
        base = self._base_slot_from_anchor(payday_date)
        flip_count = sum(1 for d in self._flip_dates() if d < payday_date)
        if pending_flip_date and pending_flip_date < payday_date:
            flip_count += 1
        if flip_count % 2 == 1:
            return 2 if base == 1 else 1
        return base

    def _cycle_slot(self, payday_str: str) -> int:
        payday_date = self._parse_date(payday_str)
        return self._slot_for_date(payday_date)

    def _payday_index(self, payday_date: date) -> int:
        anchor = self.data.get("anchor_date")
        if not anchor:
            self.data["anchor_date"] = self._fmt_date(payday_date)
            self._save_data()
            return 1

        anchor_date = self._parse_date(anchor)
        delta = (payday_date - anchor_date).days
        if delta % 14 != 0:
            raise ValueError("Payday must be exactly every 14 days from the anchor date.")
        return (delta // 14) + 1

    def _payday_number_in_year(self, payday_date: date) -> int:
        first = payday_date
        while (first - timedelta(days=14)).year == payday_date.year:
            first -= timedelta(days=14)
        return ((payday_date - first).days // 14) + 1

    def _next_free_check_date(self, from_date: date) -> tuple[date | None, int | None]:
        targets = set(int(x) for x in self.data.get("free_check_numbers", DEFAULT_FREE_CHECK_NUMBERS))
        if not targets:
            return None, None

        probe = from_date
        for _ in range(80):
            number = self._payday_number_in_year(probe)
            if number in targets and probe >= from_date:
                return probe, number
            probe += timedelta(days=14)
        return None, None

    def _templates_for_slot(self, slot: int) -> list[dict]:
        return [t for t in self.data["templates"] if t.get("active", True) and int(t["slot"]) == slot]

    def _new_session_for_date(self, payday_str: str) -> dict:
        slot = self._cycle_slot(payday_str)
        bills = []
        for tpl in self._templates_for_slot(slot):
            bills.append(
                {
                    "template_id": tpl["id"],
                    "name": tpl["name"],
                    "amount": self._money_str(tpl["default_amount"]),
                    "included": True,
                    "notes": tpl.get("notes", ""),
                    "url": tpl.get("url", ""),
                    "slot": int(tpl["slot"]),
                    "pushed_from": None,
                }
            )
        return {
            "paycheck_amount": "0.00",
            "bills": bills,
        }

    def _ensure_session(self, payday_str: str) -> dict:
        sessions = self.data["sessions"]
        if payday_str not in sessions:
            sessions[payday_str] = self._new_session_for_date(payday_str)
            self._save_data()
        return sessions[payday_str]

    # -------------------- UI --------------------
    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_rowconfigure(1, weight=1)

        self.top_frame = ctk.CTkFrame(self.root)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=14, pady=14)
        self.top_frame.grid_columnconfigure(11, weight=1)

        ctk.CTkLabel(self.top_frame, text="Payday Date (MM/DD/YYYY)").grid(row=0, column=0, padx=6, pady=8)
        self.payday_var = tk.StringVar()
        self.payday_entry = ctk.CTkEntry(self.top_frame, textvariable=self.payday_var, width=130)
        self.payday_entry.grid(row=0, column=1, padx=6, pady=8)

        ctk.CTkButton(self.top_frame, text="Load Payday", command=self.load_payday).grid(
            row=0, column=2, padx=6, pady=8
        )

        ctk.CTkLabel(self.top_frame, text="Paycheck Amount").grid(row=0, column=3, padx=6, pady=8)
        self.paycheck_var = tk.StringVar(value="0.00")
        self.paycheck_entry = ctk.CTkEntry(self.top_frame, textvariable=self.paycheck_var, width=120)
        self.paycheck_entry.grid(row=0, column=4, padx=6, pady=8)
        self.paycheck_entry.bind("<FocusOut>", lambda _e: self._on_paycheck_changed())

        ctk.CTkButton(self.top_frame, text="Save Payday", command=self.save_current_session).grid(
            row=0, column=5, padx=6, pady=8
        )

        ctk.CTkButton(
            self.top_frame,
            text="Start Free Check Review",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=self.start_free_check_review,
        ).grid(row=0, column=6, padx=6, pady=8)

        ctk.CTkButton(
            self.top_frame,
            text="Spreadsheet View",
            fg_color="#455A64",
            hover_color="#37474F",
            command=self.show_spreadsheet_view,
        ).grid(row=0, column=7, padx=6, pady=8)

        self.next_payday_label = ctk.CTkLabel(self.top_frame, text="Next payday: --")
        self.next_payday_label.grid(row=0, column=8, padx=6, pady=8)

        self.slot_label = ctk.CTkLabel(self.top_frame, text="Slot: --")
        self.slot_label.grid(row=0, column=9, padx=6, pady=8)

        self.next_free_check_label = ctk.CTkLabel(self.top_frame, text="Next free check: --")
        self.next_free_check_label.grid(row=0, column=10, padx=6, pady=8)

        # Bills area
        self.left_frame = ctk.CTkFrame(self.root)
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=(14, 7), pady=(0, 8))
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_frame, text="Bills for this payday", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )

        self.bill_scroll = ctk.CTkScrollableFrame(self.left_frame)
        self.bill_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        self.bill_scroll.grid_columnconfigure(2, weight=1)

        self.summary_frame = ctk.CTkFrame(self.left_frame)
        self.summary_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(4, 10))
        self.summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.total_bills_label = ctk.CTkLabel(self.summary_frame, text="Selected Bills Total: $0.00")
        self.total_bills_label.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        self.remaining_label = ctk.CTkLabel(self.summary_frame, text="Remaining: $0.00")
        self.remaining_label.grid(row=0, column=1, padx=8, pady=8, sticky="w")

        ctk.CTkButton(self.summary_frame, text="Recalculate", command=self.recalculate_summary).grid(
            row=0, column=2, padx=8, pady=8, sticky="e"
        )

        # Template management
        self.right_frame = ctk.CTkFrame(self.root)
        self.right_frame.grid(row=1, column=1, sticky="nsew", padx=(7, 14), pady=(0, 8))
        self.right_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.right_frame, text="Bill Templates", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 6)
        )

        self.template_menu = ctk.CTkOptionMenu(self.right_frame, values=["(none)"], command=self._on_template_select)
        self.template_menu.grid(row=1, column=0, sticky="ew", padx=10, pady=6)

        form = ctk.CTkFrame(self.right_frame)
        form.grid(row=2, column=0, sticky="ew", padx=10, pady=6)
        form.grid_columnconfigure(1, weight=1)

        labels = ["Name", "Default Amount", "Paycheck Cycle (1/2)", "Notes", "URL"]
        for i, label in enumerate(labels):
            ctk.CTkLabel(form, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=6)

        self.tpl_name_var = tk.StringVar()
        self.tpl_amount_var = tk.StringVar(value="0.00")
        self.tpl_slot_var = tk.StringVar(value="1")
        self.tpl_notes_var = tk.StringVar()
        self.tpl_url_var = tk.StringVar()

        ctk.CTkEntry(form, textvariable=self.tpl_name_var).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ctk.CTkEntry(form, textvariable=self.tpl_amount_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ctk.CTkOptionMenu(form, variable=self.tpl_slot_var, values=["1", "2"]).grid(
            row=2, column=1, sticky="ew", padx=8, pady=6
        )
        ctk.CTkEntry(form, textvariable=self.tpl_notes_var).grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ctk.CTkEntry(form, textvariable=self.tpl_url_var).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

        button_row = ctk.CTkFrame(self.right_frame)
        button_row.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
        button_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(button_row, text="New", command=self.new_template).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(button_row, text="Save", command=self.save_template).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(button_row, text="Delete", fg_color="#8B1E3F", hover_color="#6E1631", command=self.delete_template).grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )

    def _load_initial_state(self) -> None:
        self._refresh_template_menu()
        initial_date = self.data.get("current_date") or self.data.get("anchor_date")
        if initial_date:
            self.payday_var.set(initial_date)
            self.load_payday()

    # -------------------- Template management --------------------
    def _template_label(self, tpl: dict) -> str:
        return f"{tpl['name']} (cycle {tpl['slot']})"

    def _template_by_id(self, template_id: str) -> dict | None:
        for tpl in self.data["templates"]:
            if tpl["id"] == template_id:
                return tpl
        return None

    def _template_id_by_label(self, label: str) -> str | None:
        for tpl in self.data["templates"]:
            if self._template_label(tpl) == label:
                return tpl["id"]
        return None

    def _refresh_template_menu(self) -> None:
        templates = self.data["templates"]
        labels = [self._template_label(t) for t in templates] or ["(none)"]
        self.template_menu.configure(values=labels)
        if self.selected_template_id:
            selected = self._template_by_id(self.selected_template_id)
            if selected:
                self.template_menu.set(self._template_label(selected))
                self._load_template_to_form(selected)
                return
        self.template_menu.set(labels[0])
        if labels[0] != "(none)":
            first_tpl = templates[0]
            self.selected_template_id = first_tpl["id"]
            self._load_template_to_form(first_tpl)
        else:
            self.selected_template_id = None
            self._clear_template_form()

    def _on_template_select(self, label: str) -> None:
        template_id = self._template_id_by_label(label)
        if not template_id:
            return
        self.selected_template_id = template_id
        tpl = self._template_by_id(template_id)
        if tpl:
            self._load_template_to_form(tpl)

    def _clear_template_form(self) -> None:
        self.tpl_name_var.set("")
        self.tpl_amount_var.set("0.00")
        self.tpl_slot_var.set("1")
        self.tpl_notes_var.set("")
        self.tpl_url_var.set("")

    def _load_template_to_form(self, tpl: dict) -> None:
        self.tpl_name_var.set(tpl.get("name", ""))
        self.tpl_amount_var.set(self._money_str(tpl.get("default_amount", "0.00")))
        self.tpl_slot_var.set(str(tpl.get("slot", 1)))
        self.tpl_notes_var.set(tpl.get("notes", ""))
        self.tpl_url_var.set(tpl.get("url", ""))

    def new_template(self) -> None:
        self.selected_template_id = None
        self._clear_template_form()

    def save_template(self) -> None:
        name = self.tpl_name_var.get().strip()
        if not name:
            messagebox.showerror("Validation", "Template name is required.")
            return

        try:
            default_amount = self._money_str(self._parse_money(self.tpl_amount_var.get()))
        except (InvalidOperation, ValueError):
            messagebox.showerror("Validation", "Default amount must be a valid number.")
            return

        slot = self.tpl_slot_var.get().strip()
        if slot not in {"1", "2"}:
            messagebox.showerror("Validation", "Cycle must be 1 or 2.")
            return

        url = self.tpl_url_var.get().strip()
        if url and not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showerror("Validation", "URL must start with http:// or https://")
            return

        payload = {
            "name": name,
            "default_amount": default_amount,
            "slot": int(slot),
            "notes": self.tpl_notes_var.get().strip(),
            "url": url,
            "active": True,
        }

        if self.selected_template_id:
            tpl = self._template_by_id(self.selected_template_id)
            if tpl:
                tpl.update(payload)
        else:
            new_id = str(uuid.uuid4())
            payload["id"] = new_id
            self.data["templates"].append(payload)
            self.selected_template_id = new_id

        self._save_data()
        self._refresh_template_menu()
        self._reload_current_payday_bills()

    def delete_template(self) -> None:
        if not self.selected_template_id:
            return
        if not messagebox.askyesno("Confirm", "Delete selected bill template?"):
            return

        self.data["templates"] = [t for t in self.data["templates"] if t["id"] != self.selected_template_id]
        self.selected_template_id = None
        self._save_data()
        self._refresh_template_menu()
        self._reload_current_payday_bills()

    # -------------------- Payday/session --------------------
    def _on_paycheck_changed(self) -> None:
        current_date = self.payday_var.get().strip()
        if not current_date:
            return
        session = self._ensure_session(current_date)
        try:
            normalized = self._money_str(self._parse_money(self.paycheck_var.get()))
        except (InvalidOperation, ValueError):
            messagebox.showerror("Validation", "Paycheck amount must be numeric.")
            return

        session["paycheck_amount"] = normalized
        self.paycheck_var.set(normalized)
        self._save_data()
        self.recalculate_summary()

    def _update_top_labels(self, payday_str: str, slot: int) -> None:
        self.next_payday_label.configure(text=f"Next payday: {self._next_payday_str(payday_str)}")
        payday_date = self._parse_date(payday_str)
        payday_number = self._payday_number_in_year(payday_date)
        self.slot_label.configure(text=f"Cycle: {slot} (payday #{payday_number} this year)")

        next_free_date, next_free_number = self._next_free_check_date(payday_date)
        if next_free_date and next_free_number:
            self.next_free_check_label.configure(
                text=f"Next free check: {self._fmt_date(next_free_date)} (#{next_free_number})"
            )
        else:
            self.next_free_check_label.configure(text="Next free check: --")

    def load_payday(self) -> None:
        payday_str = self.payday_var.get().strip()
        try:
            _ = self._parse_date(payday_str)
            slot = self._cycle_slot(payday_str)
        except ValueError as exc:
            messagebox.showerror("Date error", str(exc))
            return

        session = self._ensure_session(payday_str)
        self.data["current_date"] = payday_str
        self._save_data()

        self.paycheck_var.set(self._money_str(session.get("paycheck_amount", "0.00")))
        self._update_top_labels(payday_str, slot)

        self._render_bills(session)
        self.recalculate_summary()

    def save_current_session(self) -> None:
        current_date = self.payday_var.get().strip()
        if not current_date:
            return
        self._persist_visible_bills_to_session(current_date)
        self._on_paycheck_changed()
        self._save_data()
        messagebox.showinfo("Saved", "Payday session saved.")

    def _reload_current_payday_bills(self) -> None:
        current = self.payday_var.get().strip()
        if current:
            self.load_payday()

    def _clear_future_sessions(self, from_date: date) -> None:
        to_delete = []
        for payday_str in self.data["sessions"].keys():
            payday_date = self._parse_date(payday_str)
            if payday_date > from_date:
                to_delete.append(payday_str)
        for key in to_delete:
            self.data["sessions"].pop(key, None)

    def _find_next_due_for_template_after_flip(self, tpl: dict, current_date: date) -> str:
        for i in range(1, 80):
            probe = current_date + timedelta(days=14 * i)
            slot = self._slot_for_date(probe, pending_flip_date=current_date)
            if slot == int(tpl["slot"]):
                return self._fmt_date(probe)
        return "(not found)"

    def start_free_check_review(self) -> None:
        current_str = self.payday_var.get().strip()
        if not current_str:
            messagebox.showerror("Missing date", "Load a payday first.")
            return

        current_date = self._parse_date(current_str)
        payday_number = self._payday_number_in_year(current_date)
        free_numbers = [int(x) for x in self.data.get("free_check_numbers", DEFAULT_FREE_CHECK_NUMBERS)]

        if payday_number not in free_numbers:
            proceed = messagebox.askyesno(
                "Not a configured free check",
                f"This is payday #{payday_number} this year.\n"
                f"Configured free checks are #{free_numbers}.\n\n"
                "Do you still want to run Free Check Review?",
            )
            if not proceed:
                return

        if not self.data["templates"]:
            messagebox.showinfo("No templates", "No bill templates are set up yet.")
            return

        summary_lines = [
            f"Free Check Review for {current_str}",
            "",
            "For each bill:",
            "Yes = wait until new flipped schedule",
            "No = pay from this free check (and keep future schedule)",
            "Cancel = stop review",
            "",
        ]

        session = self._ensure_session(current_str)
        pay_now_count = 0
        wait_count = 0

        existing_ids = {b.get("template_id") for b in session.get("bills", [])}

        sorted_templates = sorted(self.data["templates"], key=lambda t: t.get("name", "").lower())
        for tpl in sorted_templates:
            next_due = self._find_next_due_for_template_after_flip(tpl, current_date)
            choice = messagebox.askyesnocancel(
                "Free Check Bill Review",
                f"{tpl['name']} (cycle {tpl['slot']})\n\n"
                f"Can this wait until {next_due}?\n\n"
                "Yes = Wait\nNo = Pay now on free check\nCancel = stop",
            )
            if choice is None:
                break

            if choice is True:
                wait_count += 1
                summary_lines.append(f"WAIT: {tpl['name']} -> {next_due}")
                continue

            if tpl["id"] not in existing_ids:
                session["bills"].append(
                    {
                        "template_id": tpl["id"],
                        "name": tpl["name"],
                        "amount": self._money_str(tpl["default_amount"]),
                        "included": True,
                        "notes": tpl.get("notes", ""),
                        "url": tpl.get("url", ""),
                        "slot": int(tpl["slot"]),
                        "pushed_from": "Free Check Review",
                    }
                )
                existing_ids.add(tpl["id"])
            pay_now_count += 1
            summary_lines.append(f"PAY NOW: {tpl['name']} (future stays on schedule)")

        if current_str not in self.data.get("free_check_flips", []):
            self.data.setdefault("free_check_flips", []).append(current_str)

        self._clear_future_sessions(current_date)
        self._save_data()
        self.load_payday()

        summary_lines.extend(["", f"Wait: {wait_count}", f"Pay now: {pay_now_count}", "", "Cycle flip applied for future paydays."])
        messagebox.showinfo("Free Check Review Complete", "\n".join(summary_lines))

    def _build_payday_sequence(self, start_date: date) -> list[date]:
        paydays: list[date] = []
        probe = start_date
        while probe.year == start_date.year:
            paydays.append(probe)
            probe += timedelta(days=14)
        return paydays

    def show_spreadsheet_view(self) -> None:
        current_str = self.payday_var.get().strip()
        if not current_str:
            messagebox.showerror("Missing date", "Load a payday first.")
            return

        try:
            start_date = self._parse_date(current_str)
        except ValueError as exc:
            messagebox.showerror("Date error", str(exc))
            return

        paydays = self._build_payday_sequence(start_date)
        templates = sorted(self.data.get("templates", []), key=lambda t: t.get("name", "").lower())
        free_numbers = set(int(x) for x in self.data.get("free_check_numbers", DEFAULT_FREE_CHECK_NUMBERS))

        window = ctk.CTkToplevel(self.root)
        window.title("Spreadsheet Simulation (Read Only)")
        window.geometry("1200x700")
        window.transient(self.root)

        container = ctk.CTkFrame(window)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container, bg="#ffffff")
        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=canvas.xview)
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

        h_scroll.pack(side="bottom", fill="x")
        v_scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg="#ffffff")
        canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        inner.bind("<Configure>", _on_configure)

        row_h = 24
        col_w = 84
        name_col_w = 260
        header_bg = "#4F81BD"
        neutral_bg = "#EAF2FB"
        red_bg = "#FF0000"
        yellow_bg = "#FFF200"
        green_bg = "#548235"

        tk.Label(inner, text="Bill Name", width=30, anchor="w", bg="#D9E1F2").grid(row=0, column=0, sticky="nsew")
        for i, payday in enumerate(paydays, start=1):
            tk.Label(
                inner,
                text=f"{payday.day}-{payday.strftime('%b')}",
                bg=header_bg,
                fg="white",
                width=10,
                anchor="center",
            ).grid(row=0, column=i, sticky="nsew")

        for row_i, tpl in enumerate(templates, start=1):
            tk.Label(inner, text=tpl["name"], anchor="w", width=30, bg="#F2F2F2").grid(row=row_i, column=0, sticky="nsew")
            template_slot = int(tpl.get("slot", 1))
            for col_i, payday in enumerate(paydays, start=1):
                payday_number = self._payday_number_in_year(payday)
                if payday_number in free_numbers:
                    bg = green_bg
                else:
                    slot = self._slot_for_date(payday)
                    if slot == template_slot:
                        bg = red_bg if template_slot == 1 else yellow_bg
                    else:
                        bg = neutral_bg
                cell = tk.Label(inner, text="", bg=bg, width=10)
                cell.grid(row=row_i, column=col_i, sticky="nsew")

        total_row = len(templates) + 1
        tk.Label(inner, text="Legend", anchor="w", width=30, bg="#D9E1F2").grid(row=total_row, column=0, sticky="nsew")
        legend_items = [
            ("Cycle 1 due", red_bg),
            ("Cycle 2 due", yellow_bg),
            ("Free check", green_bg),
            ("Not due", neutral_bg),
        ]
        for idx, (text, color) in enumerate(legend_items, start=1):
            lbl = tk.Label(inner, text=text, bg=color, width=10)
            lbl.grid(row=total_row, column=idx, sticky="nsew")

        for r in range(total_row + 1):
            inner.grid_rowconfigure(r, minsize=row_h)
        inner.grid_columnconfigure(0, minsize=name_col_w)
        for c in range(1, len(paydays) + 1):
            inner.grid_columnconfigure(c, minsize=col_w)

    # -------------------- Bill rendering --------------------
    def _clear_bill_rows(self) -> None:
        for row in self.bill_row_widgets:
            row.frame.destroy()
        self.bill_row_widgets.clear()

    def _render_bills(self, session: dict) -> None:
        self._clear_bill_rows()

        header = ctk.CTkFrame(self.bill_scroll)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=4)
        header.grid_columnconfigure(2, weight=1)
        for c, text in enumerate(["In", "Amount", "Bill", "Notes", "Link"]):
            ctk.CTkLabel(header, text=text, font=ctk.CTkFont(weight="bold")).grid(row=0, column=c, padx=6, pady=4)

        for i, bill in enumerate(session.get("bills", []), start=1):
            frame = ctk.CTkFrame(self.bill_scroll)
            frame.grid(row=i, column=0, sticky="ew", padx=4, pady=4)
            frame.grid_columnconfigure(2, weight=1)

            include_var = tk.BooleanVar(value=bool(bill.get("included", True)))
            amount_var = tk.StringVar(value=self._money_str(bill.get("amount", "0.00")))

            ctk.CTkCheckBox(frame, text="", variable=include_var, command=self.recalculate_summary).grid(
                row=0, column=0, padx=6, pady=6
            )

            amount_entry = ctk.CTkEntry(frame, width=100, textvariable=amount_var)
            amount_entry.grid(row=0, column=1, padx=6, pady=6)
            amount_entry.bind("<FocusOut>", lambda _e, idx=i - 1: self._on_bill_amount_changed(idx))

            pushed_from = bill.get("pushed_from")
            name = bill.get("name", "")
            if pushed_from:
                name = f"{name} ({pushed_from})"

            ctk.CTkLabel(frame, text=name, anchor="w").grid(row=0, column=2, padx=6, pady=6, sticky="w")

            ctk.CTkButton(frame, text="Notes", width=70, command=lambda b=bill: self._show_notes(b)).grid(
                row=0, column=3, padx=6, pady=6
            )

            ctk.CTkButton(frame, text="Open", width=70, command=lambda b=bill: self._open_link(b)).grid(
                row=0, column=4, padx=6, pady=6
            )

            self.bill_row_widgets.append(BillRowWidgets(frame=frame, include_var=include_var, amount_var=amount_var))

    def _on_bill_amount_changed(self, index: int) -> None:
        current_date = self.payday_var.get().strip()
        if not current_date:
            return
        session = self._ensure_session(current_date)
        try:
            normalized = self._money_str(self._parse_money(self.bill_row_widgets[index].amount_var.get()))
        except (InvalidOperation, ValueError):
            messagebox.showerror("Validation", "Bill amount must be numeric.")
            return

        self.bill_row_widgets[index].amount_var.set(normalized)
        session["bills"][index]["amount"] = normalized
        self._save_data()
        self.recalculate_summary()

    def _persist_visible_bills_to_session(self, payday_str: str) -> None:
        session = self._ensure_session(payday_str)
        for i, row in enumerate(self.bill_row_widgets):
            if i >= len(session["bills"]):
                continue
            session["bills"][i]["included"] = bool(row.include_var.get())
            session["bills"][i]["amount"] = row.amount_var.get().strip()

    def recalculate_summary(self) -> None:
        current_date = self.payday_var.get().strip()
        if not current_date:
            return

        self._persist_visible_bills_to_session(current_date)
        session = self._ensure_session(current_date)

        try:
            paycheck = self._parse_money(self.paycheck_var.get())
        except (InvalidOperation, ValueError):
            paycheck = Decimal("0")

        selected_total = Decimal("0")
        for bill in session.get("bills", []):
            if not bill.get("included", True):
                continue
            try:
                selected_total += self._parse_money(str(bill.get("amount", "0")))
            except (InvalidOperation, ValueError):
                pass

        remaining = paycheck - selected_total
        self.total_bills_label.configure(text=f"Selected Bills Total: ${selected_total:.2f}")
        self.remaining_label.configure(text=f"Remaining: ${remaining:.2f}")

        color = "#2E8B57" if remaining >= 0 else "#B22222"
        self.remaining_label.configure(text_color=color)

        session["paycheck_amount"] = self._money_str(paycheck)
        self._save_data()

    # -------------------- Bill actions --------------------
    def _show_notes(self, bill: dict) -> None:
        notes = bill.get("notes") or "No notes."
        messagebox.showinfo(f"Notes: {bill.get('name', 'Bill')}", notes)

    def _open_link(self, bill: dict) -> None:
        url = (bill.get("url") or "").strip()
        if not url:
            messagebox.showinfo("No link", "No payment URL stored for this bill.")
            return
        webbrowser.open(url)

    # -------------------- App lifecycle --------------------
    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = PaydayBillApp()
    app.run()
