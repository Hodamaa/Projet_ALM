import numpy as np
import pandas as pd

from alm_engine.risk.ear_calculator import calculate_ear
from alm_engine.risk.hedging_policy import SwapOverlayPolicy, hedge_curve_impact


def test_calculate_ear_zero_when_baseline_equals_stressed():
    asset = pd.DataFrame({"time": [0.5], "interest": [100.0]})
    liab = pd.DataFrame({"time": [0.5], "interest_cost": [40.0]})
    baseline = 60.0
    assert calculate_ear(asset, liab, baseline_nii=baseline, horizon_years=1.0) == 0.0


def test_hedge_curve_impact_changes_with_rate_shock():
    base = np.full(24, 0.02)
    shocked = np.full(24, 0.03)
    policy = SwapOverlayPolicy(notional=100_000_000, pay_fixed_rate=0.02)
    base_carry, shocked_carry = hedge_curve_impact(base, shocked, policy)
    assert shocked_carry > base_carry
