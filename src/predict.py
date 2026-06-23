"""
Inférence : chargement du modèle et prédiction de toxicité sur des SMILES.
"""

import pickle
import numpy as np
import pandas as pd

from .feature_engineering import smiles_to_mol, compute_descriptors, compute_morgan_fp, FP_RADIUS, FP_NBITS
from .data_preprocessing  import TARGET_COLS, TARGET_DESCRIPTIONS


def load_model(path: str) -> dict:
    """Charge un package modèle sauvegardé avec pickle."""
    with open(path, "rb") as f:
        return pickle.load(f)


def _featurize_one(smiles: str, radius: int = FP_RADIUS, nbits: int = FP_NBITS):
    mol  = smiles_to_mol(smiles)
    desc = compute_descriptors(mol)
    if desc is None:
        return None
    fp = compute_morgan_fp(mol, radius, nbits)
    return np.hstack([desc, fp]).reshape(1, -1).astype(np.float32)


def predict_toxicity(
    smiles_input,
    package: dict,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Prédit le profil de toxicité multi-label pour un ou plusieurs SMILES.

    Paramètres
    ----------
    smiles_input : str ou liste de str
    package      : dict retourné par load_model()
    threshold    : seuil de décision (défaut 0.5)

    Retourne
    --------
    DataFrame avec colonnes SMILES, valide, n_toxic,
    {label}_prob et {label}_pred pour chaque cible.
    """
    if isinstance(smiles_input, str):
        smiles_input = [smiles_input]

    model  = package["model"]
    labels = package.get("targets", TARGET_COLS)
    fe     = package.get("feature_engineering", {})
    radius = fe.get("fp_radius", FP_RADIUS)
    nbits  = fe.get("fp_nbits",  FP_NBITS)

    rows = []
    for smi in smiles_input:
        X = _featurize_one(smi, radius, nbits)
        if X is None:
            rows.append({"SMILES": smi, "valide": False, "n_toxic": None})
            continue

        proba = np.column_stack([
            est.predict_proba(X)[:, 1] for est in model.estimators_
        ])[0]
        pred  = (proba >= threshold).astype(int)

        row = {"SMILES": smi, "valide": True}
        for j, lbl in enumerate(labels):
            row[f"{lbl}_prob"] = round(float(proba[j]), 4)
            row[f"{lbl}_pred"] = int(pred[j])
        row["n_toxic"] = int(pred.sum())
        rows.append(row)

    return pd.DataFrame(rows)


def print_toxicity_profile(smiles: str, package: dict, threshold: float = 0.5) -> None:
    """Affiche un profil de toxicité lisible pour une molécule."""
    df  = predict_toxicity(smiles, package, threshold)
    row = df.iloc[0]

    if not row["valide"]:
        print(f"SMILES invalide : {smiles}")
        return

    labels = package.get("targets", TARGET_COLS)
    sep = "-" * 75
    print(f"\n{sep}")
    print(f"  Molecule : {smiles}")
    print(f"{sep}")
    print(f"  {'Label':<18} {'Description':<42} {'Prob':>6}  {'Toxique'}")
    print(f"  {'-'*70}")
    for lbl in labels:
        prob    = row[f"{lbl}_prob"]
        toxique = "OUI [!]" if row[f"{lbl}_pred"] else "non"
        desc    = TARGET_DESCRIPTIONS.get(lbl, "")
        print(f"  {lbl:<18} {desc:<42} {prob:>6.3f}  {toxique}")
    print(f"{sep}")
    print(f"  Cibles toxiques : {int(row['n_toxic'])} / {len(labels)}")
    print(f"{sep}\n")
