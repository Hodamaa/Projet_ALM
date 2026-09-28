import numpy as np
import pandas as pd

from alm_engine.funding.ftp_calculator import calculate_ftp
from alm_engine.liquidity.lcr_calculator import calculate_lcr
from alm_engine.liquidity.nsfr_calculator import calculate_nsfr


def test_lcr_computation():
    res = calculate_lcr(50_000_000, 15_000_000, 5_000_000, 45_000_000, 20_000_000)
    assert res.hqla > 0
    assert res.lcr_ratio > 0


def test_nsfr_computation():
    res = calculate_nsfr(150_000_000, 40_000_000, 20_000_000, 120_000_000, 30_000_000)
    assert res.asf > 0
    assert res.nsfr_ratio > 0


def test_ftp_computation():
    asset = pd.DataFrame({"time": [0.5, 1.0], "cashflow": [1000.0, 1000.0], "interest": [20.0, 25.0]})
    liab = pd.DataFrame({"time": [0.5, 1.0], "cashflow": [800.0, 700.0], "balance": [800.0, 700.0]})
    curve = np.array([0.02] * 24)
    res = calculate_ftp(asset, liab, curve)
    assert isinstance(res.total_ftp_pnl, float)

