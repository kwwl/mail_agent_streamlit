# 🎫 Email Checker — Agent de tri intelligent d'emails

Application Streamlit permettant de classifier automatiquement des emails Gmail grâce à l'IA (Groq + LLaMA).

---

## 🚀 Fonctionnalités

- 🔐 Authentification SSO Google
- 📬 Lecture des emails Gmail non lus
- 🤖 Classification automatique par catégorie et niveau d'urgence
- 📊 Dashboard interactif avec graphiques
- 💾 Export Excel et Google Sheets
- 🗑️ Suppression des emails depuis l'interface

---

## ⚠️ Limitation d'accès importante

L'application est actuellement déployée en **mode test** sur Google Cloud.

Cela signifie que **tout le monde ne peut pas se connecter** même si l'app est accessible publiquement sur Streamlit Cloud.

### Pourquoi ?

Lors de la création d'une application OAuth2 sur Google Cloud Console, l'app passe par deux états :

- **Mode Test** (actuel) : seuls les comptes Google ajoutés manuellement comme *testeurs* dans la Google Cloud Console peuvent s'authentifier. Tout autre compte reçoit une erreur `403 access_denied`.
- **Mode Production** : n'importe quel compte Google peut se connecter, mais nécessite une validation par Google (processus de vérification).

### Comment autoriser un nouvel utilisateur ?

Pour l'instant, la seule solution est d'ajouter manuellement l'email de l'utilisateur dans :

> Google Cloud Console → APIs & Services → OAuth consent screen → Test users → Add users

---

## 🛠️ Installation locale

### Prérequis

- Python 3.10+
- Un compte Google Cloud avec les APIs Gmail et Drive activées
- Une clé API Groq

### 1. Cloner le projet
```bash
git clone https://github.com/ton-repo/classification_mail.git
cd classification_mail
```

### 2. Créer un environnement virtuel
```bash
python3 -m venv env
source env/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les secrets
```bash
mkdir -p .streamlit
```

Créer le fichier `.streamlit/secrets.toml` :
```toml
GROQ_KEY = "gsk_xxxxxxxxxxxx"
GOOGLE_CLIENT_ID = "xxxxxxxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "GOCSPX-xxxxxxxx"
REDIRECT_URI = "http://localhost:8501"
MAIL_PROVIDER = "gmail"
```

### 5. Lancer l'application
```bash
streamlit run app.py
```

---

## 🏗️ Architecture du projet
```
classification_mail/
│
├── 📱 INTERFACE
│   └── app.py                  # Interface Streamlit principale
│
├── 🤖 AGENT IA
│   ├── agent_mail.py           # Classification des emails via Groq
│   ├── context.txt             # Contexte injecté dans le prompt LLM
│   └── prompt.txt              # Prompt de base du LLM
│
├── 📬 LECTURE DES EMAILS
│   └── mail_reader.py          # Lecture des emails Gmail
│
├── 🔗 GOOGLE
│   ├── credentials.json        # Identifiants OAuth2 Google Cloud
│   ├── generate_token.py       # Script de génération du token Gmail
│   └── drive_client.py         # Client Google Drive / Sheets
│
├── ⚙️ CONFIGURATION
│   ├── .env                    # Variables d'environnement (local)
│   ├── .streamlit/             # Config Streamlit (secrets.toml)
│   ├── requirements.txt        # Dépendances Python
│   └── .gitignore              # Fichiers exclus de GitHub
│
└── 📄 DOCS
    ├── README.md
    └── LICENSE
```

---

## 🔑 Variables d'environnement

| Variable | Description |
|----------|-------------|
| `GROQ_KEY` | Clé API Groq (console.groq.com) |
| `GOOGLE_CLIENT_ID` | Client ID OAuth2 Google Cloud |
| `GOOGLE_CLIENT_SECRET` | Client Secret OAuth2 Google Cloud |
| `REDIRECT_URI` | URI de redirection OAuth2 |
| `MAIL_PROVIDER` | Provider mail (`gmail` ou `imap`) |

---

## 👥 Auteurs

Kémil Lamouri & Mathias Segura — HETIC 2026
