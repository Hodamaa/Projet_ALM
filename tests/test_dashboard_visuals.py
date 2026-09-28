from __future__ import annotations

import plotly.graph_objects as go

from alm_engine.dashboard.charts import (
    chart_eve_impact,
    chart_nii_waterfall,
    chart_risk_heatmap,
    chart_traffic_light_summary,
    chart_yield_curve_shocks,
)
from alm_engine.dashboard.presets import BPAURA_BALANCE_SHEET, BPAURA_PRESET, MODEL_LIMITATIONS
from alm_engine.engine import run_engine
from alm_engine.reporting.alco_reporting import build_risk_dashboard_table


def test_bpaura_preset_runs():
    table, wal, metadata = run_engine(
        tier1_capital=BPAURA_PRESET["tier1"],
        cpr=BPAURA_PRESET["cpr"],
        hedge_notional=BPAURA_PRESET["hedge_notional"],
        balance_sheet=BPAURA_BALANCE_SHEET,
    )
    assert len(table) == 9
    assert wal > 0
    assert metadata["fixed_notional"] == 250_000_000.0
    assert metadata["nmd_notional"] == 300_000_000.0
    assert metadata["wholesale_funding"] == 50_000_000.0
    assert metadata["hedge_notional"] == 75_000_000.0


def test_plotly_charts_build():
    table, _, metadata = run_engine()
    tier1 = float(metadata["tier1_capital"])
    kpi = build_risk_dashboard_table(table, tier1)
    from alm_engine.dashboard.presets import DEFAULT_BALANCE_SHEET
    from alm_engine.dashboard.charts import chart_balance_sheet_composition

    figs = [
        chart_eve_impact(table, tier1),
        chart_nii_waterfall(table, hedge_notional=50_000_000.0),
        chart_yield_curve_shocks(),
        chart_risk_heatmap(table),
        chart_traffic_light_summary(kpi),
    ]
    assert all(isinstance(f, go.Figure) for f in figs)
    fig_a, fig_l, detail = chart_balance_sheet_composition(DEFAULT_BALANCE_SHEET, tier1, 0.0)
    assert isinstance(fig_a, go.Figure) and isinstance(fig_l, go.Figure)
    assert not detail.empty


def test_model_limitations_documented():
    assert "NMD Behavior" in MODEL_LIMITATIONS
    assert "Prepayment" in MODEL_LIMITATIONS
