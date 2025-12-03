import win32com.client as win32
import pyodbc
import pandas as pd
import datetime
import tkinter as tk
from tkinter import messagebox
import webbrowser
import os  # for planerade.txt

MESSAGE = ""

PALETTE = {
    "bg":        "#f7f9f5",
    "panel":     "#ffffff",
    "ink":       "#243226",
    "muted":     "#6b7a6f",
    "primary":   "#0a7f2e",
    "primary-2": "#0f6135",
    "accent":    "#f2c300",
    "accent-2":  "#e1b100",
    "stroke":    "#e7eee4",
    "success":   "#15803d",
    "danger":    "#cc2e2e",
    "warning":   "#b58100",
    "shadow":    "#dfe6dc",
}

FONT_FAMILY = "Segoe UI"

TODO_FILE = "planerade.txt"   # file for ToDo items
planerade_items = []          # in-memory list of ToDo items

def style_button(btn: tk.Button, base=PALETTE["primary"], hover=PALETTE["primary-2"], active=PALETTE["primary-2"], fg="white"):
    btn.configure(
        bg=base, fg=fg,
        activebackground=active, activeforeground=fg,
        bd=0, relief="flat",
        padx=14, pady=10,
        cursor="hand2",
        font=(FONT_FAMILY, 11, "bold"),
        highlightthickness=0,
    )
    def on_enter(_): btn.configure(bg=hover)
    def on_leave(_): btn.configure(bg=base)
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

def style_secondary_button(btn: tk.Button):
    style_button(btn, base=PALETTE["accent"], hover=PALETTE["accent-2"], active=PALETTE["accent-2"], fg=PALETTE["ink"])

def raise_card(frame: tk.Frame):
    """Give a card look: light border + faux shadow (solid, since Tk has no alpha)."""
    frame.configure(bg=PALETTE["panel"], bd=0, highlightthickness=1, highlightbackground=PALETTE["stroke"])
    try:
        shadow = tk.Frame(frame.master, bg=PALETTE["shadow"])
        shadow.place(in_=frame, x=3, y=3, relwidth=1, relheight=1)
        shadow.lower(frame)
        frame._shadow = shadow

        def _sync(_evt=None):
            shadow.place_configure(in_=frame)
            shadow.lower(frame)
        frame.bind("<Configure>", _sync)
        frame.bind("<Destroy>", lambda _e: shadow.destroy())
    except tk.TclError:
        pass

current_month_number = datetime.datetime.now().month
current_hour = datetime.datetime.now().hour

print(current_hour)

SEND_FROM_EMAIL = 'beslutsstod@systembolaget.se'
SEND_TO_EMAIL = 'best_driftst_rning@systembolaget.onmicrosoft.com'

prognos_data = {
    "Datalager": "Succeeded",
    "Butiksrapporter": "Succeeded",
    "Mercur": "Succeeded",
    "Kub": "Succeeded",
    "Assortment (alla utvärderingar)": "Succeeded",
    "Space": "Succeeded",
    "Försäljningsmodellen": "Succeeded",
    "StyrkortButik": "Succeeded",
    "Tilldelningsmodellen": "Succeeded",
    "Kundbeställningsmodellen": "Succeeded",
    "Varuavstämningsmodellen": "Succeeded",
    "Varuförsörjningsmodellen": "Succeeded"
}

visa_data = {
    "Assortment (alla utvärderingar)": "Succeeded",
    "Artikel (laddas efter kl 20 ikväll)": "Succeeded"
}

def format_status_line(name, status):
    print(name, status)
    if status == "Succeeded":
        status = 'klar'
        color = "green"
    else:
        color = "red"
        status = 'x'
    return f"<span style='color:{color};'> {name} – {status}</span>"

connection = None

driftstörning = False
senVA = False
senVF = False

prognos_html = "<p><b>Prognos</b><br>"
for name, status in prognos_data.items():
    prognos_html += format_status_line(name, status)

