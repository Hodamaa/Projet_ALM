from pathlib import Path

from alm_engine.engine import run_engine
from alm_engine.reporting.alco_reporting import build_risk_dashboard_table, export_alco_excel, export_alco_pdf


def test_run_engine_output_shapes():
    table, wal, metadata = run_engine()
    assert len(table) == 9
    assert wal > 0
    assert "calibration_source" in metadata
    assert "initial_curve_source" in metadata
    assert "delta_ear" in table.columns
    assert "lcr_ratio" in metadata
    assert "nsfr_ratio" in metadata
    assert "ftp_total_pnl" in metadata


def test_export_files_are_created(tmp_path: Path):
    table, _, metadata = run_engine()
    excel = export_alco_excel(tmp_path / "report.xlsx", table, metadata)
    pdf = export_alco_pdf(tmp_path / "report.pdf", table, metadata)
    assert excel.exists()
    assert pdf.exists()


def test_dashboard_table_contains_traffic_light():
    table, _, metadata = run_engine()
    kpi = build_risk_dashboard_table(table, float(metadata["tier1_capital"]))
    assert "risk_light" in kpi.columns


def test_hedge_notional_changes_nii_profile():
    base_table, _, _ = run_engine(hedge_notional=0.0)
    hedged_table, _, _ = run_engine(hedge_notional=100_000_000.0)
    assert not hedged_table["delta_nii"].equals(base_table["delta_nii"])

