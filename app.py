"""
app_sso.py
Interface Streamlit avec authentification SSO Google.
Création automatique du Google Sheet à la connexion.
"""

import streamlit as st
from streamlit_oauth import OAuth2Component
import os
import gspread
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from agent_mail import classify_mail
import time

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Agent de Traitement de Tickets - SSO", page_icon="🎫", layout="wide"
)

# OAuth2 Configuration
CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
CLIENT_SECRET = st.secrets.get(
    "GOOGLE_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET")
)
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "http://localhost:8501")

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

CATEGORIES = [
    "probleme_technique_informatique",
    "demande_administrative",
    "probleme_acces_authentification",
    "support_utilisateur",
    "bug_service",
]

CATEGORY_MAP = {
    "Problème technique informatique": "probleme_technique_informatique",
    "Demande administrative": "demande_administrative",
    "Problème d'accès": "probleme_acces_authentification",
    "Support utilisateur": "support_utilisateur",
    "Bug": "bug_service",
}

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

if "token" not in st.session_state:
    st.session_state.token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "sheet_id" not in st.session_state:
    st.session_state.sheet_id = None
if "sheet_url" not in st.session_state:
    st.session_state.sheet_url = None

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════


def get_user_info(token):
    """Récupère les infos utilisateur."""
    import requests

    headers = {"Authorization": f"Bearer {token['access_token']}"}
    response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo", headers=headers
    )
    return response.json() if response.status_code == 200 else None


def create_google_sheet(creds, user_email):
    """Crée automatiquement un Google Sheet avec les 5 feuilles."""
    try:
        client = gspread.authorize(creds)

        # Créer le Sheet
        sheet_name = f"Tickets - {user_email.split('@')[0]}"
        spreadsheet = client.create(sheet_name)

        # Donner les droits à l'utilisateur
        spreadsheet.share(user_email, perm_type="user", role="writer")

        # Supprimer la feuille par défaut
        default_sheet = spreadsheet.sheet1

        # Créer les 5 feuilles avec en-têtes
        for cat in CATEGORIES:
            ws = spreadsheet.add_worksheet(title=cat, rows=1000, cols=3)
            ws.append_row(["Sujet", "Urgence", "Synthèse"])

        # Supprimer la feuille par défaut après avoir créé les autres
        spreadsheet.del_worksheet(default_sheet)

        return spreadsheet.id, spreadsheet.url

    except Exception as e:
        st.error(f"Erreur création Sheet : {e}")
        return None, None


def logout():
    """Déconnexion."""
    st.session_state.token = None
    st.session_state.user_info = None
    st.session_state.sheet_id = None
    st.session_state.sheet_url = None
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE DE LOGIN
# ══════════════════════════════════════════════════════════════════════════════


