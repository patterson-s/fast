# config.py
from __future__ import annotations

from pathlib import Path

# =========================
# App meta
# =========================
APP_TITLE = "FAST-cm Interactive Visualizer"

# =========================
# Outcome-probability (pie)
# =========================
PIE_BINS = [-float("inf"), 0.01, 0.5, 0.99, float("inf")]
PIE_LABELS = [
    "Near-certain no conflict",
    "Improbable conflict",
    "Probable conflict",
    "Near-certain conflict",
]
# Map each label to a color (must be a dict, not a set)
PIE_COLORS = {
    "Near-certain no conflict": "green",
    "Improbable conflict": "blue",
    "Probable conflict": "orange",
    "Near-certain conflict": "red",
}

# =========================
# Predicted-count bands (waffle)
# =========================
BAND_BINS = [-0.1, 0, 10, 100, 1000, 10000, float("inf")]
BAND_LABELS = ["0", "1–10", "11–100", "101–1,000", "1,001–10,000", "10,001+"]
BAND_COLORS = {
    "0": "#6baed6",
    "1–10": "#74c476",
    "11–100": "#fd8d3c",
    "101–1,000": "#9e9ac8",
    "1,001–10,000": "#e34a33",
    "10,001+": "#636363",
}

# Waffle layout
WAFFLE_COLS = 12   # tiles per row
WAFFLE_GAP = 0.0   # space between tiles
WAFFLE_CELL = 1.0  # logical tile size (used for spacing math)

# =========================
# Paths
# =========================
ROOT = Path(__file__).resolve().parent
DEF_PARQUET = ROOT / "data" / "FAST-Forecast.parquet"
MODEL_DETAILS_PATH = ROOT / "docs" / "model_details.md"
