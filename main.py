from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from alm_engine.engine import run_engine
from alm_engine.reporting.alco_reporting import export_alco_excel, export_alco_pdf
from alm_engine.reporting.interview_pack import build_interview_pack
from alm_engine.risk.hedge_optimizer import optimize_hedge_notional


def main():
    parser = argparse.ArgumentParser(description="ALM Engine - IRRBB EVE and NII")
    parser.add_argument("--tier1", type=float, default=120_000_000.0, help="Tier 1 capital")
    parser.add_argument("--cpr", type=float, default=0.06, help="CPR prepayment rate for fixed loans")
    parser.add_argument("--export-dir", type=str, default="outputs", help="Directory for ALCO exports")
    parser.add_argument("--no-internal-scenarios", action="store_true", help="Disable ICAAP internal scenarios")
    parser.add_argument("--hedge-notional", type=float, default=0.0, help="Swap overlay notional for NII mitigation")
    parser.add_argument("--optimize-hedge", action="store_true", help="Auto-optimize hedge notional for delta NII max")
    args = parser.parse_args()

    hedge_notional = args.hedge_notional
    if args.optimize_hedge:
        opt = optimize_hedge_notional(
            run_engine,
            tier1_capital=args.tier1,
            cpr=args.cpr,
            include_internal_scenarios=not args.no_internal_scenarios,
        )
        hedge_notional = opt.optimal_notional
        print(
            "Hedge optimizer selected notional "
            f"{opt.optimal_notional:,.0f} EUR (worst scenario: {opt.best_scenario}, objective={opt.objective_value:,.0f})"
        )

    table, wal, metadata = run_engine(
        tier1_capital=args.tier1,
        cpr=args.cpr,
        include_internal_scenarios=not args.no_internal_scenarios,
        hedge_notional=hedge_notional,
    )
    print("=== IRRBB Scenario Results (EVE + NII) ===")
    print(table.to_string(index=False))
    print(f"\nWAL (fixed-rate mortgage pool): {wal:.2f} years")
    print(f"Calibration source: {metadata['calibration_source']}")
    print(f"Initial curve source: {metadata['initial_curve_source']}")
    print(f"LCR: {metadata['lcr_ratio']:.2f}x ({'OK' if metadata['lcr_compliant'] else 'Breach'})")
    print(f"NSFR: {metadata['nsfr_ratio']:.2f}x ({'OK' if metadata['nsfr_compliant'] else 'Breach'})")
    print(f"FTP total PnL: {metadata['ftp_total_pnl']:.0f} EUR")

    export_dir = Path(args.export_dir)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    xlsx_path = export_alco_excel(export_dir / f"alco_report_{stamp}.xlsx", table, metadata)
    pdf_path = export_alco_pdf(export_dir / f"alco_report_{stamp}.pdf", table, metadata)
    pack_path = build_interview_pack(
        export_dir / f"interview_pack_{stamp}.zip",
        [xlsx_path, pdf_path, "docs/METHODOLOGIE_MODELE_GOUVERNANCE.md", "docs/INTERVIEW_ONE_PAGER.md"],
    )
    print(f"Excel export: {xlsx_path}")
    print(f"PDF export: {pdf_path}")
    print(f"Interview pack export: {pack_path}")


if __name__ == "__main__":
    main()
