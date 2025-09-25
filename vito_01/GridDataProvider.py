from pathlib import Path
import pandas as pd
from typing import Set, Tuple
from datetime import datetime

class GridDataProvider:
    def __init__(self):
        self.pgm_path = Path(r"C:\Users\spatt\Desktop\FAST\data\pgm_data.parquet")
        self.forecast_path = Path(r"C:\Users\spatt\Desktop\FAST\data\monthly_submission_2025_dr_growseas.parquet")
        self.historical_data = None
        self.forecast_data = None
        self.regional_grids = None
        
        self.core_variables = [
            'country_id', 'priogrid_gid', 'month_id',
            'ged_sb', 'splag_1_1_sb_1', 'growseasdummy', 'tlag1_dr_mod_gs',
            'Month', 'Year', 'name', 'isoab',
            'in_africa', 'in_middle_east'
        ]
    
    def _load_regional_grids(self) -> Set[int]:
        if self.regional_grids is not None:
            return self.regional_grids
        
        if self.historical_data is None:
            self.load_data()
        
        regional_mask = (self.historical_data['in_africa'] == 1) | (self.historical_data['in_middle_east'] == 1)
        regional_grids = set(self.historical_data[regional_mask]['priogrid_gid'].unique())
        
        if not regional_grids:
            raise ValueError("No grids found in Africa or Middle East regions")
        
        self.regional_grids = regional_grids
        return self.regional_grids
    
    def load_data(self):
        if self.historical_data is None:
            print(f"Loading {self.pgm_path.name}...")
            self.historical_data = pd.read_parquet(self.pgm_path)
            print(f"Loaded {len(self.historical_data):,} rows")
        
        if self.forecast_data is None:
            print(f"Loading {self.forecast_path.name}...")
            self.forecast_data = pd.read_parquet(self.forecast_path)
            print(f"Loaded {len(self.forecast_data):,} forecast rows")
    
    def get_historical_data(self) -> pd.DataFrame:
        self.load_data()
        regional_grids = self._load_regional_grids()
        return self.historical_data[self.historical_data['priogrid_gid'].isin(regional_grids)].copy()
    
    def get_forecast_data(self) -> pd.DataFrame:
        self.load_data()
        regional_grids = self._load_regional_grids()
        return self.forecast_data[self.forecast_data['priogrid_gid'].isin(regional_grids)].copy()
    
    def month_id_to_date(self, month_id: int) -> Tuple[int, int]:
        months_since_jan_2020 = month_id - 481
        year = 2020 + (months_since_jan_2020 // 12)
        month = (months_since_jan_2020 % 12) + 1
        return year, month
    
    def month_id_to_string(self, month_id: int) -> str:
        year, month = self.month_id_to_date(month_id)
        date_obj = datetime(year, month, 1)
        return date_obj.strftime("%B %Y")
    
    def inspect_data(self):
        self.load_data()
        
        print("\n=== DATA INSPECTION ===")
        print(f"\nShape: {self.historical_data.shape}")
        print(f"\nCore variables: {self.core_variables}")
        
        print(f"\nFirst few rows:")
        print(self.historical_data[self.core_variables].head())
        
        print(f"\nUnique grids: {self.historical_data['priogrid_gid'].nunique():,}")
        print(f"Unique months: {self.historical_data['month_id'].nunique()}")
        print(f"Date range: {self.historical_data['Year'].min()}-{self.historical_data['Year'].max()}")
        
        hist_min = int(self.historical_data['month_id'].min())
        hist_max = int(self.historical_data['month_id'].max())
        print(f"\nHistorical month_id range: {hist_min} - {hist_max}")
        print(f"  {hist_min} = {self.month_id_to_string(hist_min)}")
        print(f"  {hist_max} = {self.month_id_to_string(hist_max)}")
        
        print(f"\nRegional coverage:")
        print(f"Africa grids: {(self.historical_data['in_africa'] == 1).sum():,}")
        print(f"Middle East grids: {(self.historical_data['in_middle_east'] == 1).sum():,}")
        
        regional_grids = self._load_regional_grids()
        print(f"\nUnique regional grids: {len(regional_grids):,}")
        
        print("\n=== FORECAST DATA INSPECTION ===")
        print(f"\nForecast shape: {self.forecast_data.shape}")
        print(f"\nForecast columns: {self.forecast_data.columns.tolist()}")
        print(f"\nFirst few forecast rows:")
        print(self.forecast_data.head())
        
        print(f"\nForecast grids: {self.forecast_data['priogrid_gid'].nunique():,}")
        print(f"Forecast months (month_id): {sorted(self.forecast_data['month_id'].unique())}")
        
        print("\nForecast month mapping:")
        for month_id in sorted(self.forecast_data['month_id'].unique()):
            print(f"  {month_id} = {self.month_id_to_string(month_id)}")
        
        regional_forecast = self.forecast_data[self.forecast_data['priogrid_gid'].isin(regional_grids)]
        print(f"\nRegional forecast rows: {len(regional_forecast):,}")


if __name__ == "__main__":
    provider = GridDataProvider()
    provider.inspect_data()