visa_html = "<p><b>VISA:</b><br>"
for name, status in visa_data.items():
    visa_html += format_status_line(name, status)

def sendVAprocessingLate(SEND_FROM_EMAIL, input_message):
    olapp = win32.Dispatch('Outlook.Application')
    systemEmail = olapp.Session.Accounts[SEND_FROM_EMAIL]
    message = olapp.CreateItem(0)
    message.To = "Ida.Lund@systembolaget.se; Ewa-Li.Nyren@systembolaget.se; dryckesfakturor@systembolaget.se;"
    message.Subject = "Gårdagens försäljningsstatistik"
    message.HTMLBody = input_message
    message._oleobj_.Invoke(*(64209, 0, 8, 0, systemEmail))
    message.Display()

def sendVFprocessingLate(SEND_FROM_EMAIL, input_message):
    olapp = win32.Dispatch('Outlook.Application')
    systemEmail = olapp.Session.Accounts[SEND_FROM_EMAIL]
    message = olapp.CreateItem(0)
    message.To = "jenny.forssman@systembolaget.se; Ewa-Li.Nyren@systembolaget.se; linda.carlberg@systembolaget.se; varuplanering@systembolaget.se; logistiker@systembolaget.se;"
    message.Subject = "Gårdagens försäljningsstatistik"
    message.HTMLBody = input_message
    message._oleobj_.Invoke(*(64209, 0, 8, 0, systemEmail))
    message.Display()

def sendDriftstorningsmail(SEND_FROM_EMAIL, SEND_TO_EMAIL, input_message):
    olapp = win32.Dispatch('Outlook.Application')
    systemEmail = olapp.Session.Accounts[SEND_FROM_EMAIL]
    message = olapp.CreateItem(0)
    message.To = SEND_TO_EMAIL
    message.Subject = "Gårdagens försäljningsstatistik"
    message.HTMLBody = input_message
    message._oleobj_.Invoke(*(64209, 0, 8, 0, systemEmail))
    message.Display()

sendLateMessageVA = f"""
                <html>
                <body>
                <i>God morgon!<br>
                VA - laddningen är sen idag och förväntas vara klar till efter 09:00
               </i>
                <p><i>Med vänliga hälsningar,<br>
                Beslutsstöd</i></p>
                </body>
                </html>
                """

sendLateMessageVF = f"""
                <html>
                <body>
                <i>God morgon!<br>
                VF - laddningen är sen idag och förväntas vara klar till efter 09:00
               </i>
                <p><i>Med vänliga hälsningar,<br>
                Beslutsstöd</i></p>
                </body>
                </html>
                """

def authentic():
    global connection
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=SBBESTPROD10;"
        "DATABASE=BEST_EDW;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Trusted_Connection=yes;"
    )

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    print("Before test")
    print(connection_string)
    connection = pyodbc.connect(connection_string)
    print("Connected!", connection.getinfo(pyodbc.SQL_DBMS_NAME))

