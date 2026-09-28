from pathlib import Path

from alm_engine.dashboard.run_history import append_run_history, load_run_history


def test_append_and_load_history(tmp_path: Path):
    history_file = tmp_path / "runs.csv"
    metadata = {
        "run_timestamp": "2026-04-22T12:00:00Z",
        "lcr_ratio": 1.2,
        "nsfr_ratio": 1.1,
        "ftp_total_pnl": 1234.0,
        "hedge_notional": 10_000_000.0,
        "n_scenarios": 9,
    }
    append_run_history(history_file, metadata)
    df = load_run_history(history_file)
    assert len(df) == 1
    assert float(df.iloc[0]["lcr_ratio"]) == 1.2

