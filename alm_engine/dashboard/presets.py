from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BalanceSheetConfig:
    """Retail banking-book snapshot used by ``run_engine``."""

    fixed_notional: float = 200_000_000.0
    fixed_rate: float = 0.034
    fixed_maturity_years: float = 20.0
    floating_notional: float = 80_000_000.0
    floating_spread: float = 0.012
    floating_maturity_years: float = 7.0
    nmd_notional: float = 240_000_000.0
    nmd_beta: float = 0.28
    nmd_core_ratio: float = 0.82
    nmd_behavioral_maturity_years: float = 4.5
    wholesale_funding: float = 30_000_000.0
    level1_assets: float = 45_000_000.0
    level2a_assets: float = 20_000_000.0
    level2b_assets: float = 8_000_000.0
    outflows_30d: float = 52_000_000.0
    inflows_30d: float = 27_000_000.0
    stable_funding: float = 180_000_000.0
    less_stable_funding: float = 70_000_000.0
    required_stable_assets: float = 260_000_000.0
    less_liquid_assets: float = 55_000_000.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


DEFAULT_BALANCE_SHEET = BalanceSheetConfig()

BPAURA_BALANCE_SHEET = BalanceSheetConfig(
    fixed_notional=250_000_000.0,
    fixed_rate=0.025,
    fixed_maturity_years=15.0,
    floating_notional=100_000_000.0,
    floating_spread=0.015,
    floating_maturity_years=7.0,
    nmd_notional=300_000_000.0,
    nmd_beta=0.30,
    nmd_core_ratio=0.85,
    nmd_behavioral_maturity_years=5.0,
    wholesale_funding=50_000_000.0,
    level1_assets=55_000_000.0,
    level2a_assets=25_000_000.0,
    level2b_assets=10_000_000.0,
    outflows_30d=60_000_000.0,
    inflows_30d=30_000_000.0,
    stable_funding=220_000_000.0,
    less_stable_funding=80_000_000.0,
    required_stable_assets=300_000_000.0,
    less_liquid_assets=65_000_000.0,
)

BPAURA_PRESET = {
    "tier1": 150_000_000.0,
    "cpr": 0.05,
    "hedge_notional": 75_000_000.0,
    "include_internal": True,
    "balance_sheet": BPAURA_BALANCE_SHEET,
    "label": "Scénario adapté au profil BPAURA (banque coopérative retail)",
}

DEMO_PRESET = {
    "tier1": 120_000_000.0,
    "cpr": 0.06,
    "hedge_notional": 0.0,
    "include_internal": True,
    "balance_sheet": DEFAULT_BALANCE_SHEET,
    "label": "Preset demo entretien: Tier1=120M, CPR=6%, ICAAP=ON",
}

MODEL_LIMITATIONS = {
    "NMD Behavior": "Base statique ; overlay optionnel « crise NMD / bank run » (fuite, core↓, runoff↑, beta↑, LCR)",
    "Treasury timeline": "Pas de projection temporelle de trésorerie (cash ladder) — liquidité via LCR/NSFR ponctuels uniquement",
    "Calibration": "Hull-White calibré sur historique récent uniquement",
    "Credit-Rate Correlation": "Non pris en compte",
    "Prepayment": "CPR constant (pas de sensibilité aux taux)",
    "SOT NII": "Seuil 5% Tier1 / Parallel only — sans toutes les hypothèses modelling du RTS EBA",
}
