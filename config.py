# Outcome-probability (pie)
PIE_BINS   = [-float("inf"), 0.01, 0.5, 0.99, float("inf")]
PIE_LABELS = [
    "Near-certain no conflict",
    "Improbable conflict",
    "Probable conflict",
    "Near-certain conflict",
]
PIE_COLORS = {...}

# Predicted-count bands (waffle)
BAND_BINS   = [-0.1, 0, 10, 100, 1000, 10000, float("inf")]
BAND_LABELS = ["0", "1–10", "11–100", "101–1,000", "1,001–10,000", "10,001+"]
BAND_COLORS = {...}

WAFFLE_COLS = 12
WAFFLE_GAP  = 0.0
WAFFLE_CELL = 1.0

DEF_PARQUET = Path(__file__).resolve().parent / "data" / "FAST-Forecast.parquet"
MODEL_DETAILS_PATH = Path(__file__).resolve().parent / "docs" / "model_details.md"
