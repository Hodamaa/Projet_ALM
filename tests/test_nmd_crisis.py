from __future__ import annotations

from alm_engine.dashboard.presets import DEFAULT_BALANCE_SHEET
from alm_engine.engine import run_engine
from alm_engine.instruments.nmd import NonMaturityDeposit
from alm_engine.risk.nmd_crisis import (
    NmdCrisisStress,
    apply_nmd_crisis,
    crisis_extra_outflows_30d,
)


def test_nmd_crisis_stress_transforms_deposit():
    nmd = NonMaturityDeposit(
        notional=240_000_000.0,
        beta=0.28,
        core_ratio=0.82,
        behavioral_maturity_years=4.5,
    )
    mild = apply_nmd_crisis(nmd, NmdCrisisStress(severity=0.35))
    severe = apply_nmd_crisis(nmd, NmdCrisisStress(severity=1.0))
    assert mild.notional < nmd.notional
    assert severe.notional < mild.notional
    assert severe.core_ratio < nmd.core_ratio
    assert severe.behavioral_maturity_years < nmd.behavioral_maturity_years
    assert severe.beta > nmd.beta
    assert crisis_extra_outflows_30d(nmd.notional, NmdCrisisStress(severity=1.0)) == 0.30 * nmd.notional


def test_run_engine_nmd_crisis_adds_scenario_and_stresses_lcr():
    base_table, _, base_meta = run_engine(nmd_crisis_severity=0.0)
    crisis_table, _, crisis_meta = run_engine(nmd_crisis_severity=1.0)

    assert len(base_table) == 9
    assert len(crisis_table) == 10
    assert any(str(s).startswith("NMD Bank Run") for s in crisis_table["scenario"])
    assert crisis_meta["nmd_crisis_active"] is True
    assert crisis_meta["nmd_flight_eur"] > 0
    assert crisis_meta["lcr_ratio"] < crisis_meta["lcr_ratio_unstressed"]
    assert abs(crisis_meta["lcr_ratio_unstressed"] - base_meta["lcr_ratio"]) < 1e-9
    # Didactic row must not pollute regulatory SOT flags
    crisis_row = crisis_table[crisis_table["scenario"].astype(str).str.startswith("NMD Bank Run")].iloc[0]
    assert bool(crisis_row["outlier"]) is False
    assert bool(crisis_row["outlier_nii"]) is False


def test_default_balance_sheet_unchanged_by_crisis_helper():
    assert DEFAULT_BALANCE_SHEET.nmd_notional == 240_000_000.0
