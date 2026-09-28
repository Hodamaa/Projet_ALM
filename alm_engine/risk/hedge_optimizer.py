from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class HedgeOptimizationResult:
    optimal_notional: float
    objective_value: float
    best_scenario: str


def optimize_hedge_notional(
    run_engine_func,
    tier1_capital: float,
    cpr: float,
    include_internal_scenarios: bool,
    search_min: float = 0.0,
    search_max: float = 250_000_000.0,
    step: float = 10_000_000.0,
    balance_sheet=None,
    nmd_crisis_severity: float = 0.0,
) -> HedgeOptimizationResult:
    best_notional = search_min
    best_obj = float("inf")
    best_scenario = ""

    grid = []
    current = search_min
    while current <= search_max + 1e-9:
        grid.append(current)
        current += step

    for notional in grid:
        kwargs = {
            "tier1_capital": tier1_capital,
            "cpr": cpr,
            "include_internal_scenarios": include_internal_scenarios,
            "hedge_notional": notional,
            "nmd_crisis_severity": nmd_crisis_severity,
        }
        if balance_sheet is not None:
            kwargs["balance_sheet"] = balance_sheet
        table, _, _ = run_engine_func(**kwargs)
        objective = _objective_from_table(table)
        worst_scenario = _worst_scenario(table)
        if objective < best_obj:
            best_obj = objective
            best_notional = notional
            best_scenario = worst_scenario

    return HedgeOptimizationResult(optimal_notional=best_notional, objective_value=best_obj, best_scenario=best_scenario)


def _objective_from_table(table: pd.DataFrame) -> float:
    return float(table["delta_nii"].abs().max())


def _worst_scenario(table: pd.DataFrame) -> str:
    idx = table["delta_nii"].abs().idxmax()
    return str(table.loc[idx, "scenario"])

