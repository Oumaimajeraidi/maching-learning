"""
Builders et entraîneurs de modèles multi-label pour TOX21.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.multioutput import MultiOutputClassifier
import xgboost as xgb

RANDOM_STATE = 42


def build_random_forest(n_estimators: int = 200, **kwargs) -> MultiOutputClassifier:
    """Random Forest multi-label avec class_weight='balanced'."""
    base = RandomForestClassifier(
        n_estimators=n_estimators,
        min_samples_split=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        **kwargs,
    )
    return MultiOutputClassifier(base, n_jobs=-1)


def build_logistic_regression(C: float = 1.0, **kwargs) -> MultiOutputClassifier:
    """Régression Logistique multi-label avec class_weight='balanced'."""
    base = LogisticRegression(
        C=C,
        max_iter=1000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        **kwargs,
    )
    return MultiOutputClassifier(base, n_jobs=-1)


def build_xgboost(n_estimators: int = 200, **kwargs) -> MultiOutputClassifier:
    """XGBoost multi-label."""
    base = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbosity=0,
        **kwargs,
    )
    return MultiOutputClassifier(base, n_jobs=-1)


def get_probabilities(model: MultiOutputClassifier, X: np.ndarray) -> np.ndarray:
    """Extrait la matrice de probabilités (n_samples, n_labels)."""
    return np.column_stack([
        est.predict_proba(X)[:, 1] for est in model.estimators_
    ])
