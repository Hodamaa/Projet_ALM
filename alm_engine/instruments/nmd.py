from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class NonMaturityDeposit:
    notional: float
    beta: float = 0.3
    core_ratio: float = 0.8
    behavioral_maturity_years: float = 4.0
    admin_margin: float = 0.0025
    payments_per_year: int = 12

    def replicated_cashflows(self, rates: np.ndarray) -> pd.DataFrame:
        n_periods = len(rates)
        dt = 1.0 / self.payments_per_year
        times = np.arange(1, n_periods + 1, dtype=float) * dt
        core = self.notional * self.core_ratio
        run_off = core / max(1, int(self.behavioral_maturity_years * self.payments_per_year))

        balances = []
        interest_costs = []
        balance = self.notional
        for i, r in enumerate(rates):
            effective_rate = max(0.0, self.beta * r - self.admin_margin)
            interest = balance * effective_rate * dt
            decay = run_off if i < int(self.behavioral_maturity_years * self.payments_per_year) else 0.0
            balance = max(self.notional - core, balance - decay)
            balances.append(balance)
            interest_costs.append(interest)
        return pd.DataFrame({"time": times, "balance": balances, "interest_cost": interest_costs})

