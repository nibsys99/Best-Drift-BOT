import time
import tkinter as tk
import win32com.client as win32
import requests

import json
import pyodbc

import pandas as pd
import datetime

# Get current month name
import datetime
import os

import tkinter as tk
from tkinter import messagebox
import webbrowser


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
        # shadow DESIGN
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

SEND_FROM_EMAIL = 'beslutsstod@systembolaget.se'  # beslutsstod@systembolaget.se
SEND_TO_EMAIL = 'best_driftst_rning@systembolaget.onmicrosoft.com'  # best_driftst_rning@systembolaget.onmicrosoft.com

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
        if (current_hour >= 8 and status
                == 'Running'):
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





def checkDrift():
    print("TESTAR DRIFTEN")
    run_morning_report()
    update_prognos_textbox()

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

# Tkinter
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
subtitle = tk.Label(header, text="Beslutsstöd • nattkörningar & driftsstatus", bg=PALETTE["panel"], fg=PALETTE["muted"], font=(FONT_FAMILY, 11))
title.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
subtitle.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

# header
stripe = tk.Frame(header, bg=PALETTE["accent"], height=4)
stripe.grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 0))

#toolbar
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




# content
content = tk.Frame(root, bg=PALETTE["panel"], highlightbackground=PALETTE["stroke"], highlightthickness=1)
content.grid(row=2, column=0, sticky="nsew", padx=18, pady=(8, 18))
raise_card(content)

content.grid_rowconfigure(0, weight=1)
content.grid_columnconfigure(0, weight=1)

# text

prognos_text = tk.Text(content, height=10, wrap="word",
                       bg=PALETTE["panel"], fg=PALETTE["ink"],
                       insertbackground=PALETTE["primary"],  # caret color
                       bd=0, relief="flat",
                       padx=18, pady=16,
                       font=(FONT_FAMILY, 11))
prognos_text.grid(row=0, column=0, sticky="nsew")

# Scrollbar
scrollbar = tk.Scrollbar(content, command=prognos_text.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
prognos_text.configure(yscrollcommand=scrollbar.set)

# text + color
prognos_text.tag_config("green", foreground=PALETTE["success"])
prognos_text.tag_config("red", foreground=PALETTE["danger"])
prognos_text.tag_config("yellow", foreground=PALETTE["warning"])
prognos_text.tag_config("h1", font=(FONT_FAMILY, 14, "bold"), foreground=PALETTE["primary"])
prognos_text.tag_config("h2", font=(FONT_FAMILY, 12, "bold"), foreground=PALETTE["ink"])

# THE hedaers
prognos_text.insert(tk.END, "Välj en åtgärd ovan för att hämta status…", "h2")
prognos_text.config(state="disabled")

print("PÅ SLUUUUUTET")

root.mainloop()
