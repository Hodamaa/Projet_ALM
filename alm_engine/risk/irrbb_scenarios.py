from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IRRBBShock:
    name: str
    short_bp: float
    long_bp: float
    mode: str


def _maturity_weight(maturities: np.ndarray, cutoff: float = 2.0) -> np.ndarray:
    return np.exp(-np.maximum(maturities, 1e-8) / cutoff)


def apply_shock(base_curve: np.ndarray, maturities: np.ndarray, shock: IRRBBShock) -> np.ndarray:
    s = shock.short_bp / 10000.0
    l = shock.long_bp / 10000.0
    w_short = _maturity_weight(maturities)
    w_long = 1.0 - w_short

    if shock.mode == "parallel":
        delta = s * np.ones_like(base_curve)
    elif shock.mode == "steepener":
        delta = -abs(s) * w_short + abs(l) * w_long
    elif shock.mode == "flattener":
        delta = abs(s) * w_short - abs(l) * w_long
    elif shock.mode == "short_only":
        delta = s * w_short
    else:
        raise ValueError(f"Unknown shock mode: {shock.mode}")

    shocked = base_curve + delta
    return np.maximum(shocked, 0.0)


def standard_irrbb_scenarios() -> list[IRRBBShock]:
    return [
        IRRBBShock("Parallel Up", 200.0, 200.0, "parallel"),
        IRRBBShock("Parallel Down", -200.0, -200.0, "parallel"),
        IRRBBShock("Steepener", -65.0, 90.0, "steepener"),
        IRRBBShock("Flattener", 80.0, -60.0, "flattener"),
        IRRBBShock("Short Rate Up", 250.0, 0.0, "short_only"),
        IRRBBShock("Short Rate Down", -250.0, 0.0, "short_only"),
    ]

