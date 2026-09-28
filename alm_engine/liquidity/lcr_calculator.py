from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LCRResult:
    hqla: float
    net_outflows_30d: float
    lcr_ratio: float
    compliant: bool


def calculate_lcr(
    level1_assets: float,
    level2a_assets: float,
    level2b_assets: float,
    outflows_30d: float,
    inflows_30d: float,
) -> LCRResult:
    """Simplified Basel LCR with haircuts and stock caps.

    Caps (after haircuts):
    - Level 2B ≤ 15% of total HQLA
    - Level 2 (2A+2B) ≤ 40% of total HQLA
    Equivalent unconstrained forms:
    - L2B ≤ (15/85) × (L1 + L2A)
    - L2 ≤ (40/60) × L1 = (2/3) × L1
    """
    l1 = float(level1_assets)
    l2a = 0.85 * float(level2a_assets)
    l2b = 0.50 * float(level2b_assets)

    # Level 2B ≤ 15% of HQLA ⇔ L2B ≤ (15/85)*(L1+L2A) after the 40% interaction is applied stepwise.
    l2b_cap = (0.15 / 0.85) * (l1 + l2a) if (l1 + l2a) > 0 else 0.0
    l2b_capped = min(l2b, l2b_cap)

    # Level 2 ≤ 40% of HQLA ⇔ L2 ≤ (2/3)*L1
    l2_cap = (0.40 / 0.60) * l1 if l1 > 0 else 0.0
    l2_total = min(l2a + l2b_capped, l2_cap)

    hqla = l1 + l2_total
    capped_inflows = min(float(inflows_30d), 0.75 * float(outflows_30d))
    net_outflows = max(1.0, float(outflows_30d) - capped_inflows)
    ratio = hqla / net_outflows
    return LCRResult(hqla=hqla, net_outflows_30d=net_outflows, lcr_ratio=ratio, compliant=ratio >= 1.0)
