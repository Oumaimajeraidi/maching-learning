"""
Feature engineering for TOX21.
Produces: 15 physicochemical descriptors + 2048-bit Morgan fingerprint (ECFP4).
"""

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors, DataStructs, AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

# ── Constants ──────────────────────────────────────────────────────────────────
FP_RADIUS = 2
FP_NBITS  = 2048

DESCRIPTOR_NAMES = [
    "MolWt",           # Poids moléculaire
    "LogP",            # Lipophilicité
    "TPSA",            # Aire polaire topologique de surface
    "NumAtoms",        # Nombre d'atomes
    "NumBonds",        # Nombre de liaisons
    "HBondDonors",     # Donneurs de liaisons hydrogène
    "HBondAcceptors",  # Accepteurs de liaisons hydrogène
    "RotatableBonds",  # Liaisons rotatives
    "AromaticRings",   # Anneaux aromatiques
    "FractionCSP3",    # Fraction de carbones sp3
    "HeavyAtomCount",  # Atomes lourds
    "NumRings",        # Nombre de cycles
    "NumHeteroatoms",  # Hétéroatomes
    "NumAliphaticRings",# Cycles aliphatiques
    "MolMR",           # Réfractivité molaire
]


def smiles_to_mol(smiles: str):
    """Convertit un SMILES en RDKit Mol. Retourne None si invalide."""
    try:
        return Chem.MolFromSmiles(str(smiles))
    except Exception:
        return None


def compute_descriptors(mol) -> list | None:
    """Calcule 15 descripteurs physicochimiques. Retourne None si erreur."""
    if mol is None:
        return None
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


def compute_morgan_fp(mol, radius: int = FP_RADIUS, nbits: int = FP_NBITS) -> np.ndarray:
    """Retourne le Morgan fingerprint (ECFP4) sous forme de tableau numpy uint8."""
    fp  = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=nbits)
    arr = np.zeros(nbits, dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def featurize(
    smiles_list: list,
    radius: int = FP_RADIUS,
    nbits:  int = FP_NBITS,
) -> tuple[np.ndarray, list[str], list[int]]:
    """
    Extrait les features (descripteurs + fingerprint) d'une liste de SMILES.

    Retourne
    --------
    X             : np.ndarray  (n_valides, 15 + nbits)
    feature_names : list[str]
    valid_indices : list[int]   indices dans smiles_list qui ont réussi
    """
    descs, fps, valid_idx = [], [], []

    for i, smi in enumerate(smiles_list):
        mol  = smiles_to_mol(smi)
        desc = compute_descriptors(mol)
        if desc is None:
            continue
        fp = compute_morgan_fp(mol, radius, nbits)
        descs.append(desc)
        fps.append(fp)
        valid_idx.append(i)

    if not descs:
        return np.empty((0, 15 + nbits)), get_feature_names(nbits), []

    X = np.hstack([
        np.array(descs, dtype=np.float32),
        np.array(fps,   dtype=np.float32),
    ])
    return X, get_feature_names(nbits), valid_idx


def get_feature_names(nbits: int = FP_NBITS) -> list[str]:
    """Retourne la liste ordonnée des noms de features."""
    return DESCRIPTOR_NAMES + [f"FP_{i}" for i in range(nbits)]
