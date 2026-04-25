"""Phase 2 — AnomalyDetector.

Reads time-series rows from the `time_series_data` table, trains a
`sklearn.ensemble.IsolationForest` per metric (with hour-of-day as a
contextual feature so that "low sales at 11 AM" can be distinguished
from "low sales at 3 AM"), and returns anomalies as a list of dicts
that satisfies the locked Phase 2 I/O contract:

    [{"timestamp": "<isoformat>",
      "metric":    "<name>",
      "value":     <float>,
      "status":    "anomaly"}, ...]
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy import select

from src.db.connection import TimeSeriesData, get_session


class AnomalyDetector:
    """Per-metric IsolationForest detector over the SRAE time-series table."""

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
    ) -> None:
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.models: dict[str, IsolationForest] = {}

    def load(self) -> pd.DataFrame:
        """Fetch every row from `time_series_data`, ordered by metric and ts."""
        with get_session() as session:
            rows = (
                session.execute(
                    select(TimeSeriesData).order_by(
                        TimeSeriesData.metric_name, TimeSeriesData.ts
                    )
                )
                .scalars()
                .all()
            )
        return pd.DataFrame(
            {"ts": r.ts, "metric_name": r.metric_name, "value": r.value}
            for r in rows
        )

    @staticmethod
    def _features(df: pd.DataFrame) -> np.ndarray:
        ts = pd.to_datetime(df["ts"], utc=True)
        hour = ts.dt.hour.to_numpy()
        value = df["value"].to_numpy(dtype=float)
        return np.column_stack([value, hour])

    def fit(self, df: Optional[pd.DataFrame] = None) -> "AnomalyDetector":
        """Train one IsolationForest per metric_name."""
        if df is None:
            df = self.load()
        self.models = {}
        for metric, group in df.groupby("metric_name"):
            model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=self.random_state,
            )
            model.fit(self._features(group))
            self.models[str(metric)] = model
        return self

    def detect(self, df: Optional[pd.DataFrame] = None) -> list[dict]:
        """Return anomalies in the contract shape. Trains on first call."""
        if df is None:
            df = self.load()
        if not self.models:
            self.fit(df)

        anomalies: list[dict] = []
        for metric, group in df.groupby("metric_name"):
            metric_key = str(metric)
            model = self.models.get(metric_key)
            if model is None:
                model = IsolationForest(
                    contamination=self.contamination,
                    n_estimators=self.n_estimators,
                    random_state=self.random_state,
                )
                model.fit(self._features(group))
                self.models[metric_key] = model

            preds = model.predict(self._features(group))
            for (_, row), pred in zip(group.iterrows(), preds):
                if pred != -1:
                    continue
                ts = row["ts"]
                anomalies.append(
                    {
                        "timestamp": ts.isoformat(),
                        "metric": metric_key,
                        "value": float(row["value"]),
                        "status": "anomaly",
                    }
                )

        anomalies.sort(key=lambda r: (r["metric"], r["timestamp"]))
        return anomalies
