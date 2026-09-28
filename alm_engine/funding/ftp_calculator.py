from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FTPResult:
    avg_ftp_rate: float
    asset_transfer_margin: float
    liability_transfer_margin: float
    total_ftp_pnl: float


def calculate_ftp(
    asset_cfs: pd.DataFrame,
    liability_cfs: pd.DataFrame,
    zero_curve: np.ndarray,
    asset_spread: float = 0.012,
    liability_spread: float = 0.003,
) -> FTPResult:
    if asset_cfs.empty:
        return FTPResult(0.0, 0.0, 0.0, 0.0)
    idx_asset = np.clip((asset_cfs["time"].to_numpy() * 12).astype(int) - 1, 0, len(zero_curve) - 1)
    ftp_asset_rates = zero_curve[idx_asset]
    asset_volume = asset_cfs["cashflow"].to_numpy()
    avg_ftp = float(np.average(ftp_asset_rates, weights=np.maximum(asset_volume, 1e-8)))
    asset_margin = float(np.sum((asset_spread + ftp_asset_rates) * asset_volume / 12.0))

    liab_margin = 0.0
    if not liability_cfs.empty:
        liab_col = "balance" if "balance" in liability_cfs.columns else "cashflow"
        liab_values = liability_cfs[liab_col].to_numpy()
        idx_liab = np.clip((liability_cfs["time"].to_numpy() * 12).astype(int) - 1, 0, len(zero_curve) - 1)
        ftp_liab_rates = zero_curve[idx_liab]
        liab_margin = float(np.sum((ftp_liab_rates - liability_spread) * liab_values / 12.0))

    total = asset_margin - liab_margin
    return FTPResult(
        avg_ftp_rate=avg_ftp,
        asset_transfer_margin=asset_margin,
        liability_transfer_margin=liab_margin,
        total_ftp_pnl=total,
    )

