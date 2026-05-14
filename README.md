# NetPulse-Shield 🛡️

**Démo pédagogique : détection d’anomalies sur trafic tabulaire (UNSW-NB15), rapports et intégration SIEM optionnelle — pas un produit SOC commercial.**

NetPulse-Shield enchaîne : données CSV nettoyées → **Isolation Forest** (scikit-learn) → alertes (CSV / SQLite) → conseils textuels (**RAG** hors ligne par défaut, **Ollama** en option) → envoi HTTP vers un SIEM si configuré. Tout est pensé pour **reproduire un petit pipeline** et **mesurer** des métriques quand des labels existent, pas pour remplacer un IDS/NIDS temps réel ni un moteur de détection validé en production sur votre réseau.

---

## Limites et transparence (à lire en premier)

### Ce que ce projet n’est pas

- **Pas un remplacement d’un SOC ou d’un IDS/IPS** : pas d’inspection de paquets en direct, pas de corrélation multi-sources, pas de playbooks d’incident intégrés.
- **Pas une preuve de sécurité** : des scores élevés sur UNSW-NB15 ne garantissent **rien** sur votre trafic réel (autres protocoles, dérive, attaques absentes du jeu de données).
- **Pas une certification** : aucun audit externe, aucune garantie de conformité (RGPD, secteur réglementé, etc.).

### Données et prétraitement

- Le flux par défaut part d’un **CSV** (souvent issu de `clean_data.py` sur UNSW-NB15). Ce n’est **pas** du streaming.
- `clean_data.py` ne garde qu’**un sous-ensemble de colonnes** et peut **échantillonner** (jusqu’à 50 000 lignes) : vous n’analysez pas « tout le dataset » brut sauf configuration contraire.
- Les valeurs manquantes / infinies sont gérées de façon simple (par ex. **imputation par 0** dans le détecteur) : c’est pratique mais **biaisant** ; ce n’est pas une imputation statistique soignée par variable.
- Les libellés `Label` du jeu public **ne correspondent pas** forcément à ce que votre organisation appellerait « attaque » en production.

### Modèles d’anomalie

- **Isolation Forest** suppose des anomalies « rares » et « faciles à isoler » dans l’espace des features ; ce n’est pas adapté à toutes les menaces ni à toutes les formes de dérive.
- Avec `python pipeline.py --compare-lof`, un second modèle (**Local Outlier Factor**) est entraîné sur **la même matrice `X` normalisée** et avec la **même `contamination`** que la forêt après réglage : cela sert de **comparaison pédagogique**, pas de vérité absolue. LOF peut fortement varier selon `n_neighbors` et la densité locale.
- Le réglage de `contamination` sur une **split de validation** quand `Label` est présent aligne le modèle sur **cette partition** ; le modèle final est ré-entraîné sur tout le jeu passé à `analyze`, ce qui peut **légèrement** décaler l’optimum par rapport au sweep.

### Labels, métriques, généralisation

- Les labels ne sont **pas** la cible supervisée de `IsolationForest.fit` ; ils servent à **choisir un hyperparamètre** (`contamination`) et à **calculer** précision, rappel, F1, ROC-AUC, FPR **sur le même fichier** que vous venez de scorer. Ce sont des métriques **in-sample** sur ce batch : elles **surestiment souvent** la performance en généralisation et ne remplacent pas une validation temporelle ou sur site.
- Sans colonne `Label`, il n’y a pas de vérité terrain : les alertes restent des **candidats** à interpréter.

### Remédiation (RAG / LLM)

- Le RAG **retourne du texte** issu d’une base de connaissances locale (avec repli). Ce n’est **pas** une exécution automatique de commandes sur vos équipements.
- **Ollama / Llama** peut halluciner ou proposer des actions **inadaptées** à votre contexte. **Vérifiez** toute recommandation avant de l’appliquer ; l’auteur du dépôt et les contributeurs **ne portent pas** la responsabilité d’actions prises sur la base de ces textes.

### SIEM et opérations

