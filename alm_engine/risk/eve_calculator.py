from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class EVEMetrics:
    base_eve: float
    shocked_eve: float
    delta_eve: float
    outlier: bool


def pv_cashflows(cashflows: pd.DataFrame, zero_curve: np.ndarray) -> float:
    if cashflows.empty:
        return 0.0
    idx = np.clip((cashflows["time"].to_numpy() * 12).astype(int) - 1, 0, len(zero_curve) - 1)
    rates = zero_curve[idx]
    dfs = np.exp(-rates * cashflows["time"].to_numpy())
    return float(np.sum(cashflows["cashflow"].to_numpy() * dfs))


def calculate_eve(
    asset_cfs: pd.DataFrame,
    liability_cfs: pd.DataFrame,
    base_curve: np.ndarray,
    shocked_curve: np.ndarray,
    tier1_capital: float,
    threshold: float = 0.15,
    shocked_liability_cfs: pd.DataFrame | None = None,
) -> EVEMetrics:
    base_assets = pv_cashflows(asset_cfs, base_curve)
    base_liabs = pv_cashflows(liability_cfs, base_curve)
    liab_shocked = liability_cfs if shocked_liability_cfs is None else shocked_liability_cfs
    shocked_assets = pv_cashflows(asset_cfs, shocked_curve)
    shocked_liabs = pv_cashflows(liab_shocked, shocked_curve)

    base_eve = base_assets - base_liabs
    shocked_eve = shocked_assets - shocked_liabs
    delta = shocked_eve - base_eve
    outlier = abs(delta) > threshold * tier1_capital
    return EVEMetrics(base_eve=base_eve, shocked_eve=shocked_eve, delta_eve=delta, outlier=outlier)

