from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

# Streamlit runs this file with cwd/script-dir on sys.path, not the repo root.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

# Force-reload market-data + engine stack: Streamlit often hot-reloads only this
# script and keeps stale alm_engine.* modules (old ECB URL → perpetual synthetic fallback).
import alm_engine.data.ecb_data as _ecb_mod
import alm_engine.calibration.calibrate_hw as _calib_mod
import alm_engine.risk.eve_calculator as _eve_mod
import alm_engine.risk.nmd_crisis as _nmd_crisis_mod
import alm_engine.engine as _engine_mod
import alm_engine.dashboard.charts as _charts_mod

importlib.reload(_ecb_mod)
importlib.reload(_calib_mod)
importlib.reload(_eve_mod)
importlib.reload(_nmd_crisis_mod)
importlib.reload(_engine_mod)
importlib.reload(_charts_mod)
run_engine = _engine_mod.run_engine
chart_balance_sheet_composition = _charts_mod.chart_balance_sheet_composition
chart_eve_impact = _charts_mod.chart_eve_impact
chart_nii_waterfall = _charts_mod.chart_nii_waterfall
chart_risk_heatmap = _charts_mod.chart_risk_heatmap
chart_traffic_light_summary = _charts_mod.chart_traffic_light_summary
chart_yield_curve_shocks = _charts_mod.chart_yield_curve_shocks

from alm_engine.dashboard.presets import (
    BalanceSheetConfig,
    DEFAULT_BALANCE_SHEET,
    DEMO_PRESET,
    MODEL_LIMITATIONS,
)

# Widget display units: M€ for notionnels, % for taux/beta/core, years otherwise.
_BS_MEUR_FIELDS = frozenset(
    {
        "fixed_notional",
        "floating_notional",
        "nmd_notional",
        "wholesale_funding",
        "level1_assets",
        "level2a_assets",
        "level2b_assets",
        "outflows_30d",
        "inflows_30d",
        "stable_funding",
        "less_stable_funding",
        "required_stable_assets",
        "less_liquid_assets",
    }
)
_BS_PCT_FIELDS = frozenset({"fixed_rate", "floating_spread", "nmd_beta", "nmd_core_ratio"})
from alm_engine.dashboard.run_history import append_run_history, load_run_history
from alm_engine.reporting.alco_reporting import (
    build_management_commentary,
    build_risk_dashboard_table,
    export_alco_excel,
    export_alco_pdf,
)
from alm_engine.risk.hedge_optimizer import optimize_hedge_notional


def _sync_bs_widgets_from_config(bs: BalanceSheetConfig) -> None:
    """Push BalanceSheetConfig into Streamlit widget keys (M€ / %)."""
    for field, val in bs.to_dict().items():
        key = f"bs_{field}"
        if field in _BS_MEUR_FIELDS:
            st.session_state[key] = float(val) / 1e6
        elif field in _BS_PCT_FIELDS:
            st.session_state[key] = float(val) * 100.0
        else:
            st.session_state[key] = float(val)


def _ensure_bs_widgets() -> None:
    if "bs_fixed_notional" not in st.session_state:
        _sync_bs_widgets_from_config(
            st.session_state.get("balance_sheet", DEFAULT_BALANCE_SHEET)
        )


def _balance_sheet_from_widgets() -> BalanceSheetConfig:
    """Rebuild frozen config from interactive bilan widgets."""
    kwargs: dict[str, float] = {}
    for field in BalanceSheetConfig.__dataclass_fields__:
        raw = float(st.session_state[f"bs_{field}"])
        if field in _BS_MEUR_FIELDS:
            kwargs[field] = raw * 1e6
        elif field in _BS_PCT_FIELDS:
            kwargs[field] = raw / 100.0
        else:
            kwargs[field] = raw
    return BalanceSheetConfig(**kwargs)


def _reset_balance_sheet() -> None:
    st.session_state["balance_sheet"] = DEFAULT_BALANCE_SHEET
    _sync_bs_widgets_from_config(DEFAULT_BALANCE_SHEET)
    st.session_state["preset"] = "default"
    st.session_state["preset_label"] = "Bilan réinitialisé (défaut)"


