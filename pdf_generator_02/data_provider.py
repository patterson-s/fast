from pathlib import Path
import pandas as pd
import json
from typing import Dict, Any, Optional, List, Tuple

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
    
    def get_risk_intensity_category(self, country_code: str, month: int, year: int) -> Tuple[str, str]:
        month_data = self.get_monthly_forecast_distribution(month, year)
        target_country = month_data[month_data['isoab'] == country_code]
        
        if target_country.empty:
            return "Unknown", "Unknown"
        
        target_row = target_country.iloc[0]
        risk_category = self.categorize_probability(target_row['outcome_p'])
        intensity_category = self.categorize_intensity(target_row['predicted'])
        
        return risk_category, intensity_category
    
    def get_cohort_countries(self, risk_category: str, intensity_category: str, month: int, year: int) -> List[str]:
        month_data = self.get_monthly_forecast_distribution(month, year)
        
        if month_data.empty:
            return []
        
        month_data['risk_category'] = month_data['outcome_p'].apply(self.categorize_probability)
        month_data['intensity_category'] = month_data['predicted'].apply(self.categorize_intensity)
        
        cohort_data = month_data[
            (month_data['risk_category'] == risk_category) & 
            (month_data['intensity_category'] == intensity_category)
        ]
        
        return cohort_data['isoab'].tolist()
    
    def get_global_monthly_averages(self, target_month: int, target_year: int) -> Dict[str, float]:
        self.load_data()
        
        averages = {}
        
        # Historical averages
        historical_points = {}
        for year in range(target_year - 5, target_year + 1):
            for month in [12, 3, 9]:  # Dec, Mar, Sep
                if year == 2025 and month == 9:  # Sept 2025 - no data
                    continue
                if year == 2025 and month > 12:  # Future months in 2025
                    continue
                if year > 2025:  # All of 2026+ is future
                    continue
                
                date_key = f"{year}-{month:02d}"
                
                # Calculate total fatalities for all countries in this month/year
                month_year_data = self.historical_data[
                    (self.historical_data['year'] == year) & 
                    (self.historical_data['month'] == month)
                ].copy()
                
                if not month_year_data.empty:
                    month_year_data['total_fatalities'] = (
                        month_year_data['ucdp_ged_ns_best_sum'] + 
                        month_year_data['ucdp_ged_sb_best_sum'] + 
                        month_year_data['ucdp_ged_os_best_sum']
                    )
                    # Average across all countries for this time period
                    avg_fatalities = month_year_data.groupby('isoab')['total_fatalities'].sum().mean()
                    historical_points[date_key] = avg_fatalities
                else:
                    historical_points[date_key] = 0.0
        
        # Forecast averages
        month_mappings = {
            12: (552, "2025-12"),  # Dec 2025
            3: (555, "2026-03"),   # Mar 2026  
            9: (561, "2026-09")    # Sep 2026
        }
        
        forecast_points = {}
        for month, (outcome_n, date_key) in month_mappings.items():
            month_data = self.forecast_data[self.forecast_data['outcome_n'] == outcome_n]
            if not month_data.empty:
                avg_predicted = month_data['predicted'].mean()
                forecast_points[date_key] = avg_predicted
            else:
                forecast_points[date_key] = 0.0
        
        averages.update(historical_points)
        averages.update(forecast_points)
        return averages
    
    def get_cohort_monthly_averages(self, cohort_countries: List[str], target_month: int, target_year: int) -> Dict[str, float]:
        if not cohort_countries:
            return {}
        
        self.load_data()
        averages = {}
        
        # Historical averages for cohort
        historical_points = {}
        for year in range(target_year - 5, target_year + 1):
            for month in [12, 3, 9]:  # Dec, Mar, Sep
                if year == 2025 and month == 9:  # Sept 2025 - no data
                    continue
                if year == 2025 and month > 12:  # Future months in 2025
                    continue
                if year > 2025:  # All of 2026+ is future
                    continue
                
                date_key = f"{year}-{month:02d}"
                
                # Get data for cohort countries only
                cohort_data = self.historical_data[
                    (self.historical_data['year'] == year) & 
                    (self.historical_data['month'] == month) &
                    (self.historical_data['isoab'].isin(cohort_countries))
                ].copy()
                
                if not cohort_data.empty:
                    cohort_data['total_fatalities'] = (
                        cohort_data['ucdp_ged_ns_best_sum'] + 
                        cohort_data['ucdp_ged_sb_best_sum'] + 
                        cohort_data['ucdp_ged_os_best_sum']
                    )
                    # Average across cohort countries for this time period
                    avg_fatalities = cohort_data.groupby('isoab')['total_fatalities'].sum().mean()
                    historical_points[date_key] = avg_fatalities
                else:
                    historical_points[date_key] = 0.0
        
        # Forecast averages for cohort
        month_mappings = {
            12: (552, "2025-12"),  # Dec 2025
            3: (555, "2026-03"),   # Mar 2026  
            9: (561, "2026-09")    # Sep 2026
        }
        
        forecast_points = {}
        for month, (outcome_n, date_key) in month_mappings.items():
            cohort_forecast_data = self.forecast_data[
                (self.forecast_data['outcome_n'] == outcome_n) &
                (self.forecast_data['isoab'].isin(cohort_countries))
            ]
            if not cohort_forecast_data.empty:
                avg_predicted = cohort_forecast_data['predicted'].mean()
                forecast_points[date_key] = avg_predicted
            else:
                forecast_points[date_key] = 0.0
        
        averages.update(historical_points)
        averages.update(forecast_points)
        return averages