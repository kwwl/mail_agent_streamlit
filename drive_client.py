import os
import time
from collections import defaultdict
import gspread
from gspread_formatting import (
    batch_updater,
    CellFormat,
    Color,
    TextFormat,
    set_column_width,
)
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials

load_dotenv()
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CATEGORIES = [
    "probleme_technique_informatique",
    "demande_administrative",
    "probleme_acces_authentification",
    "support_utilisateur",
    "bug_service",
]

URGENCY_ORDER = {
    "Critique": 0,
    "Élevée": 1,
    "Modérée": 2,
    "Faible": 3,
    "Anodine": 4,
}

URGENCY_COLORS = {
    "Critique": Color(0.96, 0.26, 0.21),
    "Élevée": Color(1.00, 0.60, 0.00),
    "Modérée": Color(1.00, 0.90, 0.20),
    "Faible": Color(0.42, 0.78, 0.42),
    "Anodine": Color(0.53, 0.81, 0.98),
}

HEADER_BG_COLOR = Color(0.20, 0.40, 0.75)
HEADER_TEXT_COLOR = Color(1, 1, 1)


class DriveClient:
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(self.sheet_id)
        self._ensure_sheets_exist()

    def _ensure_sheets_exist(self):
        existing_sheets = [ws.title for ws in self.sheet.worksheets()]
        for cat in CATEGORIES:
            if cat not in existing_sheets:
                ws = self.sheet.add_worksheet(title=cat, rows="1000", cols="3")
                ws.append_row(["Sujet", "Urgence", "Synthèse"])
                print(f"Feuille '{cat}' créée")
            else:
                ws = self.sheet.worksheet(cat)
                if ws.row_values(1) != ["Sujet", "Urgence", "Synthèse"]:
                    ws.insert_row(["Sujet", "Urgence", "Synthèse"], 1)

    def write_to_sheet(self, categorie, sujet, urgence, synthese):
        try:
            worksheet = self.sheet.worksheet(categorie)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.sheet.add_worksheet(title=categorie, rows="1000", cols="3")
            worksheet.append_row(["Sujet", "Urgence", "Synthèse"])
        worksheet.append_row([sujet, urgence, synthese])
        print(f" Ajouté dans '{categorie}' : {sujet[:50]}")

    def finalize_all_sheets(self):
        print("\n Finalisation des feuilles Google Sheet")
        for cat in CATEGORIES:
            try:
                ws = self.sheet.worksheet(cat)
                print(f"  → Tri de '{cat}'")
                self._sort_sheet(ws)
                time.sleep(2)
                print(f"  → Formatage de '{cat}'")
                self._format_sheet(ws)
                time.sleep(3)
                print(f"'{cat}' trié et formaté.")
            except gspread.exceptions.WorksheetNotFound:
                print(f" Feuille '{cat}' introuvable, ignorée")
        print("Formatage terminé")

    def _sort_sheet(self, worksheet):
        all_rows = worksheet.get_all_values()
        if len(all_rows) <= 1:
            return
        header = all_rows[0]
        data = sorted(all_rows[1:], key=lambda row: URGENCY_ORDER.get(row[1], 99))
        worksheet.clear()
        time.sleep(1)
        worksheet.append_row(header)
        if data:
            worksheet.append_rows(data)

    def _format_sheet(self, worksheet):
        # Envoie tout le formatage en UN SEUL batch par feuille pour éviter le rate limit 429.
        all_rows = worksheet.get_all_values()
        if len(all_rows) <= 1:
            return

        with batch_updater(worksheet.spreadsheet) as batch:
            # En-têtes
            batch.format_cell_range(
                worksheet,
                "A1:C1",
                CellFormat(
                    backgroundColor=HEADER_BG_COLOR,
                    textFormat=TextFormat(
                        bold=True,
                        foregroundColor=HEADER_TEXT_COLOR,
                        fontSize=11,
                    ),
                ),
            )
            # Couleurs urgence
            for i, row in enumerate(all_rows[1:], start=2):
                urgence = row[1] if len(row) > 1 else ""
                color = URGENCY_COLORS.get(urgence)
                if color:
                    batch.format_cell_range(
                        worksheet,
                        f"B{i}",
                        CellFormat(
                            backgroundColor=color,
                            textFormat=TextFormat(bold=True),
                        ),
                    )

        # Largeurs (appels séparés, pas dans le batch)
        time.sleep(1)
        set_column_width(worksheet, "A", 300)
        time.sleep(0.5)
        set_column_width(worksheet, "B", 120)
        time.sleep(0.5)
        set_column_width(worksheet, "C", 500)
