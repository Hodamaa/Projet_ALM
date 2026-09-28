from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NSFRResult:
    asf: float
    rsf: float
    nsfr_ratio: float
    compliant: bool


def calculate_nsfr(
    stable_funding: float,
    less_stable_funding: float,
    short_term_wholesale_funding: float,
    required_stable_assets: float,
    less_liquid_assets: float,
) -> NSFRResult:
    # Simplified ASF/RSF decomposition.
    asf = 1.0 * stable_funding + 0.9 * less_stable_funding + 0.5 * short_term_wholesale_funding
    rsf = 0.5 * required_stable_assets + 0.85 * less_liquid_assets
    rsf = max(1.0, rsf)
    ratio = asf / rsf
    return NSFRResult(asf=asf, rsf=rsf, nsfr_ratio=ratio, compliant=ratio >= 1.0)

