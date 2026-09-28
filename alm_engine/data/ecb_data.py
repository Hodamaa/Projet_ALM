from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import numpy as np
import pandas as pd
import requests


# SDMX REST: {base}/service/data/{flowRef}/{key}
# Old bug: concatenating "FM.M.U2...." as a single path segment → HTTP 400.
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# Euro area AAA government bond yield curve (daily spot rates) — dataset YC.
YC_FLOW = "YC"
YC_CURVE_PREFIX = "B.U2.EUR.4F.G_N_A.SV_C_YM"
YC_TENORS: dict[str, tuple[str, float]] = {
    "3M": ("SR_3M", 0.25),
    "1Y": ("SR_1Y", 1.0),
    "2Y": ("SR_2Y", 2.0),
    "5Y": ("SR_5Y", 5.0),
    "10Y": ("SR_10Y", 10.0),
    "20Y": ("SR_20Y", 20.0),
    "30Y": ("SR_30Y", 30.0),
}
SHORT_RATE_TENOR = "3M"


@dataclass(frozen=True)
class ECBFetchResult:
    """Payload + provenance for dashboard / metadata."""

    data: pd.DataFrame
    source: str
    as_of: str | None = None
    detail: str = ""


def sdmx_data_url(flow_ref: str, key: str) -> str:
    """Build a correct SDMX data URL (flowRef and key are separate path segments)."""
    return f"{ECB_API_BASE}/{flow_ref.strip('/')}/{key.strip('/')}"


def _parse_csvdata(text: str) -> pd.DataFrame:
    raw = pd.read_csv(StringIO(text))
    if "TIME_PERIOD" not in raw.columns or "OBS_VALUE" not in raw.columns:
        raise ValueError(f"Unexpected ECB schema; columns={list(raw.columns)}")
    return raw


def fetch_sdmx_csv(
    flow_ref: str,
    key: str,
    *,
    start_period: str | None = None,
    end_period: str | None = None,
    last_n_observations: int | None = None,
    timeout_seconds: int = 25,
) -> pd.DataFrame:
    """GET ECB SDMX data as csvdata and return the raw dataframe."""
    params: dict[str, str | int] = {"format": "csvdata"}
    if start_period:
        params["startPeriod"] = start_period
    if end_period:
        params["endPeriod"] = end_period
    if last_n_observations is not None:
        params["lastNObservations"] = int(last_n_observations)

    url = sdmx_data_url(flow_ref, key)
    response = requests.get(url, params=params, timeout=timeout_seconds)
    response.raise_for_status()
    return _parse_csvdata(response.text)


def _tenor_from_key(series_key: str) -> str:
    """Map KEY like YC.B.U2....SR_10Y → '10Y'."""
    token = str(series_key).rsplit(".", 1)[-1]  # SR_10Y
    for tenor, (code, _) in YC_TENORS.items():
        if token == code:
            return tenor
    raise ValueError(f"Unknown YC tenor token in key={series_key!r}")


def _yc_multi_key(tenors: list[str] | None = None) -> str:
    selected = tenors or list(YC_TENORS)
    codes = [YC_TENORS[t][0] for t in selected]
    # SDMX OR syntax: ...SR_3M+SR_1Y+...
    return f"{YC_CURVE_PREFIX}.{'+'.join(codes)}"


def fetch_ecb_yield_curve_history(
    start_period: str = "2018-01-01",
    tenors: list[str] | None = None,
    timeout_seconds: int = 30,
) -> pd.DataFrame:
    """Daily AAA EUR yield curve as a wide table (index=date, columns=tenors)."""
    selected = [t for t in (tenors or list(YC_TENORS)) if t in YC_TENORS]
    raw = fetch_sdmx_csv(
        YC_FLOW,
        _yc_multi_key(selected),
        start_period=start_period,
        timeout_seconds=timeout_seconds,
    )
    frame = raw[["TIME_PERIOD", "KEY", "OBS_VALUE"]].copy()
    frame["date"] = pd.to_datetime(frame["TIME_PERIOD"])
    frame["tenor"] = frame["KEY"].map(_tenor_from_key)
    frame["yield"] = pd.to_numeric(frame["OBS_VALUE"], errors="coerce") / 100.0
    frame = frame.dropna(subset=["yield"])
    pivot = frame.pivot_table(index="date", columns="tenor", values="yield", aggfunc="last")
    # Keep a stable column order
    ordered = [t for t in YC_TENORS if t in pivot.columns]
    pivot = pivot[ordered].dropna().sort_index()
    if pivot.empty:
        raise ValueError("ECB YC returned no complete term-structure rows")
    return pivot