def login_page():
    """Page de connexion SSO."""

    st.markdown(
        '<h1 class="main-header">🎫 Agent de Traitement de Tickets</h1>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
        ### 🔐 Connexion requise
        
        Connectez-vous avec votre compte Google pour :
        - ✅ Lire vos emails Gmail
        - ✅ Créer automatiquement votre Google Sheet
        - ✅ Classifier vos tickets intelligemment
        """
        )

        st.info(
            """
        **🔒 Sécurité :**
        - Authentification Google officielle
        - Aucun mot de passe stocké
        - Révocable à tout moment
        """
        )

        # Bouton OAuth2
        oauth2 = OAuth2Component(
            CLIENT_ID,
            CLIENT_SECRET,
            AUTHORIZATION_URL,
            TOKEN_URL,
            REDIRECT_URI,
        )

        result = oauth2.authorize_button(
            name="🔑 Connexion avec Google",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope=" ".join(SCOPES),
            key="google_oauth",
            extras_params={"prompt": "consent", "access_type": "offline"},
        )

        if result and "token" in result:
            with st.spinner("🔄 Initialisation de votre espace..."):
                # Sauvegarder le token
                st.session_state.token = result["token"]

                # Récupérer info utilisateur
                user_info = get_user_info(result["token"])
                st.session_state.user_info = user_info

                # Créer les credentials
                creds = Credentials(
                    token=result["token"]["access_token"],
                    refresh_token=result["token"].get("refresh_token"),
                    token_uri=TOKEN_URL,
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    scopes=SCOPES,
                )

                # Créer le Google Sheet automatiquement
                sheet_id, sheet_url = create_google_sheet(creds, user_info["email"])

                if sheet_id:
                    st.session_state.sheet_id = sheet_id
                    st.session_state.sheet_url = sheet_url
                    st.success("✅ Google Sheet créé avec succès !")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la création du Sheet")


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════


def main_app():
    """Application principale."""

    st.markdown(
        '<h1 class="main-header">🎫 Agent de Traitement de Tickets</h1>',
        unsafe_allow_html=True,
    )

    # Créer les credentials
    creds = Credentials(
        token=st.session_state.token["access_token"],
        refresh_token=st.session_state.token.get("refresh_token"),
        token_uri=TOKEN_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    # Sidebar
    with st.sidebar:
        if st.session_state.user_info:
            st.image(st.session_state.user_info.get("picture", ""), width=80)
            st.markdown(f"**{st.session_state.user_info.get('name', 'Utilisateur')}**")
            st.caption(st.session_state.user_info.get("email", ""))

        if st.button("🚪 Se déconnecter", use_container_width=True):
            logout()

        st.markdown("---")

        st.success(f"📊 [Votre Google Sheet]({st.session_state.sheet_url})")

        st.markdown("---")

        st.header("🎛️ Paramètres")
        max_emails = st.number_input("Emails à traiter", 1, 500, 10, 10)
        mark_as_read = st.checkbox("Marquer comme lus")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🚀 Traitement", "📊 Dashboard", "📖 Guide"])

    with tab1:
        st.header("🚀 Traiter vos emails")

        # Récupérer la clé Groq depuis les secrets
        groq_key = st.secrets.get("GROQ_KEY", os.getenv("GROQ_KEY"))

        if not groq_key:
            st.error("❌ Clé API Groq manquante. Contactez l'administrateur.")
            return

        st.info(
            f"""
        **Configuration :**
        - 📧 Compte : {st.session_state.user_info.get('email')}
        - 📊 [Voir le Google Sheet]({st.session_state.sheet_url})
        - 📨 Emails à traiter : {max_emails}
        - ✅ Marquer comme lu : {'Oui' if mark_as_read else 'Non'}
        """
        )

        if st.button(
            "▶️ Lancer le traitement", type="primary", use_container_width=True
        ):

            os.environ["GROQ_KEY"] = groq_key

            progress_bar = st.progress(0)
            status_text = st.empty()
            log_container = st.empty()

            logs = []

            def log(msg):
                logs.append(msg)
                log_container.text_area("📋 Logs", "\n".join(logs[-15:]), height=200)

            try:
                # Gmail
                log("📬 Connexion à Gmail...")
                gmail = build("gmail", "v1", credentials=creds)

                response = (
                    gmail.users()
                    .messages()
                    .list(
                        userId="me",
                        q="is:unread",
                        maxResults=max_emails,
                        labelIds=["INBOX"],
                    )
                    .execute()
                )

                messages = response.get("messages", [])

                if not messages:
                    log("✅ Aucun email non lu")
                    st.success("✅ Aucun email à traiter")
                    return

                log(f"✅ {len(messages)} email(s) trouvé(s)")

                # Google Sheets
                log("📊 Connexion à Google Sheets...")
                gc = gspread.authorize(creds)
                sheet = gc.open_by_key(st.session_state.sheet_id)

                # Traitement
                success = 0
                errors = 0

                for i, msg in enumerate(messages):
                    try:
                        # Récupérer le message
                        msg_detail = (
                            gmail.users()
                            .messages()
                            .get(userId="me", id=msg["id"], format="full")
                            .execute()
                        )

                        # Extraire sujet et corps
                        headers = msg_detail["payload"]["headers"]
                        sujet = next(
                            (
                                h["value"]
                                for h in headers
                                if h["name"].lower() == "subject"
                            ),
                            "(Sans sujet)",
                        )

                        # Corps simplifié
                        payload = msg_detail["payload"]
                        corps = ""
                        if "body" in payload and payload["body"].get("data"):
                            import base64

                            corps = base64.urlsafe_b64decode(
                                payload["body"]["data"]
                            ).decode("utf-8", errors="ignore")[:1000]

                        status_text.text(f"[{i+1}/{len(messages)}] {sujet[:50]}...")

                        # Classification
                        mail_content = f"Sujet : {sujet}\n\n{corps}"
                        classification = classify_mail(mail_content)

                        categorie = classification.get(
                            "categorie", "Support utilisateur"
                        )
                        urgence = classification.get("urgence", "Modérée")
                        resume = classification.get("résumé", sujet)

                        log(f"  → {categorie} | {urgence}")

                        # Écrire dans Sheet
                        sheet_name = CATEGORY_MAP.get(categorie, "support_utilisateur")
                        ws = sheet.worksheet(sheet_name)
                        ws.append_row([sujet, urgence, resume])

                        # Marquer comme lu
                        if mark_as_read:
                            gmail.users().messages().modify(
                                userId="me",
                                id=msg["id"],
                                body={"removeLabelIds": ["UNREAD"]},
                            ).execute()

                        success += 1

                    except Exception as e:
                        errors += 1
                        log(f"  ❌ Erreur : {str(e)[:80]}")

                    progress_bar.progress((i + 1) / len(messages))
                    time.sleep(0.5)  # Rate limiting

                log(f"\n✅ Terminé : {success}/{len(messages)} succès")

                # Tri et formatage des feuilles
                if success > 0:
                    log("\n🎨 Tri et formatage des feuilles...")

                    from gspread_formatting import (
                        format_cell_range,
                        batch_updater,
                        CellFormat,
                        Color,
                        TextFormat,
                        set_column_width,
                    )

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
                    HEADER_BG = Color(0.20, 0.40, 0.75)
                    HEADER_TEXT = Color(1, 1, 1)

                    for cat in CATEGORIES:
                        try:
                            ws = sheet.worksheet(cat)

                            # Tri par urgence
                            all_rows = ws.get_all_values()
                            if len(all_rows) > 1:
                                header = all_rows[0]
                                data = sorted(
                                    all_rows[1:],
                                    key=lambda r: URGENCY_ORDER.get(r[1], 99),
                                )
                                ws.clear()
                                time.sleep(1)
                                ws.append_row(header)
                                if data:
                                    ws.append_rows(data)
                                time.sleep(1)

                            # Formatage
                            all_rows = ws.get_all_values()
                            if len(all_rows) > 1:
                                with batch_updater(sheet) as batch:
                                    # En-têtes
                                    batch.format_cell_range(
                                        ws,
                                        "A1:C1",
                                        CellFormat(
                                            backgroundColor=HEADER_BG,
                                            textFormat=TextFormat(
                                                bold=True,
                                                foregroundColor=HEADER_TEXT,
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
                                                ws,
                                                f"B{i}",
                                                CellFormat(
                                                    backgroundColor=color,
                                                    textFormat=TextFormat(bold=True),
                                                ),
                                            )

                                time.sleep(1)
                                set_column_width(ws, "A", 300)
                                time.sleep(0.5)
                                set_column_width(ws, "B", 120)
                                time.sleep(0.5)
                                set_column_width(ws, "C", 500)

                            log(f"  ✅ '{cat}' formaté")

                        except Exception as e:
                            log(f"  ⚠️ Erreur formatage '{cat}': {str(e)[:50]}")

                    log("✅ Formatage terminé")

                if success > 0:
                    st.success(f"🎉 {success} ticket(s) traité(s) avec succès !")
                    st.markdown(
                        f"[📊 Voir les résultats dans le Sheet]({st.session_state.sheet_url})"
                    )

                if errors > 0:
                    st.warning(f"⚠️ {errors} erreur(s)")

            except Exception as e:
                log(f"❌ Erreur fatale : {e}")
                st.error(f"Erreur : {e}")

    with tab2:
        st.header("📊 Dashboard des tickets")

        try:
            # Récupérer toutes les données du Sheet
            gc = gspread.authorize(creds)
            sheet_data = gc.open_by_key(st.session_state.sheet_id)

            all_tickets = []
            for cat in CATEGORIES:
                try:
                    ws = sheet_data.worksheet(cat)
                    rows = ws.get_all_records()
                    for row in rows:
                        row["Catégorie"] = cat.replace("_", " ").title()
                    all_tickets.extend(rows)
                except:
                    continue

            if not all_tickets:
                st.info(
                    "📭 Aucun ticket traité pour le moment. Lancez un traitement dans l'onglet 'Traitement'."
                )
            else:
                import pandas as pd
                import plotly.express as px
                import plotly.graph_objects as go
                from io import BytesIO

                df = pd.DataFrame(all_tickets)

                # KPIs en haut
                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.metric("📬 Total tickets", len(df))

                with col2:
                    critical = (
                        len(df[df["Urgence"] == "Critique"])
                        if "Urgence" in df.columns
                        else 0
                    )
                    st.metric("🔴 Critiques", critical)

                with col3:
                    elevated = (
                        len(df[df["Urgence"] == "Élevée"])
                        if "Urgence" in df.columns
                        else 0
                    )
                    st.metric("🟠 Élevées", elevated)

                with col4:
                    categories_count = (
                        df["Catégorie"].nunique() if "Catégorie" in df.columns else 0
                    )
                    st.metric("📁 Catégories", categories_count)

                with col5:
                    avg_synth = (
                        int(df["Synthèse"].str.len().mean())
                        if "Synthèse" in df.columns
                        else 0
                    )
                    st.metric("📝 Moy. synthèse", f"{avg_synth} car.")

                st.markdown("---")

                # Graphiques interactifs
                col1, col2 = st.columns(2)

                with col1:
                    if "Catégorie" in df.columns:
                        fig_cat = px.pie(
                            df,
                            names="Catégorie",
                            title="📊 Répartition par catégorie",
                            hole=0.4,
                            color_discrete_sequence=px.colors.qualitative.Pastel,
                        )
                        fig_cat.update_traces(
                            textposition="inside", textinfo="percent+label"
                        )
                        st.plotly_chart(fig_cat, use_container_width=True)

                with col2:
                    if "Urgence" in df.columns:
                        urgency_order = [
                            "Critique",
                            "Élevée",
                            "Modérée",
                            "Faible",
                            "Anodine",
                        ]
                        urgency_counts = (
                            df["Urgence"]
                            .value_counts()
                            .reindex(urgency_order, fill_value=0)
                        )

                        colors = ["#F44336", "#FF9800", "#FFEB3B", "#4CAF50", "#2196F3"]

                        fig_urg = go.Figure(
                            data=[
                                go.Bar(
                                    x=urgency_counts.index,
                                    y=urgency_counts.values,
                                    marker_color=colors,
                                    text=urgency_counts.values,
                                    textposition="outside",
                                )
                            ]
                        )
                        fig_urg.update_layout(
                            title="🔥 Distribution par urgence",
                            xaxis_title="Niveau d'urgence",
                            yaxis_title="Nombre de tickets",
                            showlegend=False,
                        )
                        st.plotly_chart(fig_urg, use_container_width=True)

                st.markdown("---")

                # Matrice Catégorie × Urgence
                if "Catégorie" in df.columns and "Urgence" in df.columns:
                    st.subheader("🔥 Matrice Catégorie × Urgence")

                    pivot = pd.crosstab(df["Catégorie"], df["Urgence"])
                    pivot = pivot.reindex(
                        columns=["Critique", "Élevée", "Modérée", "Faible", "Anodine"],
                        fill_value=0,
                    )

                    fig_heat = px.imshow(
                        pivot,
                        labels=dict(x="Urgence", y="Catégorie", color="Nombre"),
                        color_continuous_scale="RdYlGn_r",
                        text_auto=True,
                        aspect="auto",
                    )
                    fig_heat.update_xaxes(side="top")
                    st.plotly_chart(fig_heat, use_container_width=True)

                st.markdown("---")

                # Tableau des derniers tickets
                st.subheader("📋 Derniers tickets traités")
                st.dataframe(
                    df[["Sujet", "Urgence", "Catégorie", "Synthèse"]].tail(15),
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("---")

                # Section téléchargement
                st.subheader("💾 Télécharger les données")

            col1, col2 = st.columns(2)

            with col1:
                # Export Excel
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Tous les tickets", index=False)
                    for cat in df["Catégorie"].unique():
                        cat_df = df[df["Catégorie"] == cat]
                        cat_df.to_excel(writer, sheet_name=cat[:30], index=False)
                buffer.seek(0)
                st.download_button(
                    label="📥 Télécharger Excel",
                    data=buffer.getvalue(),
                    file_name="tickets.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

                with col2:
                    # Lien vers le Google Sheet
                    st.link_button(
                        label="🔗 Ouvrir Google Sheet",
                        url=st.session_state.sheet_url,
                        use_container_width=True,
                    )

        except Exception as e:
            st.error(f"❌ Erreur lors du chargement du dashboard : {e}")

    with tab2:
        st.header("📖 Guide d'utilisation")

        st.markdown(
            """
        ### 🚀 Comment ça marche ?
        
        1. **Connexion** : Vous vous êtes connecté avec votre compte Google
        2. **Sheet créé** : Un Google Sheet a été créé automatiquement dans votre Drive
        3. **Traitement** : Lancez le traitement de vos emails
        4. **Résultats** : Consultez vos tickets organisés dans le Sheet
        
        ### 📊 Structure du Sheet
        
        Votre Sheet contient 5 feuilles :
        - 🔧 Problème technique informatique
        - 📋 Demande administrative
        - 🔐 Problème d'accès / authentification
        - 💬 Support utilisateur
        - 🐛 Bug ou dysfonctionnement
        
        Chaque ticket est classé automatiquement avec son niveau d'urgence (Critique → Anodine).
    
        """
        )


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if st.session_state.token is None:
        login_page()
    else:
        main_app()
