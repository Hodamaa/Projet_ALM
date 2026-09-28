from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from alm_engine.calibration.calibrate_hw import calibrate_hw_from_ecb, calibrate_nss_from_ecb, default_nss_curve
from alm_engine.dashboard.presets import BalanceSheetConfig, DEFAULT_BALANCE_SHEET
from alm_engine.funding.ftp_calculator import calculate_ftp
from alm_engine.instruments.fixed_rate_loan import FixedRateLoan
from alm_engine.instruments.floating_rate_loan import FloatingRateLoan
from alm_engine.instruments.nmd import NonMaturityDeposit
from alm_engine.liquidity.lcr_calculator import calculate_lcr
from alm_engine.liquidity.nsfr_calculator import calculate_nsfr
from alm_engine.risk.ear_calculator import calculate_ear
from alm_engine.risk.eve_calculator import calculate_eve
from alm_engine.risk.hedging_policy import SwapOverlayPolicy, hedge_curve_impact
from alm_engine.risk.internal_scenarios import apply_internal_scenario, internal_icaap_scenarios
from alm_engine.risk.irrbb_scenarios import apply_shock, standard_irrbb_scenarios
from alm_engine.risk.nii_calculator import calculate_nii, delta_nii, is_nii_sot_outlier, scenario_table, summarize_nii_sot
from alm_engine.risk.nmd_crisis import NmdCrisisStress, apply_nmd_crisis, crisis_extra_outflows_30d, crisis_summary


def run_engine(
    tier1_capital: float = 120_000_000.0,
    cpr: float = 0.06,
    include_internal_scenarios: bool = True,
    hedge_notional: float = 0.0,
    balance_sheet: BalanceSheetConfig | None = None,
    nmd_crisis_severity: float = 0.0,
):
    bs = balance_sheet or DEFAULT_BALANCE_SHEET
    crisis = NmdCrisisStress(severity=nmd_crisis_severity)
    months = 120
    maturities = np.arange(1, months + 1, dtype=float) / 12.0
    try:
        curve, curve_source = calibrate_nss_from_ecb()
    except Exception:
        curve = default_nss_curve()
        curve_source = "Default NSS"
    base_curve = curve.zero_rate(maturities)
    hw_calib, calib_source = calibrate_hw_from_ecb()

    fixed_loan = FixedRateLoan(
        notional=bs.fixed_notional,
        annual_rate=bs.fixed_rate,
        maturity_years=bs.fixed_maturity_years,
        cpr=cpr,
    )
    floating_loan = FloatingRateLoan(
        notional=bs.floating_notional,
        spread=bs.floating_spread,
        maturity_years=bs.floating_maturity_years,
    )
    nmd = NonMaturityDeposit(
        notional=bs.nmd_notional,
        beta=bs.nmd_beta,
        core_ratio=bs.nmd_core_ratio,
        behavioral_maturity_years=bs.nmd_behavioral_maturity_years,
    )
    nmd_stressed = apply_nmd_crisis(nmd, crisis)

    fixed_cf = fixed_loan.cashflows()
    float_cf = floating_loan.cashflows(base_curve)
    asset_cfs = fixed_cf[["time", "cashflow", "interest"]].copy()
    float_sel = float_cf[["time", "cashflow", "interest"]].copy()
    asset_cfs = _concat_frames(asset_cfs, float_sel)

    base_nmd = nmd.replicated_cashflows(base_curve)
    hedge = SwapOverlayPolicy(notional=hedge_notional, pay_fixed_rate=0.022, receive_float_spread=0.0)
    ftp = calculate_ftp(asset_cfs, base_nmd.rename(columns={"interest_cost": "cashflow"}), base_curve)

    extra_outflows = crisis_extra_outflows_30d(bs.nmd_notional, crisis)
    outflows_30d = bs.outflows_30d + extra_outflows
    lcr = calculate_lcr(
        level1_assets=bs.level1_assets,
        level2a_assets=bs.level2a_assets,
        level2b_assets=bs.level2b_assets,
        outflows_30d=outflows_30d,
        inflows_30d=bs.inflows_30d,
    )
    lcr_base = calculate_lcr(
        level1_assets=bs.level1_assets,
        level2a_assets=bs.level2a_assets,
        level2b_assets=bs.level2b_assets,
        outflows_30d=bs.outflows_30d,
        inflows_30d=bs.inflows_30d,
    )
    nsfr = calculate_nsfr(
        stable_funding=bs.stable_funding,
        less_stable_funding=bs.less_stable_funding,
        short_term_wholesale_funding=bs.wholesale_funding,
        required_stable_assets=bs.required_stable_assets,
        less_liquid_assets=bs.less_liquid_assets,
    )

    rows: list[dict[str, float | str | bool]] = []
    for shock in standard_irrbb_scenarios():
        shocked_curve = apply_shock(base_curve, maturities, shock)
        rows.append(
            _compute_metrics_row(shock.name, asset_cfs, base_nmd, base_curve, shocked_curve, nmd, tier1_capital, hedge)
        )

    if include_internal_scenarios:
        for scen in internal_icaap_scenarios():
            shocked_curve = apply_internal_scenario(base_curve, maturities, scen)
            rows.append(
                _compute_metrics_row(scen.name, asset_cfs, base_nmd, base_curve, shocked_curve, nmd, tier1_capital, hedge)
            )

    if crisis.active:
        # Funding-stress curve overlay: +rate_shock_bp parallel, plus behavioral NMD flight.
        # Not a Basel SOT scenario — keep regulatory outlier flags off.
        crisis_curve = np.maximum(base_curve + crisis.rate_shock_bp / 10000.0, 0.0)
        crisis_row = _compute_metrics_row(
            crisis.scenario_name,
            asset_cfs,
            base_nmd,
            base_curve,
            crisis_curve,
            nmd_stressed,
            tier1_capital,
            hedge,
            shocked_liability_from_nmd=True,
        )
        crisis_row["outlier"] = False
        crisis_row["outlier_nii"] = False
        rows.append(crisis_row)

    metadata = {
        "run_timestamp": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tier1_capital": tier1_capital,
        "cpr": cpr,
        "hw_mean_reversion": hw_calib.mean_reversion,
        "hw_sigma": hw_calib.sigma,
        "hw_long_run_mean": hw_calib.long_run_mean,
        "calibration_source": calib_source,
        "initial_curve_source": curve_source,
        "n_scenarios": len(rows),
        "hedge_notional": hedge_notional,
        "lcr_ratio": lcr.lcr_ratio,
        "lcr_hqla": lcr.hqla,
        "lcr_net_outflows_30d": lcr.net_outflows_30d,
        "lcr_compliant": lcr.compliant,
        "lcr_ratio_unstressed": lcr_base.lcr_ratio,
        "lcr_compliant_unstressed": lcr_base.compliant,
        "nsfr_ratio": nsfr.nsfr_ratio,
        "nsfr_asf": nsfr.asf,
        "nsfr_rsf": nsfr.rsf,
        "nsfr_compliant": nsfr.compliant,
        "ftp_avg_rate": ftp.avg_ftp_rate,
        "ftp_asset_transfer_margin": ftp.asset_transfer_margin,
        "ftp_liability_transfer_margin": ftp.liability_transfer_margin,
        "ftp_total_pnl": ftp.total_ftp_pnl,
        "fixed_notional": bs.fixed_notional,
        "floating_notional": bs.floating_notional,
        "nmd_notional": bs.nmd_notional,
        "wholesale_funding": bs.wholesale_funding,
        **crisis_summary(nmd, crisis),
    }
    table = scenario_table(rows)
    nii_sot = summarize_nii_sot(table, tier1_capital)
    metadata["sot_eve_breach"] = bool(table["outlier"].any())
    metadata["sot_nii_breach"] = bool(nii_sot.breach)
    metadata["sot_nii_worst_scenario"] = nii_sot.worst_scenario
    metadata["sot_nii_worst_delta"] = nii_sot.worst_delta_nii
    metadata["sot_nii_threshold"] = nii_sot.threshold_pct
    return table, fixed_loan.wal(), metadata


