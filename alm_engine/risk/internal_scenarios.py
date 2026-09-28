from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class InternalScenario:
    name: str
    level_shift_bp: float
    slope_bp: float
    curvature_bp: float


def _hump(x: np.ndarray, center: float = 5.0, width: float = 3.0) -> np.ndarray:
    return np.exp(-((x - center) ** 2) / (2 * width * width))


def apply_internal_scenario(base_curve: np.ndarray, maturities: np.ndarray, scenario: InternalScenario) -> np.ndarray:
    level = scenario.level_shift_bp / 10000.0
    slope = scenario.slope_bp / 10000.0
    curvature = scenario.curvature_bp / 10000.0
    mat_norm = (maturities - maturities.min()) / max(1e-8, maturities.max() - maturities.min())
    delta = level + slope * (0.5 - mat_norm) + curvature * _hump(maturities)
    return np.maximum(base_curve + delta, 0.0)


def internal_icaap_scenarios() -> list[InternalScenario]:
    return [
        InternalScenario("ICAAP Stagflation", 150.0, -80.0, 60.0),
        InternalScenario("ICAAP Recession Bull-Flattening", -120.0, 90.0, 40.0),
        InternalScenario("ICAAP Policy Shock", 90.0, 160.0, -40.0),
    ]

