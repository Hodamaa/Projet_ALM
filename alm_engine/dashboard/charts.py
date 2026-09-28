from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from alm_engine.calibration.calibrate_hw import calibrate_nss_from_ecb, default_nss_curve
from alm_engine.risk.irrbb_scenarios import apply_shock, standard_irrbb_scenarios


def _to_meur(series: pd.Series) -> pd.Series:
    return series.astype(float) / 1_000_000.0


def chart_eve_impact(table: pd.DataFrame, tier1_capital: float) -> go.Figure:
    df = table.copy()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="EVE base",
            x=df["scenario"],
            y=_to_meur(df["base_eve"]),
            marker_color="#2563eb",
        )
    )
    fig.add_trace(
        go.Bar(
            name="EVE choc",
            x=df["scenario"],
            y=_to_meur(df["shocked_eve"]),
            marker_color="#dc2626",
        )
    )
    # Visual guide: base EVE ± 15% Tier 1 (outlier band around mean base)
    base_mean = float(_to_meur(df["base_eve"]).mean())
    band = 0.15 * tier1_capital / 1_000_000.0
    fig.add_hline(
        y=base_mean - band,
        line_dash="dash",
        line_color="#f59e0b",
        annotation_text="Seuil outlier −15% Tier 1 (vs EVE moyen)",
        annotation_position="bottom left",
    )
    fig.add_hline(
        y=base_mean + band,
        line_dash="dash",
        line_color="#f59e0b",
        annotation_text="Seuil outlier +15% Tier 1",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Impact EVE par scénario",
        barmode="group",
        xaxis_title="Scénario",
        yaxis_title="EVE (M€)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60, b=40),
        height=420,
    )
    return fig


def chart_nii_waterfall(table: pd.DataFrame, hedge_notional: float = 0.0) -> go.Figure:
    df = table.copy()
    deltas = _to_meur(df["delta_nii"]).tolist()
    scenarios = df["scenario"].tolist()
    worst_idx = int(np.argmax(np.abs(deltas)))

    measure = ["relative"] * len(deltas)
    texts = [f"{v:+.2f}" for v in deltas]
    colors = ["#dc2626" if i == worst_idx else ("#16a34a" if v >= 0 else "#ea580c") for i, v in enumerate(deltas)]

    fig = go.Figure(
        go.Waterfall(
            name="ΔNII",
            orientation="v",
            measure=measure,
            x=scenarios,
            y=deltas,
            text=texts,
            textposition="outside",
            connector={"line": {"color": "#94a3b8"}},
            increasing={"marker": {"color": "#16a34a"}},
            decreasing={"marker": {"color": "#ea580c"}},
            # per-bar colors via customdata highlight of worst case
            customdata=colors,
        )
    )
    # Re-color worst bar via overlay annotation
    fig.add_annotation(
        x=scenarios[worst_idx],
        y=deltas[worst_idx],
        text="Pire cas",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(color="#dc2626", size=12),
    )
    title = "Sensibilité NII (waterfall ΔNII, M€)"
    if hedge_notional > 0:
        hedge_effect = float(_to_meur(df["hedge_effect_nii"]).sum())
        title += f" — hedge {hedge_notional / 1e6:.0f} M€ (effet cumulé {hedge_effect:+.2f} M€)"
        fig.add_trace(
            go.Scatter(
                x=scenarios,
                y=_to_meur(df["hedge_effect_nii"]),
                mode="lines+markers",
                name="Effet hedge NII",
                line=dict(color="#7c3aed", dash="dot"),
            )
        )
    fig.update_layout(
        title=title,
        yaxis_title="ΔNII (M€)",
        xaxis_title="Scénario",
        showlegend=True,
        height=420,
        margin=dict(t=60, b=40),
    )
    return fig


def chart_yield_curve_shocks() -> go.Figure:
    tenors = np.array([1 / 12, 3 / 12, 6 / 12, 1.0, 2.0, 5.0, 10.0, 20.0])
    labels = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "20Y"]
    try:
        curve, _ = calibrate_nss_from_ecb()
    except Exception:
        curve = default_nss_curve()
    base = np.asarray(curve.zero_rate(tenors), dtype=float)
    shocks = {s.name: s for s in standard_irrbb_scenarios()}
    up = apply_shock(base, tenors, shocks["Parallel Up"])
    down = apply_shock(base, tenors, shocks["Parallel Down"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=base * 100, mode="lines+markers", name="Courbe NSS", line=dict(color="#0f172a", width=3)))
    fig.add_trace(go.Scatter(x=labels, y=up * 100, mode="lines+markers", name="Parallel Up", line=dict(color="#dc2626", dash="dash")))
    fig.add_trace(go.Scatter(x=labels, y=down * 100, mode="lines+markers", name="Parallel Down", line=dict(color="#2563eb", dash="dash")))
    fig.update_layout(
        title="Courbe des taux NSS — avant / après chocs parallèles",
        xaxis_title="Maturité",
        yaxis_title="Taux zéro (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400,
        margin=dict(t=60, b=40),
    )
    return fig


