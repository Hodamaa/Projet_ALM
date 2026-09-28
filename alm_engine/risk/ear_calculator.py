from __future__ import annotations

import pandas as pd


def calculate_ear(
    asset_cfs: pd.DataFrame,
    liability_costs: pd.DataFrame,
    baseline_nii: float,
    horizon_years: float = 1.0,
) -> float:
    stressed_nii = _calc_nii(asset_cfs, liability_costs, horizon_years=horizon_years)
    return stressed_nii - baseline_nii


def _calc_nii(asset_cfs: pd.DataFrame, liability_costs: pd.DataFrame, horizon_years: float) -> float:
    asset_hz = asset_cfs[asset_cfs["time"] <= horizon_years]
    liab_hz = liability_costs[liability_costs["time"] <= horizon_years]
    income = float(asset_hz.get("interest", pd.Series(dtype=float)).sum())
    expense = float(liab_hz.get("interest_cost", pd.Series(dtype=float)).sum())
    return income - expense

