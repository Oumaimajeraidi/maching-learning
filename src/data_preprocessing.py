"""
Chargement et prétraitement du dataset TOX21 multi-label.
"""

import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

# ── Labels ─────────────────────────────────────────────────────────────────────
TARGET_COLS = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

TARGET_DESCRIPTIONS = {
    "NR-AR":         "Nuclear Receptor – Androgen Receptor",
    "NR-AR-LBD":     "Nuclear Receptor – AR Ligand Binding Domain",
    "NR-AhR":        "Nuclear Receptor – Aryl hydrocarbon Receptor",
    "NR-Aromatase":  "Nuclear Receptor – Aromatase",
    "NR-ER":         "Nuclear Receptor – Estrogen Receptor",
    "NR-ER-LBD":     "Nuclear Receptor – ER Ligand Binding Domain",
    "NR-PPAR-gamma": "Nuclear Receptor – PPAR-gamma",
    "SR-ARE":        "Stress Response – Antioxidant Response Element",
    "SR-ATAD5":      "Stress Response – ATAD5",
    "SR-HSE":        "Stress Response – Heat Shock Element",
    "SR-MMP":        "Stress Response – Mitochondrial Membrane Potential",
    "SR-p53":        "Stress Response – p53 Pathway",
}


def load_data(path: str) -> pd.DataFrame:
    """Charge tox21.csv et conserve les colonnes utiles."""
    df = pd.read_csv(path)
    keep = ["smiles"] + (["mol_id"] if "mol_id" in df.columns else []) + TARGET_COLS
    df = df[[c for c in keep if c in df.columns]].copy()
    df[TARGET_COLS] = df[TARGET_COLS].apply(pd.to_numeric, errors="coerce")
    return df


def filter_valid_smiles(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les lignes avec des SMILES invalides (non parsables par RDKit)."""
    def valid(smi):
        try:
            return Chem.MolFromSmiles(str(smi)) is not None
        except Exception:
            return False
    mask = df["smiles"].apply(valid)
    n_dropped = (~mask).sum()
    if n_dropped:
        print(f"  {n_dropped} SMILES invalides supprimés")
    return df[mask].copy()


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les SMILES dupliqués (garde le premier)."""
    before = len(df)
    df = df.drop_duplicates(subset=["smiles"]).copy()
    print(f"  {before - len(df)} doublons supprimés")
    return df


def prepare_complete_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Stratégie 'complète' : conserve uniquement les molécules
    ayant un label non-NaN pour les 12 cibles.
    """
    return df.dropna(subset=TARGET_COLS).copy()


def get_label_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un DataFrame de statistiques par label."""
    rows = []
    for t in TARGET_COLS:
        col   = df[t].dropna()
        n_val = len(col)
        n_pos = int((col == 1.0).sum())
        n_neg = int((col == 0.0).sum())
        rows.append({
            "Label":       t,
            "N valide":    n_val,
            "N positifs":  n_pos,
            "N négatifs":  n_neg,
            "% positifs":  round(100.0 * n_pos / n_val, 2) if n_val else 0,
            "Manquants":   int(df[t].isna().sum()),
            "% manquants": round(100.0 * df[t].isna().sum() / len(df), 2),
        })
    return pd.DataFrame(rows).set_index("Label")
