"""
Optional second anomaly baseline for comparison (same scaled feature matrix as Isolation Forest).

Local Outlier Factor (LOF) is density-based: it flags points that sit in sparser neighborhoods
than their neighbors. It is not "more true" than Isolation Forest; side-by-side metrics are
only a sanity check on a fixed CSV and label set.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.neighbors import LocalOutlierFactor


def evaluate_lof(
    X: np.ndarray,
    y_true: pd.Series,
    *,
    contamination: float,
    n_neighbors: int | None = None,
) -> dict:
    """
    Fit LOF on ``X`` and return the same style of metrics as ``NetworkAnomalyDetector.evaluate``.

    Parameters
    ----------
    X
        Scaled numeric matrix (identical preprocessing as the primary detector).
    y_true
        Raw labels; non-zero rows are treated as attacks (same convention as ``detector.py``).
    contamination
        Passed to ``LocalOutlierFactor``; use the same value as the tuned Isolation Forest
        when you want a like-for-like anomaly rate target (still different algorithms).
    n_neighbors
        If None, uses ``max(2, min(20, n_samples - 1)))``.
    """
    if y_true is None or len(y_true) != len(X):
        raise ValueError("y_true must align with X row-wise.")

    y_true_bin = (y_true != 0).astype(int)
    n = len(X)
    if n_neighbors is None:
        n_neighbors = max(2, min(20, n - 1))

    contamination = float(np.clip(contamination, 0.01, 0.5))

    lof = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination=contamination,
        novelty=False,
    )
    predictions = lof.fit_predict(X)
    y_pred = (predictions == -1).astype(int)
    # Higher score => more anomalous (aligned with negated IF decision_function in detector)
    y_scores = -lof.negative_outlier_factor_

    precision = precision_score(y_true_bin, y_pred, zero_division=0)
    recall = recall_score(y_true_bin, y_pred, zero_division=0)
    f1 = f1_score(y_true_bin, y_pred, zero_division=0)
    try:
        roc_auc_val = float(roc_auc_score(y_true_bin, y_scores))
    except ValueError:
        roc_auc_val = float("nan")

    cm = confusion_matrix(y_true_bin, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    fpr = fp / max(tn + fp, 1)

    metrics = {
        "method": "local_outlier_factor",
        "n_neighbors": int(n_neighbors),
        "contamination": contamination,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": None if np.isnan(roc_auc_val) else roc_auc_val,
        "false_positive_rate": fpr,
        "true_positives": int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives": int(tn),
        "confusion_matrix": {
            "rows": ["actual_normal (0)", "actual_attack (1)"],
            "cols": ["pred_normal (0)", "pred_anomaly (1)"],
            "counts": [[int(tn), int(fp)], [int(fn), int(tp)]],
        },
    }

    print("\n" + "=" * 50)
    print("📈  Baseline: Local Outlier Factor (same X, same contamination target)")
    print("=" * 50)
    print(
        classification_report(
            y_true_bin, y_pred, target_names=["Normal", "Attack"], zero_division=0
        )
    )
    print(
        f"  ROC-AUC Score      : {roc_auc_val:.4f}"
        if not np.isnan(roc_auc_val)
        else "  ROC-AUC Score      : n/a (single class in y_true)"
    )
    print(f"  False Positive Rate: {fpr:.4f}")
    print("=" * 50)

    return metrics
