"""
main.py
Point d'entrée principal de l'agent de traitement de tickets.
Orchestre : lecture Gmail → classification LLM → écriture Google Sheet.
"""

import time
from dotenv import load_dotenv
import os

from mail_reader import get_gmail_service, fetch_unread_emails
from agent_mail import classify_mail
from drive_client import DriveClient

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
DELAY_BETWEEN_CALLS = 0.5  # secondes entre chaque appel LLM

# Mapping classification LLM → nom exact de la feuille Google Sheet
CATEGORY_TO_SHEET = {
    "Problème technique informatique": "probleme_technique_informatique",
    "Demande administrative": "demande_administrative",
    "Problème d'accès": "probleme_acces_authentification",
    "Support utilisateur": "support_utilisateur",
    "Bug": "bug_service",
}


def process_ticket(service, drive: DriveClient, ticket: dict, index: int, total: int):
    """
    Traite un ticket complet :
    1. Classifie via LLM
    2. Écrit dans Google Sheet
    3. Marque le mail comme lu
    """
    sujet = ticket.get("sujet", "(Sans sujet)")
    corps = ticket.get("corps", "")
    mail_id = ticket.get("id")

    print(f"\n[{index}/{total}] 📧 {sujet[:65]}...")

    # ── 1. Classification LLM ─────────────────────────────────────────────────
    mail_content = f"Sujet : {sujet}\n\n{corps}"
    classification = classify_mail(mail_content)

    categorie = classification.get("categorie", "Support utilisateur")
    urgence = classification.get("urgence", "Modérée")
    resume = classification.get("résumé", sujet)

    print(f"         → Catégorie : {categorie}")
    print(f"         → Urgence   : {urgence}")
    print(f"         → Synthèse  : {resume[:80]}...")

    # ── 2. Écriture dans Google Sheet ─────────────────────────────────────────
    sheet_name = CATEGORY_TO_SHEET.get(categorie, "support_utilisateur")
    drive.write_to_sheet(sheet_name, sujet, urgence, resume)

    # ── 3. Marquer le mail comme lu ───────────────────────────────────────────
    service.users().messages().modify(
        userId="me",
        id=mail_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


def main():
    print("=" * 60)
    print("   AGENT DE TRAITEMENT DE TICKETS")
    print("=" * 60)

    # ── Initialisation des clients ─────────────────────────────────────────────
    print("\n🔐 Connexion à Gmail...")
    gmail_service = get_gmail_service()

    print("📊 Connexion à Google Sheets...")
    drive = DriveClient(SPREADSHEET_ID)

    # ── Lecture des mails non lus ──────────────────────────────────────────────
    tickets = fetch_unread_emails(gmail_service, max_results=500, mark_as_read=False)

    if not tickets:
        print("\n✅ Aucun mail non lu à traiter.")
        return

    total = len(tickets)
    print(f"\n🚀 Début du traitement de {total} ticket(s)...\n")

    success = 0
    errors = 0

    # ── Traitement ticket par ticket ───────────────────────────────────────────
    for i, ticket in enumerate(tickets, 1):
        try:
            process_ticket(gmail_service, drive, ticket, i, total)
            success += 1
        except Exception as e:
            errors += 1
            print(
                f"         ❌ Erreur sur le ticket '{ticket.get('sujet', '?')}' : {e}"
            )

        # Pause entre chaque appel LLM
        if i < total:
            time.sleep(DELAY_BETWEEN_CALLS)

    # ── Tri et formatage final du Google Sheet ────────────────────────────────
    drive.finalize_all_sheets()

    # ── Résumé final ───────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"   ✅ Traitement terminé")
    print(f"   → Succès  : {success}/{total}")
    if errors:
        print(f"   → Erreurs : {errors}/{total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
