"""
Évaluation multi-label et visualisations pour TOX21.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    roc_auc_score, f1_score, hamming_loss, jaccard_score,
    confusion_matrix, roc_curve, auc, average_precision_score,
)


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    labels: list[str],
    model_name: str = "",
) -> dict:
    """
    Calcule toutes les métriques multi-label.

    Retourne un dict avec :
        name, hamming, jaccard, f1_micro, f1_macro, auc_macro, per_label (DataFrame)
    """
    rows = []
    for i, lbl in enumerate(labels):
        try:
            auc_s = roc_auc_score(y_true[:, i], y_proba[:, i])
        except ValueError:
            auc_s = float("nan")
        try:
            ap = average_precision_score(y_true[:, i], y_proba[:, i])
        except ValueError:
            ap = float("nan")
        rows.append({
            "Label":     lbl,
            "AUC-ROC":   round(auc_s, 4),
            "Avg Prec.": round(ap, 4),
            "F1":        round(f1_score(y_true[:, i], y_pred[:, i], zero_division=0), 4),
            "Positifs":  int(y_true[:, i].sum()),
        })

    per_label = pd.DataFrame(rows).set_index("Label")

    return {
        "name":      model_name,
        "hamming":   round(hamming_loss(y_true, y_pred), 4),
        "jaccard":   round(jaccard_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "f1_micro":  round(f1_score(y_true, y_pred, average="micro",  zero_division=0), 4),
        "f1_macro":  round(f1_score(y_true, y_pred, average="macro",  zero_division=0), 4),
        "auc_macro": round(float(np.nanmean(per_label["AUC-ROC"])), 4),
        "per_label": per_label,
        "y_pred":    y_pred,
        "y_proba":   y_proba,
    }


def plot_roc_curves(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    labels: list[str],
    title: str = "Courbes ROC",
    save_path: str | None = None,
) -> None:
    ncols = 4
    nrows = -(-len(labels) // ncols)  # ceil division
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    axes = axes.ravel()

    for i, lbl in enumerate(labels):
        fpr, tpr, _ = roc_curve(y_true[:, i], y_proba[:, i])
        roc_auc     = auc(fpr, tpr)
        ax = axes[i]
        ax.plot(fpr, tpr, color="#E91E63", lw=2, label=f"AUC = {roc_auc:.3f}")
        ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1)
        ax.fill_between(fpr, tpr, alpha=0.1, color="#E91E63")
        ax.set_title(lbl, fontsize=9, fontweight="bold")
        ax.legend(loc="lower right", fontsize=8)
        ax.set_xlabel("FPR", fontsize=7)
        ax.set_ylabel("TPR", fontsize=7)
        ax.set_xlim([0, 1]); ax.set_ylim([0, 1.05])

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle(title, fontsize=13, fontweight="bold")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_confusion_matrices(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[str],
    title: str = "Matrices de Confusion",
    save_path: str | None = None,
) -> None:
    ncols = 4
    nrows = -(-len(labels) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 4 * nrows))
    axes = axes.ravel()

    for i, lbl in enumerate(labels):
        cm = confusion_matrix(y_true[:, i], y_pred[:, i])
        sns.heatmap(cm, annot=True, fmt="d", ax=axes[i], cmap="Blues",
                    xticklabels=["Négatif", "Positif"],
                    yticklabels=["Négatif", "Positif"])
        axes[i].set_title(lbl, fontsize=9, fontweight="bold")
        axes[i].set_xlabel("Prédit", fontsize=7)
        axes[i].set_ylabel("Réel", fontsize=7)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    plt.suptitle(title, fontsize=13, fontweight="bold")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


def plot_auc_comparison(
    results_list: list[dict],
    labels: list[str],
    save_path: str | None = None,
) -> None:
    """Compare l'AUC-ROC par cible entre plusieurs modèles."""
    n = len(results_list)
    x = np.arange(len(labels))
    width = 0.8 / n
    colors = ["#1976D2", "#388E3C", "#F57C00", "#7B1FA2"]

    fig, ax = plt.subplots(figsize=(14, 7))
    for j, res in enumerate(results_list):
        aucs   = res["per_label"]["AUC-ROC"].reindex(labels).values
        offset = (j - n / 2 + 0.5) * width
        ax.bar(x + offset, aucs, width, label=res["name"],
               color=colors[j % len(colors)], alpha=0.85)

    ax.axhline(y=0.8, color="red", ls="--", alpha=0.5, label="Seuil 0.8")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("AUC-ROC")
    ax.set_ylim([0.4, 1.05])
    ax.set_title("AUC-ROC par Cible et par Modèle", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()
