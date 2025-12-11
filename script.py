import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import webbrowser
import datetime
import win32com.client as win32
import pyodbc
import pandas as pd
from tkinter import font as tkfont



ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

PALETTE = {
    "bg":        "#050816",  # mörkblå / nästan svart bakgrund
    "panel":     "#0B1220",  # väldigt mörk marinblå panel
    "ink":       "#E5ECEF",  # ljus kallgrå (nästan vit) text
    "muted":     "#9CA3AF",  # dämpad mellangrå text/ikoner
    "primary":   "#10B981",  # klar grön (SYS)
    "primary-2": "#059669",  # mörkare grön (hover)
    "accent":    "#EAB308",  # guld / varm gul accent
    "stroke":    "#1F2933",  # mörk gråblå kantlinjer
    "success":   "#22C55E",  # tydlig grön för “lyckades”
    "danger":    "#F97373",  # röd/korall för fel/varning
    "warning":   "#F59E0B",  # orangegul varning
}

FONT_FAMILY = "Segoe UI"

# Environment / server
CURRENT_SERVER = "SBBESTPROD10"   # default PROD



def add_shadow(widget: tk.Widget, offset: int = 6, color: str = "#000000"):
    parent = widget.master
    shadow = tk.Frame(parent, bg=color, bd=0, highlightthickness=0)

    def update_shadow(_event=None):
        try:
            x = widget.winfo_x()
            y = widget.winfo_y()
            w = widget.winfo_width()
            h = widget.winfo_height()
            if w > 1 and h > 1:
                shadow.place(x=x + offset, y=y + offset, width=w, height=h)
                shadow.lower(widget)
        except tk.TclError:
            pass

    widget.bind("<Configure>", update_shadow)
    widget.bind("<Destroy>", lambda _e: shadow.destroy())

# ------------------------------------------------------------------------------------
#   BUTTON STYLE
# ------------------------------------------------------------------------------------

def style_primary_button_3d(btn: ctk.CTkButton):
    btn.configure(
        fg_color=PALETTE["primary"],
        hover_color=PALETTE["primary-2"],
        text_color="black",
        corner_radius=18,
        border_width=2,
        border_color="#065F46",
        font=(FONT_FAMILY, 13, "bold"),
        height=36
    )
    add_shadow(btn, offset=3, color="#020617")


def style_accent_button_3d(btn: ctk.CTkButton):
    btn.configure(
        fg_color=PALETTE["accent"],
        hover_color=PALETTE["warning"],
        text_color="black",
        corner_radius=18,
        border_width=2,
        border_color="#92400E",
        font=(FONT_FAMILY, 13, "bold"),
        height=36
    )
    add_shadow(btn, offset=3, color="#020617")

# --------------------------------------------------------------
#   Email skicka
# --------------------------------------------------------------

MESSAGE = ""

current_month_number = datetime.datetime.now().month    #Behövs för Space_I2E_STEPS
current_hour = datetime.datetime.now().hour             #Behövs för Cube VA + Genmod varuförsörjning

SEND_FROM_EMAIL = 'beslutsstod@systembolaget.se'
SEND_TO_EMAIL = 'best_driftst_rning@systembolaget.onmicrosoft.com;teamsortiment@systembolaget.se;'