def checkJob(job, status):
    global senVA, senVF
    if job == 'BEST_ETL_BEST_EDW_Master ETL' and status != 'Succeeded':
        for key in prognos_data:
            prognos_data[key] = "Failed"
        for key in visa_data:
            visa_data[key] = "Failed"
    if job == 'BEST_ETL_BEST_EDW_Load undersokningar' and status != 'Succeeded':
        prognos_data['Datalager'] = 'Failed'
        prognos_data['Butiksrapporter'] = 'Failed'
    if job == 'BEST_ETL_Cube_Process BEST cube (triggered)' and status != 'Succeeded':
        prognos_data['Kub'] = 'Failed'
    if job == 'BEST_ETL_Assortment_Update Master Data and Facts (triggered)' and status != 'Succeeded':
        prognos_data['Assortment (alla utvärderingar)'] = 'Failed'
        visa_data['Assortment (alla utvärderingar)'] = 'Failed'
    if job == 'BEST_ETL_Assortment_FSN Ranking' and status != 'Succeeded':
        prognos_data['Assortment (alla utvärderingar)'] = 'Failed'
        visa_data['Assortment (alla utvärderingar)'] = 'Failed'
    if job == 'BEST_ETL_BEST_EDW_Prep data and trigger Mercur (triggered)' and status != 'Succeeded':
        prognos_data['Mercur'] = 'Failed'
    if job == 'BEST_ETL_GENMOD_Tilldelning (triggered)' and status != 'Succeeded':
        prognos_data['Tilldelningsmodellen'] = 'Failed'
    if job == 'BEST_ETL_GenMod_Försäljning (triggered)' and status != 'Succeeded':
        prognos_data['Försäljningsmodellen'] = 'Failed'
    if job == 'BEST_ETL_GENMOD_Varuförsörjning (triggered)' and status != 'Succeeded':
        if status == 'Failed':
            prognos_data['Varuförsörjningsmodellen'] = 'Failed'
        if (current_hour >= 8 and status == 'Running'):
            senVF = True
    if job == 'BEST_ETL_Cube_Tabular_VA' and status != 'Succeeded':
        if status == 'Failed':
            prognos_data['Kub'] = 'Failed'
            prognos_data['Varuavstämningsmodellen'] = 'Failed'
        if status == 'Running' and current_hour >= 8:
            senVA = True
    if job == 'BEST_ETL_Cube_Tabular_VA_Process' and status != 'Succeeded':
        if status == 'Failed':
            prognos_data['Kub'] = 'Failed'
            prognos_data['Varuavstämningsmodellen'] = 'Failed'
        if status == 'Running' and current_hour >= 8:
            senVA = True
    if job == 'BEST_ETL_Cube_Kundbest (triggered)' and status != 'Succeeded':
        prognos_data['Kundbeställningsmodellen'] = 'Failed'
    if job == 'BEST_ETL_GENMOD_StyrkortButik (triggered)' and status != 'Succeeded':
        prognos_data['StyrkortButik'] = 'Failed'
    if job == 'BEST_ETL_SPACE_I2E_STEPS' and status != 'Succeeded' and (current_month_number == 2 or current_month_number == 8):
        prognos_data['Space'] = 'Failed'

def jobsSucceededOrFailed(job_status_dict):
    for job, status in job_status_dict.items():
        checkJob(job, status)

def getMorningRapport():
    print(pyodbc.drivers())
    sql = open('queryForMorningRapport.txt', 'r').read()
    print(sql)
    data = pd.read_sql(sql, connection)
    print(data)
    job_status_dict = dict(zip(data["JobName"], data["LastRunStatus"]))
    print(job_status_dict)
    jobsSucceededOrFailed(job_status_dict)

print(prognos_data)

def run_morning_report():
    global MESSAGE, driftstörning, prognos_html, visa_html, senVA, senVF, sendLateMessageVA, sendLateMessageVF
    authentic()
    getMorningRapport()

    prognos_html = "<p><b>Prognos</b><br>"
    for name, status in prognos_data.items():
        prognos_html += f"{format_status_line(name, status)}<br>"

    visa_html = "<p><b>VISA:</b><br>"
    for name, status in visa_data.items():
        visa_html += f"{format_status_line(name, status)}<br>"

    MESSAGE = f"""
        <html>
        <body>
        <i>God morgon!<br> <br>
        Nattens laddning av Beslutsstöd gick fel och gårdagens försäljningsinformation och ekonomiska siffror saknas i nedan rödmarkerade gränssnitt. </i>
        {prognos_html}
        {visa_html}
        <p><i>OBS!! Under laddning av Kuben kan svarstiderna vara tröga.<br>
        Under laddning av datalager bör man som användare undvika att ställa SQL-frågor mot datalagret.</i></p>
        <p><i>Med vänliga hälsningar<br>
        Beslutsstöd</i></p>
        </body>
        </html>
        """

    driftstörning = any(status != 'Succeeded' for status in prognos_data.values())

