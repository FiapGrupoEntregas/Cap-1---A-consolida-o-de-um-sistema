from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

TRAINABLE_TARGETS = [
    "soil_moisture_percent",
    "ph",
    "nitrogen",
    "phosphorus",
    "potassium",
    "air_temperature",
    "air_humidity",
    "light_percent",
]

FEATURE_COLUMNS = [
    "air_humidity",
    "air_temperature",
    "soil_moisture_raw",
    "ph",
    "nitrogen",
    "phosphorus",
    "potassium",
    "light_raw",
    "light_percent",
]


def _prepare_data(
    df: pd.DataFrame,
    target: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    if target not in df.columns:
        raise ValueError(f"Coluna alvo '{target}' não encontrada nos dados.")

    available_features = [col for col in FEATURE_COLUMNS if col in df.columns and col != target]
    df = df[[target, *available_features]].dropna()

    if df.empty:
        raise ValueError("Nenhum dado válido após remover valores ausentes.")

    X = df[available_features].values
    y = df[target].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, scaler


def train_regression(
    df: pd.DataFrame,
    target: str,
    model_type: str = "random_forest",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, Any]:
    X_train, X_test, y_train, y_test, scaler = _prepare_data(
        df, target, test_size=test_size, random_state=random_state
    )

    model = RandomForestRegressor(n_estimators=100, random_state=random_state)

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    return {
        "target": target,
        "model_type": model_type,
        "model": model,
        "scaler": scaler,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "y_pred": y_pred,
        "metrics": {
            "r2": float(r2_score(y_test, y_pred)),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "mse": float(mean_squared_error(y_test, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        },
    }


def predict_next(
    model: Any,
    scaler: StandardScaler,
    last_row: pd.Series,
    feature_columns: List[str],
    target: str,
) -> Optional[float]:
    features = [col for col in FEATURE_COLUMNS if col in last_row.index and col != target]
    if not features:
        return None
    X = last_row[features].values.reshape(1, -1)
    X_scaled = scaler.transform(X)
    return float(model.predict(X_scaled)[0])
