import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "pdf_generator_03"))
from data_provider import DataProvider

dp = DataProvider()
hist = dp.get_historical_data()
print(hist.columns.tolist())
print(hist.head())