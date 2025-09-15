import pandas as pd
from typing import Optional
from functools import lru_cache
from config import PIE_BINS, PIE_LABELS, BAND_BINS, BAND_LABELS, MODEL_DETAILS_PATH

def categorize_prob_single(p: float) -> str:
    if p <= 0.01: return "Near-certain no conflict"
    elif p < 0.5: return "Improbable conflict"
    elif p < 0.99: return "Probable conflict"
    else: return "Near-certain conflict"

def categorize_band_single(pred: float) -> str:
    edges, labs = BAND_BINS, BAND_LABELS
    for i in range(len(labs)):
        if edges[i] < pred <= edges[i+1] or (i==0 and pred==edges[0]):
            return labs[i]
    return labs[-1]

def pie_counts_for_month(df: pd.DataFrame, month_idx: int) -> pd.Series:
    dfm = df.loc[df["outcome_n"] == month_idx]
    if dfm.empty:
        return pd.Series(0, index=PIE_LABELS, dtype=int)
    cats = pd.cut(dfm["outcome_p"].fillna(0.0), bins=PIE_BINS, labels=PIE_LABELS,
                  right=True, include_lowest=True)
    return cats.value_counts().reindex(PIE_LABELS, fill_value=0)

def waffle_counts_for_month(df: pd.DataFrame, month_idx: int) -> pd.Series:
    dfm = df.loc[df["outcome_n"] == month_idx]
    if dfm.empty:
        return pd.Series(0, index=BAND_LABELS, dtype=int)
    bands = pd.cut(dfm["predicted"].fillna(0.0), bins=BAND_BINS, labels=BAND_LABELS, include_lowest=True)
    return bands.value_counts().reindex(BAND_LABELS, fill_value=0)

def find_country_row(df: pd.DataFrame, month_idx: int, iso3: str) -> Optional[pd.Series]:
    dfm = df.loc[(df["outcome_n"] == month_idx) & (df["isoab"].str.upper() == iso3.upper())]
    if dfm.empty: return None
    return dfm.iloc[0]

@lru_cache(maxsize=1)
def _read_model_details_cached(_cache_buster: float) -> str:
    if not MODEL_DETAILS_PATH.exists():
        return "*(model_details.md not found — create docs/model_details.md)*"
    return MODEL_DETAILS_PATH.read_text(encoding="utf-8")

def read_model_details() -> str:
    try:
        mtime = MODEL_DETAILS_PATH.stat().st_mtime
    except FileNotFoundError:
        mtime = 0.0
    return _read_model_details_cached(mtime)
