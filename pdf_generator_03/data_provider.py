from pathlib import Path
import pandas as pd
import json
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime

class DataProvider:
    def __init__(self):
        self.forecast_path = Path(r"C:\Users\spatt\Desktop\FAST\data\FAST-Forecast-2025-09-23.parquet")
        self.historical_path = Path(r"C:\Users\spatt\Desktop\FAST\data\violence_cm_updated.xlsx")
        self.covariate_path = Path(r"C:\Users\spatt\Desktop\FAST\data\cy_covariates.json")
        self.forecast_data = None
        self.historical_data = None
        self.covariate_data = None
        self.regional_countries = None
    
    def _load_regional_countries(self) -> Set[str]:
        """Load and cache the set of Africa & Middle East country codes"""
        if self.regional_countries is not None:
            return self.regional_countries
        
        if self.historical_data is None:
            self.load_data()
        
        # Check for required columns
        required_cols = ['in_africa', 'in_middle_east', 'isoab']
        missing_cols = [col for col in required_cols if col not in self.historical_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required regional columns in historical data: {missing_cols}")
        
        # Get countries where in_africa == 1 OR in_middle_east == 1
        regional_mask = (self.historical_data['in_africa'] == 1) | (self.historical_data['in_middle_east'] == 1)
        regional_countries = set(self.historical_data[regional_mask]['isoab'].unique())
        
        if not regional_countries:
            raise ValueError("No countries found in Africa or Middle East regions")
        
        self.regional_countries = regional_countries
        return self.regional_countries
    
    def _validate_regional_country(self, country_code: str) -> None:
        """Validate that a country is in Africa or Middle East"""
        regional_countries = self._load_regional_countries()
        if country_code not in regional_countries:
            raise ValueError(f"Country {country_code} is not in Africa or Middle East regions. Only Africa/Middle East countries are supported.")
    
    def load_data(self):
        if self.forecast_data is None:
            self.forecast_data = pd.read_parquet(self.forecast_path)
            if 'dates' in self.forecast_data.columns:
                self.forecast_data['dates'] = pd.to_datetime(self.forecast_data['dates'])
        if self.historical_data is None:
            self.historical_data = pd.read_excel(self.historical_path)
            self.historical_data['total_fatalities'] = self.historical_data['ged_sb']
    
    def load_covariate_data(self):
        if self.covariate_data is None:
            with open(self.covariate_path, 'r') as f:
                covariate_list = json.load(f)
            self.covariate_data = pd.DataFrame(covariate_list)
    
    def get_forecast_data(self) -> pd.DataFrame:
        self.load_data()
        # Filter to regional countries only
        regional_countries = self._load_regional_countries()
        return self.forecast_data[self.forecast_data['isoab'].isin(regional_countries)].copy()
    
    def get_historical_data(self) -> pd.DataFrame:
        self.load_data()
        # Filter to regional countries only
        regional_countries = self._load_regional_countries()
        return self.historical_data[self.historical_data['isoab'].isin(regional_countries)].copy()
    
    def get_covariate_data(self) -> pd.DataFrame:
        self.load_covariate_data()
        # Filter to regional countries only
        regional_countries = self._load_regional_countries()
        return self.covariate_data[self.covariate_data['isoab.x'].isin(regional_countries)].copy()
    
    def get_country_covariates(self, country_code: str) -> Optional[Dict[str, Any]]:
        self._validate_regional_country(country_code)
        self.load_covariate_data()
        country_match = self.covariate_data[self.covariate_data['isoab.x'] == country_code]
        if not country_match.empty:
            return country_match.iloc[0].to_dict()
        return None
    
    def get_country_name(self, country_code: str) -> str:
        self._validate_regional_country(country_code)
        self.load_data()
        
        # Try forecast data first (using isoab)
        forecast_match = self.forecast_data[self.forecast_data['isoab'] == country_code]
        if not forecast_match.empty:
            return forecast_match['name'].iloc[0]
        
        # Try historical data (using isoab)
        historical_match = self.historical_data[self.historical_data['isoab'] == country_code]
        if not historical_match.empty:
            return historical_match['name'].iloc[0]
        
        return country_code
    
    def get_monthly_forecast_distribution(self, month: int, year: int) -> pd.DataFrame:
        # This will automatically be filtered to regional countries via get_forecast_data()
        forecast_data = self.get_forecast_data()
        
        # Filter forecast data by year and month
        month_data = forecast_data[
            (forecast_data['dates'].dt.year == year) &
            (forecast_data['dates'].dt.month == month)
        ].copy()
        
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
        self._validate_regional_country(country_code)
        month_data = self.get_monthly_forecast_distribution(month, year)
        target_country = month_data[month_data['isoab'] == country_code]
        
        if target_country.empty:
            return "Unknown", "Unknown"
        
        target_row = target_country.iloc[0]
        risk_category = self.categorize_probability(target_row['outcome_p'])
        intensity_category = self.categorize_intensity(target_row['predicted'])
        
        return risk_category, intensity_category
    
    def get_cohort_countries(self, risk_category: str, intensity_category: str, month: int, year: int) -> List[str]:
        # This will automatically be filtered to regional countries
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
        # "Global" averages are now regional averages (Africa & Middle East only)
        historical_data = self.get_historical_data()
        forecast_data = self.get_forecast_data()
        
        averages = {}
        
        # Historical averages - get ALL months for past 5 years (regional countries only)
        historical_points = {}
        for year in range(2020, 2026):
            for month in range(1, 13):
                if year == 2025 and month >= 9:
                    continue
                    
                date_key = f"{year}-{month:02d}"
                
                # Get historical data for this month/year (already filtered to regional)
                month_year_data = historical_data[
                    (historical_data['Year'] == year) & 
                    (historical_data['Month'] == month)
                ].copy()
                
                if not month_year_data.empty:
                    # Average across all regional countries for this time period
                    avg_fatalities = month_year_data.groupby('isoab')['total_fatalities'].sum().mean()
                    historical_points[date_key] = avg_fatalities
                else:
                    historical_points[date_key] = 0.0
        
        # Forecast averages - derive from dates field (already filtered to regional)
        forecast_points = {}
        unique_dates = forecast_data['dates'].unique()
        
        for date in unique_dates:
            if pd.isna(date):
                continue
            date_obj = pd.Timestamp(date)
            date_key = f"{date_obj.year}-{date_obj.month:02d}"
            month_data = forecast_data[forecast_data['dates'] == date]
            if not month_data.empty:
                avg_predicted = month_data['predicted'].mean()
                forecast_points[date_key] = avg_predicted
        
        averages.update(historical_points)
        averages.update(forecast_points)
        return averages
    
    def get_cohort_monthly_averages(self, cohort_countries: List[str], target_month: int, target_year: int) -> Dict[str, float]:
        if not cohort_countries:
            return {}
        
        # Validate all cohort countries are regional
        for country in cohort_countries:
            self._validate_regional_country(country)
        
        historical_data = self.get_historical_data()
        forecast_data = self.get_forecast_data()
        averages = {}
        
        # Historical averages for cohort - ALL months
        historical_points = {}
        for year in range(2020, 2026):
            for month in range(1, 13):
                if year == 2025 and month >= 9:
                    continue
                
                date_key = f"{year}-{month:02d}"
                
                # Get data for cohort countries only (already filtered to regional)
                cohort_data = historical_data[
                    (historical_data['Year'] == year) & 
                    (historical_data['Month'] == month) &
                    (historical_data['isoab'].isin(cohort_countries))
                ].copy()
                
                if not cohort_data.empty:
                    # Average across cohort countries for this time period
                    avg_fatalities = cohort_data.groupby('isoab')['total_fatalities'].sum().mean()
                    historical_points[date_key] = avg_fatalities
                else:
                    historical_points[date_key] = 0.0
        
        # Forecast averages for cohort (already filtered to regional)
        forecast_points = {}
        unique_dates = forecast_data['dates'].unique()
        
        for date in unique_dates:
            if pd.isna(date):
                continue
            date_obj = pd.Timestamp(date)
            date_key = f"{date_obj.year}-{date_obj.month:02d}"
            cohort_forecast_data = forecast_data[
                (forecast_data['dates'] == date) &
                (forecast_data['isoab'].isin(cohort_countries))
            ]
            if not cohort_forecast_data.empty:
                avg_predicted = cohort_forecast_data['predicted'].mean()
                forecast_points[date_key] = avg_predicted
            else:
                forecast_points[date_key] = 0.0
        
        averages.update(historical_points)
        averages.update(forecast_points)
        return averages