print(MESSAGE)
print("DU KAN GÅ VIDAREEEEE")

for key in prognos_data:
    if prognos_data[key] != 'Succeeded':
        driftstörning = True

print()
print()
print(prognos_data)
print()
print()
print(prognos_html)
print()

def hide_todo_toolbar():
    """Hide the inner ToDo toolbar from the content area."""
    try:
        todo_toolbar.grid_remove()
    except Exception:
        pass

def show_todo_toolbar():
    """Show the inner ToDo toolbar in the content area."""
    todo_toolbar.grid()
    btn_add_todo.config(state="normal")
    btn_remove_todo.config(state="normal")

def checkDrift():
    print("TESTAR DRIFTEN")
    run_morning_report()
    update_prognos_textbox()

    hide_todo_toolbar()

    if driftstörning:
        messagebox.showerror("Fel", "Alla laddningar har EJ gått igenom. Driftmail skapas")
        sendDriftstorningsmail(SEND_FROM_EMAIL, SEND_TO_EMAIL, MESSAGE)
    elif senVA:
        messagebox.showwarning("Varning", "VA-processningen är sen")
        sendVAprocessingLate(SEND_FROM_EMAIL, sendLateMessageVA)
    elif senVF:
        messagebox.showwarning("Varning", "VF-processningen är sen")
        sendVFprocessingLate(SEND_FROM_EMAIL, sendLateMessageVF)
    else:
        messagebox.showinfo('Bra', 'Alla laddningar har gått igenom!')

def open_link():
    webbrowser.open('https://systembolaget.sharepoint.com/:x:/s/Beslutsstd/EaQFAUEAtZhErNBSmVCrbcQB26W4XMIg1RvQXTHpaItH7A?e=KYtjcL')

def update_prognos_textbox():
    prognos_text.config(state="normal")
    prognos_text.delete("1.0", tk.END)

    # Prognos + VISA
    prognos_text.insert(tk.END, "Prognos\n", "h1")
    for key, value in prognos_data.items():
        line = f"  • {key} – {('klar' if value=='Succeeded' else ('pågår' if value=='Running' else 'fel'))}\n"
        tag = "green" if value == "Succeeded" else ("yellow" if value == "Running" else "red")
        prognos_text.insert(tk.END, line, tag)

    prognos_text.insert(tk.END, "\nVISA\n", "h1")
    for key, value in visa_data.items():
        line = f"  • {key} – {('klar' if value=='Succeeded' else ('pågår' if value=='Running' else 'fel'))}\n"
        tag = "green" if value == "Succeeded" else ("yellow" if value == "Running" else "red")
        prognos_text.insert(tk.END, line, tag)

    prognos_text.config(state="disabled")

def checkETL():
    prognos_text.config(state="normal")
    prognos_text.delete('1.0', tk.END)
    authentic()
    sql = open('queryForWhoLogETLidag.txt', 'r').read()
    df = pd.read_sql(sql, connection)
    df["CONTR_STUS_CD_NUM"] = pd.to_numeric(df["CONTR_STUS_CD"], errors="coerce")
    ids_with_zero = df.loc[df["CONTR_STUS_CD_NUM"] == 0, "LOAD_ID"].unique()
    df_ok = df[~df["LOAD_ID"].isin(ids_with_zero)].copy()

    load_to_rows = {}
    for load_id, group in df_ok.groupby("LOAD_ID"):
        load_to_rows[load_id] = group.to_dict(orient="records")

    prognos_text.insert(tk.END, "ETL idag\n", "h1")
    for load_id, rows in sorted(load_to_rows.items()):
        prognos_text.insert(tk.END, f"LOAD_ID {load_id}\n", "h2")
        for row in rows:
            pkg_nm = row.get("PKG_NM", "")
            prognos_text.insert(tk.END, f"  • {pkg_nm}\n", "red")

    prognos_text.config(state="disabled")

    hide_todo_toolbar()

