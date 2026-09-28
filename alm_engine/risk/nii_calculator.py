from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# SOT NII (CDR EU 2024/856 / EBA RTS): parallel shocks only, 1Y horizon, 5% Tier 1.
NII_SOT_PARALLEL_SCENARIOS = frozenset({"Parallel Up", "Parallel Down"})
NII_SOT_THRESHOLD = 0.05


def calculate_nii(asset_cfs: pd.DataFrame, liability_costs: pd.DataFrame, horizon_years: float = 1.0) -> float:
    asset_hz = asset_cfs[asset_cfs["time"] <= horizon_years]
    liab_hz = liability_costs[liability_costs["time"] <= horizon_years]
    income = float(asset_hz.get("interest", pd.Series(dtype=float)).sum())
    expense = float(liab_hz.get("interest_cost", pd.Series(dtype=float)).sum())
    return income - expense


def delta_nii(base_nii: float, shocked_nii: float) -> float:
    return shocked_nii - base_nii


def is_nii_sot_applicable(scenario_name: str) -> bool:
    return scenario_name in NII_SOT_PARALLEL_SCENARIOS


def is_nii_sot_outlier(scenario_name: str, delta_nii_value: float, tier1_capital: float, threshold: float = NII_SOT_THRESHOLD) -> bool:
    """True if parallel-shock ΔNII decline exceeds threshold × Tier 1 (supervisory indicator)."""
    if not is_nii_sot_applicable(scenario_name):
        return False
    # "Large decline" = NII drops vs base → negative delta beyond threshold in magnitude.
    decline = max(0.0, -float(delta_nii_value))
    return decline > threshold * max(1.0, float(tier1_capital))


@dataclass(frozen=True)
class NIISOTSummary:
    applicable: bool
    breach: bool
    worst_scenario: str
    worst_delta_nii: float
    threshold_pct: float


def summarize_nii_sot(scenario_results: pd.DataFrame, tier1_capital: float, threshold: float = NII_SOT_THRESHOLD) -> NIISOTSummary:
    parallel = scenario_results[scenario_results["scenario"].isin(NII_SOT_PARALLEL_SCENARIOS)].copy()
    if parallel.empty:
        return NIISOTSummary(False, False, "", 0.0, threshold)
    # Worst = most negative ΔNII (largest decline)
    idx = parallel["delta_nii"].idxmin()
    worst = parallel.loc[idx]
    decline = max(0.0, -float(worst["delta_nii"]))
    breach = decline > threshold * max(1.0, float(tier1_capital))
    return NIISOTSummary(
        applicable=True,
        breach=breach,
        worst_scenario=str(worst["scenario"]),
        worst_delta_nii=float(worst["delta_nii"]),
        threshold_pct=threshold,
    )


def scenario_table(rows: list[dict[str, float | str | bool]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    preferred = [
        "scenario",
        "base_eve",
        "shocked_eve",
        "delta_eve",
        "outlier",
        "outlier_nii",
        "base_nii",
        "shocked_nii",
        "delta_nii",
        "base_ear",
        "shocked_ear",
        "delta_ear",
        "hedge_effect_nii",
    ]
    order = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in order]
    return df[order + remaining]