# --- DEFAULT status dictionaries (används för reset) ---
DEFAULT_PROGNOS_DATA = {
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

DEFAULT_VISA_DATA = {
    "Assortment (alla utvärderingar)": "Succeeded",
    "Artikel (laddas efter kl 20 ikväll)": "Succeeded"
}

# Dessa globala variabler kommer att resetas i run_morning_report()
prognos_data = DEFAULT_PROGNOS_DATA.copy()
visa_data = DEFAULT_VISA_DATA.copy()

connection = None       #LOG IN
driftstörning = False   #Skicka MEJL eller ej
senVA = False           #Sen VA
senVF = False           #Sen VF

all_jobs_status = {}

prognos_html = "<p><b>Prognos</b><br>"
for name, status in prognos_data.items():
    prognos_html += f"{name} – {status}<br>"

visa_html = "<p><b>VISA:</b><br>"
for name, status in visa_data.items():
    visa_html += f"{name} – {status}<br>"

#Format med färg
def format_status_line(name, status):
    print(name, status)
    if status == "Succeeded":
        status_txt = 'klar'
        color = "green"
    else:
        color = "red"
        status_txt = 'x'
    return f"<span style='color:{color};'> {name} – {status_txt}</span>"


#Sen VA
def sendVAprocessingLate(send_from, input_message):
    olapp = win32.Dispatch('Outlook.Application')
    systemEmail = olapp.Session.Accounts[send_from]
    message = olapp.CreateItem(0)
    message.To = "Ida.Lund@systembolaget.se; Ewa-Li.Nyren@systembolaget.se; dryckesfakturor@systembolaget.se;"
    message.Subject = "Gårdagens försäljningsstatistik"
    message.HTMLBody = input_message
    message._oleobj_.Invoke(*(64209, 0, 8, 0, systemEmail))
    message.Display()

#Sen VF
def sendVFprocessingLate(send_from, input_message):
    olapp = win32.Dispatch('Outlook.Application')
    systemEmail = olapp.Session.Accounts[send_from]
    message = olapp.CreateItem(0)
    message.To = ("jenny.forssman@systembolaget.se; Ewa-Li.Nyren@systembolaget.se; "
                  "linda.carlberg@systembolaget.se; varuplanering@systembolaget.se; logistiker@systembolaget.se;")
    message.Subject = "Gårdagens försäljningsstatistik"
    message.HTMLBody = input_message
    message._oleobj_.Invoke(*(64209, 0, 8, 0, systemEmail))
    message.Display()


#Driftstörning
def sendDriftstorningsmail(send_from, send_to, input_message):
    olapp = win32.Dispatch('Outlook.Application')
    systemEmail = olapp.Session.Accounts[send_from]
    message = olapp.CreateItem(0)
    message.To = send_to
    message.Subject = "Gårdagens försäljningsstatistik"
    message.HTMLBody = input_message
    message._oleobj_.Invoke(*(64209, 0, 8, 0, systemEmail))
    message.Display()


sendLateMessageVA = """
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

sendLateMessageVF = """
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

#Logga in till SERVER (Prod10, Test10),  Ändra DRIVER till 17 OM EJ FUNGERAR

def authentic():
    global connection, CURRENT_SERVER
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={CURRENT_SERVER};"
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

#gå igenom varje jobb o deras status, uppdatera sedan Morgon mejlet
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
        if current_hour >= 8 and status == 'Running':
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

#checka job o status
def jobsSucceededOrFailed(job_status_dict):
    for job, status in job_status_dict.items():
        checkJob(job, status)

# KÖR querin för morgon jobben
def getMorningRapport():
    global all_jobs_status
    print(pyodbc.drivers())
    sql = open('queryForMorningRapport.txt', 'r').read()
    print(sql)
    data = pd.read_sql(sql, connection)
    print(data)

    # Bygg upp dict med alla jobb
    job_status_dict = dict(zip(data["JobName"], data["LastRunStatus"]))
    print(job_status_dict)

    # Spara globalt så vi kan visa dem i GUI
    all_jobs_status = job_status_dict

    # Befintlig logik som sätter prognos_data / visa_data
    jobsSucceededOrFailed(job_status_dict)

# Skapa morgon driftstörningmejl utifrån getMorningRapport). Den kör ALLA STEG
def run_morning_report():
    global MESSAGE, driftstörning, prognos_html, visa_html
    global senVA, senVF, sendLateMessageVA, sendLateMessageVF
    global prognos_data, visa_data

    # ⚠️ Reset all state varje gång vi kör – annars läcker TEST till PROD
    prognos_data = DEFAULT_PROGNOS_DATA.copy()
    visa_data = DEFAULT_VISA_DATA.copy()
    senVA = False
    senVF = False
    driftstörning = False

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

# --------------------------------------------------------------
#   PLANERADE FILE HANDLING
# --------------------------------------------------------------
PLANERADE_FILE = "planerade.txt"


def load_planerade():
    items = []
    try:
        with open(PLANERADE_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(";")]
                if len(parts) < 3:
                    continue
                date, text, status = parts[0], parts[1], parts[2]
                url = parts[3] if len(parts) > 3 and parts[3].strip() else None
                status = status.lower()
                if status not in ("open", "done"):
                    status = "open"
                items.append({"date": date, "text": text, "status": status, "url": url})
    except FileNotFoundError:
        pass

    #  Sortera alltid i datumordning innan vi returnerar
    items.sort(key=lambda x: x["date"])
    return items


def save_planerade(items):
    # Sortera alltid i datumordning (äldst → nyast)
    items = sorted(items, key=lambda x: x["date"])

    with open(PLANERADE_FILE, "w", encoding="utf-8") as f:
        for item in items:
            line = f"{item['date']}; {item['text']}; {item['status']}"
            if item.get("url"):
                line += f"; {item['url']}"
            f.write(line + "\n")


#GÖRA MODERN UI

class ModernApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        # sätt storlek + position lite högre upp
        w, h = 840, 650
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        x = (sw - w) // 2
        y = 40
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.title("BEST Drift • Systembolaget (PROD)")
        self.configure(fg_color=PALETTE["bg"])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.env_var = tk.StringVar(value="PROD")

        self.make_header()
        self.make_toolbar()
        self.make_content()

# HEADER

    def make_header(self):
        self.header = ctk.CTkFrame(self, fg_color=PALETTE["panel"], corner_radius=16)
        self.header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 10))
        add_shadow(self.header, offset=8, color="#020617")

        title = ctk.CTkLabel(
            self.header, text="🍃 BEST-Drift-BOT",
            font=(FONT_FAMILY, 28, "bold"), text_color=PALETTE["primary"]
        )
        subtitle = ctk.CTkLabel(
            self.header,
            text="Beslutsstöd • nattkörningar & driftsstatus",
            font=(FONT_FAMILY, 14), text_color=PALETTE["muted"]
        )

        stripe = ctk.CTkFrame(self.header, height=4, fg_color=PALETTE["accent"], corner_radius=2)

        title.pack(anchor="w", padx=20, pady=(15, 0))
        subtitle.pack(anchor="w", padx=20, pady=(0, 10))
        stripe.pack(fill="x")

 #TOOLBAREN

    def make_toolbar(self):
        self.toolbar = ctk.CTkFrame(self, fg_color="#020617", corner_radius=16)
        self.toolbar.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
        add_shadow(self.toolbar, offset=6, color="#000000")

        self.toolbar.grid_columnconfigure(10, weight=1)

        self.btn_drift = ctk.CTkButton(self.toolbar, text="🚦 Kör drift", command=self.check_drift)
        self.btn_etl = ctk.CTkButton(self.toolbar, text="📦 ETL idag", command=self.check_etl)
        self.btn_excel = ctk.CTkButton(
            self.toolbar, text="📊 Sena laddningar.xlsx",
            command=lambda: webbrowser.open(
                "https://systembolaget.sharepoint.com/:x:/s/Beslutsstd/"
                "EaQFAUEAtZhErNBSmVCrbcQB26W4XMIg1RvQXTHpaItH7A?e=KYtjcL"
            )
        )
        self.btn_plan = ctk.CTkButton(self.toolbar, text="🗓 Planerade", command=self.show_planerade)

        style_primary_button_3d(self.btn_drift)
        style_primary_button_3d(self.btn_etl)
        style_primary_button_3d(self.btn_excel)
        style_primary_button_3d(self.btn_plan)

        self.btn_drift.grid(row=0, column=0, padx=10, pady=12)
        self.btn_etl.grid(row=0, column=1, padx=10)
        self.btn_excel.grid(row=0, column=2, padx=10)
        self.btn_plan.grid(row=0, column=3, padx=10)

        # --- PROD / TEST radio ---
        radio_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        radio_frame.grid(row=0, column=4, padx=(20, 5), sticky="w")

        self.rad_prod = ctk.CTkRadioButton(
            radio_frame,
            text="PROD",
            variable=self.env_var,
            value="PROD",
            command=self.on_env_change,
            fg_color=PALETTE["primary"],
            border_color=PALETTE["stroke"],
            text_color=PALETTE["ink"],
            font=(FONT_FAMILY, 12, "bold")
        )
        self.rad_test = ctk.CTkRadioButton(
            radio_frame,
            text="TEST",
            variable=self.env_var,
            value="TEST",
            command=self.on_env_change,
            fg_color=PALETTE["primary"],
            border_color=PALETTE["stroke"],
            text_color=PALETTE["ink"],
            font=(FONT_FAMILY, 12, "bold")
        )

        # PROD överst, TEST direkt under
        self.rad_prod.pack(anchor="w")
        self.rad_test.pack(anchor="w", pady=(2, 0))

    def on_env_change(self):
        global CURRENT_SERVER
        val = self.env_var.get()
        if val == "PROD":
            CURRENT_SERVER = "SBBESTPROD10"
        else:
            CURRENT_SERVER = "SBBESTVTEST10"
        self.title(f"BEST Drift • Systembolaget ({val})")

  #MAIN

    def make_content(self):
        self.card = ctk.CTkFrame(self, corner_radius=18, fg_color=PALETTE["panel"])
        self.card.grid(row=2, column=0, sticky="nsew", padx=24, pady=(12, 24))
        add_shadow(self.card, offset=10, color="#020617")

        self.card.grid_rowconfigure(0, weight=1)
        self.card.grid_columnconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self.card, fg_color=PALETTE["panel"])
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.label_placeholder()

    def scroll_to_top(self):
        """Scrolla alltid till toppen i CTkScrollableFrame."""
        try:
            # parent_CANVAS
            self.scroll._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass


    def label_placeholder(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.scroll,
            text="Välj en åtgärd ovan för att hämta status…",
            font=(FONT_FAMILY, 16),
            text_color=PALETTE["muted"]
        ).pack(pady=15)

 #CHECKA DRIFT

    def check_drift(self):
        global driftstörning, senVA, senVF, MESSAGE, all_jobs_status

        # Töm scroll-innehållet
        for w in self.scroll.winfo_children():
            w.destroy()

        self.scroll_to_top()

        # Kör backend-logiken (sätter bl.a. prognos_data, visa_data, all_jobs_status)
        run_morning_report()


        env = self.env_var.get()  # "PROD" eller "TEST"

        # Kompakt text-widget
        text = tk.Text(
            self.scroll,
            bg=PALETTE["panel"],
            fg=PALETTE["ink"],
            bd=0,
            highlightthickness=0,
            font=(FONT_FAMILY, 15),
            spacing1=0,
            spacing2=0,
            spacing3=0
        )
        text.pack(fill="both", expand=True)

        # Tags
        text.tag_config("header", font=(FONT_FAMILY, 20, "bold"), foreground=PALETTE["primary"])
        text.tag_config("green", foreground=PALETTE["success"])
        text.tag_config("yellow", foreground=PALETTE["warning"])
        text.tag_config("red", foreground=PALETTE["danger"])

        # PROD + VISA

        if env == "PROD":
            #   TEXT ANG PROD
            text.insert("end", "Prognos\n", ("header",))
            for key, value in prognos_data.items():
                status_text = (
                    "klar" if value == "Succeeded"
                    else "pågår" if value == "Running"
                    else "fel"
                )
                line = f"• {key} – {status_text}\n"
                tag = "green" if value == "Succeeded" else ("yellow" if value == "Running" else "red")
                text.insert("end", line, (tag,))

            # TEXT ANG VISA
            text.insert("end", "\nVISA\n", ("header",))
            for key, value in visa_data.items():
                status_text = (
                    "klar" if value == "Succeeded"
                    else "pågår" if value == "Running"
                    else "fel"
                )
                line = f"• {key} – {status_text}\n"
                tag = "green" if value == "Succeeded" else ("yellow" if value == "Running" else "red")
                text.insert("end", line, (tag,))

        # ----- ALLA JOBB: alltid, både PROD och TEST -----
        text.insert("end", "\nAlla Jobb\n", ("header",))

        # all_jobs_status: { JobName: LastRunStatus }
        for job_name, status in all_jobs_status.items():
            if status == "Succeeded":
                tag = "white"
            elif status == "Running":
                tag = "yellow"
            else:
                tag = "red"
            line = f"{job_name} – {status}\n"
            text.insert("end", line, (tag,))

        # Read only, kan ej ändra
        text.config(state="disabled")

        # Mail/logik endast i PROD
        if env == "PROD":
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


 # ETL IDAG

    def check_etl(self):
        global connection
        for w in self.scroll.winfo_children():
            w.destroy()

        self.scroll_to_top()

        authentic() # LOGGA IN
        sql = open('queryForWhoLogETLidag.txt', 'r').read()
        df = pd.read_sql(sql, connection)

        # numerisk status
        df["CONTR_STUS_CD_NUM"] = pd.to_numeric(df["CONTR_STUS_CD"], errors="coerce")

        # 1) hitta alla PKG_NM som NÅGON gång haft status 0
        pkgs_with_zero = df.loc[df["CONTR_STUS_CD_NUM"] == 0, "PKG_NM"].unique()

        # 2) filtrera bort alla rader för dessa paket
        df_ok = df[~df["PKG_NM"].isin(pkgs_with_zero)].copy()

        # 3) gruppera på LINEAGE_ID
        load_to_rows = {}
        for LINEAGE_ID, group in df_ok.groupby("LINEAGE_ID"):
            load_to_rows[LINEAGE_ID] = group.to_dict(orient="records")

        ctk.CTkLabel(
            self.scroll, text="ETL idag",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=PALETTE["primary"]
        ).pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            self.scroll, text="Fel på nedanstående paket:",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=PALETTE["primary"]
        ).pack(anchor="w", pady=(0, 6))

        for LINEAGE_ID, rows in sorted(load_to_rows.items()):
            ctk.CTkLabel(
                self.scroll,
                text=f"LINEAGE_ID {LINEAGE_ID}",
                font=(FONT_FAMILY, 14, "bold"),
                text_color=PALETTE["ink"]
            ).pack(anchor="w", padx=6, pady=(2, 0))
            for row in rows:
                pkg_nm = row.get("PKG_NM", "")
                ctk.CTkLabel(
                    self.scroll,
                    text=f"  • {pkg_nm}",
                    font=(FONT_FAMILY, 13),
                    text_color=PALETTE["danger"]
                ).pack(anchor="w", padx=14)

        # --- COPY SQL BUTTON ---
        unique_lineages = sorted(df_ok["LINEAGE_ID"].unique())
        if len(unique_lineages) > 0:
            lineage_conditions = " or ".join(
                f"cl.LINEAGE_ID = {int(x)}" for x in unique_lineages
            )