# ---------- ToDo / "Planerade" helpers ----------

def sort_planerade_items():
    planerade_items.sort(key=lambda i: (i["date"] is None, i["date"] or datetime.date.max))

def parse_todo_line(line: str):
    """
    Format:
      2025-12-06; Stänga change: CH16736; open
      date; text; status(optional)

    Returns dict with:
      - date (datetime.date or None)
      - date_str (original string)
      - text
      - done (bool)
    """
    parts = [p.strip() for p in line.split(";", 2)]
    if len(parts) < 2:
        return None

    date_str, text = parts[0], parts[1]
    status = parts[2].lower() if len(parts) == 3 else ""

    try:
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        date = None

    done = status in ("done", "klar", "x", "1", "true")

    return {
        "date": date,
        "date_str": date_str,
        "text": text,
        "done": done,
    }

def load_planerade():
    """Read planerade.txt into planerade_items and return them."""
    global planerade_items
    planerade_items = []

    if not os.path.exists(TODO_FILE):
        return planerade_items

    with open(TODO_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            item = parse_todo_line(line)
            if item:
                planerade_items.append(item)

    sort_planerade_items()
    return planerade_items

def save_planerade():
    """Save current planerade_items back to planerade.txt."""
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        for item in planerade_items:
            date_str = item["date"].strftime("%Y-%m-%d") if item["date"] else item["date_str"]
            status = "done" if item["done"] else "open"
            f.write(f"{date_str}; {item['text']}; {status}\n")

def show_planerade():
    """Show the planned ToDo list in the main text area and show inner toolbar."""
    load_planerade()
    today = datetime.date.today()

    prognos_text.config(state="normal")
    prognos_text.delete("1.0", tk.END)

    # Header
    prognos_text.insert(tk.END, "Planerade aktiviteter\n", "h1")
    prognos_text.insert(
        tk.END,
        "Uppdateras via filen 'planerade.txt' och via Lägg till / Ta bort nedan.\n\n",
        "muted",
    )

    if not planerade_items:
        prognos_text.insert(
            tk.END,
            "Inga planerade aktiviteter hittades.\n",
            "muted",
        )
        prognos_text.config(state="disabled")
        show_todo_toolbar()
        btn_remove_todo.config(state="disabled")
        return

    for item in planerade_items:
        symbol = "✔" if item["done"] else "☐"
        date_label = item["date"].strftime("%Y-%m-%d") if item["date"] else item["date_str"]

        # lite extra spacing så det känns större/luftigare
        line = f"  {symbol}  {date_label} – {item['text']}\n"

        # Color logic:
        #  - green: done
        #  - red: passed date but not done
        #  - yellow: upcoming/ongoing
        if item["done"]:
            # grön + struken + lite större font (todo)
            tags = ("green", "done", "todo")
        elif item["date"] and item["date"] < today:
            tags = ("red", "todo")
        else:
            tags = ("yellow", "todo")

        prognos_text.insert(tk.END, line, tags)

    prognos_text.config(state="disabled")

    show_todo_toolbar()

    prognos_text.config(state="disabled")

    show_todo_toolbar()




def add_planerad_item():
    """Open a small window to add a new ToDo item."""
    def on_save():
        date_str = entry_date.get().strip()
        text = entry_text.get().strip()
        done = bool(var_done.get())

        if not date_str or not text:
            messagebox.showwarning("Fel", "Både datum och text måste fyllas i.")
            return
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Fel", "Datum måste vara i formatet ÅÅÅÅ-MM-DD.")
            return

        new_item = {
            "date": date_obj,
            "date_str": date_str,
            "text": text,
            "done": done,
        }
        planerade_items.append(new_item)
        sort_planerade_items()
        save_planerade()
        show_planerade()
        win.destroy()

    win = tk.Toplevel(root)
    win.title("Lägg till aktivitet")
    win.transient(root)
    win.grab_set()

    tk.Label(win, text="Datum (YYYY-MM-DD):", font=(FONT_FAMILY, 10)).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
    entry_date = tk.Entry(win, width=20, font=(FONT_FAMILY, 10))
    entry_date.grid(row=0, column=1, sticky="w", padx=10, pady=(10, 4))

    tk.Label(win, text="Aktivitet:", font=(FONT_FAMILY, 10)).grid(row=1, column=0, sticky="w", padx=10, pady=4)
    entry_text = tk.Entry(win, width=40, font=(FONT_FAMILY, 10))
    entry_text.grid(row=1, column=1, sticky="w", padx=10, pady=4)

    var_done = tk.IntVar(value=0)
    chk_done = tk.Checkbutton(win, text="Redan klar", variable=var_done, font=(FONT_FAMILY, 10))
    chk_done.grid(row=2, column=1, sticky="w", padx=10, pady=4)

    btn_frame = tk.Frame(win)
    btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

    btn_save = tk.Button(btn_frame, text="Spara", command=on_save)
    style_button(btn_save)
    btn_save.grid(row=0, column=0, padx=5)

    btn_cancel = tk.Button(btn_frame, text="Avbryt", command=win.destroy)
    style_secondary_button(btn_cancel)
    btn_cancel.grid(row=0, column=1, padx=5)

def remove_planerade_items():
    """Open a window where you can select and remove one or more ToDo items."""
    if not planerade_items:
        messagebox.showinfo("Planerade", "Det finns inga aktiviteter att ta bort.")
        return

    def on_delete():
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Ta bort", "Markera minst en aktivitet att ta bort.")
            return
        if not messagebox.askyesno("Ta bort", "Är du säker på att du vill ta bort de markerade aktiviteterna?"):
            return

        # delete from highest index to lowest
        for idx in sorted(selection, reverse=True):
            del planerade_items[idx]

        save_planerade()
        show_planerade()
        win.destroy()

    win = tk.Toplevel(root)
    win.title("Ta bort aktiviteter")
    win.transient(root)
    win.grab_set()

    tk.Label(win, text="Markera de aktiviteter du vill ta bort:", font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", padx=10, pady=(10, 4))

    listbox = tk.Listbox(win, selectmode="extended", width=60, height=10, font=(FONT_FAMILY, 10))
    listbox.pack(fill="both", expand=True, padx=10, pady=4)

    for item in planerade_items:
        date_label = item["date"].strftime("%Y-%m-%d") if item["date"] else item["date_str"]
        status_symbol = "✔" if item["done"] else "☐"
        listbox.insert(tk.END, f"{status_symbol} {date_label} – {item['text']}")

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)

    btn_delete = tk.Button(btn_frame, text="Ta bort markerade", command=on_delete)
    style_button(btn_delete)
    btn_delete.grid(row=0, column=0, padx=5)

    btn_cancel = tk.Button(btn_frame, text="Avbryt", command=win.destroy)
    style_secondary_button(btn_cancel)
    btn_cancel.grid(row=0, column=1, padx=5)

# ---------- Tkinter UI ----------

root = tk.Tk()
root.title("BEST Drift • Systembolaget")
root.geometry("980x640")
root.minsize(820, 420)
root.configure(bg=PALETTE["bg"])

# Global grid config
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(2, weight=1)

# Header
header = tk.Frame(root, bg=PALETTE["panel"], highlightbackground=PALETTE["stroke"], highlightthickness=1)
header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
raise_card(header)

title = tk.Label(header, text="BEST-Drift-BOT", bg=PALETTE["panel"], fg=PALETTE["primary"], font=(FONT_FAMILY, 20, "bold"))
subtitle = tk.Label(header, text="Beslutsstöd • nattkörningar, driftsstatus & ToDo", bg=PALETTE["panel"], fg=PALETTE["muted"], font=(FONT_FAMILY, 11))
title.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
subtitle.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

stripe = tk.Frame(header, bg=PALETTE["accent"], height=4)
stripe.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 0))