def _compute_metrics_row(
    scenario_name: str,
    asset_cfs: pd.DataFrame,
    base_nmd: pd.DataFrame,
    base_curve: np.ndarray,
    shocked_curve: np.ndarray,
    nmd: NonMaturityDeposit,
    tier1_capital: float,
    hedge: SwapOverlayPolicy,
    shocked_liability_from_nmd: bool = False,
) -> dict[str, float | str | bool]:
    shocked_nmd = nmd.replicated_cashflows(shocked_curve)
    shocked_liability_cfs = (
        shocked_nmd.rename(columns={"interest_cost": "cashflow"}) if shocked_liability_from_nmd else None
    )
    eve = calculate_eve(
        asset_cfs,
        base_nmd.rename(columns={"interest_cost": "cashflow"}),
        base_curve,
        shocked_curve,
        tier1_capital,
        shocked_liability_cfs=shocked_liability_cfs,
    )
    base_val = calculate_nii(asset_cfs, base_nmd, horizon_years=1.0)
    shocked_val = calculate_nii(asset_cfs, shocked_nmd, horizon_years=1.0)
    base_hedge, shocked_hedge = hedge_curve_impact(base_curve, shocked_curve, hedge)
    hedged_base = base_val + base_hedge
    hedged_shocked = shocked_val + shocked_hedge
    base_ear = calculate_ear(asset_cfs, base_nmd, baseline_nii=base_val, horizon_years=1.0)
    shocked_ear = calculate_ear(asset_cfs, shocked_nmd, baseline_nii=base_val, horizon_years=1.0)
    d_nii = delta_nii(hedged_base, hedged_shocked)
    return {
        "scenario": scenario_name,
        "base_eve": eve.base_eve,
        "shocked_eve": eve.shocked_eve,
        "delta_eve": eve.delta_eve,
        "outlier": eve.outlier,  # SOT EVE (15% Tier 1, all applicable shocks)
        "outlier_nii": is_nii_sot_outlier(scenario_name, d_nii, tier1_capital),  # SOT NII (5%, parallel only)
        "base_nii": hedged_base,
        "shocked_nii": hedged_shocked,
        "delta_nii": d_nii,
        "base_ear": base_ear,
        "shocked_ear": shocked_ear,
        "delta_ear": shocked_ear - base_ear,
        "hedge_effect_nii": (shocked_hedge - base_hedge),
    }


def _concat_frames(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([df1, df2], axis=0, ignore_index=True).sort_values("time")
