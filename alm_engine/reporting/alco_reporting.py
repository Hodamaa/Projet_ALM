from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from alm_engine.risk.nii_calculator import summarize_nii_sot


def build_risk_dashboard_table(scenario_results: pd.DataFrame, tier1_capital: float) -> pd.DataFrame:
    out = scenario_results.copy()
    out["delta_eve_pct_tier1"] = out["delta_eve"] / max(1.0, tier1_capital)
    out["risk_light"] = out["delta_eve_pct_tier1"].abs().apply(_risk_light)
    out["delta_nii_pct_tier1"] = out["delta_nii"] / max(1.0, tier1_capital)
    if "outlier_nii" not in out.columns:
        out["outlier_nii"] = False
    return out


def _risk_light(delta_ratio: float) -> str:
    """Internal early-warning lights on |ΔEVE|/Tier1.

    Only 15% is the hard regulatory SOT EVE threshold (RED).
    10% AMBER is an internal ALCO early-warning, not an EBA limit.
    """
    if abs(delta_ratio) >= 0.15:
        return "RED"
    if abs(delta_ratio) >= 0.10:
        return "AMBER"
    return "GREEN"


def build_management_commentary(scenario_results: pd.DataFrame, tier1_capital: float) -> list[str]:
    enriched = build_risk_dashboard_table(scenario_results, tier1_capital)
    worst = enriched.loc[enriched["delta_eve"].abs().idxmax()]
    nii_sot = summarize_nii_sot(enriched, tier1_capital)
    lines = [
        f"EVE = PV(actifs) − PV(passifs). Worst ΔEVE: {worst['scenario']} = {worst['delta_eve']:.0f} EUR.",
        f"SOT EVE (réglementaire, 15% Tier1, 6 chocs): {'BREACH' if bool(worst['outlier']) or bool(enriched['outlier'].any()) else 'OK'}.",
        (
            f"SOT NII (indicateur supervision, 5% Tier1, Parallel Up/Down, 1 an): "
            f"{'BREACH' if nii_sot.breach else 'OK'}"
            + (f" — pire {nii_sot.worst_scenario} ΔNII={nii_sot.worst_delta_nii:.0f} EUR." if nii_sot.applicable else ".")
        ),
    ]
    n_red = int((enriched["risk_light"] == "RED").sum())
    n_amber = int((enriched["risk_light"] == "AMBER").sum())
    lines.append(
        f"Feux internes ALCO (early-warning, non réglementaires) -> "
        f"RED(≥15%): {n_red}, AMBER(10–15%): {n_amber}, GREEN(<10%): {len(enriched) - n_red - n_amber}."
    )
    return lines


