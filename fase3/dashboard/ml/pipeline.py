from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

FEATURES: List[str] = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"

ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = ROOT / "produtos_agricolas.csv"


def load_dataset(path: Path | str | None = None) -> pd.DataFrame:
    p = Path(path) if path else CSV_PATH
    return pd.read_csv(p)


def _build_models() -> Dict[str, Pipeline]:
    return {
        "Logistic Regression": Pipeline(
            [("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=2000, n_jobs=None))]
        ),
        "KNN (k=5)": Pipeline(
            [("scaler", StandardScaler()), ("clf", KNeighborsClassifier(n_neighbors=5))]
        ),
        "Decision Tree": Pipeline(
            [("clf", DecisionTreeClassifier(random_state=42))]
        ),
        "Random Forest": Pipeline(
            [("clf", RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1))]
        ),
        "Gradient Boosting": Pipeline(
            [("clf", GradientBoostingClassifier(random_state=42))]
        ),
        "Naive Bayes": Pipeline(
            [("scaler", StandardScaler()), ("clf", GaussianNB())]
        ),
    }


def train_models(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
    cv_folds: int = 5,
) -> Dict:
    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    models = _build_models()
    results = []
    fitted = {}
    reports = {}
    cms = {}

    for name, pipe in models.items():
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        cv = cross_val_score(pipe, X, y, cv=cv_folds, scoring="accuracy", n_jobs=-1)

        results.append(
            {
                "Modelo": name,
                "Acurácia": accuracy_score(y_test, y_pred),
                "Precisão (macro)": precision_score(y_test, y_pred, average="macro", zero_division=0),
                "Recall (macro)": recall_score(y_test, y_pred, average="macro", zero_division=0),
                "F1 (macro)": f1_score(y_test, y_pred, average="macro", zero_division=0),
                "CV Acc (média)": cv.mean(),
                "CV Acc (std)": cv.std(),
            }
        )
        fitted[name] = pipe
        reports[name] = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
        cms[name] = (confusion_matrix(y_test, y_pred, labels=sorted(y.unique())), sorted(y.unique()))

    metrics_df = (
        pd.DataFrame(results)
        .sort_values("F1 (macro)", ascending=False)
        .reset_index(drop=True)
    )

    return {
        "metrics": metrics_df,
        "models": fitted,
        "reports": reports,
        "confusion": cms,
        "split": (X_train, X_test, y_train, y_test),
        "classes": sorted(y.unique()),
    }


def ideal_profiles(df: pd.DataFrame, cultures: List[str]) -> pd.DataFrame:
    rows = []
    for c in cultures:
        sub = df[df[TARGET] == c]
        if sub.empty:
            continue
        row = {"Cultura": c}
        for feat in FEATURES:
            row[f"{feat} (média)"] = round(sub[feat].mean(), 2)
            row[f"{feat} (min)"] = round(sub[feat].min(), 2)
            row[f"{feat} (max)"] = round(sub[feat].max(), 2)
        rows.append(row)
    return pd.DataFrame(rows)