def chart_risk_heatmap(table: pd.DataFrame) -> go.Figure:
    metrics = ["delta_eve", "delta_nii", "delta_ear"]
    labels = ["ΔEVE", "ΔNII", "ΔEAR"]
    # Normalize each metric by abs max so red = high risk magnitude
    z = []
    text = []
    for col in metrics:
        vals = table[col].astype(float).to_numpy()
        scale = max(float(np.max(np.abs(vals))), 1.0)
        z.append(np.abs(vals) / scale)
        text.append([f"{v / 1e6:+.2f} M€" for v in vals])
    z_arr = np.array(z).T  # scenarios × metrics
    text_arr = np.array(text).T

    fig = go.Figure(
        data=go.Heatmap(
            z=z_arr,
            x=labels,
            y=table["scenario"].tolist(),
            text=text_arr,
            texttemplate="%{text}",
            colorscale=[
                [0.0, "#16a34a"],
                [0.5, "#facc15"],
                [1.0, "#dc2626"],
            ],
            colorbar=dict(title="Risque relatif"),
            hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Heatmap de risque (intensité |Δ| normalisée)",
        height=max(360, 40 * len(table) + 120),
        margin=dict(t=60, b=40),
    )
    return fig


def chart_traffic_light_summary(kpi: pd.DataFrame) -> go.Figure:
    counts = kpi["risk_light"].value_counts()
    order = ["GREEN", "AMBER", "RED"]
    colors = {"GREEN": "#16a34a", "AMBER": "#f59e0b", "RED": "#dc2626"}
    values = [int(counts.get(k, 0)) for k in order]
    fig = go.Figure(
        go.Bar(
            x=["GREEN (<10%)", "AMBER (10–15% interne)", "RED (≥15% SOT EVE)"],
            y=values,
            marker_color=[colors[k] for k in order],
            text=values,
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Feux internes ALCO (AMBER = early-warning, non réglementaire)",
        yaxis_title="Nombre de scénarios",
        height=320,
        margin=dict(t=50, b=30),
    )
    return fig


def chart_balance_sheet_composition(balance_sheet, tier1: float, hedge_notional: float = 0.0) -> tuple[go.Figure, go.Figure, pd.DataFrame]:
    """Build asset/liability pie charts and a detail table from BalanceSheetConfig."""
    assets = {
        "Crédits taux fixe": float(balance_sheet.fixed_notional),
        "Crédits taux variable": float(balance_sheet.floating_notional),
        "HQLA Level 1": float(balance_sheet.level1_assets),
        "HQLA Level 2A": float(balance_sheet.level2a_assets),
        "HQLA Level 2B": float(balance_sheet.level2b_assets),
    }
    liabilities = {
        "Dépôts NMD": float(balance_sheet.nmd_notional),
        "Wholesale funding": float(balance_sheet.wholesale_funding),
        "Tier 1 (fonds propres)": float(tier1),
    }
    if hedge_notional > 0:
        liabilities["Hedge overlay (info)"] = float(hedge_notional)

    fig_a = go.Figure(
        go.Pie(
            labels=list(assets.keys()),
            values=list(assets.values()),
            hole=0.35,
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,.0f} €<extra></extra>",
        )
    )
    fig_a.update_layout(title="Composition Actif", height=380, margin=dict(t=50, b=20))

    fig_l = go.Figure(
        go.Pie(
            labels=list(liabilities.keys()),
            values=list(liabilities.values()),
            hole=0.35,
            textinfo="label+percent",
            hovertemplate="%{label}<br>%{value:,.0f} €<extra></extra>",
        )
    )
    fig_l.update_layout(title="Composition Passif / Capitaux", height=380, margin=dict(t=50, b=20))

    rows = []
    for name, value in assets.items():
        rows.append({"Côté": "Actif", "Poste": name, "Montant (M€)": value / 1e6})
    for name, value in liabilities.items():
        rows.append({"Côté": "Passif / FP", "Poste": name, "Montant (M€)": value / 1e6})
    rows.append(
        {
            "Côté": "Paramètres",
            "Poste": f"Taux fixe {100 * balance_sheet.fixed_rate:.2f}% / maturité {balance_sheet.fixed_maturity_years:.0f} ans",
            "Montant (M€)": balance_sheet.fixed_notional / 1e6,
        }
    )
    rows.append(
        {
            "Côté": "Paramètres",
            "Poste": f"Flottant spread {100 * balance_sheet.floating_spread:.2f}% / maturité {balance_sheet.floating_maturity_years:.0f} ans",
            "Montant (M€)": balance_sheet.floating_notional / 1e6,
        }
    )
    rows.append(
        {
            "Côté": "Paramètres",
            "Poste": f"NMD β={balance_sheet.nmd_beta:.2f}, core={balance_sheet.nmd_core_ratio:.0%}, mat. comportementale={balance_sheet.nmd_behavioral_maturity_years:.1f} ans",
            "Montant (M€)": balance_sheet.nmd_notional / 1e6,
        }
    )
    detail = pd.DataFrame(rows)
    return fig_a, fig_l, detail