def fetch_ecb_short_rate_history(
    start_period: str = "2018-01-01",
    timeout_seconds: int = 25,
) -> pd.DataFrame:
    """Daily short rate from the AAA EUR 3M spot on the YC curve."""
    code = YC_TENORS[SHORT_RATE_TENOR][0]
    key = f"{YC_CURVE_PREFIX}.{code}"
    raw = fetch_sdmx_csv(
        YC_FLOW,
        key,
        start_period=start_period,
        timeout_seconds=timeout_seconds,
    )
    df = raw[["TIME_PERIOD", "OBS_VALUE"]].rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "yield"})
    df["date"] = pd.to_datetime(df["date"])
    df["yield"] = pd.to_numeric(df["yield"], errors="coerce") / 100.0
    df = df.dropna().sort_values("date")
    if df.empty:
        raise ValueError("ECB YC short-rate series returned no usable rows")
    return df.reset_index(drop=True)


def fallback_synthetic_short_rate_history(n_obs: int = 120) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_obs, freq="B")
    base = 0.02 + 0.004 * np.sin(np.linspace(0, 8, n_obs))
    shock = np.linspace(-0.002, 0.002, n_obs)
    return pd.DataFrame({"date": dates, "yield": base + shock})


def fallback_synthetic_multi_maturity_history(n_obs: int = 120) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_obs, freq="B")
    base_level = 0.022 + 0.003 * np.sin(np.linspace(0, 6, n_obs))
    data: dict[str, np.ndarray] = {}
    for tenor, (_, tau) in YC_TENORS.items():
        slope_component = 0.004 * np.exp(-tau / 7.0)
        curvature = 0.002 * np.sin(np.linspace(0, 3, n_obs) + tau / 10.0)
        data[tenor] = base_level - slope_component + curvature
    return pd.DataFrame(data, index=dates)


def _as_of_label(index_like) -> str | None:
    if index_like is None or len(index_like) == 0:
        return None
    ts = pd.Timestamp(index_like[-1] if not hasattr(index_like, "iloc") else index_like.iloc[-1])
    return ts.strftime("%Y-%m-%d")


def fetch_or_fallback_short_rate_history() -> tuple[pd.DataFrame, str]:
    try:
        df = fetch_ecb_short_rate_history()
        as_of = _as_of_label(df["date"])
        return df, f"ECB YC API ({SHORT_RATE_TENOR} AAA EUR, as-of {as_of})"
    except Exception as exc:  # noqa: BLE001 — intentional resilient fallback for demos
        return fallback_synthetic_short_rate_history(), f"Synthetic fallback ({type(exc).__name__}: {exc})"


def fetch_or_fallback_multi_maturity_history() -> tuple[pd.DataFrame, str]:
    try:
        # Curve fit uses 1Y–30Y; keep 3M available for diagnostics / short end.
        pivot = fetch_ecb_yield_curve_history()
        as_of = _as_of_label(pivot.index)
        return pivot, f"ECB YC API (AAA EUR curve, as-of {as_of})"
    except Exception as exc:  # noqa: BLE001
        return (
            fallback_synthetic_multi_maturity_history(),
            f"Synthetic fallback ({type(exc).__name__}: {exc})",
        )


# Backwards-compatible aliases used by older docs / imports
fetch_ecb_multi_maturity_history = fetch_ecb_yield_curve_history