- L’envoi vers Azure Log Analytics est **optionnel** ; en cas d’échec réseau ou de mauvaise clé, le pipeline continue mais les événements peuvent être **perdus** si vous ne les journalisez pas ailleurs.
- Les champs d’alerte (type d’attaque, etc.) déduits de features ou de texte ne sont **pas** une attribution MITRE certifiée.

---

## ✨ Fonctionnalités (aperçu factuel)

- Détection d’anomalies avec **Isolation Forest** (persistance `.joblib`, réglage de `contamination` quand des labels sont disponibles).
- Option **`--compare-lof`** : baseline **Local Outlier Factor** sur les mêmes features normalisées ; métriques regroupées dans `metrics.json` sous `baselines` lorsque les labels et `--metrics` sont présents.
- Nettoyage UNSW-NB15 avec **12 features** numériques choisies pour l’exercice (pas une recherche exhaustive de features).
- Alertes **CSV** + **SQLite** ; tableau de bord **Streamlit** ; rapport texte.
- Conseils **RAG** (FAISS / repli TF-IDF) ou **Ollama** en option.
- **Webhook** Azure Data Collector ou endpoint générique.

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
Prérequis : Ollama installé + modèle Ollama (par défaut : `NETPULSE_OLLAMA_MODEL=phi3:mini`, configurable dans le dashboard)

---

## 🔐 Intégration SIEM / Azure Sentinel

*(Rappel : lire la section **Limites et transparence** plus haut — l’ingestion SIEM ne transforme pas ce dépôt en produit certifié.)*

NetPulse-Shield peut envoyer les alertes détectées vers un SIEM via HTTP. L'intégration **Azure Log Analytics / Microsoft Sentinel** utilise le **Data Collector API** avec signature SharedKey lorsque `NETPULSE_WORKSPACE_ID` et `NETPULSE_PRIMARY_KEY` sont définis. Un mode webhook générique est aussi disponible pour les tests locaux ou pour d'autres plateformes SIEM.

Cette intégration permet de centraliser les alertes, de les corréler avec d'autres événements de sécurité, de créer des règles d'alerte basées sur les anomalies, et de les exploiter dans un tableau de bord SIEM sans modifier le cœur du pipeline de détection.

### Ce qui se passe dans le pipeline

```text
CSV / flux réseau
    ↓
si colonne Label : réglage de la contamination (validation) — même logique que detector.py
    ↓
detector.py : Isolation Forest (+ option --compare-lof : LOF sur le même X dans metrics.json)
    ↓
advisor.py génère un conseil de remédiation
    ↓
webhook.py formate l’alerte en JSON
    ↓
envoi vers Azure Log Analytics / Sentinel
    ↓
table personnalisée NetPulseAlerts dans le SIEM
```

Le pipeline appelle l'envoi SIEM après la génération du conseil de remédiation. Si l'envoi échoue, la détection et la génération du rapport continuent quand même. Dans Azure Log Analytics, la table d’ingestion apparaît généralement sous la forme `NetPulseAlerts_CL` après indexation.

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
    - couvert par des tests unitaires de la requête et de la signature

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
│   ├── detector.py              ← Isolation Forest (détection principale)
│   └── baselines.py             ← Baseline optionnelle (LOF) pour comparaison de métriques
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
│   └── tasks.py                 ← Fonction worker pour RQ, avec fallback synchrone côté dashboard
│
├── Utils & Déploiement
│   └── system_utils.py
│
└── Autres
    ├── tests/                   ← Tests unitaires
    ├── models/                  ← Modèles sauvegardés (.joblib)
    └── data/                    ← Données traitées

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

### Métriques exportées (`metrics.json`)

Quand la colonne **`Label`** est présente et que vous n’avez pas désactivé `--metrics`, le pipeline écrit un fichier JSON avec les métriques de l’Isolation Forest et, si **`--compare-lof`**, une section **`baselines.local_outlier_factor`**. Ces chiffres décrivent **ce fichier-là**, pas votre réseau en production.

### Troubleshooting

- Données manquantes → Exécute `python clean_data.py`
- Redis non disponible → Le dashboard passe automatiquement en mode synchrone
- Ollama non lancé → Le RAG continue de fonctionner normalement
- Problème de schéma → Relance `python clean_data.py` puis `python pipeline.py`

### License
MIT License
