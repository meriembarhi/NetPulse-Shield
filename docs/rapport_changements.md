# Rapport des changements proposés

Ce document explique, en langage simple, les problèmes détectés dans le projet et les solutions que nous allons appliquer. Il est destiné aux débutants.

## Résumé

- Objectif : améliorer la qualité des données, stabiliser la détection d'anomalies et documenter le projet.
- Format : explication simple, étapes concrètes, tests et vérification.

## Problèmes identifiés

1. Qualité des données : données brutes mal formatées, valeurs manquantes et colonnes non normalisées.
2. Pipeline peu documenté : difficulté à comprendre le flux des scripts et l'ordre d'exécution.
3. Tests limités : couverture de tests insuffisante pour garantir les changements.
4. Déploiement et démonstration : manque d'instructions claires pour lancer l'application et le tableau de bord.

## Changements proposés

1. Nettoyage des données
   - Standardiser les noms de colonnes.
   - Remplir ou supprimer les valeurs manquantes selon le cas.
   - Sauvegarder un fichier de données nettoyées pour reproductibilité.

2. Documenter le pipeline
   - Ajouter un README en français (fichier `README_FR.md`) décrivant chaque script.
   - Ajouter des schémas (Mermaid) pour montrer le flux des données.

3. Renforcer les tests
   - Ajouter tests unitaires pour `clean_data.py` et `detector.py` (vérifier sorties attendues pour jeux de données exemples).
   - Mettre en place tests d'intégration simples pour `pipeline.py`.

4. Instructions d'exécution
   - Fournir commandes claires pour créer l'environnement, installer les dépendances et lancer le dashboard.

## Solutions appliquées (ce que nous avons fait)

- Ajout d'un document clair décrivant les problèmes et solutions (ce fichier).
- Création d'un README en français détaillé expliquant le projet et le pipeline (fichier `README_FR.md`).
- Inclusion d'un schéma pipeline en Mermaid pour visualiser le flux des données.

## Impact attendu

- Meilleure compréhension du code pour les nouveaux contributeurs.
- Moins d'erreurs liées à la qualité des données.
- Facilité pour tester et reproduire les résultats.

## Comment vérifier les changements

1. Lire `README_FR.md` pour comprendre le projet et le pipeline.
2. Lancer les scripts dans l'ordre indiqué (voir README) sur un petit jeu de données d'exemple.
3. Exécuter les tests avec `pytest`.

## Flux de génération des conseils de sécurité

Le système donne des conseils de sécurité en suivant deux approches :

### Approche 1 : RAG (Retrieval-Augmented Generation) avec FAISS
- **Fichier** : `advisor.py`
- **Fonctionnement** :
  1. Charger la base de connaissances (`docs/remediation_knowledge.txt`)
  2. Transformer le texte en vecteurs (embeddings) et stocker dans un index FAISS
  3. Quand une anomalie est détectée, chercher les conseils pertinents similaires
  4. Retourner les top-3 conseils les plus proches (par similarité sémantique)
- **Avantage** : Rapide, pas besoin d'internet, utilise une base de connaissances locale.
- **Fallback** : Si la base est vide, retourner des conseils génériques automatiques.

### Approche 2 : LLM Ollama/Llama3 (plus avancée)
- **Fichier** : `remediator.py`
- **Fonctionnement** :
  1. Détecter une anomalie et extraire ses caractéristiques (Sload, sttl, sbytes, etc.)
  2. Envoyer la description au modèle LLM Llama3 local
  3. Llama3 analyse les données et génère un rapport structuré :
     - Type d'attaque (DoS, Port Scan, Exploit, etc.)
     - Niveau de risque (Low, Medium, High, Critical)
     - Analyse technique détaillée
     - Commandes Cisco ACL pour bloquer l'attaque
- **Avantage** : Conseils très détaillés et spécifiques au contexte.
- **Prérequis** : Ollama (serveur local) et le modèle Llama3 doivent être en cours d'exécution.

### Flux complet de sécurité
```
Données réseau (CSV) → detector.py → Anomalie détectée
                                          ↓
                                   advisor.py (RAG)
                                   ou remediator.py (Llama3)
                                          ↓
                                   Conseils de sécurité
                                          ↓
                                   Dashboard + Alertes
```

## Prochaines étapes recommandées

- Implémenter les tests manquants pour `clean_data.py` et `detector.py`.
- Automatiser l'exécution du pipeline (ex : script `run_pipeline.sh` ou tâche `Makefile`).
- Ajouter un exemple d'alertes et un guide pas-à-pas pour le dashboard.

---

Si vous voulez, je peux maintenant :
- ajouter les tests unitaires basiques,
- modifier `clean_data.py` pour appliquer des nettoyages concrets,
- ou remplacer `README.md` par la version française complète.