#KOPIERA SQL QUERY TILL SSMS

            full_query = f"""
select LINEAGE_ID, LOAD_ID, LOAD_SEQ_NBR, THREAD_ID, CONTR_STUS_CD, CONTR_NM, CONTR_ST_DTM, CONTR_END_DTM,
       datediff(minute, CONTR_ST_DTM, CONTR_END_DTM) as CONTR_DURATION,
       LOAD_DT, PKG_NM, REC_STAGE_CNT, REC_INSERT_CNT, REC_UPDT_CNT, REC_DEL_CNT,
       REC_ERROR_CNT, REC_IGNR_CNT, SRC_FILE_FULL_NM, ARCHV_FILE_FULL_NM, REC_INSERTION_DT
from ETL_Config.dbo.ETL_Container_Log cl
where 1 = 1
  and cast(cl.CONTR_ST_DTM as date) = dateadd(day, -0, cast(getdate() as date))
  and ({lineage_conditions})
order by cl.CONTR_ST_DTM desc
""".strip()

            def copy_query():
                self.clipboard_clear()
                self.clipboard_append(full_query)
                self.update()

            btn_copy = ctk.CTkButton(
                self.scroll,
                text="📋 Kopiera SQL",
                command=copy_query
            )
            style_accent_button_3d(btn_copy)
            btn_copy.pack(anchor="w", padx=6, pady=(10, 0))

    # ----------------------------------------------------------
    #     PLANERADE
    # ----------------------------------------------------------

    def show_planerade(self):
        items = load_planerade()
        for w in self.scroll.winfo_children():
            w.destroy()

        self.scroll_to_top()

        ctk.CTkLabel(
            self.scroll, text="🗓 Planerade aktiviteter",
            font=(FONT_FAMILY, 20, "bold"),
            text_color=PALETTE["primary"]
        ).pack(anchor="w", pady=(0, 10))

        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(anchor="w", pady=10)

        btn_add = ctk.CTkButton(row, text="➕ Lägg till aktivitet", command=self.add_planerad_dialog)
        btn_remove = ctk.CTkButton(row, text="🗑 Ta bort markerade", command=self.remove_planerade_done)
        style_accent_button_3d(btn_add)
        style_accent_button_3d(btn_remove)
        btn_add.pack(side="left", padx=5)
        btn_remove.pack(side="left", padx=5)

        for idx, item in enumerate(items):
            self.render_planerad_item(item, idx, items)

    def render_planerad_item(self, item, index, items):
        outer = ctk.CTkFrame(self.scroll, fg_color="transparent")
        outer.pack(fill="x", pady=0, padx=2)

        frame = ctk.CTkFrame(outer, corner_radius=8, fg_color="#020617")
        frame.pack(fill="x", padx=2, pady=1)

        # Gör så att texten kan ta plats i mitten och antal dagar högerjusteras
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=0)

        var = tk.BooleanVar(value=(item["status"] == "done"))

        cb = ctk.CTkCheckBox(
            frame,
            text="",
            variable=var,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary-2"],
            border_color=PALETTE["stroke"],
            border_width=2,
            command=lambda: self.toggle_task(item, index, items, var, lbl)
        )
        cb.grid(row=0, column=0, padx=8, pady=4)

        base_font = tkfont.Font(family=FONT_FAMILY, size=14, weight="normal")
        strike_font = tkfont.Font(family=FONT_FAMILY, size=14, weight="normal")
        strike_font.configure(overstrike=1)

        txt = f"{item['date']} – {item['text']}"

        if item["status"] == "done":
            used_font = strike_font
            color = PALETTE["muted"]
        else:
            used_font = base_font
            color = PALETTE["ink"]

        lbl = tk.Label(
            frame,
            text=txt,
            bg="#020617",
            fg=color,
            font=used_font,
            anchor="w",
            justify="left"
        )
        lbl.grid(row=0, column=1, sticky="w", padx=4)

        lbl.base_font = base_font
        lbl.strike_font = strike_font

        # visa "X dagar kvar" med färgkodning ---

        days_left = None
        try:
            # item['date'] förväntas vara "yyyy-mm-dd"
            due_date = datetime.datetime.strptime(item["date"], "%Y-%m-%d").date()
            today = datetime.date.today()
            days_left = (due_date - today).days
        except Exception:
            days_left = None

        if days_left is not None:
            if days_left < 0:
                # datum har passerat
                days_text = f"{abs(days_left)} dagar sedan"
                days_color = PALETTE["danger"]
            elif days_left == 0:
                days_text = "Idag"
                days_color = PALETTE["danger"]
            elif days_left == 1:
                days_text = "1 dag kvar"
                days_color = PALETTE["danger"]
            else:
                days_text = f"{days_left} dagar kvar"
                if days_left < 5:
                    days_color = PALETTE["warning"]
                else:
                    days_color = PALETTE["success"]

            days_lbl = tk.Label(
                frame,
                text=days_text,
                bg="#020617",
                fg=days_color,
                font=(FONT_FAMILY, 12, "bold"),
                anchor="e",
                justify="right"
            )
            days_lbl.grid(row=0, column=2, sticky="e", padx=8)

        if item.get("url"):
            lbl.config(cursor="hand2")

            def on_enter(_evt=None, label=lbl):
                label.config(fg="#60A5FA")

            def on_leave(_evt=None, label=lbl, c=color):
                label.config(fg=c)

            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)
            lbl.bind(
                "<Button-1>",
                lambda e, u=item["url"]: webbrowser.open(u)
            )

    def toggle_task(self, item, index, items, var, lbl):
        item["status"] = "done" if var.get() else "open"
        items[index] = item
        save_planerade(items)

        if item["status"] == "done":
            lbl.config(fg=PALETTE["muted"], font=lbl.strike_font)
        else:
            lbl.config(fg=PALETTE["ink"], font=lbl.base_font)

    # ----------------------------------------------------------
    #   LÄGG TILL AKTIVITET
    # ----------------------------------------------------------

    def add_planerad_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Lägg till aktivitet")
        dlg.geometry("400x450")
        dlg.grab_set()

        ctk.CTkLabel(
            dlg, text="Välj datum:",
            font=(FONT_FAMILY, 14, "bold")
        ).pack(pady=(20, 4))

        cal = Calendar(
            dlg,
            selectmode="day",
            date_pattern="yyyy-mm-dd",
            showweeknumbers=False,
            font=("Segoe UI", 14),
            weekendbackground="white",
            weekendforeground="black",
            background="white",
            foreground="black",
            headersbackground="#EAB308",
            headersforeground="black",
            bordercolor="#A7A7A7",
            disabledforeground="gray",
            cursor="hand2"
        )
        cal.pack(pady=10, ipadx=10, ipady=10)

        ctk.CTkLabel(dlg, text="Beskrivning:", font=(FONT_FAMILY, 13)).pack(anchor="w", padx=20)
        txt = ctk.CTkEntry(dlg, width=300)
        txt.pack(pady=5)

        ctk.CTkLabel(dlg, text="URL (valfritt):", font=(FONT_FAMILY, 13)).pack(anchor="w", padx=20)
        url = ctk.CTkEntry(dlg, width=300)
        url.pack(pady=5)

        def save_item():
            desc = txt.get().strip()
            if not desc:
                messagebox.showerror("Fel", "Beskrivning måste fyllas i.")
                return
            items = load_planerade()
            items.append({
                "date": cal.get_date(),
                "text": desc,
                "status": "open",
                "url": url.get().strip() or None
            })
            save_planerade(items)
            dlg.destroy()
            self.show_planerade()

        save_btn = ctk.CTkButton(dlg, text="Spara", command=save_item)
        style_primary_button_3d(save_btn)
        save_btn.pack(pady=10)

    def remove_planerade_done(self):
        items = load_planerade()
        new_items = [x for x in items if x["status"] != "done"]
        if len(new_items) == len(items):
            messagebox.showinfo("Info", "Det finns inga markerade aktiviteter att ta bort.")
        save_planerade(new_items)
        self.show_planerade()



ModernApp().mainloop()