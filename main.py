# -*- coding: utf-8 -*-
"""
Pipeline complet TOX21 - Prediction Multi-Label de la Toxicite des Molecules
Executer depuis VS Code : Run > Run Without Debugging  (ou F5)
"""

import os
import sys
import warnings
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # backend sans fenetre (compatible tous OS)
import matplotlib.pyplot as plt
import seaborn as sns

# Forcer UTF-8 sur la console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors, DataStructs, AllChem
from rdkit import RDLogger

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, f1_score, hamming_loss, jaccard_score,
    confusion_matrix, roc_curve, auc, average_precision_score,
    classification_report, precision_score, recall_score,
)

from imblearn.over_sampling import SMOTE
import xgboost as xgb
import shap

warnings.filterwarnings("ignore")
RDLogger.DisableLog("rdApp.*")
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")

# ============================================================
# CHEMINS
# ============================================================
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(BASE_DIR, "data",   "tox21.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "multilabel_rf_model.pkl")
FIG_DIR    = os.path.join(BASE_DIR, "figures")
os.makedirs(FIG_DIR,                          exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "models"), exist_ok=True)

# ============================================================
# CONSTANTES
# ============================================================
RANDOM_STATE = 42
TEST_SIZE    = 0.20
FP_RADIUS    = 2
FP_NBITS     = 2048

TARGET_COLS = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

DESCRIPTOR_NAMES = [
    "MolWt", "LogP", "TPSA", "NumAtoms", "NumBonds",
    "HBondDonors", "HBondAcceptors", "RotatableBonds",
    "AromaticRings", "FractionCSP3", "HeavyAtomCount",
    "NumRings", "NumHeteroatoms", "NumAliphaticRings", "MolMR",
]

FEATURE_NAMES = DESCRIPTOR_NAMES + [f"FP_{i}" for i in range(FP_NBITS)]

SEP  = "=" * 65
SEP2 = "-" * 65

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def compute_descriptors(mol):
    try:
        return [
            Descriptors.MolWt(mol),
            Descriptors.MolLogP(mol),
            Descriptors.TPSA(mol),
            mol.GetNumAtoms(),
            mol.GetNumBonds(),
            rdMolDescriptors.CalcNumHBD(mol),
            rdMolDescriptors.CalcNumHBA(mol),
            rdMolDescriptors.CalcNumRotatableBonds(mol),
            rdMolDescriptors.CalcNumAromaticRings(mol),
            rdMolDescriptors.CalcFractionCSP3(mol),
            mol.GetNumHeavyAtoms(),
            rdMolDescriptors.CalcNumRings(mol),
            rdMolDescriptors.CalcNumHeteroatoms(mol),
            rdMolDescriptors.CalcNumAliphaticRings(mol),
            Descriptors.MolMR(mol),
        ]
    except Exception:
        return None


