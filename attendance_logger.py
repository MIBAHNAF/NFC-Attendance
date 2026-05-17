import queue, threading, os, openpyxl, serial
from datetime import datetime
from tkinter import (Tk, Label, Frame, Checkbutton, BooleanVar,
                     simpledialog, messagebox)
from transport import USBReader, BleReader

# ---------------- Excel ----------------
EXCEL_FILE = os.path.abspath("attendance.xlsm")
SHEET_NAME = "Template"
UID1_COL, UID2_COL, PHONE_COL, NAME_COL = 1, 2, 3, 4
START_ROW = 10

# ---------------- Tk UI ----------------
root = Tk()
root.title("Smart Attendance Logger")
root.geometry("650x480")
root.configure(bg="#1e1e2f")

Label(root, text="Smart", fg="red", bg="#1e1e2f",
      font=("Helvetica", 34, "bold")).pack(pady=(15, 0))
Label(root, text="Attendance System", fg="white", bg="#1e1e2f",
      font=("Helvetica", 34)).pack()

date_label = Label(root, bg="#1e1e2f", fg="lightgray",
                   font=("Helvetica", 24))
date_label.pack(pady=(18, 2))

status_label = Label(root, text="Waiting for device…", fg="cyan",
                     bg="#1e1e2f", font=("Helvetica", 24, "bold"))
status_label.pack(pady=(10, 15))

second_uid_frame = Frame(root, bg="#1e1e2f")
has_second_uid = BooleanVar(value=False)
Checkbutton(second_uid_frame, text=" Do you have a second Device?",
            variable=has_second_uid, font=("Helvetica", 18),
            bg="#1e1e2f", fg="yellow", selectcolor="#1e1e2f",
            activebackground="#1e1e2f", activeforeground="yellow",
            highlightthickness=0).pack()
second_uid_frame.pack(pady=(0, 10))

def update_status(msg: str, colour="white"):
    status_label.config(text=msg, fg=colour)

def update_date_label():
    date_label.config(text=f"Attendance for {datetime.today():%B %d}")

is_ready = False

# ---------------- Excel open ----------------
wb = openpyxl.load_workbook(EXCEL_FILE, keep_vba=True)
ws = wb[SHEET_NAME]

today = datetime.today().date()
date_col = None
for col in range(5, 36):
    v = ws.cell(row=9, column=col).value
    if isinstance(v, datetime) and v.date() == today:
        date_col = col; break
if not date_col:
    messagebox.showerror("Date column missing",
                         f"No header for {today:%B %d}")
    root.destroy(); raise SystemExit

# ---------------- queues & transports ----------------
serial_queue: queue.Queue[str] = queue.Queue()

def gui_logger(msg: str):
    global is_ready
    # Default cyan for progress messages
    colour = "cyan"
    if "Connected" in msg or "Subscribed" in msg:
        is_ready = True
        colour = "blue"
        # After a short connection confirmation, show the scan-ready state.
        root.after(800, lambda: update_status("NFC ready", "lime"))
    elif "using USB" in msg and is_ready:
        return
    update_status(msg, colour)

USBReader(serial_queue, logger=gui_logger).start()
BleReader (serial_queue, name_hint="DSD TECH", logger=gui_logger).start()

# ---------------- helpers ----------------
DIGITS_ONLY = set("0123456789")
def looks_like_uid(s: str) -> bool:
    return 19 <= len(s) <= 24 and all(ch in DIGITS_ONLY for ch in s)

def wait_for_second_uid(row_idx, name):
    update_status("Waiting for second Device…", "cyan")
    while True:
        raw = serial_queue.get()
        if looks_like_uid(raw):
            ws.cell(row=row_idx, column=UID2_COL).value = raw
            wb.save(EXCEL_FILE)
            update_status(f"Second Device saved for {name} ✔", "lime")
            break

def process_queue():
    while not serial_queue.empty():
        raw = serial_queue.get().strip()
        if not looks_like_uid(raw):
            continue
        uid = raw

        # -------- Excel lookup -----------
        row, found = START_ROW, False
        while row <= ws.max_row + 1:
            uid1 = str(ws.cell(row=row, column=UID1_COL).value or "").strip()
            uid2 = str(ws.cell(row=row, column=UID2_COL).value or "").strip()

            if uid in (uid1, uid2):
                name = str(ws.cell(row=row, column=NAME_COL).value or "")
                present = str(ws.cell(row=row, column=date_col).value or "")
                if present.upper() == "P":
                    update_status(f"Already marked: {name}", "orange")
                else:
                    ws.cell(row=row, column=date_col, value="P")
                    wb.save(EXCEL_FILE)
                    update_status(f"{name} marked Present for "
                                  f"{datetime.today():%B %d}", "green")
                found = True; break

            if uid1 == "" and uid2 == "" and row >= START_ROW:
                break
            row += 1

        # -------- new person flow --------
        if not found:
            def add_new():
                update_status("New person. Awaiting details…", "cyan")
                name = simpledialog.askstring("New Entry", "Enter Name:",
                                              parent=root)
                if not name:
                    return update_status("Entry cancelled", "red")
                phone = simpledialog.askstring("Phone", "Phone Number:",
                                               parent=root)
                if phone is None:
                    return update_status("Entry cancelled", "red")

                ws.cell(row=row, column=UID1_COL, value=uid)
                ws.cell(row=row, column=PHONE_COL, value=phone)
                ws.cell(row=row, column=NAME_COL, value=name)
                ws.cell(row=row, column=date_col, value="P")
                wb.save(EXCEL_FILE)
                update_status(f"{name} added & Present for "
                              f"{datetime.today():%B %d}", "blue")

                if has_second_uid.get():
                    threading.Thread(target=wait_for_second_uid,
                                     args=(row, name), daemon=True).start()
            root.after(5, add_new)

    root.after(150, process_queue)

# ---------------- kick off ----------------
update_date_label()
root.after(150, process_queue)
root.mainloop()