# Toolbar
toolbar = tk.Frame(root, bg=PALETTE["bg"])
toolbar.grid(row=1, column=0, sticky="ew", padx=18, pady=8)
toolbar.grid_columnconfigure(10, weight=1)

btn_drift = tk.Button(toolbar, text="⚙️ Kör drift", command=checkDrift)
style_button(btn_drift)
btn_drift.grid(row=0, column=0, padx=(0, 10), pady=4)

btn_etl = tk.Button(toolbar, text="📦 Kör ETL idag", command=checkETL)
style_button(btn_etl)
btn_etl.grid(row=0, column=1, padx=(0, 10), pady=4)

btn_link = tk.Button(toolbar, text="📊 Sena laddningar (Excel)", command=open_link)
style_secondary_button(btn_link)
btn_link.grid(row=0, column=2, padx=(0, 10), pady=4)

btn_planerade = tk.Button(toolbar, text="📝 Planerade", command=show_planerade)
style_secondary_button(btn_planerade)
btn_planerade.grid(row=0, column=3, padx=(0, 10), pady=4)

# Content
content = tk.Frame(root, bg=PALETTE["panel"], highlightbackground=PALETTE["stroke"], highlightthickness=1)
content.grid(row=2, column=0, sticky="nsew", padx=18, pady=(8, 18))
raise_card(content)

