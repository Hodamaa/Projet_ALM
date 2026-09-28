import numpy as np
import pandas as pd

from alm_engine.calibration.calibrate_hw import calibrate_nss_from_term_structure


def test_nss_calibration_returns_curve_object():
    latest = pd.Series(
        [0.02, 0.021, 0.023, 0.024, 0.025, 0.0255],
        index=["1Y", "2Y", "5Y", "10Y", "20Y", "30Y"],
    )
    mats = np.array([1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
    curve = calibrate_nss_from_term_structure(latest, mats, n_trials=200, seed=1)
    rates = curve.zero_rate(mats)
    assert rates.shape[0] == 6
