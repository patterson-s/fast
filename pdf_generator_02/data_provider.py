from pathlib import Path
import pandas as pd
import json
from typing import Dict, Any, Optional

class DataProvider:
    def __init__(self):
        self.forecast_path = Path(r"C:\Users\spatt\Desktop\FAST\data\FAST-Forecast.parquet")
        self.historical_path = Path(r"C:\Users\spatt\Desktop\FAST\analysis\views_px_fatalities002_cm_ALL_20150101_20251201.csv")
        self.covariate_path = Path(r"C:\Users\spatt\Desktop\FAST\data\cy_covariates.json")
        self.forecast_data = None
        self.historical_data = None
        self.covariate_data = None
    
    def load_data(self):
        if self.forecast_data is None:
            self.forecast_data = pd.read_parquet(self.forecast_path)
        if self.historical_data is None:
            self.historical_data = pd.read_csv(self.historical_path)
    
    def load_covariate_data(self):
        if self.covariate_data is None:
            with open(self.covariate_path, 'r') as f:
                covariate_list = json.load(f)
            self.covariate_data = pd.DataFrame(covariate_list)
    
    def get_forecast_data(self) -> pd.DataFrame:
        self.load_data()
        return self.forecast_data
    
    def get_historical_data(self) -> pd.DataFrame:
        self.load_data()
        return self.historical_data
    
    def get_covariate_data(self) -> pd.DataFrame:
        self.load_covariate_data()
        return self.covariate_data
    
    def get_country_covariates(self, country_code: str) -> Optional[Dict[str, Any]]:
        self.load_covariate_data()
        country_match = self.covariate_data[self.covariate_data['isoab.x'] == country_code]
        if not country_match.empty:
            return country_match.iloc[0].to_dict()
        return None
    
    def get_country_name(self, country_code: str) -> str:
        self.load_data()
        forecast_match = self.forecast_data[self.forecast_data['isoab'] == country_code]
        if not forecast_match.empty:
            return forecast_match['name'].iloc[0]
        
        historical_match = self.historical_data[self.historical_data['isoab'] == country_code]
        if not historical_match.empty:
            return historical_match['name'].iloc[0]
        
        return country_code
    
    def get_monthly_forecast_distribution(self, month: int, year: int) -> pd.DataFrame:
        self.load_data()
        
        month_mappings = {
            (12, 2025): 552,  # Dec 2025
            (3, 2026): 555,   # Mar 2026  
            (9, 2026): 561    # Sep 2026
        }
        
        outcome_n = month_mappings.get((month, year))
        if outcome_n is None:
            return pd.DataFrame()
        
        month_data = self.forecast_data[self.forecast_data['outcome_n'] == outcome_n].copy()
        return month_data
    
    def categorize_probability(self, prob: float) -> str:
        if prob <= 0.01:
            return "Near-certain no conflict"
        elif prob <= 0.50:
            return "Improbable conflict"
        elif prob <= 0.99:
            return "Probable conflict"
        else:
            return "Near-certain conflict"
    
    def categorize_intensity(self, predicted: float) -> str:
        if predicted == 0:
            return "0"
        elif predicted <= 10:
            return "1-10"
        elif predicted <= 100:
            return "11-100"
        elif predicted <= 1000:
            return "101-1,000"
        elif predicted <= 10000:
            return "1,001-10,000"
        else:
            return "10,001+"