# ALM Interview One Pager

## Problem solved
- Industrial-style IRRBB engine for retail bank balance sheet steering.
- Dual risk lenses: EVE (economic value) and NII/EAR (earnings sensitivity).

## Why this is credible for top-tier banking internships
- Regulatory alignment: 6 Basel/EBA IRRBB scenarios, SOT EVE 15% Tier1 + SOT NII 5% Tier1 (parallel shocks).
- Management layer: ICAAP internal scenarios, traffic light dashboard, ALCO commentary.
- Model rigor: ECB-based calibration (short-rate + multi-maturity term structure).
- Delivery rigor: tests, CI, reproducible exports, interview ZIP package.

## Architecture snapshot
- `models/`: NSS curve + Hull-White + Vasicek benchmark
- `instruments/`: fixed, floating, NMD behavioral replication
- `risk/`: EVE, NII, EAR, Basel shocks, internal ICAAP shocks, hedge overlay
- `reporting/`: Excel/PDF ALCO export + interview pack builder
- `dashboard/`: Streamlit app for live demo in under 2 minutes

## Suggested talking points in interview
- Explain the difference between EVE and NII/EAR and why both matter.
- Show one outlier scenario and mitigation via hedge overlay.
- Mention model limitations and roadmap (caps/floors calibration, FTP, hedging strategy optimization).

