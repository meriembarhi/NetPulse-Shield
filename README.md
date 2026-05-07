# NetPulse-Shield 🛡️

**Système intelligent de détection d’anomalies réseau avec conseils de remédiation**

NetPulse-Shield analyse le trafic réseau (dataset UNSW-NB15), détecte les anomalies avec **Isolation Forest**, stocke les alertes et fournit des conseils de sécurité via un système **RAG** (recommandé) ou en option avec **Llama 3 via Ollama**.

---

## ✨ Fonctionnalités principales

- Détection d’anomalies avec Isolation Forest (modèle persistant + tuning intelligent de contamination)
- Nettoyage et sélection fixe des features pour une meilleure reproductibilité
- Stockage des alertes dans **CSV** + **SQLite**
- Conseils de remédiation via **RAG** (recherche sémantique avec fallback TF-IDF)- **Intégration SIEM** complète vers **Azure Log Analytics / Microsoft Sentinel** (Data Collector API)- Mode avancé avec **Ollama / Llama 3** (optionnel)
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

---

## 🔐 Intégration SIEM / Azure Sentinel

NetPulse-Shield envoie **automatiquement** les alertes détectées vers un SIEM via HTTP. L'intégration **Azure Log Analytics / Microsoft Sentinel** est entièrement implémentée et testée, en utilisant le **Data Collector API** avec signature SharedKey. Un mode webhook générique est aussi disponible pour les tests locaux ou pour d'autres plateformes SIEM.

Cette intégration permet de centraliser les alertes, de les corréler avec d'autres événements de sécurité, de créer des règles d'alerte basées sur les anomalies, et de les exploiter dans un tableau de bord SIEM sans modifier le cœur du pipeline de détection.

### Ce qui se passe dans le pipeline

```text
CSV / flux réseau
    ↓
detector.py détecte les anomalies
    ↓
advisor.py génère un conseil de remédiation
    ↓
webhook.py formate l’alerte en JSON
    ↓
envoi vers Azure Log Analytics / Sentinel
    ↓
table personnalisée NetPulseAlerts dans le SIEM
```

Le pipeline appelle l'envoi SIEM après la génération du conseil de remédiation. Si l'envoi échoue, la détection et la génération du rapport continuent quand même. Les alertes arrivent dans la table `NetPulseAlerts_CL` de votre workspace Log Analytics avec un délai d'indexation de 5 à 15 minutes.

### Variables d’environnement

Le code lit la configuration SIEM depuis l'environnement. Aucune valeur sensible ne doit être codée en dur. Ces variables sont optionnelles ; sans elles, le pipeline continue de fonctionner normalement sans envoyer aux SIEM.

| Variable | Rôle | Exemple |
|----------|------|---------|
| `NETPULSE_WEBHOOK_URL` | URL du Data Collector API ou webhook générique | `https://<workspace-id>.ods.opinsights.azure.com/api/logs?api-version=2016-04-01` |
| `NETPULSE_WORKSPACE_ID` | Identifiant du workspace Azure Log Analytics | `5d39ad3f-862f-49f5-a7b4-65d750113545` |
| `NETPULSE_PRIMARY_KEY` | Clé primaire du workspace pour signer la requête | `*****` |
| `NETPULSE_WEBHOOK_TIMEOUT` | Délai d’attente avant abandon | `5` |
| `NETPULSE_WEBHOOK_BATCH_SIZE` | Taille de lot si vous étendez l’envoi par lot | `100` |
| `NETPULSE_WEBHOOK_RETRY` | Réessai optionnel côté orchestration | `true` |

### Format de destination Azure

Pour Azure Log Analytics / Sentinel, l’URL suit ce format :

```bash
https://<workspace-id>.ods.opinsights.azure.com/api/logs?api-version=2016-04-01
```

Le dépôt utilise par défaut le type de log personnalisé `NetPulseAlerts`, ce qui crée une table de destination cohérente côté SIEM.

### Structure des données envoyées

Chaque alerte est convertie en JSON avant envoi. Le schéma reste simple et stable pour faciliter l’indexation dans Azure ou dans un autre SIEM.

```json
[
  {
    "source": "NetPulse-Shield",
    "timestamp": "2026-05-07T10:30:00Z",
    "alert_id": 123,
    "severity": "medium",
    "anomaly_score": -0.95,
    "source_ip": "10.0.0.5",
    "destination_ip": "10.0.0.20",
    "attack_type": "DDoS",
    "description": "Anomaly detected with anomaly_score=-0.95. Features: sttl=31.00, sbytes=19202.00, dbytes=1087890.00",
    "advice": "Block source IP and enable rate-limiting"
  }
]
```

Dans Azure Log Analytics, ces champs deviennent des colonnes avec le suffixe `_s` (string), `_d` (double), etc. :
- `source_s`, `severity_s`, `description_s`, `advice_s`
- `anomaly_score_d`, `alert_id_d`
- `source_ip_s`, `destination_ip_s`, `attack_type_s`
- `TimeGenerated` (généré automatiquement par Azure)

