"""Crowd forecasting model.

Target: utilisation = visitors present / carrying capacity, modelled as log(util + EPS). Utilisation is
scale-free, so one model serves every attraction and a newly added attraction gets forecasts from its
category, capacity, popularity and season without its own history (no attraction-ID feature).

Evaluation is chronological: train | validation (hyper-parameter choice) | test (reported once).
Two baselines are reported on the same test period: seasonal-naive (same hour one week earlier)
and the weekday x hour mean per attraction.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from . import crowd_sim

EPS = 0.02
TEST_DAYS = 14
VAL_DAYS = 14
MIN_COUNT_FOR_MAPE = 10
CATEGORIES = ["adventure", "beach", "garden", "heritage", "lake", "market", "museum", "nature", "plantation",
              "river", "spiritual", "viewpoint", "waterfall", "wildlife", "other"]
CLIMATES = ["coastal", "desert", "mountain", "plains", "tropical"]
FEATURES = ["category", "climate", "hour", "dow", "is_weekend", "is_holiday", "festival", "month", "in_season",
            "rain", "popularity", "log_capacity", "open_frac", "covered", "sensitive"]
CANDIDATES = [
    dict(learning_rate=0.06, max_leaf_nodes=31, max_iter=400, min_samples_leaf=20, l2_regularization=1.0),
    dict(learning_rate=0.10, max_leaf_nodes=63, max_iter=250, min_samples_leaf=40, l2_regularization=0.5),
]


def metrics(actual, pred) -> dict:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    m = actual >= MIN_COUNT_FOR_MAPE
    mape = float(np.mean(np.abs(actual[m] - pred[m]) / actual[m]) * 100) if m.any() else float("nan")
    wape = float(np.sum(np.abs(actual - pred)) / max(np.sum(actual), 1e-9) * 100)
    ss_res = float(np.sum((actual - pred) ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2)) or 1e-9
    return {"mape": round(mape, 2), "wape": round(wape, 2), "mae": round(float(np.mean(np.abs(actual - pred))), 1),
            "r2": round(1 - ss_res / ss_tot, 4), "n": int(len(actual))}


def features(df: pd.DataFrame, spec_by_key: dict[str, dict]) -> pd.DataFrame:
    """df needs columns key, date, hour, rain. Returns the model feature frame."""
    sp = df["key"].map(spec_by_key)
    dates = pd.to_datetime(df["date"])
    hol = df["date"].map(crowd_sim.holiday)
    open_h = sp.map(lambda s: s["open_hour"])
    close_h = sp.map(lambda s: s["close_hour"])
    cat = sp.map(lambda s: s["category"] if s["category"] in CATEGORIES else "other")
    out = pd.DataFrame({
        "category": pd.Categorical(cat, categories=CATEGORIES),
        "climate": pd.Categorical(sp.map(lambda s: s.get("climate", "plains")), categories=CLIMATES),
        "hour": df["hour"].astype(int).values,
        "dow": dates.dt.day_of_week.values,
        "is_weekend": (dates.dt.day_of_week >= 5).astype(int).values,
        "is_holiday": hol.map(lambda h: int(h["holiday"])).values,
        "festival": hol.map(lambda h: int(h["festival"])).values,
        "month": dates.dt.month.values,
        "in_season": [int(crowd_sim.in_season(s, m)) for s, m in zip(sp, dates.dt.month)],
        "rain": df["rain"].astype(float).values,
        "popularity": sp.map(lambda s: s["popularity"]).astype(float).values,
        "log_capacity": np.log(sp.map(lambda s: s["capacity"]).astype(float).values),
        "open_frac": ((df["hour"] - open_h) / (close_h - open_h).clip(lower=1)).astype(float).values,
        "covered": sp.map(lambda s: int(bool(s.get("covered")))).values,
        "sensitive": sp.map(lambda s: int(bool(s.get("sensitive")))).values,
    })
    return out[FEATURES]


def _regressor(params):
    return HistGradientBoostingRegressor(categorical_features="from_dtype", random_state=7, **params)


class CrowdModel:
    def __init__(self):
        self.reg = None
        self.sigma: float = 0.15
        self.sigma_by_category: dict[str, float] = {}
        self.info: dict = {}

    # ------------------------------------------------------------------ training
    def train(self, specs: list[dict], end_date: dt.date | None = None, days: int = 365) -> dict:
        t0 = time.time()
        end_date = end_date or dt.date.today()
        by_key = {s["key"]: s for s in specs}
        hist = crowd_sim.counts(specs, crowd_sim.date_range(end_date, days))
        cap = hist["key"].map(lambda k: by_key[k]["capacity"]).astype(float)
        hist["util"] = hist["count"] / cap
        X = features(hist, by_key)
        y = np.log(hist["util"].values + EPS)

        test_start = end_date - dt.timedelta(days=TEST_DAYS)
        val_start = test_start - dt.timedelta(days=VAL_DAYS)
        tr = (hist["date"] < val_start).values
        va = ((hist["date"] >= val_start) & (hist["date"] < test_start)).values
        te = (hist["date"] >= test_start).values

        def to_counts(pred_log, mask):
            return np.clip(np.exp(pred_log) - EPS, 0, None) * cap.values[mask]

        # 1) choose hyper-parameters on the validation period
        val_scores = []
        for p in CANDIDATES:
            r = _regressor(p).fit(X[tr], y[tr])
            val_scores.append(metrics(hist["count"].values[va], to_counts(r.predict(X[va]), va))["mape"])
        best = CANDIDATES[int(np.argmin(val_scores))]

        # 2) refit on train+validation, score once on the untouched test period
        trva = tr | va
        r = _regressor(best).fit(X[trva], y[trva])
        pred_te = to_counts(r.predict(X[te]), te)
        actual_te = hist["count"].values[te]
        test_m = metrics(actual_te, pred_te)
        resid = np.log(np.clip(pred_te / cap.values[te], 0, None) + EPS) - np.log(hist["util"].values[te] + EPS)
        self.sigma = float(max(0.05, np.std(resid)))
        cats = X["category"].values[te]
        self.sigma_by_category = {str(c): float(max(0.05, np.std(resid[cats == c]))) for c in pd.unique(cats)}

        # 3) baselines on the same test rows
        h = hist.set_index(["key", "date", "hour"])["count"]
        prev = [h.get((k, d - dt.timedelta(days=7), hr), np.nan)
                for k, d, hr in zip(hist["key"][te], hist["date"][te], hist["hour"][te])]
        prev = np.array(prev, float)
        ok = ~np.isnan(prev)
        hist_trva = hist[trva].assign(dow=pd.to_datetime(hist["date"][trva]).dt.day_of_week)
        mean_tbl = hist_trva.groupby(["key", "dow", "hour"])["count"].mean()
        dows = pd.to_datetime(hist["date"][te]).dt.day_of_week
        wm = np.array([mean_tbl.get((k, dw, hr), np.nan)
                       for k, dw, hr in zip(hist["key"][te], dows, hist["hour"][te])], float)
        wm = np.nan_to_num(wm, nan=float(np.nanmean(actual_te)))

        # 4) feature importance (permutation on a test sample)
        top = []
        try:
            from sklearn.inspection import permutation_importance
            idx = np.random.default_rng(1).choice(np.where(te)[0], size=min(2000, int(te.sum())), replace=False)
            imp = permutation_importance(r, X.iloc[idx], y[idx], n_repeats=3, random_state=1, n_jobs=1)
            top = sorted(zip(FEATURES, imp.importances_mean), key=lambda kv: -kv[1])[:6]
        except Exception:  # pragma: no cover - importance is informative only
            pass

        # 5) final serving model on all history
        self.reg = _regressor(best).fit(X, y)
        d = lambda x: x.isoformat()  # noqa: E731
        self.info = {
            "backend": "scikit-learn HistGradientBoostingRegressor",
            "target": "log(utilisation + 0.02); utilisation = visitors / assumed carrying capacity",
            "trained_at": dt.datetime.now().isoformat(timespec="seconds"),
            "history_end": d(end_date), "history_days": days, "attractions": len(specs),
            "data_provenance": "demonstration",
            "split": {"train_start": d(end_date - dt.timedelta(days=days)), "train_end": d(val_start - dt.timedelta(days=1)),
                      "val_start": d(val_start), "val_end": d(test_start - dt.timedelta(days=1)),
                      "test_start": d(test_start), "test_end": d(end_date - dt.timedelta(days=1))},
            "rows": {"train": int(tr.sum()), "validation": int(va.sum()), "test": int(te.sum())},
            "chosen_params": best, "validation_mape_by_candidate": val_scores,
            "test_metrics": test_m,
            "baselines": {
                "seasonal_naive": {**metrics(actual_te[ok], prev[ok]), "description": "same attraction and hour, 7 days earlier"},
                "weekday_hour_mean": {**metrics(actual_te, wm), "description": "mean of train+validation by attraction, weekday, hour"},
            },
            "uncertainty": {"method": "log-normal residual spread on the test period (80% band = ±1.28σ)",
                            "sigma": round(self.sigma, 4)},
            "top_features": [{"feature": f, "importance": round(float(v), 4)} for f, v in top],
            "features": FEATURES,
            "note": "Measured on DEMONSTRATION (simulated) data: shows the pipeline works, not real-world accuracy.",
            "seconds": round(time.time() - t0, 1),
        }
        return self.info

    # ---------------------------------------------------------------- inference
    def predict_util(self, rows) -> np.ndarray:
        """rows: iterable of (spec, date, hour, rain) -> predicted utilisation per row."""
        rows = list(rows)
        if not rows:
            return np.array([])
        by_key = {r[0]["key"]: r[0] for r in rows}
        df = pd.DataFrame({"key": [r[0]["key"] for r in rows], "date": [r[1] for r in rows],
                           "hour": [r[2] for r in rows], "rain": [r[3] for r in rows]})
        return np.clip(np.exp(self.reg.predict(features(df, by_key))) - EPS, 0, None)

    def sigma_for(self, category: str) -> float:
        return self.sigma_by_category.get(category, self.sigma)

    # ---------------------------------------------------------------- persistence
    def save(self, directory: Path | str) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump({"reg": self.reg, "sigma": self.sigma, "sigma_by_category": self.sigma_by_category,
                     "info": self.info}, directory / "crowd_model.joblib")
        (directory / "metrics.json").write_text(json.dumps(self.info, indent=2))

    @classmethod
    def load(cls, directory: Path | str) -> "CrowdModel":
        blob = joblib.load(Path(directory) / "crowd_model.joblib")
        m = cls()
        m.reg, m.sigma, m.sigma_by_category, m.info = blob["reg"], blob["sigma"], blob["sigma_by_category"], blob["info"]
        return m
