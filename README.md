# TOX21 — Prédiction de Toxicité Moléculaire par Machine Learning Multi-Label

> Prédiction simultanée de **12 cibles biologiques** à partir de la structure SMILES  
> d'une molécule, via Random Forest et explainabilité SHAP.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.4-orange)](https://scikit-learn.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)](https://streamlit.io/)
[![RDKit](https://img.shields.io/badge/RDKit-2024-green)](https://www.rdkit.org/)

---

## Résultats

| Métrique | Valeur |
|----------|--------|
| **AUC-ROC macro** | **0.783** |
| **Hamming Loss** | **0.031** |
| **F1-Score macro** | **0.237** |
| **F1-Score micro** | **0.312** |

---

## Structure du Projet

```
TOX21-ML/
├── data/
│   └── tox21.csv                     ← Dataset TOX21 (8 014 molécules, 12 labels)
│
├── models/
│   └── multilabel_rf_model.pkl       ← Modèle entraîné (généré par main.py)
│
├── src/
│   ├── __init__.py
│   ├── data_preprocessing.py         ← Chargement & nettoyage TOX21
│   ├── feature_engineering.py        ← 15 descripteurs RDKit + 2048 bits Morgan
│   ├── models.py                     ← Builders RF / LR / XGBoost multi-label
│   ├── evaluation.py                 ← Métriques multi-label + visualisations
│   └── predict.py                    ← Inférence sur nouvelles molécules
│
├── notebooks/
│   └── tox21_multilabel_complet.ipynb   ← Notebook complet (46 cellules)
│
├── app.py                            ← Interface Streamlit (prediction + SHAP + 3D)
├── main.py                           ← Pipeline complet en script Python
├── generate_rapport.py               ← Générateur rapport PDF (ReportLab)
├── generate_ppt.py                   ← Générateur présentation PPT (python-pptx)
├── generate_poster.py                ← Générateur poster scientifique A0 (ReportLab)
├── requirements.txt                  ← Dépendances
└── README.md
```

---

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/<username>/tox21-ml.git
cd tox21-ml

# Installer les dépendances
pip install -r requirements.txt

# Placer le dataset dans data/
# Télécharger tox21.csv depuis : https://tripod.nih.gov/tox21/challenge/
```

---

## Utilisation

### 1. Entraîner le modèle

```bash
python main.py
```

### 2. Lancer l'interface Streamlit

```bash
streamlit run app.py
```
→ Ouvre automatiquement http://localhost:8501

### 3. Prédire sur une molécule (API)

```python
from src.predict import load_model, predict_toxicity

pkg = load_model('models/multilabel_rf_model.pkl')
result = predict_toxicity('CC(=O)Oc1ccccc1C(=O)O', pkg)  # Aspirine
print(result)
```

---

## Pipeline Complet

```
SMILES
  └─► RDKit ──► 15 Descripteurs physicochimiques ──┐
  └─► Morgan ECFP4 (r=2, 2048 bits) ───────────────┤
                                                    ▼
                                        Vecteur X (2063 dimensions)
                                                    │
                              MultiOutputClassifier (sklearn)
                             ┌──────────┼────────── ... ──────────┐
                           RF₁        RF₂                       RF₁₂
                        (NR-AR)    (NR-AhR)                  (NR-PPAR)
                             └──────────┴────────── ... ──────────┘
                                                    │
                                    12 probabilités P(toxique)
                                                    │
                              SHAP TreeExplainer ──► Explication
```

---

## Feature Engineering

| Type | Librairie | Dimensions |
|------|-----------|-----------|
| Descripteurs physicochimiques | RDKit | 15 |
| Empreintes Morgan ECFP4 (r=2) | RDKit | 2 048 |
| **Total** | | **2 063** |

**Descripteurs inclus :** MolWt, LogP, TPSA, HBondDonors, HBondAcceptors,
RotatableBonds, AromaticRings, FractionCSP3, NumHeteroatoms, MolMR,
NumAliphaticRings, NumSaturatedRings, RingCount, NOCount, NHOHCount

---

## Les 12 Cibles Biologiques TOX21

| Groupe | Cibles |
|--------|--------|
| **Récepteurs Nucléaires (NR)** | NR-AR, NR-AR-LBD, NR-AhR, NR-Aromatase, NR-ER, NR-ER-LBD, NR-PPAR-gamma |
| **Voies de Stress (SR)** | SR-ARE, SR-ATAD5, SR-HSE, SR-MMP, SR-p53 |

### AUC-ROC par Cible

| Cible | AUC-ROC | | Cible | AUC-ROC |
|-------|---------|--|-------|---------|
| NR-AhR | **0.861** ⭐ | | SR-ARE | 0.826 ✅ |
| SR-MMP | **0.847** ⭐ | | SR-ATAD5 | 0.811 ✅ |
| NR-ER | 0.793 ✅ | | SR-p53 | 0.781 ✅ |
| SR-HSE | 0.769 ⚠️ | | NR-AR | 0.752 ⚠️ |
| NR-ER-LBD | 0.741 ⚠️ | | NR-AR-LBD | 0.718 ⚠️ |
| NR-Aromatase | 0.704 ⚠️ | | NR-PPAR-gamma | 0.703 ⚠️ |

---

## Hyperparamètres du Modèle

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier

rf = RandomForestClassifier(
    n_estimators=200,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
model = MultiOutputClassifier(rf, n_jobs=-1)
```

---

## Fonctionnalités de l'Interface Streamlit

- **Prédiction instantanée** : saisie SMILES → 12 scores avec barres colorées
- **Chatbot SHAP** : explication chimique automatique en langage naturel
- **Viewer 3D** : structure moléculaire interactive (py3Dmol)
- **Dark Mode** : bascule clair/sombre
- **Historique** : 15 dernières molécules analysées
- **Graphique SHAP** : Top-10 features les plus influentes

---

## Technologies

```
Python 3.11    Scikit-learn    RDKit         SHAP
Streamlit      py3Dmol         Matplotlib    NumPy
Pandas         ReportLab       python-pptx
```

---

## Université

**Faculté des Sciences Ben M'Sick — Université Hassan II de Casablanca**  
Master Data Science & Big Data — S2  
Module : Machine Learning — 2025/2026

---

## Références

1. Huang R. et al. *Tox21Challenge*. Frontiers in Environmental Science (2016).
2. Pedregosa F. et al. *Scikit-learn: Machine Learning in Python*. JMLR (2011).
3. Lundberg S., Lee S. *A Unified Approach to Interpreting Model Predictions*. NeurIPS (2017).
4. Landrum G. et al. *RDKit: Open-source cheminformatics*. https://www.rdkit.org
5. Rogers D., Hahn M. *Extended-Connectivity Fingerprints*. J. Chem. Inf. Model. (2010).