def _init_state() -> None:
    defaults = {
        "preset": "default",
        "presentation_mode": False,
        "pres_step": 0,
        "pres_start": None,
        "tier1": 120_000_000.0,
        "cpr": 0.06,
        "hedge_notional": 0.0,
        "include_internal": True,
        "nmd_crisis_on": False,
        "nmd_crisis_severity_pct": 65.0,
        "balance_sheet": DEFAULT_BALANCE_SHEET,
        "preset_label": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    _ensure_bs_widgets()


def _lcr_color(ratio: float) -> tuple[str, str]:
    """Return (label, hex) for LCR traffic light (ratio is e.g. 1.2 = 120%)."""
    pct = ratio * 100.0
    if pct > 100:
        return "OK (>100%)", "#16a34a"
    if pct >= 90:
        return "Vigilance (90–100%)", "#f59e0b"
    return "Breach (<90%)", "#dc2626"


def _alco_recommendation(table, kpi, metadata, tier1: float) -> str:
    outliers_eve = table[table["outlier"]]
    outliers_nii = table[table["outlier_nii"]] if "outlier_nii" in table.columns else table.iloc[0:0]
    n_red = int((kpi["risk_light"] == "RED").sum())
    n_amber = int((kpi["risk_light"] == "AMBER").sum())
    # Prefer regulatory / rate scenarios for hedge sizing (exclude didactic bank-run row).
    rate_kpi = kpi[~kpi["scenario"].astype(str).str.startswith("NMD Bank Run")]
    if rate_kpi.empty:
        rate_kpi = kpi
    worst = rate_kpi.loc[rate_kpi["delta_eve"].abs().idxmax()]
    hedge = float(metadata.get("hedge_notional", 0.0))
    sot_nii = bool(metadata.get("sot_nii_breach", False))
    crisis_on = bool(metadata.get("nmd_crisis_active", False))
    lcr_ok = bool(metadata.get("lcr_compliant", True))
    flight = float(metadata.get("nmd_flight_eur", 0.0))

    crisis_bits: list[str] = []
    if crisis_on:
        crisis_bits.append(
            f"Crise NMD {metadata.get('nmd_crisis_label', '')} "
            f"(fuite ~{flight / 1e6:.0f} M€, LCR {float(metadata.get('lcr_ratio', 0.0)):.2f}x)"
        )
        if not lcr_ok:
            crisis_bits.append("LCR breach sous bank run — activer plan de liquidité / HQLA")

    if outliers_eve.empty and not sot_nii and n_red == 0 and n_amber == 0 and lcr_ok:
        base = "Position conforme — SOT EVE et SOT NII OK, aucun early-warning interne."
        return base if not crisis_bits else base + " | " + " ; ".join(crisis_bits)
    if outliers_eve.empty and not sot_nii and (n_red > 0 or n_amber > 0) and lcr_ok and not crisis_on:
        return (
            f"Vigilance ALCO (limite interne) — {n_amber} AMBER / {n_red} RED sur |ΔEVE|/Tier1 ; "
            "pas de breach SOT réglementaire EVE/NII."
        )
    parts = []
    if not outliers_eve.empty:
        suggested = max(0.0, abs(float(worst["delta_eve"])) - 0.15 * tier1)
        parts.append(
            f"SOT EVE breach ({worst['scenario']}, |ΔEVE|={abs(float(worst['delta_eve'])) / 1e6:.1f} M€)"
            + (f" — renforcer hedge ~{suggested / 1e6:.0f} M€" if hedge <= 0 else f" malgré hedge {hedge / 1e6:.0f} M€")
        )
    if sot_nii or not outliers_nii.empty:
        scen = metadata.get("sot_nii_worst_scenario", "Parallel")
        d = float(metadata.get("sot_nii_worst_delta", 0.0))
        parts.append(f"SOT NII breach ({scen}, ΔNII={d / 1e6:+.2f} M€ vs 5% Tier1)")
    parts.extend(crisis_bits)
    if not parts:
        return (
            f"Vigilance ALCO (limite interne) — {n_amber} AMBER / {n_red} RED sur |ΔEVE|/Tier1 ; "
            "pas de breach SOT réglementaire EVE/NII."
        )
    return " | ".join(parts) + " — revue ALCO / supervision."


def _render_kpi_card(title: str, value: str, detail: str, color: str) -> None:
    st.markdown(
        f"""
        <div style="
            border-left: 6px solid {color};
            background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
            border-radius: 10px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.5rem;
            min-height: 110px;
        ">
            <div style="font-size: 0.85rem; color: #64748b; font-weight: 600;">{title}</div>
            <div style="font-size: 1.55rem; font-weight: 700; color: #0f172a; margin: 0.25rem 0;">{value}</div>
            <div style="font-size: 0.9rem; color: #334155;">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_synthese_tab(table, kpi, metadata, tier1: float) -> None:
    worst_idx = kpi["delta_eve"].abs().idxmax()
    worst = kpi.loc[worst_idx]
    lcr = float(metadata["lcr_ratio"])
    lcr_label, lcr_color = _lcr_color(lcr)
    n_outliers_eve = int(table["outlier"].sum())
    sot_eve_ok = n_outliers_eve == 0
    sot_nii_ok = not bool(metadata.get("sot_nii_breach", False))
    n_red = int((kpi["risk_light"] == "RED").sum())
    n_amber = int((kpi["risk_light"] == "AMBER").sum())
    n_green = int((kpi["risk_light"] == "GREEN").sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_kpi_card(
            "Pire ΔEVE",
            f"{float(worst['delta_eve']) / 1e6:+.1f} M€",
            f"{worst['scenario']} · EVE = PV(A)−PV(P)",
            "#dc2626" if bool(worst["outlier"]) else "#f59e0b",
        )
    with c2:
        _render_kpi_card(
            "SOT EVE (15% Tier 1)",
            "PASS" if sot_eve_ok else "FAIL",
            "Réglementaire · 6 chocs",
            "#16a34a" if sot_eve_ok else "#dc2626",
        )
    with c3:
        nii_detail = metadata.get("sot_nii_worst_scenario", "Parallel Up/Down")
        if not sot_nii_ok:
            nii_detail = f"{nii_detail} · ΔNII={float(metadata.get('sot_nii_worst_delta', 0.0)) / 1e6:+.2f} M€"
        _render_kpi_card(
            "SOT NII (5% Tier 1)",
            "PASS" if sot_nii_ok else "FAIL",
            f"Supervision · {nii_detail}",
            "#16a34a" if sot_nii_ok else "#dc2626",
        )
    with c4:
        lcr_detail = lcr_label
        if bool(metadata.get("nmd_crisis_active", False)):
            lcr_detail = (
                f"{lcr_label} · crise NMD {metadata.get('nmd_crisis_label')} "
                f"(base {float(metadata.get('lcr_ratio_unstressed', lcr)):.2f}x)"
            )
        _render_kpi_card(
            "LCR",
            f"{lcr:.2f}x ({lcr * 100:.0f}%)",
            lcr_detail,
            lcr_color,
        )

    if bool(metadata.get("nmd_crisis_active", False)):
        st.warning(
            f"**{metadata.get('nmd_crisis_scenario')}** — "
            f"fuite dépôts ~{float(metadata.get('nmd_flight_eur', 0.0)) / 1e6:.0f} M€ · "
            f"NMD restant {float(metadata.get('nmd_notional_stressed', 0.0)) / 1e6:.0f} M€ · "
            f"core {100 * float(metadata.get('nmd_core_ratio_stressed', 0.0)):.0f}% · "
            f"β {100 * float(metadata.get('nmd_beta_stressed', 0.0)):.0f}% · "
            f"mat. comportementale {float(metadata.get('nmd_behavioral_maturity_stressed', 0.0)):.1f} ans · "
            f"choc taux +{float(metadata.get('nmd_crisis_rate_shock_bp', 0.0)):.0f} bp"
        )

    st.markdown("#### Feux tricolores (early-warning **interne** ALCO)")
    st.caption(
        "Seul le seuil **15%** (rouge) correspond au SOT EVE réglementaire. "
        "AMBER 10–15% = limite interne de vigilance, **pas** un seuil EBA/Bâle."
    )
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("🟢 GREEN (<10%)", n_green)
    t2.metric("🟠 AMBER (10–15% interne)", n_amber)
    t3.metric("🔴 RED (≥15% = SOT EVE)", n_red)
    t4.metric("NSFR", f"{float(metadata['nsfr_ratio']):.2f}x")
    st.plotly_chart(chart_traffic_light_summary(kpi), use_container_width=True)

    reco = _alco_recommendation(table, kpi, metadata, tier1)
    # Solid high-contrast box: light text on dark fill stays readable in présentation / dark theme.
    lcr_ok = bool(metadata.get("lcr_compliant", True))
    if sot_eve_ok and sot_nii_ok and n_red == 0 and lcr_ok:
        box_bg, box_border, label_color, body_color = (
            "#14532d",
            "#4ade80",
            "#bbf7d0",
            "#f0fdf4",
        )
    else:
        box_bg, box_border, label_color, body_color = (
            "#7f1d1d",
            "#facc15",
            "#fef08a",
            "#fffbeb",
        )
    st.markdown(
        f"""
        <div style="
            background: {box_bg};
            border: 2px solid {box_border};
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-top: 0.5rem;
        ">
            <strong style="color:{label_color}; font-size:1.05rem;">Recommandation ALCO — </strong>
            <span style="color:{body_color}; font-size:1.05rem; font-weight:600;">{reco}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_charts_block(table, tier1: float, hedge_notional: float, presentation: bool) -> None:
    charts = [
        (
            "Impact EVE par scénario",
            "Compare EVE de base vs EVE après choc. La bande ambre ≈ seuil outlier 15% Tier 1.",
            chart_eve_impact(table, tier1),
        ),
        (
            "Sensibilité NII",
            "Waterfall des ΔNII. Le pire cas est annoté ; l'effet hedge apparaît si notionnel > 0.",
            chart_nii_waterfall(table, hedge_notional),
        ),
        (
            "Courbe des taux NSS",
            "Courbe zéro calibrée + overlays Parallel Up / Down (maturités retail classiques).",
            chart_yield_curve_shocks(),
        ),
        (
            "Heatmap de risque",
            "Intensité normalisée de |ΔEVE|, |ΔNII|, |ΔEAR| — rouge = risque relatif élevé.",
            chart_risk_heatmap(table),
        ),
    ]

    if presentation:
        step = int(st.session_state["pres_step"]) % len(charts)
        st.caption(f"Étape {step + 1} / {len(charts)}")
        nav1, nav2, nav3 = st.columns([1, 1, 2])
        if nav1.button("◀ Précédent", key="pres_prev"):
            st.session_state["pres_step"] = (step - 1) % len(charts)
            st.rerun()
        if nav2.button("Suivant ▶", key="pres_next"):
            st.session_state["pres_step"] = (step + 1) % len(charts)
            st.rerun()
        title, explain, fig = charts[step]
        st.subheader(title)
        st.info(explain)
        st.plotly_chart(fig, use_container_width=True)
    else:
        for title, explain, fig in charts:
            with st.expander(title, expanded=True):
                st.caption(explain)
                st.plotly_chart(fig, use_container_width=True)


def render_presentation_timer() -> None:
    if st.session_state["pres_start"] is None:
        st.session_state["pres_start"] = time.time()
    elapsed = time.time() - float(st.session_state["pres_start"])
    remaining = max(0.0, 120.0 - elapsed)
    mins, secs = divmod(int(remaining), 60)
    progress = min(1.0, elapsed / 120.0)
    st.progress(progress, text=f"⏱ Mode présentation — temps restant {mins}:{secs:02d} / 2:00")
    if remaining <= 0:
        st.warning("Les 2 minutes sont écoulées — conclure la démo.")


def render_limitations() -> None:
    with st.expander("Limites du modèle", expanded=False):
        st.caption("Transparence modèle — points à assumer en entretien.")
        for name, detail in MODEL_LIMITATIONS.items():
            st.markdown(f"- **{name}** : {detail}")


def render_bilan_tab(balance_sheet, metadata: dict, tier1: float, cpr: float, hedge_notional: float) -> None:
    st.subheader("Composition actif / passif")
    st.caption(
        "Ces montants alimentent directement EVE, NII, LCR/NSFR. "
        f"Source courbe: {metadata.get('initial_curve_source')} · "
        f"Calibration HW: {metadata.get('calibration_source')}"
    )

    with st.expander("Ajuster le bilan (interactif)", expanded=True):
        st.caption(
            "Modifiez les postes puis laissez le moteur recalculer EVE / NII / LCR / NSFR. "
            "Unités : M€ pour les notionnels, % pour taux / beta / core."
        )
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("**Actif — crédits**")
            st.number_input("Crédits taux fixe (M€)", min_value=0.0, step=5.0, key="bs_fixed_notional")
            st.number_input("Taux fixe (%)", min_value=0.0, max_value=15.0, step=0.05, key="bs_fixed_rate")
            st.number_input(
                "Maturité fixe (années)",
                min_value=1.0,
                max_value=40.0,
                step=1.0,
                key="bs_fixed_maturity_years",
            )
            st.number_input("Crédits flottants (M€)", min_value=0.0, step=5.0, key="bs_floating_notional")
            st.number_input(
                "Spread flottant (%)",
                min_value=0.0,
                max_value=10.0,
                step=0.05,
                key="bs_floating_spread",
            )
            st.number_input(
                "Maturité flottant (années)",
                min_value=1.0,
                max_value=30.0,
                step=1.0,
                key="bs_floating_maturity_years",
            )
        with a2:
            st.markdown("**Passif — NMD & wholesale**")
            st.number_input("Dépôts NMD (M€)", min_value=0.0, step=5.0, key="bs_nmd_notional")
            st.slider("Beta NMD (%)", min_value=0.0, max_value=100.0, step=1.0, key="bs_nmd_beta")
            st.slider("Core ratio NMD (%)", min_value=0.0, max_value=100.0, step=1.0, key="bs_nmd_core_ratio")
            st.number_input(
                "Maturité comportementale NMD (années)",
                min_value=0.5,
                max_value=15.0,
                step=0.5,
                key="bs_nmd_behavioral_maturity_years",
            )
            st.number_input("Wholesale funding (M€)", min_value=0.0, step=5.0, key="bs_wholesale_funding")

        st.markdown("**Liquidité — HQLA & flux 30j (LCR)**")
        l1, l2, l3, l4, l5 = st.columns(5)
        l1.number_input("HQLA L1 (M€)", min_value=0.0, step=1.0, key="bs_level1_assets")
        l2.number_input("HQLA L2A (M€)", min_value=0.0, step=1.0, key="bs_level2a_assets")
        l3.number_input("HQLA L2B (M€)", min_value=0.0, step=1.0, key="bs_level2b_assets")
        l4.number_input("Outflows 30j (M€)", min_value=0.0, step=1.0, key="bs_outflows_30d")
        l5.number_input("Inflows 30j (M€)", min_value=0.0, step=1.0, key="bs_inflows_30d")

        st.markdown("**Funding — NSFR**")
        n1, n2, n3, n4 = st.columns(4)
        n1.number_input("Stable funding (M€)", min_value=0.0, step=5.0, key="bs_stable_funding")
        n2.number_input("Less stable funding (M€)", min_value=0.0, step=5.0, key="bs_less_stable_funding")
        n3.number_input("Required stable assets (M€)", min_value=0.0, step=5.0, key="bs_required_stable_assets")
        n4.number_input("Less liquid assets (M€)", min_value=0.0, step=5.0, key="bs_less_liquid_assets")

        st.button("Réinitialiser le bilan", use_container_width=True, on_click=_reset_balance_sheet)

    fig_a, fig_l, detail = chart_balance_sheet_composition(balance_sheet, tier1, hedge_notional)
    c1, c2 = st.columns(2)
    c1.plotly_chart(fig_a, use_container_width=True)
    c2.plotly_chart(fig_l, use_container_width=True)

    total_assets = (
        balance_sheet.fixed_notional
        + balance_sheet.floating_notional
        + balance_sheet.level1_assets
        + balance_sheet.level2a_assets
        + balance_sheet.level2b_assets
    )
    total_funding = balance_sheet.nmd_notional + balance_sheet.wholesale_funding + tier1
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total actif (simplifié)", f"{total_assets / 1e6:.0f} M€")
    m2.metric("Total passif + FP", f"{total_funding / 1e6:.0f} M€")
    m3.metric("Gap notionnel (A − P−FP)", f"{(total_assets - total_funding) / 1e6:+.0f} M€")
    m4.metric("CPR / Hedge", f"{100 * cpr:.1f}% / {hedge_notional / 1e6:.0f} M€")

    st.subheader("Détail des postes (d’où viennent les valeurs)")
    st.dataframe(detail, use_container_width=True, hide_index=True)
    with st.expander("Lien avec les métriques"):
        st.markdown(
            """
- **Crédits fixe + flottant** → cashflows actifs → **EVE** (PV) et **NII** (intérêts 12 mois)
- **NMD** → coût des dépôts (beta × taux) → passif EVE / charge NII
- **HQLA L1/L2** + flux 30j → **LCR**
- **Stable / less stable / wholesale + RSF** → **NSFR**
- **Tier 1** → dénominateur du test outlier (|ΔEVE| ≥ 15% Tier 1)
- **Hedge notionnel** → overlay swap sur le NII (pas un actif de bilan comptable ici)
            """
        )


def _apply_demo_preset() -> None:
    p = DEMO_PRESET
    st.session_state["preset"] = "demo"
    st.session_state["tier1"] = p["tier1"]
    st.session_state["cpr_pct"] = p["cpr"] * 100.0
    st.session_state["hedge_notional"] = p["hedge_notional"]
    st.session_state["include_internal"] = p["include_internal"]
    st.session_state["balance_sheet"] = p["balance_sheet"]
    _sync_bs_widgets_from_config(p["balance_sheet"])
    st.session_state["preset_label"] = p["label"]
    st.session_state["presentation_mode"] = True
    st.session_state["pres_step"] = 0
    st.session_state["pres_start"] = time.time()


def _optimize_hedge_callback() -> None:
    _ensure_bs_widgets()
    bs = _balance_sheet_from_widgets()
    st.session_state["balance_sheet"] = bs
    crisis_on = bool(st.session_state.get("nmd_crisis_on", False))
    crisis_sev = float(st.session_state.get("nmd_crisis_severity_pct", 65.0)) / 100.0 if crisis_on else 0.0
    opt = optimize_hedge_notional(
        run_engine,
        tier1_capital=float(st.session_state.get("tier1", 120_000_000.0)),
        cpr=float(st.session_state.get("cpr_pct", 6.0)) / 100.0,
        include_internal_scenarios=bool(st.session_state.get("include_internal", True)),
        balance_sheet=bs,
        nmd_crisis_severity=crisis_sev,
    )
    st.session_state["hedge_notional"] = float(opt.optimal_notional)
    st.session_state["preset_label"] = (
        f"Hedge optimisé: {opt.optimal_notional:,.0f} EUR "
        f"(worst: {opt.best_scenario}, obj={opt.objective_value:,.0f})"
    )


def render():
    st.set_page_config(page_title="ALM IRRBB Dashboard", layout="wide", initial_sidebar_state="expanded")
    _init_state()

    st.title("ALM Engine — IRRBB Bâle IV")
    st.caption("EVE · NII · EAR · LCR/NSFR · Hedge — démo comité ALCO / entretien BPAURA")

    with st.sidebar:
        st.header("Paramètres")
        if "tier1" not in st.session_state:
            st.session_state["tier1"] = 120_000_000.0
        if "cpr_pct" not in st.session_state:
            st.session_state["cpr_pct"] = float(st.session_state.get("cpr", 0.06)) * 100.0
        if "hedge_notional" not in st.session_state:
            st.session_state["hedge_notional"] = 0.0
        if "include_internal" not in st.session_state:
            st.session_state["include_internal"] = True

        # Presets BEFORE widgets + on_click: Streamlit runs callbacks before widgets
        # are instantiated, which avoids "cannot be modified after the widget..." errors.
        st.subheader("Presets")
        st.button("Mode Demo 2 min", use_container_width=True, on_click=_apply_demo_preset)
        st.button("Optimiser hedge", use_container_width=True, on_click=_optimize_hedge_callback)
        st.divider()
        st.number_input(
            "Tier 1 Capital (EUR)",
            min_value=1_000_000.0,
            step=5_000_000.0,
            key="tier1",
        )
        st.slider(
            "CPR hypothécaire (%)",
            min_value=0.0,
            max_value=25.0,
            step=0.5,
            key="cpr_pct",
        )
        st.number_input(
            "Notionnel hedge swap (EUR)",
            min_value=0.0,
            step=5_000_000.0,
            key="hedge_notional",
        )
        st.toggle("Scénarios ICAAP internes", key="include_internal")
        st.divider()
        st.subheader("Crise NMD")
        st.toggle("Bank run / fuite dépôts", key="nmd_crisis_on")
        st.slider(
            "Sévérité crise NMD (%)",
            min_value=10.0,
            max_value=100.0,
            step=5.0,
            key="nmd_crisis_severity_pct",
            disabled=not bool(st.session_state.get("nmd_crisis_on", False)),
            help="Mild ≈ 35% · Moderate ≈ 65% · Severe = 100% — fuite, core↓, runoff↑, beta↑, LCR outflows↑",
        )

    if st.session_state.get("preset_label"):
        st.info(st.session_state["preset_label"])

    if st.session_state["presentation_mode"]:
        render_presentation_timer()

    tier1 = float(st.session_state["tier1"])
    cpr = float(st.session_state["cpr_pct"]) / 100.0
    st.session_state["cpr"] = cpr
    hedge_notional = float(st.session_state["hedge_notional"])
    include_internal = bool(st.session_state["include_internal"])
    balance_sheet = _balance_sheet_from_widgets()
    st.session_state["balance_sheet"] = balance_sheet
    crisis_on = bool(st.session_state.get("nmd_crisis_on", False))
    nmd_crisis_severity = (
        float(st.session_state.get("nmd_crisis_severity_pct", 65.0)) / 100.0 if crisis_on else 0.0
    )

    with st.spinner("Calcul moteur ALM…"):
        table, wal, metadata = run_engine(
            tier1_capital=tier1,
            cpr=cpr,
            include_internal_scenarios=include_internal,
            hedge_notional=hedge_notional,
            balance_sheet=balance_sheet,
            nmd_crisis_severity=nmd_crisis_severity,
        )

    curve_src = str(metadata.get("initial_curve_source", ""))
    calib_src = str(metadata.get("calibration_source", ""))
    if "fallback" in curve_src.lower() or "fallback" in calib_src.lower():
        st.warning(
            "Courbe / calibration en **fallback synthétique** (API BCE indisponible ou en erreur). "
            f"Courbe: `{curve_src}` · HW: `{calib_src}`"
        )
    else:
        st.caption(f"Données marché BCE — courbe: `{curve_src}` · HW: `{calib_src}`")

    history_file = Path("outputs") / "run_history.csv"
    append_run_history(history_file, metadata)
    history_df = load_run_history(history_file)
    kpi = build_risk_dashboard_table(table, tier1)

    tab_synth, tab_bilan, tab_irrbb, tab_liquidity, tab_exports = st.tabs(
        ["Synthèse ALCO", "Bilan A/P", "IRRBB & ALCO", "Liquidity & Funding", "Exports"]
    )

    with tab_synth:
        render_synthese_tab(table, kpi, metadata, tier1)
        render_limitations()

    with tab_bilan:
        render_bilan_tab(balance_sheet, metadata, tier1, cpr, hedge_notional)

    with tab_irrbb:
        st.subheader("Visualisations")
        render_charts_block(table, tier1, hedge_notional, bool(st.session_state["presentation_mode"]))

        st.subheader("Résultats scénarios (Bâle + ICAAP + crise NMD)")
        st.dataframe(table, use_container_width=True)
        st.subheader("KPI comité ALCO (feu tricolore)")
        st.dataframe(kpi, use_container_width=True)

        m1, m2 = st.columns(2)
        m1.metric("WAL portefeuille fixe (années)", f"{wal:.2f}")
        m2.metric("Notionnel hedge overlay (EUR)", f"{metadata['hedge_notional']:,.0f}")
        st.caption(
            f"Source calibration HW: {metadata['calibration_source']} | "
            f"Source courbe initiale: {metadata['initial_curve_source']}"
        )
        outliers = table[table["outlier"]]
        outliers_nii = table[table["outlier_nii"]] if "outlier_nii" in table.columns else table.iloc[0:0]
        if outliers.empty:
            st.success("SOT EVE OK — aucun scénario |ΔEVE| ≥ 15% Tier 1.")
        else:
            st.error("SOT EVE breach — revue ALCO / supervision.")
            st.dataframe(outliers[["scenario", "delta_eve"]], use_container_width=True)
        if outliers_nii.empty:
            st.success("SOT NII OK — pas de large decline NII ≥ 5% Tier 1 sur Parallel Up/Down.")
        else:
            st.error("SOT NII breach (indicateur de supervision, Parallel uniquement).")
            st.dataframe(outliers_nii[["scenario", "delta_nii"]], use_container_width=True)

        st.subheader("Commentaire de gestion automatique")
        for line in build_management_commentary(table, tier1):
            st.write(f"- {line}")

        render_limitations()

    with tab_liquidity:
        st.subheader("Jauges Liquidity & Funding")
        c5, c6, c7 = st.columns(3)
        c5.metric("LCR", f"{metadata['lcr_ratio']:.2f}x", "OK" if metadata["lcr_compliant"] else "Breach")
        c6.metric("NSFR", f"{metadata['nsfr_ratio']:.2f}x", "OK" if metadata["nsfr_compliant"] else "Breach")
        c7.metric("FTP Total PnL", f"{metadata['ftp_total_pnl']:,.0f} EUR")
        if bool(metadata.get("nmd_crisis_active", False)):
            st.info(
                f"LCR sous crise NMD ({metadata.get('nmd_crisis_label')}) : "
                f"**{metadata['lcr_ratio']:.2f}x** vs base **{float(metadata.get('lcr_ratio_unstressed', 0.0)):.2f}x** — "
                f"outflows 30j +{float(metadata.get('nmd_flight_eur', 0.0)) / 1e6:.0f} M€ de fuite dépôts."
            )
        st.write("LCR progress (regulatory floor = 1.0)")
        st.progress(int(min(100, max(0, metadata["lcr_ratio"] * 100))))
        st.write("NSFR progress (regulatory floor = 1.0)")
        st.progress(int(min(100, max(0, metadata["nsfr_ratio"] * 100))))

        if st.session_state["preset"] == "bpaura":
            st.caption(
                "Bilan BPAURA : fixe 250 M€ @2,5% (15 ans) · flottant 100 M€ (Euribor+1,5%) · "
                "NMD 300 M€ (β=0,3) · wholesale 50 M€ · hedge 75 M€"
            )

        st.subheader("Historique des runs")
        st.dataframe(history_df, use_container_width=True)
        if not history_df.empty:
            chart = history_df.copy()
            st.line_chart(chart.set_index("run_timestamp")[["lcr_ratio", "nsfr_ratio"]])
            st.line_chart(chart.set_index("run_timestamp")[["ftp_total_pnl"]])

    with tab_exports:
        st.subheader("Exports ALCO")
        export_dir = Path("outputs")
        excel_path = export_alco_excel(export_dir / "alco_dashboard_latest.xlsx", table, metadata)
        pdf_path = export_alco_pdf(export_dir / "alco_dashboard_latest.pdf", table, metadata)
        with open(excel_path, "rb") as f_excel:
            st.download_button(
                "Télécharger Excel ALCO",
                data=f_excel.read(),
                file_name=excel_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with open(pdf_path, "rb") as f_pdf:
            st.download_button(
                "Télécharger PDF ALCO",
                data=f_pdf.read(),
                file_name=pdf_path.name,
                mime="application/pdf",
            )


if __name__ == "__main__":
    render()