def compute_morgan_fp(mol):
    fp  = AllChem.GetMorganFingerprintAsBitVect(mol, FP_RADIUS, nBits=FP_NBITS)
    arr = np.zeros(FP_NBITS, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def featurize(df_in):
    descs, fps, valid_idx = [], [], []
    total = len(df_in)
    for i, (idx, row) in enumerate(df_in.iterrows()):
        if i % 500 == 0:
            print(f"     Progression : {i}/{total}", end="\r")
        mol  = Chem.MolFromSmiles(row["smiles"])
        if mol is None:
            continue
        desc = compute_descriptors(mol)
        if desc is None:
            continue
        descs.append(desc)
        fps.append(compute_morgan_fp(mol))
        valid_idx.append(idx)
    print(f"     Progression : {total}/{total}   ")
    X = np.hstack([np.array(descs, np.float32), np.array(fps, np.float32)])
    return X, valid_idx


def evaluate(model, X, y_true, name="", scaler=None):
    X_in    = scaler.transform(X) if scaler else X
    y_pred  = model.predict(X_in)
    y_proba = np.column_stack([est.predict_proba(X_in)[:, 1] for est in model.estimators_])

    per_label = []
    for i, t in enumerate(TARGET_COLS):
        try:
            auc_s = roc_auc_score(y_true[:, i], y_proba[:, i])
        except Exception:
            auc_s = float("nan")
        try:
            ap = average_precision_score(y_true[:, i], y_proba[:, i])
        except Exception:
            ap = float("nan")
        per_label.append({
            "Cible":     t,
            "AUC-ROC":   round(auc_s, 4),
            "Avg Prec.": round(ap, 4),
            "F1":        round(f1_score(y_true[:, i], y_pred[:, i], zero_division=0), 4),
            "Positifs":  int(y_true[:, i].sum()),
        })

    pl_df = pd.DataFrame(per_label).set_index("Cible")
    return {
        "name":      name,
        "y_pred":    y_pred,
        "y_proba":   y_proba,
        "hamming":   round(hamming_loss(y_true, y_pred), 4),
        "jaccard":   round(jaccard_score(y_true, y_pred, average="macro", zero_division=0), 4),
        "f1_micro":  round(f1_score(y_true, y_pred, average="micro",  zero_division=0), 4),
        "f1_macro":  round(f1_score(y_true, y_pred, average="macro",  zero_division=0), 4),
        "auc_macro": round(float(np.nanmean(pl_df["AUC-ROC"])), 4),
        "per_label": pl_df,
    }


def predict_profile(smiles_list, model, threshold=0.5):
    rows = []
    for smi in smiles_list:
        mol  = Chem.MolFromSmiles(smi)
        if mol is None:
            rows.append({"SMILES": smi, "Valide": False})
            continue
        desc = compute_descriptors(mol)
        if desc is None:
            rows.append({"SMILES": smi, "Valide": False})
            continue
        X_new = np.hstack([desc, compute_morgan_fp(mol)]).reshape(1, -1).astype(np.float32)
        proba = np.column_stack([est.predict_proba(X_new)[:, 1] for est in model.estimators_])[0]
        pred  = (proba >= threshold).astype(int)
        row   = {"SMILES": smi, "Valide": True, "N Cibles Toxiques": int(pred.sum())}
        for j, t in enumerate(TARGET_COLS):
            row[f"{t} (prob)"] = round(float(proba[j]), 3)
        rows.append(row)
    return pd.DataFrame(rows)


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def main():
    print("\n" + SEP)
    print("  PREDICTION MULTI-LABEL DE LA TOXICITE MOLECULAIRE - TOX21")
    print(SEP + "\n")

    # ----------------------------------------------------------
    # 1. CHARGEMENT DES DONNEES
    # ----------------------------------------------------------
    print("1. Chargement des donnees...")
    df = pd.read_csv(DATA_PATH)
    print(f"   Dataset : {df.shape[0]:,} molecules x {df.shape[1]} colonnes")
    print(f"   Colonnes : {list(df.columns)}")

    # ----------------------------------------------------------
    # 2. PRETRAITEMENT
    # ----------------------------------------------------------
    print("\n2. Pretraitement...")

    def is_valid(smi):
        try:
            return Chem.MolFromSmiles(str(smi)) is not None
        except Exception:
            return False

    df = df[df["smiles"].apply(is_valid)].copy()
    n_dup = df.duplicated(subset=["smiles"]).sum()
    df = df.drop_duplicates(subset=["smiles"]).copy()
    df[TARGET_COLS] = df[TARGET_COLS].apply(pd.to_numeric, errors="coerce")
    df_complete = df.dropna(subset=TARGET_COLS).copy()
    print(f"   Doublons supprimes      : {n_dup}")
    print(f"   Molecules completes     : {len(df_complete):,}  (12 labels non-NaN)")

    # ----------------------------------------------------------
    # 3. STATISTIQUES EDA
    # ----------------------------------------------------------
    print("\n3. Statistiques des 12 cibles :")
    print(f"   {'Cible':<18} {'N pos':>6} {'N neg':>6} {'% pos':>7}")
    print(f"   {SEP2[:42]}")
    for t in TARGET_COLS:
        col = df_complete[t]
        n1  = int((col == 1).sum())
        n0  = int((col == 0).sum())
        pct = round(100 * n1 / (n0 + n1), 1)
        print(f"   {t:<18} {n1:>6,} {n0:>6,} {pct:>6.1f}%")

    # ----------------------------------------------------------
    # 4. FIGURES EDA
    # ----------------------------------------------------------
    print("\n4. Generation des graphiques EDA...")

    # 4.1 Distribution des classes
    fig, axes = plt.subplots(3, 4, figsize=(18, 12))
    axes = axes.ravel()
    for i, t in enumerate(TARGET_COLS):
        counts = df_complete[t].value_counts()
        n0, n1 = int(counts.get(0, 0)), int(counts.get(1, 0))
        pct    = 100 * n1 / (n0 + n1) if (n0 + n1) else 0
        bars   = axes[i].bar(["Negatif", "Positif"], [n0, n1],
                              color=["#2196F3", "#F44336"], edgecolor="white")
        for b in bars:
            h = b.get_height()
            axes[i].text(b.get_x() + b.get_width() / 2, h + 5, f"{h:,}",
                         ha="center", va="bottom", fontsize=8)
        axes[i].set_title(f"{t}\n(+:{pct:.1f}%)", fontsize=9, fontweight="bold")
    plt.suptitle("Distribution des Classes par Cible (TOX21)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "01_class_distribution.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 4.2 Taux de positivite
    pos_s = pd.Series({
        t: 100 * (df_complete[t] == 1).sum() / len(df_complete[t].dropna())
        for t in TARGET_COLS
    }).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(pos_s.index, pos_s.values,
                   color=plt.cm.RdYlGn(np.linspace(0.15, 0.85, len(pos_s))))
    ax.axvline(pos_s.mean(), color="navy", ls="--",
               label=f"Moyenne : {pos_s.mean():.1f}%")
    for b, v in zip(bars, pos_s.values):
        ax.text(v + 0.1, b.get_y() + b.get_height() / 2,
                f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("% molecules toxiques")
    ax.set_title("Desequilibre des Classes par Cible", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "02_positive_rates.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 4.3 Correlation
    fig, ax = plt.subplots(figsize=(12, 10))
    corr = df_complete[TARGET_COLS].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, ax=ax, annot=True, fmt=".2f",
                cmap="coolwarm", center=0, square=True, linewidths=0.5)
    ax.set_title("Correlation entre les 12 Cibles", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "03_label_correlation.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # 4.4 Co-occurrence
    df_comp_eda = df_complete[TARGET_COLS].copy()
    cooc = df_comp_eda.T.dot(df_comp_eda).astype(int)
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(cooc, ax=ax, annot=True, fmt="d", cmap="YlOrRd", linewidths=0.5)
    ax.set_title("Co-occurrence des Labels Positifs", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "04_label_cooccurrence.png"), dpi=150, bbox_inches="tight")
    plt.close()

    print(f"   [OK] 4 figures EDA sauvegardees dans : {FIG_DIR}/")

    # ----------------------------------------------------------
    # 5. FEATURE ENGINEERING
    # ----------------------------------------------------------
    print("\n5. Extraction des features...")
    print(f"   = {len(DESCRIPTOR_NAMES)} descripteurs + {FP_NBITS} bits Morgan = {len(FEATURE_NAMES)} features")
    X, valid_idx = featurize(df_complete)
    y = df_complete.loc[valid_idx, TARGET_COLS].values.astype(int)
    print(f"   [OK] X : {X.shape}  |  y : {y.shape}")

    # Distribution des descripteurs
    fig, axes = plt.subplots(3, 5, figsize=(20, 10))
    axes = axes.ravel()
    for i, name in enumerate(DESCRIPTOR_NAMES):
        axes[i].hist(X[:, i], bins=40, color="#1976D2", alpha=0.8, edgecolor="white")
        axes[i].set_title(name, fontsize=9, fontweight="bold")
    plt.suptitle("Distribution des 15 Descripteurs Moleculaires", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "05_descriptor_distributions.png"), dpi=150, bbox_inches="tight")
    plt.close()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    print(f"   Train : {X_train.shape[0]:,}  |  Test : {X_test.shape[0]:,}")

    # ----------------------------------------------------------
    # 6. ENTRAINEMENT DES MODELES
    # ----------------------------------------------------------
    print("\n6. Entrainement des modeles...")

    print("   [1/3] Random Forest (200 arbres x 12 cibles)...")
    rf_model = MultiOutputClassifier(
        RandomForestClassifier(
            n_estimators=200, min_samples_split=5,
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
        ),
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    print("         [OK] Random Forest entraine")

    print("   [2/3] Logistic Regression...")
    scaler     = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)
    lr_model = MultiOutputClassifier(
        LogisticRegression(
            C=1.0, max_iter=1000, class_weight="balanced",
            solver="lbfgs", random_state=RANDOM_STATE, n_jobs=-1
        ),
        n_jobs=-1
    )
    lr_model.fit(X_train_sc, y_train)
    print("         [OK] Logistic Regression entraine")

    print("   [3/3] XGBoost (200 arbres x 12 cibles)...")
    xgb_model = MultiOutputClassifier(
        xgb.XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
            random_state=RANDOM_STATE, n_jobs=-1, verbosity=0
        ),
        n_jobs=-1
    )
    xgb_model.fit(X_train, y_train)
    print("         [OK] XGBoost entraine")

    # ----------------------------------------------------------
    # 7. EVALUATION MULTI-LABEL
    # ----------------------------------------------------------
    print("\n7. Evaluation multi-label...")
    rf_res  = evaluate(rf_model,  X_test, y_test, "Random Forest")
    lr_res  = evaluate(lr_model,  X_test, y_test, "Logistic Regression", scaler=scaler)
    xgb_res = evaluate(xgb_model, X_test, y_test, "XGBoost")

    print("\n" + SEP)
    print("   COMPARAISON DES MODELES (jeu de test)")
    print(SEP)
    comp = pd.DataFrame([
        {
            "Modele":       r["name"],
            "Hamming (v)":  r["hamming"],
            "Jaccard":      r["jaccard"],
            "F1 micro":     r["f1_micro"],
            "F1 macro":     r["f1_macro"],
            "AUC-ROC":      r["auc_macro"],
        }
        for r in [rf_res, lr_res, xgb_res]
    ]).set_index("Modele")
    print(comp.to_string())

    best_name = comp["AUC-ROC"].idxmax()
    print(f"\n   [BEST] Meilleur modele : {best_name}  (AUC-ROC macro = {comp.loc[best_name, 'AUC-ROC']})")

    print("\n   AUC-ROC par cible (Random Forest) :")
    print(rf_res["per_label"][["AUC-ROC", "F1", "Positifs"]].round(4).to_string())

    # ----------------------------------------------------------
    # 8. FIGURES D'EVALUATION
    # ----------------------------------------------------------
    print("\n8. Generation des figures d'evaluation...")

    # Courbes ROC
    fig, axes = plt.subplots(3, 4, figsize=(18, 12))
    axes = axes.ravel()
    for i, t in enumerate(TARGET_COLS):
        fpr, tpr, _ = roc_curve(y_test[:, i], rf_res["y_proba"][:, i])
        roc_auc = auc(fpr, tpr)
        axes[i].plot(fpr, tpr, "#E91E63", lw=2, label=f"AUC={roc_auc:.3f}")
        axes[i].plot([0, 1], [0, 1], "gray", ls="--", lw=1)
        axes[i].fill_between(fpr, tpr, alpha=0.1, color="#E91E63")
        axes[i].set_title(t, fontsize=9, fontweight="bold")
        axes[i].legend(loc="lower right", fontsize=8)
        axes[i].set_xlabel("FPR", fontsize=7)
        axes[i].set_ylabel("TPR", fontsize=7)
    plt.suptitle("Courbes ROC - Random Forest (12 cibles)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "06_roc_curves.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # Matrices de confusion
    fig, axes = plt.subplots(3, 4, figsize=(18, 12))
    axes = axes.ravel()
    for i, t in enumerate(TARGET_COLS):
        cm = confusion_matrix(y_test[:, i], rf_res["y_pred"][:, i])
        sns.heatmap(cm, annot=True, fmt="d", ax=axes[i], cmap="Blues",
                    xticklabels=["Neg", "Pos"], yticklabels=["Neg", "Pos"])
        axes[i].set_title(t, fontsize=9, fontweight="bold")
    plt.suptitle("Matrices de Confusion - Random Forest", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "07_confusion_matrices.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # Comparaison AUC par modele
    x     = np.arange(len(TARGET_COLS))
    width = 0.25
    fig, ax = plt.subplots(figsize=(16, 7))
    for j, (res, color) in enumerate(zip(
        [rf_res, lr_res, xgb_res],
        ["#1976D2", "#388E3C", "#F57C00"]
    )):
        ax.bar(x + j * width, res["per_label"]["AUC-ROC"].values,
               width, label=res["name"], color=color, alpha=0.85)
    ax.axhline(y=0.8, color="red", ls="--", alpha=0.5, label="Seuil 0.8")
    ax.set_xticks(x + width)
    ax.set_xticklabels(TARGET_COLS, rotation=45, ha="right")
    ax.set_ylabel("AUC-ROC")
    ax.set_ylim([0.4, 1.05])
    ax.set_title("AUC-ROC par Cible et Modele", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "08_auc_comparison.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # Analyse du seuil (SR-MMP)
    idx_mmp   = TARGET_COLS.index("SR-MMP")
    y_true_m  = y_test[:, idx_mmp]
    y_prob_m  = rf_res["y_proba"][:, idx_mmp]
    thresholds = np.arange(0.05, 0.95, 0.05)
    f1s, precs, recs = [], [], []
    for th in thresholds:
        yp = (y_prob_m >= th).astype(int)
        f1s.append(f1_score(y_true_m, yp, zero_division=0))
        precs.append(precision_score(y_true_m, yp, zero_division=0))
        recs.append(recall_score(y_true_m, yp, zero_division=0))
    best_th = thresholds[np.argmax(f1s)]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(thresholds, f1s,   "b-o",  label="F1 Score",  lw=2)
    ax.plot(thresholds, precs, "g--s", label="Precision",  lw=1.5)
    ax.plot(thresholds, recs,  "r--^", label="Rappel",     lw=1.5)
    ax.axvline(best_th, color="purple", ls=":",
               label=f"Seuil optimal F1 = {best_th:.2f}")
    ax.set_xlabel("Seuil de decision")
    ax.set_ylabel("Score")
    ax.set_title("Impact du Seuil - SR-MMP (Random Forest)", fontsize=12, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "09_threshold_analysis.png"), dpi=150, bbox_inches="tight")
    plt.close()

    print(f"   [OK] Figures sauvegardees dans : {FIG_DIR}/")

    # ----------------------------------------------------------
    # 9. SHAP EXPLAINABILITY
    # ----------------------------------------------------------
    print("\n9. Calcul SHAP (NR-AR, 100 molecules test)...")
    try:
        estimator_nrar = rf_model.estimators_[0]
        X_shap = X_test[:100].astype(np.float64)   # float64 requis par certaines versions SHAP

        explainer = shap.TreeExplainer(
            estimator_nrar,
            data=shap.sample(X_train.astype(np.float64), 50, random_state=RANDOM_STATE),
            feature_perturbation="interventional",
        )
        shap_values = explainer.shap_values(X_shap, check_additivity=False)

        # RF binaire -> liste [class0, class1] ou tableau 3D (n, f, 2)
        if isinstance(shap_values, list) and len(shap_values) == 2:
            sv = np.array(shap_values[1])
        elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
            sv = shap_values[:, :, 1]
        else:
            sv = np.array(shap_values)
            if sv.ndim == 3:
                sv = sv[:, :, 1]

        sv = sv.reshape(X_shap.shape[0], -1)   # garantit 2D (n_samples, n_features)

        # Summary plot
        plt.figure(figsize=(10, 8))
        shap.summary_plot(sv, X_shap, feature_names=FEATURE_NAMES,
                          max_display=20, show=False, plot_type="dot")
        plt.title("SHAP - Top 20 features (NR-AR)", fontsize=12, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, "10_shap_summary.png"), dpi=150, bbox_inches="tight")
        plt.close()

        # Importance des descripteurs
        desc_imp = np.abs(sv[:, :15]).mean(axis=0)
        desc_df  = pd.DataFrame({"Descripteur": DESCRIPTOR_NAMES, "SHAP": desc_imp})
        desc_df  = desc_df.sort_values("SHAP", ascending=True)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(desc_df["Descripteur"], desc_df["SHAP"],
                color=plt.cm.viridis(np.linspace(0.15, 0.9, 15)))
        ax.set_xlabel("|SHAP| moyen")
        ax.set_title("Importance des Descripteurs (SHAP - NR-AR)", fontsize=12, fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, "11_shap_descriptors.png"), dpi=150, bbox_inches="tight")
        plt.close()

        print("   [OK] SHAP calcule et sauvegarde")
        print(f"   Top 5 features : {list(pd.Series(np.abs(sv).mean(0), index=FEATURE_NAMES).nlargest(5).index)}")
    except Exception as e:
        print(f"   [WARN] SHAP ignore : {e}")

    # ----------------------------------------------------------
    # 10. PREDICTION SUR MOLECULES DE REFERENCE
    # ----------------------------------------------------------
    print("\n10. Prediction sur molecules de reference...")

    TEST_MOLS = {
        "Aspirine":          "CC(=O)Oc1ccccc1C(=O)O",
        "Benzene":           "c1ccccc1",
        "Ethanol":           "CCO",
        "Cafeine":           "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
        "Bisphenol A":       "CC(c1ccc(O)cc1)(c1ccc(O)cc1)C",
        "Tamoxifene":        "CCC(=C(c1ccccc1)c1ccc(OCCN(C)C)cc1)c1ccccc1",
        "Paracetamol":       "CC(=O)Nc1ccc(O)cc1",
        "Diethylstilbestrol":"CC(/C=C/c1ccc(O)cc1)=C(\\c1ccc(O)cc1)/CC",
        "Atrazine":          "CCNc1nc(Cl)nc(NC(C)C)n1",
        "Ibuprofen":         "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "TCDD Dioxine":      "Clc1cc2c(cc1Cl)Oc1c(Cl)c(Cl)ccc1O2",
        "Methanol":          "CO",
    }

    pred_df = predict_profile(list(TEST_MOLS.values()), rf_model)
    pred_df.insert(0, "Molecule", list(TEST_MOLS.keys()))

    print(f"\n   {'Molecule':<24} {'N Cibles Toxiques':>18}")
    print(f"   {SEP2[:44]}")
    for _, row in pred_df.iterrows():
        n = row.get("N Cibles Toxiques", "N/A")
        print(f"   {row['Molecule']:<24} {str(n):>18}")

    valid_df = pred_df[pred_df["Valide"] == True]
    prob_mat = valid_df[[f"{t} (prob)" for t in TARGET_COLS]].values
    mol_lbls = valid_df["Molecule"].values

    # Heatmap
    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(prob_mat, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    for i in range(prob_mat.shape[0]):
        for j in range(prob_mat.shape[1]):
            v = prob_mat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 0.5 else "black", fontweight="bold")
    ax.set_xticks(range(len(TARGET_COLS)))
    ax.set_xticklabels(
        [t.replace("NR-", "").replace("SR-", "") for t in TARGET_COLS],
        rotation=45, ha="right"
    )
    ax.set_yticks(range(len(mol_lbls)))
    ax.set_yticklabels(mol_lbls)
    plt.colorbar(im, ax=ax, label="Probabilite de toxicite")
    ax.set_title("Profil de Toxicite Multi-Label - Molecules de Reference",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "12_toxicity_profiles.png"), dpi=150, bbox_inches="tight")
    plt.close()

    # Radar chart
    fig, axes = plt.subplots(3, 4, figsize=(18, 13), subplot_kw=dict(polar=True))
    axes = axes.ravel()
    angles = np.linspace(0, 2 * np.pi, len(TARGET_COLS), endpoint=False).tolist()
    colors_r = plt.cm.tab10(np.linspace(0, 1, len(mol_lbls)))
    for k, (name, color) in enumerate(zip(mol_lbls, colors_r)):
        p = prob_mat[k].tolist()
        a = angles + angles[:1]
        p = p + p[:1]
        axes[k].plot(a, p, color=color, lw=2)
        axes[k].fill(a, p, color=color, alpha=0.2)
        axes[k].set_xticks(angles)
        axes[k].set_xticklabels(
            [t.replace("NR-", "").replace("SR-", "") for t in TARGET_COLS],
            fontsize=7
        )
        axes[k].set_ylim(0, 1)
        axes[k].set_title(name, size=9, fontweight="bold", pad=12)
    for j in range(k + 1, len(axes)):
        axes[j].set_visible(False)
    plt.suptitle("Radar - Probabilites de Toxicite Multi-Label", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "13_toxicity_radar.png"), dpi=150, bbox_inches="tight")
    plt.close()

    print(f"   [OK] Figures sauvegardees dans : {FIG_DIR}/")

    # ----------------------------------------------------------
    # 11. SAUVEGARDE DU MODELE
    # ----------------------------------------------------------
    print("\n11. Sauvegarde du modele...")
    package = {
        "model":   rf_model,
        "targets": TARGET_COLS,
        "feature_engineering": {
            "descriptor_names": DESCRIPTOR_NAMES,
            "n_descriptors":    len(DESCRIPTOR_NAMES),
            "fp_radius":        FP_RADIUS,
            "fp_nbits":         FP_NBITS,
            "n_features_total": len(DESCRIPTOR_NAMES) + FP_NBITS,
        },
        "metrics": {
            "hamming":       rf_res["hamming"],
            "jaccard":       rf_res["jaccard"],
            "f1_micro":      rf_res["f1_micro"],
            "f1_macro":      rf_res["f1_macro"],
            "auc_macro":     rf_res["auc_macro"],
            "per_label_auc": rf_res["per_label"]["AUC-ROC"].to_dict(),
        },
        "training_info": {
            "n_train":    X_train.shape[0],
            "n_test":     X_test.shape[0],
            "n_features": X_train.shape[1],
            "n_labels":   len(TARGET_COLS),
        },
    }
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(package, f)
    print(f"   [OK] Modele sauvegarde : {MODEL_PATH}")

    # ----------------------------------------------------------
    # RESUME FINAL
    # ----------------------------------------------------------
    print("\n" + SEP)
    print("  RESUME FINAL")
    print(SEP)
    print(f"  Dataset          : {len(df_complete):,} molecules completes")
    print(f"  Features         : {X.shape[1]} (15 descripteurs + {FP_NBITS} bits Morgan)")
    print(f"  Entrainement     : {X_train.shape[0]:,} molecules")
    print(f"  Test             : {X_test.shape[0]:,} molecules")
    print(f"  Cibles           : {len(TARGET_COLS)}")
    print(f"\n  Random Forest :")
    print(f"    AUC-ROC macro  : {rf_res['auc_macro']}")
    print(f"    F1 macro       : {rf_res['f1_macro']}")
    print(f"    Hamming Loss   : {rf_res['hamming']}")
    print(f"    Jaccard        : {rf_res['jaccard']}")
    print(f"\n  XGBoost :")
    print(f"    AUC-ROC macro  : {xgb_res['auc_macro']}")
    print(f"    F1 macro       : {xgb_res['f1_macro']}")
    print(f"\n  Logistic Regression :")
    print(f"    AUC-ROC macro  : {lr_res['auc_macro']}")
    print(f"    F1 macro       : {lr_res['f1_macro']}")
    print(f"\n  Figures dans     : {FIG_DIR}/")
    print(f"  Modele dans      : {MODEL_PATH}")
    print(SEP + "\n")
    print("  PROJET TERMINE AVEC SUCCES !")
    print(SEP + "\n")


if __name__ == "__main__":
    main()
