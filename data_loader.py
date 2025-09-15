import pandas as pd
import numpy as np
from pathlib import Path
from pandas.tseries.offsets import MonthEnd
from typing import Any, Dict, List
from config import DEF_PARQUET

def load_dataframe(parquet_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(parquet_path)
    required = {"name","isoab","dates","predicted","cumulative_outcome_n","outcome_p","outcome_n"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Parquet missing expected columns: {missing}")
    parsed = pd.to_datetime(df["dates"].astype(str), errors="coerce")
    bad_mask = parsed.isna() & df["dates"].astype(str).str.match(r"^\d{6}$").fillna(False)
    parsed.loc[bad_mask] = pd.to_datetime(df.loc[bad_mask,"dates"].astype(str), format="%Y%m", errors="coerce")
    df["_month"] = parsed.dt.to_period("M").dt.to_timestamp() + MonthEnd(0)
    df = df.sort_values(["name","_month"]).reset_index(drop=True)
    return df

def prepare_map_data(df: pd.DataFrame) -> pd.DataFrame:
    map_data = df.groupby(["name","isoab"]).agg({"predicted":"sum","_month":["min","max"]}).reset_index()
    map_data.columns = ["name","iso3","total_predicted","horizon_start","horizon_end"]
    map_data["log_predicted"] = np.log1p(map_data["total_predicted"])
    return map_data

def month_options(df: pd.DataFrame) -> List[Dict[str, Any]]:
    small = df[["_month","outcome_n"]].drop_duplicates().sort_values("_month")
    return [{"label": m.strftime("%Y-%m"), "value": int(n)} for m, n in zip(small["_month"], small["outcome_n"])]

def latest_month_idx(df: pd.DataFrame) -> int:
    small = df[["_month","outcome_n"]].drop_duplicates().sort_values("_month")
    return int(small["outcome_n"].iloc[-1])
