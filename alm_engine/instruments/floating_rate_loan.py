from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FloatingRateLoan:
    notional: float
    spread: float
    maturity_years: float
    payments_per_year: int = 12

    def cashflows(self, forward_curve: np.ndarray) -> pd.DataFrame:
        n_periods = int(self.maturity_years * self.payments_per_year)
        if len(forward_curve) < n_periods:
            raise ValueError("forward_curve length is too short for maturity")
        period_dt = 1.0 / self.payments_per_year
        principal_amort = self.notional / n_periods
        balance = self.notional
        rows: list[dict[str, float]] = []
        for i in range(n_periods):
            t = (i + 1) * period_dt
            coupon_rate = forward_curve[i] + self.spread
            interest = balance * coupon_rate * period_dt
            principal = min(balance, principal_amort)
            balance = max(0.0, balance - principal)
            rows.append(
                {
                    "time": t,
                    "rate": coupon_rate,
                    "interest": interest,
                    "principal_total": principal,
                    "cashflow": interest + principal,
                    "balance": balance,
                }
            )
        return pd.DataFrame(rows)

