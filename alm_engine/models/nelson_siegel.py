from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NelsonSiegelSvenssonCurve:
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    lambda1: float
    lambda2: float

    def zero_rate(self, tau: float | np.ndarray) -> float | np.ndarray:
        tau_arr = np.maximum(np.asarray(tau, dtype=float), 1e-8)
        x1 = tau_arr / self.lambda1
        x2 = tau_arr / self.lambda2
        term1 = (1.0 - np.exp(-x1)) / x1
        term2 = term1 - np.exp(-x1)
        term3 = (1.0 - np.exp(-x2)) / x2 - np.exp(-x2)
        return self.beta0 + self.beta1 * term1 + self.beta2 * term2 + self.beta3 * term3

    def discount_factor(self, tau: float | np.ndarray) -> float | np.ndarray:
        tau_arr = np.asarray(tau, dtype=float)
        return np.exp(-self.zero_rate(tau_arr) * tau_arr)

    def forward_rate(self, tau: float, dt: float = 1e-4) -> float:
        t1 = max(1e-8, tau - dt)
        t2 = tau + dt
        return float((self.zero_rate(t2) * t2 - self.zero_rate(t1) * t1) / (t2 - t1))

