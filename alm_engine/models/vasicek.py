from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class VasicekModel:
    mean_reversion: float
    long_term_mean: float
    sigma: float

    def simulate_short_rate(
        self,
        r0: float,
        horizon_years: float,
        steps_per_year: int = 12,
        n_paths: int = 1000,
        seed: int | None = 42,
    ) -> tuple[np.ndarray, np.ndarray]:
        dt = 1.0 / steps_per_year
        n_steps = int(horizon_years * steps_per_year)
        times = np.linspace(0.0, horizon_years, n_steps + 1)
        rates = np.zeros((n_paths, n_steps + 1), dtype=float)
        rates[:, 0] = r0
        rng = np.random.default_rng(seed)
        for i in range(1, n_steps + 1):
            z = rng.standard_normal(n_paths)
            rates[:, i] = (
                rates[:, i - 1]
                + self.mean_reversion * (self.long_term_mean - rates[:, i - 1]) * dt
                + self.sigma * np.sqrt(dt) * z
            )
        return times, rates

