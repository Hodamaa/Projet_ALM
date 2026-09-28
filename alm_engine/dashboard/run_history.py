from __future__ import annotations

from pathlib import Path

import pandas as pd


def append_run_history(history_path: str | Path, metadata: dict[str, float | str | bool]) -> Path:
    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "run_timestamp": metadata.get("run_timestamp", ""),
        "lcr_ratio": float(metadata.get("lcr_ratio", 0.0)),
        "nsfr_ratio": float(metadata.get("nsfr_ratio", 0.0)),
        "ftp_total_pnl": float(metadata.get("ftp_total_pnl", 0.0)),
        "hedge_notional": float(metadata.get("hedge_notional", 0.0)),
        "n_scenarios": float(metadata.get("n_scenarios", 0.0)),
    }
    df_new = pd.DataFrame([row])
    if path.exists():
        df_old = pd.read_csv(path)
        df = pd.concat([df_old, df_new], ignore_index=True)
        df = df.drop_duplicates(subset=["run_timestamp", "hedge_notional", "lcr_ratio", "nsfr_ratio"], keep="last")
    else:
        df = df_new
    df.to_csv(path, index=False)
    return path


def load_run_history(history_path: str | Path) -> pd.DataFrame:
    path = Path(history_path)
    if not path.exists():
        return pd.DataFrame(columns=["run_timestamp", "lcr_ratio", "nsfr_ratio", "ftp_total_pnl", "hedge_notional", "n_scenarios"])
    df = pd.read_csv(path)
    return df.sort_values("run_timestamp")

