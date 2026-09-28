from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from alm_engine.data.ecb_data import fetch_or_fallback_multi_maturity_history, fetch_or_fallback_short_rate_history
from alm_engine.models.nelson_siegel import NelsonSiegelSvenssonCurve


@dataclass
class HWCalibrationResult:
    mean_reversion: float
    sigma: float
    long_run_mean: float


def load_ecb_yields(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    expected = {"date", "yield"}
    if not expected.issubset(set(df.columns)):
        raise ValueError("ECB file must contain columns: date,yield")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def calibrate_from_historical_short_rate(df: pd.DataFrame, dt: float = 1 / 252) -> HWCalibrationResult:
    y = df["yield"].to_numpy(dtype=float)
    dy = np.diff(y)
    y_lag = y[:-1]
    x = np.column_stack([np.ones_like(y_lag), y_lag])
    alpha, beta = np.linalg.lstsq(x, dy, rcond=None)[0]
    residuals = dy - (alpha + beta * y_lag)
    a = max(1e-6, -beta / dt)
    mu = alpha / (a * dt) if a > 0 else np.mean(y)
    sigma = np.std(residuals, ddof=1) / np.sqrt(dt)
    return HWCalibrationResult(mean_reversion=float(a), sigma=float(max(1e-6, sigma)), long_run_mean=float(mu))


def default_nss_curve() -> NelsonSiegelSvenssonCurve:
    return NelsonSiegelSvenssonCurve(
        beta0=0.024,
        beta1=-0.011,
        beta2=0.018,
        beta3=-0.007,
        lambda1=1.2,
        lambda2=6.5,
    )


def calibrate_hw_from_ecb() -> tuple[HWCalibrationResult, str]:
    rates, source = fetch_or_fallback_short_rate_history()
    return calibrate_from_historical_short_rate(rates), source


def calibrate_nss_from_term_structure(
    latest_curve: pd.Series,
    maturities: np.ndarray,
    n_trials: int = 800,
    seed: int = 42,
) -> NelsonSiegelSvenssonCurve:
    y = latest_curve.to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    best_params = None
    best_loss = float("inf")

    # Random search is robust enough for this project and avoids heavy dependencies.
    for _ in range(n_trials):
        params = np.array(
            [
                rng.uniform(-0.01, 0.06),  # beta0
                rng.uniform(-0.05, 0.05),  # beta1
                rng.uniform(-0.05, 0.05),  # beta2
                rng.uniform(-0.05, 0.05),  # beta3
                rng.uniform(0.2, 5.0),  # lambda1
                rng.uniform(1.0, 15.0),  # lambda2
            ]
        )
        curve = NelsonSiegelSvenssonCurve(*params)
        pred = curve.zero_rate(maturities)
        loss = float(np.mean((pred - y) ** 2))
        if loss < best_loss:
            best_loss = loss
            best_params = params

    if best_params is None:
        return default_nss_curve()
    return NelsonSiegelSvenssonCurve(*best_params)


def calibrate_nss_from_ecb() -> tuple[NelsonSiegelSvenssonCurve, str]:
    term_structure, source = fetch_or_fallback_multi_maturity_history()
    latest = term_structure.iloc[-1]
    # Prefer classic ALM tenors when present; fall back to whatever columns we got.
    tenor_to_years = {
        "3M": 0.25,
        "1Y": 1.0,
        "2Y": 2.0,
        "5Y": 5.0,
        "10Y": 10.0,
        "20Y": 20.0,
        "30Y": 30.0,
    }
    cols = [c for c in tenor_to_years if c in latest.index]
    if not cols:
        cols = list(latest.index)
        # Unknown labels → treat as years if numeric-like, else skip to default
        maturities = np.array([float(str(c).rstrip("Y")) if str(c).endswith("Y") else float(c) for c in cols], dtype=float)
    else:
        maturities = np.array([tenor_to_years[c] for c in cols], dtype=float)
    return calibrate_nss_from_term_structure(latest[cols], maturities), source

