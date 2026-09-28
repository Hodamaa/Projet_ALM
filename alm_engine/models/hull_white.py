from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from alm_engine.models.nelson_siegel import NelsonSiegelSvenssonCurve


@dataclass
class HullWhite1F:
    mean_reversion: float
    sigma: float
    curve: NelsonSiegelSvenssonCurve

    def theta(self, t: float, dt: float = 1e-4) -> float:
        t1 = max(1e-8, t - dt)
        t2 = t + dt
        f1 = self.curve.forward_rate(t1)
        f2 = self.curve.forward_rate(t2)
        df_dt = (f2 - f1) / (t2 - t1)
        a = self.mean_reversion
        sig = self.sigma
        return df_dt + a * self.curve.forward_rate(t) + (sig * sig / (2.0 * a)) * (1.0 - np.exp(-2.0 * a * t))

    def simulate_short_rate(
        self,
        horizon_years: float,
        steps_per_year: int = 12,
        n_paths: int = 1000,
        r0: float | None = None,
        seed: int | None = 42,
    ) -> tuple[np.ndarray, np.ndarray]:
        dt = 1.0 / steps_per_year
        n_steps = int(horizon_years * steps_per_year)
        times = np.linspace(0.0, horizon_years, n_steps + 1)
        rates = np.zeros((n_paths, n_steps + 1), dtype=float)
        if r0 is None:
            r0 = float(self.curve.zero_rate(1 / 12))
        rates[:, 0] = r0

        rng = np.random.default_rng(seed)
        for i in range(1, n_steps + 1):
            t = times[i - 1]
            th = self.theta(t)
            z = rng.standard_normal(n_paths)
            rates[:, i] = rates[:, i - 1] + (th - self.mean_reversion * rates[:, i - 1]) * dt + self.sigma * np.sqrt(dt) * z
        return times, rates

