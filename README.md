# NetPulse-Shield 🛡️

**Système intelligent de détection d’anomalies réseau avec conseils de remédiation**

NetPulse-Shield analyse le trafic réseau (dataset UNSW-NB15), détecte les anomalies avec **Isolation Forest**, stocke les alertes et fournit des conseils de sécurité via un système **RAG** (recommandé) ou en option avec **Llama 3 via Ollama**.

---

## ✨ Fonctionnalités principales

- Détection d’anomalies avec Isolation Forest (modèle persistant + tuning intelligent de contamination)
- Nettoyage et sélection fixe des features pour une meilleure reproductibilité
- Stockage des alertes dans **CSV** + **SQLite**
- Conseils de remédiation via **RAG** (recherche sémantique avec fallback TF-IDF)
- Mode avancé avec **Ollama / Llama 3** (optionnel)
- Tableau de bord **Streamlit** interactif
- Pipeline complet en une seule commande (`pipeline.py`)

---

## 🚀 Démarrage rapide

### 1. Installation

```bash
git clone https://github.com/meriembarhi/NetPulse-Shield.git
cd NetPulse-Shield

python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate

pip install -r requirements.txt

# Préparer les données
python clean_data.py
```
### 2. Lancement

Mode recommandé (tout en une commande) :


```bash
python pipeline.py

```
Tableau de bord interactif :

```bash
streamlit run dashboard.py
```

### Deux méthodes de conseils de remédiation



1. RAG (Recommandé - Mode par défaut)

Fichiers principaux : advisor.py, embeddings.py, knowledge_base.py
Fonctionnement : Recherche sémantique dans une base de connaissances locale (FAISS) avec fallback TF-IDF
Avantages : Rapide, fiable, entièrement hors ligne, peu de ressources

2. Ollama / Llama 3 (Mode Avancé)

Fichiers : remediator.py, auto_remediator.py
Fonctionnement : Envoie les anomalies à Llama 3 pour générer des rapports structurés (type d’attaque, niveau de risque, commandes Cisco, etc.)
Avantages : Conseils très détaillés et naturels
Prérequis : Ollama installé + modèle llama3 (ou équivalent)

### Structure du projet

Voici une vue d’ensemble claire de l’architecture du projet :

```text
NetPulse-Shield
├── Core Pipeline (Orchestration)
│   ├── pipeline.py              ← Point d’entrée principal (recommandé)
│   └── detector.py              ← Cœur de la détection d’anomalies (Isolation Forest)
│
├── Remediation Layer
│   ├── advisor.py               ← Moteur RAG principal (recommandé par défaut)
│   ├── embeddings.py            ← Gestion des embeddings + fallback TF-IDF
│   └── knowledge_base.py        ← Base de connaissances
│
├── LLM Optionnel (Mode Avancé)
│   ├── remediator.py
│   └── auto_remediator.py       ← Génération de rapports avec Llama 3
│
├── Interface & Visualisation
│   ├── dashboard.py             ← Tableau de bord Streamlit (interactif)
│      
│
├── Données & Persistance
│   ├── db.py                    ← SQLite (Alertes + AuditLog)
│   ├── clean_data.py            ← Préparation des données
│   └── tasks.py                 ← Jobs asynchrones (Redis/RQ)
│
├── Utils & Déploiement
│   └── system_utils.py
│
└── Autres
    ├── tests/                   ← Tests unitaires
    ├── models/                  ← Modèles sauvegardés (.joblib)
    └── data/                    ← Données traitéesplet

```
### Pipeline Principal (Flux Complet)

```text
                       ┌─────────────────────┐
                       │   raw UNSW-NB15     │
                       │   (données brutes)  │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │   clean_data.py     │
                       │  (Nettoyage +       │
                       │   feature selection)│
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │  data/final_project │
                       │     _data.csv       │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │    detector.py       │
                       │  (Isolation Forest)  │
                       │  - Preprocess        │
                       │  - Train / Load      │
                       │  - Detect anomalies  │
                       │  - Tune contamination│
                       └──────────┬───────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │         ALERTES               │
                  │  alerts.csv + alerts.db       │
                  └──────────────┬────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────┐
                  │       Remediation             │
                  ├───────────────────────────────┤
                  │                               │
         ┌────────▼────────┐           ┌──────────▼──────────┐
         │   advisor.py    │           │ remediator.py       │
         │   (RAG -        │           │   (Ollama / Llama 3)│
         │    par défaut)  │           │                     │
         └────────┬────────┘           └──────────┬──────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │   Security_Report   │
                       │       .txt          │
                       └──────────┬──────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │   Tableau de bord   │
                       │    (dashboard.py)   │
                       └─────────────────────┘
```
### Déploiement

```bash
python pipeline.py
streamlit run dashboard.py
```

### Tests

```bash
pytest tests/ -q
ruff check .
```
### Troubleshooting

-Données manquantes → Exécute python clean_data.py
-Redis non disponible → Le dashboard passe automatiquement en mode synchrone
-Ollama non lancé → Le RAG continue de fonctionner normalement

-Problème de schéma → Relance clean_data.py puis pipeline.py

### License
MIT License