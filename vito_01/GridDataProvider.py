from pathlib import Path
import pandas as pd
from typing import Set, Tuple, Optional
from datetime import datetime

class GridDataProvider:
    def __init__(self):
        self.pgm_path = Path(r"C:\Users\spatt\Desktop\FAST\data\pgm_data.parquet")
        self.baseline_path = Path(r"C:\Users\spatt\Desktop\FAST\data\dorazio_base.parquet")
        self.climate_path = Path(r"C:\Users\spatt\Desktop\FAST\data\dorazio_climate.parquet")
        self.historical_data = None
        self.baseline_forecast = None
        self.climate_forecast = None
        self.regional_grids = None
        self.grid_country_map = None
        
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
    
    def _build_grid_country_map(self) -> dict:
        if self.grid_country_map is not None:
            return self.grid_country_map
        
        if self.historical_data is None:
            self.load_data()
        
        grid_country = self.historical_data[['priogrid_gid', 'name']].drop_duplicates('priogrid_gid')
        self.grid_country_map = dict(zip(grid_country['priogrid_gid'].astype(int), grid_country['name']))
        
        return self.grid_country_map
    
    def get_country_name(self, priogrid_gid: int) -> Optional[str]:
        country_map = self._build_grid_country_map()
        return country_map.get(priogrid_gid)
    
    def load_data(self):
        if self.historical_data is None:
            print(f"Loading {self.pgm_path.name}...")
            self.historical_data = pd.read_parquet(self.pgm_path)
            print(f"Loaded {len(self.historical_data):,} rows")
        
        if self.baseline_forecast is None:
            print(f"Loading {self.baseline_path.name}...")
            self.baseline_forecast = pd.read_parquet(self.baseline_path)
            print(f"Loaded {len(self.baseline_forecast):,} baseline forecast rows")
        
        if self.climate_forecast is None:
            print(f"Loading {self.climate_path.name}...")
            self.climate_forecast = pd.read_parquet(self.climate_path)
            print(f"Loaded {len(self.climate_forecast):,} climate forecast rows")
    
    def get_historical_data(self) -> pd.DataFrame:
        self.load_data()
        regional_grids = self._load_regional_grids()
        return self.historical_data[self.historical_data['priogrid_gid'].isin(regional_grids)].copy()
    
    def get_baseline_forecast(self) -> pd.DataFrame:
        self.load_data()
        regional_grids = self._load_regional_grids()
        return self.baseline_forecast[self.baseline_forecast['priogrid_gid'].isin(regional_grids)].copy()
    
    def get_climate_forecast(self) -> pd.DataFrame:
        self.load_data()
        regional_grids = self._load_regional_grids()
        return self.climate_forecast[self.climate_forecast['priogrid_gid'].isin(regional_grids)].copy()
    
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
        
        print("\n=== BASELINE FORECAST INSPECTION ===")
        print(f"\nBaseline shape: {self.baseline_forecast.shape}")
        print(f"\nBaseline columns: {self.baseline_forecast.columns.tolist()}")
        print(f"\nFirst few baseline rows:")
        print(self.baseline_forecast.head())
        
        print(f"\nBaseline grids: {self.baseline_forecast['priogrid_gid'].nunique():,}")
        print(f"Baseline months (month_id): {sorted(self.baseline_forecast['month_id'].unique())}")
        
        print("\nBaseline month mapping:")
        for month_id in sorted(self.baseline_forecast['month_id'].unique()):
            print(f"  {month_id} = {self.month_id_to_string(month_id)}")
        
        print("\n=== CLIMATE FORECAST INSPECTION ===")
        print(f"\nClimate shape: {self.climate_forecast.shape}")
        print(f"\nClimate columns: {self.climate_forecast.columns.tolist()}")
        print(f"\nFirst few climate rows:")
        print(self.climate_forecast.head())
        
        print(f"\nClimate grids: {self.climate_forecast['priogrid_gid'].nunique():,}")
        print(f"Climate months (month_id): {sorted(self.climate_forecast['month_id'].unique())}")
        
        print("\nClimate month mapping:")
        for month_id in sorted(self.climate_forecast['month_id'].unique()):
            print(f"  {month_id} = {self.month_id_to_string(month_id)}")
        
        regional_baseline = self.baseline_forecast[self.baseline_forecast['priogrid_gid'].isin(regional_grids)]
        regional_climate = self.climate_forecast[self.climate_forecast['priogrid_gid'].isin(regional_grids)]
        print(f"\nRegional baseline forecast rows: {len(regional_baseline):,}")
        print(f"Regional climate forecast rows: {len(regional_climate):,}")


if __name__ == "__main__":
    provider = GridDataProvider()
    provider.inspect_data()