# content rows: 0 = inner ToDo toolbar, 1 = text
content.grid_rowconfigure(0, weight=0)
content.grid_rowconfigure(1, weight=1)
content.grid_columnconfigure(0, weight=1)

# Inner ToDo toolbar (initially hidden)
todo_toolbar = tk.Frame(content, bg=PALETTE["panel"])
todo_toolbar.grid(row=0, column=0, sticky="w", padx=18, pady=(10, 0))

btn_add_todo = tk.Button(todo_toolbar, text="➕ Lägg till", command=add_planerad_item)
style_secondary_button(btn_add_todo)
btn_add_todo.grid(row=0, column=0, padx=(0, 8), pady=0)

btn_remove_todo = tk.Button(todo_toolbar, text="🗑 Ta bort", command=remove_planerade_items)
style_secondary_button(btn_remove_todo)
btn_remove_todo.grid(row=0, column=1, padx=(0, 8), pady=0)

# hide at startup
todo_toolbar.grid_remove()

# Text widget
prognos_text = tk.Text(
    content, height=10, wrap="word",
    bg=PALETTE["panel"], fg=PALETTE["ink"],
    insertbackground=PALETTE["primary"],
    bd=0, relief="flat",
    padx=18, pady=16,
    font=(FONT_FAMILY, 11),
)
prognos_text.grid(row=1, column=0, sticky="nsew")

# Scrollbar
scrollbar = tk.Scrollbar(content, command=prognos_text.yview)
scrollbar.grid(row=1, column=1, sticky="ns")
prognos_text.configure(yscrollcommand=scrollbar.set)

# Text tags
prognos_text.tag_config("green", foreground=PALETTE["success"])
prognos_text.tag_config("red", foreground=PALETTE["danger"])
prognos_text.tag_config("yellow", foreground=PALETTE["warning"])
prognos_text.tag_config("h1", font=(FONT_FAMILY, 14, "bold"), foreground=PALETTE["primary"])
prognos_text.tag_config("h2", font=(FONT_FAMILY, 12, "bold"), foreground=PALETTE["ink"])
prognos_text.tag_config("muted", foreground=PALETTE["muted"])
prognos_text.tag_config("done", overstrike=1)  # strikethrough for done items

prognos_text.tag_config("todo", font=(FONT_FAMILY, 13))

# Initial text
prognos_text.insert(tk.END, "Välj en åtgärd ovan för att hämta status…", "h2")
prognos_text.config(state="disabled")

print("PÅ SLUUUUUTET")

root.mainloop()
