from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SwapOverlayPolicy:
    notional: float
    pay_fixed_rate: float
    receive_float_spread: float = 0.0


def hedge_curve_impact(base_curve: np.ndarray, shocked_curve: np.ndarray, policy: SwapOverlayPolicy) -> tuple[float, float]:
    base_short = float(np.mean(base_curve[:12]))
    shocked_short = float(np.mean(shocked_curve[:12]))
    base_carry = policy.notional * ((base_short + policy.receive_float_spread) - policy.pay_fixed_rate)
    shocked_carry = policy.notional * ((shocked_short + policy.receive_float_spread) - policy.pay_fixed_rate)
    return base_carry, shocked_carry

