from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from alm_engine.data.ecb_data import (
    fetch_ecb_short_rate_history,
    fetch_ecb_yield_curve_history,
    fetch_or_fallback_multi_maturity_history,
    fetch_or_fallback_short_rate_history,
    sdmx_data_url,
)


def test_sdmx_url_splits_flow_and_key():
    url = sdmx_data_url("YC", "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y")
    assert url.endswith("/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y")
    assert "/YC/B." in url
    # Guard against the old broken pattern FM.M.U2... as a single segment
    assert "/data/YC.B." not in url


def test_parse_short_rate_from_csv_mock():
    csv = (
        "KEY,TIME_PERIOD,OBS_VALUE\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_3M,2026-09-14,2.52\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_3M,2026-09-15,2.51\n"
    )
    mock_resp = MagicMock()
    mock_resp.text = csv
    mock_resp.raise_for_status = MagicMock()
    with patch("alm_engine.data.ecb_data.requests.get", return_value=mock_resp) as get:
        df = fetch_ecb_short_rate_history(start_period="2026-01-01")
    assert len(df) == 2
    assert df["yield"].iloc[-1] == pytest.approx(0.0251)
    called_url = get.call_args.args[0]
    assert "/YC/" in called_url
    assert "SR_3M" in called_url


def test_parse_curve_from_csv_mock():
    csv = (
        "KEY,TIME_PERIOD,OBS_VALUE\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_1Y,2026-09-15,2.9\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y,2026-09-15,3.1\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y,2026-09-15,3.2\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y,2026-09-15,3.5\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_20Y,2026-09-15,3.8\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y,2026-09-15,3.7\n"
        "YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_3M,2026-09-15,2.5\n"
    )
    mock_resp = MagicMock()
    mock_resp.text = csv
    mock_resp.raise_for_status = MagicMock()
    with patch("alm_engine.data.ecb_data.requests.get", return_value=mock_resp):
        pivot = fetch_ecb_yield_curve_history(start_period="2026-01-01")
    assert list(pivot.columns)[:3] == ["3M", "1Y", "2Y"]
    assert pivot.iloc[-1]["10Y"] == pytest.approx(0.035)


def test_fallback_on_http_error():
    with patch("alm_engine.data.ecb_data.fetch_ecb_short_rate_history", side_effect=RuntimeError("boom")):
        df, source = fetch_or_fallback_short_rate_history()
    assert not df.empty
    assert source.startswith("Synthetic fallback")
    with patch("alm_engine.data.ecb_data.fetch_ecb_yield_curve_history", side_effect=RuntimeError("boom")):
        pivot, source = fetch_or_fallback_multi_maturity_history()
    assert not pivot.empty
    assert "fallback" in source.lower()


def test_live_ecb_yc_fetch():
    """Live check — skipped automatically if network/API fails."""
    try:
        df = fetch_ecb_short_rate_history(start_period="2024-01-01")
        pivot = fetch_ecb_yield_curve_history(start_period="2024-01-01")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ECB API unavailable: {exc}")
    assert len(df) > 10
    assert pivot.shape[1] >= 6
    assert float(pivot.iloc[-1]["10Y"]) > 0
