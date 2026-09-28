from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class FixedRateLoan:
    notional: float
    annual_rate: float
    maturity_years: float
    payments_per_year: int = 12
    cpr: float = 0.0

    def cashflows(self) -> pd.DataFrame:
        n_periods = int(self.maturity_years * self.payments_per_year)
        period_rate = self.annual_rate / self.payments_per_year
        times = np.arange(1, n_periods + 1, dtype=float) / self.payments_per_year
        if period_rate == 0:
            installment = self.notional / n_periods
        else:
            installment = self.notional * period_rate / (1 - (1 + period_rate) ** (-n_periods))

        smm = 1.0 - (1.0 - self.cpr) ** (1.0 / 12.0)
        balance = self.notional
        rows: list[dict[str, float]] = []
        for t in times:
            interest = balance * period_rate
            principal_sched = max(0.0, installment - interest)
            principal_sched = min(principal_sched, balance)
            prepay = smm * max(0.0, balance - principal_sched)
            principal_total = min(balance, principal_sched + prepay)
            balance = max(0.0, balance - principal_total)
            rows.append(
                {
                    "time": t,
                    "interest": interest,
                    "principal_scheduled": principal_sched,
                    "prepayment": prepay,
                    "principal_total": principal_total,
                    "cashflow": interest + principal_total,
                    "balance": balance,
                }
            )
            if balance <= 1e-8:
                break
        return pd.DataFrame(rows)

    def wal(self) -> float:
        cf = self.cashflows()
        principal = cf["principal_total"].to_numpy()
        if principal.sum() <= 0:
            return 0.0
        return float((cf["time"].to_numpy() * principal).sum() / principal.sum())

