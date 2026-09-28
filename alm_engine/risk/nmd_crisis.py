from __future__ import annotations

from dataclasses import dataclass

from alm_engine.instruments.nmd import NonMaturityDeposit


@dataclass(frozen=True)
class NmdCrisisStress:
    """Didactic bank-run / deposit-flight overlay on NMD + LCR.

    ``severity`` in [0, 1]:
    - 0.0 → no stress
    - ~0.35 mild / ~0.65 moderate / 1.0 severe
    """

    severity: float = 0.0
    max_flight_fraction: float = 0.30
    max_core_haircut: float = 0.45
    max_maturity_haircut: float = 0.70
    max_beta_uplift: float = 0.40
    rate_shock_bp: float = 100.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "severity", float(min(1.0, max(0.0, self.severity))))

    @property
    def active(self) -> bool:
        return self.severity > 1e-9

    @property
    def label(self) -> str:
        if not self.active:
            return "Off"
        if self.severity < 0.4:
            return "Mild"
        if self.severity < 0.75:
            return "Moderate"
        return "Severe"

    @property
    def scenario_name(self) -> str:
        return f"NMD Bank Run ({self.label})"

    @property
    def flight_fraction(self) -> float:
        return self.max_flight_fraction * self.severity


def apply_nmd_crisis(nmd: NonMaturityDeposit, stress: NmdCrisisStress) -> NonMaturityDeposit:
    """Return a stressed NMD: deposit flight, weaker core, faster runoff, higher beta."""
    if not stress.active:
        return nmd
    s = stress.severity
    fled = nmd.notional * stress.flight_fraction
    remaining = max(0.0, nmd.notional - fled)
    core_ratio = max(0.05, nmd.core_ratio * (1.0 - stress.max_core_haircut * s))
    maturity = max(0.5, nmd.behavioral_maturity_years * (1.0 - stress.max_maturity_haircut * s))
    beta = min(1.0, nmd.beta + stress.max_beta_uplift * s)
    return NonMaturityDeposit(
        notional=remaining,
        beta=beta,
        core_ratio=core_ratio,
        behavioral_maturity_years=maturity,
        admin_margin=nmd.admin_margin,
        payments_per_year=nmd.payments_per_year,
    )


def crisis_extra_outflows_30d(nmd_notional: float, stress: NmdCrisisStress) -> float:
    """Deposit flight assumed to hit the 30-day LCR outflow window."""
    if not stress.active:
        return 0.0
    return float(nmd_notional) * stress.flight_fraction


def crisis_summary(nmd: NonMaturityDeposit, stress: NmdCrisisStress) -> dict[str, float | str | bool]:
    stressed = apply_nmd_crisis(nmd, stress)
    flight = crisis_extra_outflows_30d(nmd.notional, stress)
    return {
        "nmd_crisis_active": stress.active,
        "nmd_crisis_severity": stress.severity,
        "nmd_crisis_label": stress.label,
        "nmd_crisis_scenario": stress.scenario_name if stress.active else "",
        "nmd_flight_eur": flight,
        "nmd_notional_stressed": stressed.notional,
        "nmd_core_ratio_stressed": stressed.core_ratio,
        "nmd_beta_stressed": stressed.beta,
        "nmd_behavioral_maturity_stressed": stressed.behavioral_maturity_years,
        "nmd_crisis_rate_shock_bp": stress.rate_shock_bp if stress.active else 0.0,
    }
