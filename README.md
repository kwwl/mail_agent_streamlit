# Agent de Traitement Automatique de Tickets

Système qui lit des emails, les classifie avec un LLM, et les organise automatiquement dans un Google Sheet.

## Ce qu'il fait

1. Lit les emails non lus dans Gmail
2. Analyse chaque email avec Groq (LLM)
3. Détermine la catégorie et l'urgence
4. Écrit tout dans un Google Sheet trié et formaté

**Résultat :** 500 emails traités en 5 minutes, organisés par priorité avec code couleur.

## Installation

```bash
# Cloner le projet
cd classification_mail

# Créer environnement virtuel
python3 -m venv env
source env/bin/activate

# Installer dépendances
pip install -r requirements.txt
```

## Configuration

### 1. Google Cloud Console

1. Créer un projet sur [console.cloud.google.com](https://console.cloud.google.com)
2. Activer **Gmail API** et **Google Sheets API**
3. Créer OAuth 2.0 Client ID (type **Desktop app**)
4. Télécharger le JSON → renommer en `credentials.json`

### 2. Créer `.env`

```bash
GROQ_KEY=gsk_votre_clé_ici
GOOGLE_SHEET_ID=votre_id_google_sheet
```

### 3. Générer le token

```bash
python3 generate_token.py
```

## Utilisation

```bash
python3 main.py
```

**Mode test** (10 emails, pas de marquage comme lu) :
- Dans `mail_reader.py` ligne 119 : `"q": ""`
- Dans `main.py` ligne 81 : `max_results=10, mark_as_read=False`

**Mode production** (tous les non lus) :
- Dans `mail_reader.py` ligne 119 : `"q": "is:unread"`
- Dans `main.py` ligne 81 : `max_results=500, mark_as_read=True`

## Fichiers

```
├── main.py              # Point d'entrée
├── mail_reader.py       # Lecture Gmail
├── agent_mail.py        # Classification LLM
├── drive_client.py      # Écriture Google Sheets
├── context.txt          # Contexte LLM
├── prompt.txt           # Instructions LLM
├── .env                 # Variables (à créer)
├── credentials.json     # OAuth (à créer)
└── requirements.txt     # Dépendances
```

## Résultat

5 feuilles dans le Google Sheet (une par catégorie) :
- Problème technique informatique
- Demande administrative
- Problème d'accès / authentification
- Support utilisateur
- Bug

Chaque feuille :
- Triée par urgence (Critique → Anodine)
- Code couleur : 🔴 Rouge (Critique) → 🔵 Bleu (Anodine)
- 3 colonnes : Sujet | Urgence | Synthèse

## Dépannage rapide

**Erreur 400 OAuth** → Vérifier que le Client ID est type "Desktop app"
**Erreur 403 Gmail** → Activer Gmail API dans Google Cloud
**Erreur 404 Sheet** → Vérifier l'ID dans `.env` (pas l'URL complète)
**Erreur 429 Groq** → Limite de tokens atteinte, attendre ou changer de modèle
**Erreur 429 Sheets** → Rate limit, le code gère déjà avec batch updates

## Performance

- **Vitesse** : ~500 emails en 5 minutes
- **Coût** : Gratuit (APIs Google + Groq free tier)
- **Limite** : 1M tokens/jour sur Groq (largement suffisant)
