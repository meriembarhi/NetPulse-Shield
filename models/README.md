# Dossier Models
Ce dossier contient les modèles de Machine Learning exportés au format `.joblib`.

## Pourquoi ce dossier est vide sur GitHub ?
Conformément aux bonnes pratiques, les fichiers binaires `.joblib` ne sont pas suivis par Git pour éviter d'alourdir le dépôt.

## Comment régénérer le modèle ?
Pour recréer le modèle d'anomalies, assurez-vous d'avoir le dataset dans `/data` et lancez :
```bash
python detector.py