def export_alco_excel(
    output_path: str | Path,
    scenario_results: pd.DataFrame,
    metadata: dict[str, str | float],
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    meta_df = pd.DataFrame([metadata])
    tier1 = float(metadata.get("tier1_capital", 1.0))
    kpi = build_risk_dashboard_table(scenario_results, tier1)
    comments = pd.DataFrame({"management_commentary": build_management_commentary(scenario_results, tier1)})
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        scenario_results.to_excel(writer, sheet_name="IRRBB_Results", index=False)
        kpi.to_excel(writer, sheet_name="KPI_Traffic_Light", index=False)
        meta_df.to_excel(writer, sheet_name="Metadata", index=False)
        comments.to_excel(writer, sheet_name="Management_Commentary", index=False)
        liquidity_cols = [c for c in meta_df.columns if c.startswith("lcr_") or c.startswith("nsfr_") or c.startswith("sot_")]
        ftp_cols = [c for c in meta_df.columns if c.startswith("ftp_")]
        if liquidity_cols:
            meta_df[liquidity_cols].to_excel(writer, sheet_name="Liquidity_SOT", index=False)
        if ftp_cols:
            meta_df[ftp_cols].to_excel(writer, sheet_name="FTP_Summary", index=False)
    return output


def _fmt_meur(value: float) -> str:
    return f"{value / 1_000_000.0:+,.1f}"


def _fmt_ratio(value: float) -> str:
    return f"{value:.2f}x"


def export_alco_pdf(
    output_path: str | Path,
    scenario_results: pd.DataFrame,
    metadata: dict[str, str | float],
) -> Path:
    """Export a readable multi-page ALCO PDF (A4 landscape)."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    tier1 = float(metadata.get("tier1_capital", 1.0))
    kpi = build_risk_dashboard_table(scenario_results, tier1)
    comments = build_management_commentary(scenario_results, tier1)
    worst = kpi.loc[kpi["delta_eve"].abs().idxmax()]
    n_outliers_eve = int(kpi["outlier"].sum())
    n_outliers_nii = int(kpi["outlier_nii"].sum()) if "outlier_nii" in kpi.columns else 0
    n_red = int((kpi["risk_light"] == "RED").sum())
    n_amber = int((kpi["risk_light"] == "AMBER").sum())
    n_green = int((kpi["risk_light"] == "GREEN").sum())
    sot_nii_breach = bool(metadata.get("sot_nii_breach", n_outliers_nii > 0))

    page_size = (11.69, 8.27)

    with PdfPages(output) as pdf:
        fig, ax = plt.subplots(figsize=page_size)
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(0.5, 0.92, "Rapport ALCO — IRRBB (SOT EVE + SOT NII)", ha="center", fontsize=18, fontweight="bold")
        ax.text(
            0.5,
            0.86,
            f"Run: {metadata.get('run_timestamp', 'n/a')}  |  "
            f"Courbe: {metadata.get('initial_curve_source', 'n/a')}  |  "
            f"HW: {metadata.get('calibration_source', 'n/a')}",
            ha="center",
            fontsize=9,
            color="#475569",
        )

        cards = [
            ("Tier 1", f"{tier1 / 1e6:.0f} M€", "#0f172a"),
            ("Pire ΔEVE", f"{_fmt_meur(float(worst['delta_eve']))} M€\n{worst['scenario']}", "#dc2626"),
            ("SOT EVE 15%", f"{n_outliers_eve} breach\n{'FAIL' if n_outliers_eve else 'PASS'}", "#dc2626" if n_outliers_eve else "#16a34a"),
            ("SOT NII 5%", f"{'BREACH' if sot_nii_breach else 'OK'}\nParallel only", "#dc2626" if sot_nii_breach else "#16a34a"),
            ("LCR", _fmt_ratio(float(metadata.get("lcr_ratio", 0.0))), "#2563eb"),
            ("NSFR", _fmt_ratio(float(metadata.get("nsfr_ratio", 0.0))), "#2563eb"),
        ]
        for i, (title, value, color) in enumerate(cards):
            x0 = 0.04 + (i % 3) * 0.32
            y0 = 0.48 if i < 3 else 0.12
            ax.add_patch(
                plt.Rectangle((x0, y0), 0.28, 0.28, fill=True, facecolor="#f8fafc", edgecolor=color, linewidth=2, transform=ax.transAxes)
            )
            ax.text(x0 + 0.14, y0 + 0.21, title, ha="center", fontsize=10, color="#64748b", transform=ax.transAxes)
            ax.text(x0 + 0.14, y0 + 0.10, value, ha="center", va="center", fontsize=12, fontweight="bold", color=color, transform=ax.transAxes)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=page_size)
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.text(0.03, 0.94, "Synthèse management", fontsize=14, fontweight="bold")
        y = 0.86
        for line in comments:
            ax.text(0.05, y, f"• {line}", fontsize=10)
            y -= 0.09
        ax.text(0.03, 0.42, "Feux tricolores (early-warning interne ALCO)", fontsize=13, fontweight="bold")
        ax.text(0.05, 0.34, f"GREEN: {n_green}    AMBER: {n_amber}    RED: {n_red}", fontsize=12)
        ax.text(
            0.05,
            0.22,
            "Seuil réglementaire SOT EVE = 15% Tier1 (6 chocs). Seuil SOT NII = 5% Tier1 (Parallel Up/Down, 1 an).",
            fontsize=9,
            color="#334155",
        )
        ax.text(
            0.05,
            0.14,
            "AMBER 10–15% = limite interne early-warning, PAS un seuil EBA/Bâle.",
            fontsize=9,
            color="#b45309",
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=page_size)
        ax.axis("off")
        ax.set_title("Matrice scénarios (montants en M€)", fontsize=13, fontweight="bold", pad=12)

        display = pd.DataFrame(
            {
                "Scénario": kpi["scenario"],
                "ΔEVE": kpi["delta_eve"].map(lambda v: f"{v / 1e6:+.1f}"),
                "ΔEVE/T1": kpi["delta_eve_pct_tier1"].map(lambda v: f"{100 * v:+.1f}%"),
                "SOT EVE": kpi["outlier"].map(lambda v: "YES" if v else "NO"),
                "SOT NII": kpi["outlier_nii"].map(lambda v: "YES" if v else "—"),
                "Feu*": kpi["risk_light"],
                "ΔNII": kpi["delta_nii"].map(lambda v: f"{v / 1e6:+.2f}"),
                "ΔNII/T1": kpi["delta_nii_pct_tier1"].map(lambda v: f"{100 * v:+.2f}%"),
            }
        )
        table = ax.table(cellText=display.values, colLabels=display.columns, loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(7.5)
        table.scale(1.15, 1.5)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#0f172a")
                cell.set_text_props(color="white", fontweight="bold")
            elif col == 5 and row > 0:
                light = display.iloc[row - 1]["Feu*"]
                colors = {"GREEN": "#bbf7d0", "AMBER": "#fde68a", "RED": "#fecaca"}
                cell.set_facecolor(colors.get(light, "#ffffff"))
        ax.text(0.5, 0.02, "* Feu = early-warning interne (|ΔEVE|/T1). SOT NII applicable aux Parallel uniquement.", ha="center", fontsize=8, transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=page_size)
        x = range(len(kpi))
        labels = [str(s)[:18] for s in kpi["scenario"]]
        ax1.bar(x, kpi["delta_eve"] / 1e6, color="#dc2626", alpha=0.85)
        ax1.axhline(0.15 * tier1 / 1e6, color="#f59e0b", ls="--", label="SOT EVE ±15% T1")
        ax1.axhline(-0.15 * tier1 / 1e6, color="#f59e0b", ls="--")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
        ax1.set_ylabel("ΔEVE (M€)")
        ax1.set_title("Impact EVE (SOT EVE = 15% Tier1)")
        ax1.legend(fontsize=8)
        ax1.grid(axis="y", alpha=0.3)

        ax2.bar(x, kpi["delta_nii"] / 1e6, color="#2563eb", alpha=0.85)
        ax2.axhline(-0.05 * tier1 / 1e6, color="#7c3aed", ls="--", label="SOT NII −5% T1 (parallel)")
        ax2.set_xticks(list(x))
        ax2.set_xticklabels(labels, rotation=35, ha="right", fontsize=7)
        ax2.set_ylabel("ΔNII (M€)")
        ax2.set_title("Sensibilité NII (SOT NII = 5% Tier1)")
        ax2.legend(fontsize=8)
        ax2.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    return output
