import pandas as pd

from alm_engine.calibration.calibrate_hw import calibrate_from_historical_short_rate


def test_hw_calibration_returns_positive_parameters():
    df = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=60, freq="ME"),
            "yield": [0.01 + 0.0003 * i for i in range(60)],
        }
    )
    out = calibrate_from_historical_short_rate(df)
    assert out.mean_reversion > 0
    assert out.sigma > 0

