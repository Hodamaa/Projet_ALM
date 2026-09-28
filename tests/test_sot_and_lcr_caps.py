from alm_engine.risk.nii_calculator import (
    is_nii_sot_outlier,
    summarize_nii_sot,
)
from alm_engine.liquidity.lcr_calculator import calculate_lcr
from alm_engine.engine import run_engine
from alm_engine.reporting.alco_reporting import build_management_commentary, build_risk_dashboard_table
import pandas as pd


def test_nii_sot_only_on_parallel():
    assert is_nii_sot_outlier("Parallel Down", -10_000_000, 100_000_000, threshold=0.05) is True
    assert is_nii_sot_outlier("Parallel Up", -10_000_000, 100_000_000, threshold=0.05) is True
    assert is_nii_sot_outlier("Steepener", -10_000_000, 100_000_000, threshold=0.05) is False
    # Increase in NII is not a "large decline"
    assert is_nii_sot_outlier("Parallel Down", +1_000_000, 100_000_000, threshold=0.05) is False


def test_nii_sot_threshold_5pct():
    # decline of 4% Tier1 → OK ; 6% → breach
    assert is_nii_sot_outlier("Parallel Down", -4_000_000, 100_000_000) is False
    assert is_nii_sot_outlier("Parallel Down", -6_000_000, 100_000_000) is True


def test_engine_exposes_dual_sot():
    table, _, metadata = run_engine()
    assert "outlier_nii" in table.columns
    assert "sot_eve_breach" in metadata
    assert "sot_nii_breach" in metadata
    assert "sot_nii_threshold" in metadata
    assert float(metadata["sot_nii_threshold"]) == 0.05
    # NII outlier flags only on parallel rows when True
    non_parallel = table[~table["scenario"].isin(["Parallel Up", "Parallel Down"])]
    assert not bool(non_parallel["outlier_nii"].any())


def test_amber_documented_as_internal():
    table, _, metadata = run_engine()
    lines = build_management_commentary(table, float(metadata["tier1_capital"]))
    joined = " ".join(lines)
    assert "early-warning" in joined or "interne" in joined
    assert "SOT NII" in joined
    assert "PV(actifs)" in joined


def test_lcr_level2b_15pct_cap():
    # Huge L2B should be capped by the 15% rule vs unconstrained haircut sum
    capped = calculate_lcr(
        level1_assets=100_000_000,
        level2a_assets=10_000_000,
        level2b_assets=200_000_000,  # would be 100M after 50% haircut without cap
        outflows_30d=50_000_000,
        inflows_30d=10_000_000,
    )
    # Max L2B contribution ≈ (15/85)*(L1+L2A) = (15/85)*(100M+8.5M) ≈ 19.15M
    # Max L2 total = (2/3)*L1 ≈ 66.67M
    assert capped.hqla < 100_000_000 + 0.85 * 10_000_000 + 0.50 * 200_000_000
    assert capped.hqla <= 100_000_000 + (2 / 3) * 100_000_000 + 1.0