Champs importants :

- `source` identifie NetPulse-Shield comme émetteur.
- `timestamp` permet la corrélation temporelle dans le SIEM.
- `severity` et `anomaly_score` aident au tri des alertes.
- `source_ip`, `destination_ip` et `attack_type` facilitent l’investigation.
- `advice` contient le conseil de remédiation produit par le moteur RAG.

### Comportement de `webhook.py`

Le module `webhook.py` supporte deux modes :

1. **Azure Log Analytics / Sentinel** (recommandé)
   - utilisé quand `NETPULSE_WORKSPACE_ID` et `NETPULSE_PRIMARY_KEY` sont définis
   - ajoute la signature `SharedKey` et les en-têtes Azure
   - envoie les alertes au format attendu par le Data Collector API
   - approuvé et testé en production avec workspace réel

2. **Webhook générique**
   - utile pour `webhook.site`, un reverse proxy, un endpoint de test ou un autre SIEM
   - n'utilise pas la signature Azure, juste un POST HTTP simple

En pratique, le pipeline n'est pas bloquant : un échec de l'envoi SIEM ne doit pas interrompre la détection des anomalies ni la génération du rapport de sécurité. Les erreurs SIEM sont loggées mais n'arrêtent jamais le flux.

### Mise en place rapide avec Azure Sentinel

1. **Dans Azure Portal**: Log Analytics workspace → Properties → récupérez l'ID du workspace.
2. **Dans Azure Portal**: Log Analytics workspace → Agents → récupérez la clé primaire.
3. **Composez l'URL du Data Collector API**:
   ```
   https://<workspace-id>.ods.opinsights.azure.com/api/logs?api-version=2016-04-01
   ```
4. **Exportez les variables d'environnement** avant de lancer le pipeline.
5. **Vérifiez dans Log Analytics** : Logs → query `NetPulseAlerts_CL` → vous devriez voir les événements en quelques minutes.

Exemple PowerShell :

```powershell
$env:NETPULSE_WEBHOOK_URL = "https://<workspace-id>.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"
$env:NETPULSE_WORKSPACE_ID = "<workspace-id>"
$env:NETPULSE_PRIMARY_KEY = "<primary-key>"
python pipeline.py tests/fixtures/detector_sample.csv --no-persist
```

### Vérification de bout en bout

Pour valider rapidement la chaîne complète :

1. Lancez le pipeline avec un petit fichier de test :
   ```powershell
   $env:NETPULSE_WEBHOOK_URL = "https://<workspace-id>.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"
   $env:NETPULSE_WORKSPACE_ID = "<workspace-id>"
   $env:NETPULSE_PRIMARY_KEY = "<primary-key>"
   python pipeline.py tests/fixtures/detector_sample.csv --no-persist
   ```
2. Vérifiez que `alerts.csv` et `Security_Report.txt` sont générés.
3. Contrôlez les logs pour voir `webhook - INFO - Sent alert to webhook endpoint`.
4. **Dans Azure Log Analytics**, ouvrez l'onglet Logs et lancez :
   ```kusto
   NetPulseAlerts_CL
   | sort by TimeGenerated desc
   | take 10
   ```
   Vous devriez voir vos alertes dans les quelques minutes.

En local, vous pouvez aussi pointer `NETPULSE_WEBHOOK_URL` vers `https://webhook.site/<votre-id>` pour vérifier la requête envoyée sans toucher au workspace Azure.

### Dépannage

| Problème | Cause probable | Solution |
|----------|---------------|-----------|
| Pas de données dans Azure | URL ou workspace ID invalide | Vérifiez `NETPULSE_WEBHOOK_URL` et `NETPULSE_WORKSPACE_ID` |
| Erreur d'authentification | Clé primaire incorrecte ou expirée | Copiez exactement la clé primaire depuis le portal Azure |
| Pipeline s'exécute mais rien dans Azure | Délai d'indexation ou requête mauvaise | Attendez 5-15 min, puis testez `NetPulseAlerts_CL \| take 1` |
| Logs vides après plus de 15 min | La signature ou le format JSON est rejeté | Testez localement avec `webhook.site` pour inspecter le POST |
| Variable d'environnement non lue | Mauvaise orthographe ou shell non rechargé | Vérifiez `echo $env:NETPULSE_WEBHOOK_URL` en PowerShell |

Pour tester localement sans Azure, utilisez `webhook.site` :
```powershell
$env:NETPULSE_WEBHOOK_URL = "https://webhook.site/<unique-id>"
python pipeline.py tests/fixtures/detector_sample.csv --no-persist
```
Puis ouvrez `https://webhook.site/<unique-id>` pour voir les POSTs reçus.

### Fichiers liés

- [webhook.py](webhook.py) : envoi HTTP et signature Azure
- [pipeline.py](pipeline.py) : point d’intégration du pipeline
- [SIEM_INTEGRATION_GUIDE.md](SIEM_INTEGRATION_GUIDE.md) : guide détaillé de configuration SIEM

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