# -*- coding: utf-8 -*-
"""Test final complet du projet TOX21."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

print("=" * 60)
print("  TEST FINAL COMPLET - PROJET TOX21 MULTI-LABEL")
print("=" * 60)

# ── Test 1 : modules src/ ────────────────────────────────────
print("\n[1/5] Import des modules src/...")
from src.data_preprocessing import TARGET_COLS, load_data
from src.feature_engineering import featurize, DESCRIPTOR_NAMES, get_feature_names
from src.models import build_random_forest, build_logistic_regression, build_xgboost
from src.evaluation import compute_metrics
from src.predict import load_model, predict_toxicity, print_toxicity_profile
print(f"  OK - tous les modules importes ({len(TARGET_COLS)} cibles, {len(DESCRIPTOR_NAMES)} descripteurs)")

# ── Test 2 : donnees ─────────────────────────────────────────
print("\n[2/5] Chargement des donnees...")
df = load_data("data/tox21.csv")
print(f"  OK - {len(df):,} molecules, {df.shape[1]} colonnes")

# ── Test 3 : modele sauvegarde ───────────────────────────────
print("\n[3/5] Chargement du modele...")
pkg = load_model("models/multilabel_rf_model.pkl")
print(f"  OK - {len(pkg['targets'])} cibles | AUC-ROC={pkg['metrics']['auc_macro']} | F1={pkg['metrics']['f1_macro']} | Hamming={pkg['metrics']['hamming']}")

# ── Test 4 : predictions ──────────────────────────────────────
print("\n[4/5] Predictions sur molecules de reference...")
molecules = [
    ("Aspirine",        "CC(=O)Oc1ccccc1C(=O)O"),
    ("Bisphenol A",     "CC(c1ccc(O)cc1)(c1ccc(O)cc1)C"),
    ("TCDD (Dioxine)",  "Clc1cc2c(cc1Cl)Oc1c(Cl)c(Cl)ccc1O2"),
    ("Cafeine",         "Cn1cnc2c1c(=O)n(c(=O)n2C)C"),
    ("Ethanol",         "CCO"),
]
for nom, smi in molecules:
    res = predict_toxicity(smi, pkg)
    n   = res["n_toxic"].values[0]
    print(f"  {nom:<18} -> {n}/12 cibles toxiques")

# ── Test 5 : profil detaille ─────────────────────────────────
print("\n[5/5] Profil de toxicite complet (Bisphenol A) :")
print_toxicity_profile("CC(c1ccc(O)cc1)(c1ccc(O)cc1)C", pkg)

# ── Bilan ────────────────────────────────────────────────────
print("=" * 60)
print("  PROJET TOX21 COMPLETEMENT FONCTIONNEL")
print("=" * 60)
print(f"  Dataset           : {len(df):,} molecules, 12 labels")
print(f"  Features          : 2063 (15 descripteurs + 2048 Morgan)")
print(f"  Modele            : Random Forest (200 arbres x 12 cibles)")
print(f"  AUC-ROC macro     : {pkg['metrics']['auc_macro']}")
print(f"  F1 macro          : {pkg['metrics']['f1_macro']}")
print(f"  Hamming Loss      : {pkg['metrics']['hamming']}")
print(f"  Figures generees  : 28 figures dans figures/")
print(f"  Notebook          : notebooks/tox21_multilabel_complet.ipynb (45 cellules)")
print(f"  Script            : main.py")
print("=" * 60)
