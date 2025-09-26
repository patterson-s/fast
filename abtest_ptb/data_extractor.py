import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any

sys.path.append(str(Path(__file__).parent.parent / "pdf_generator_03"))
from data_provider import DataProvider

class DataExtractor:
    def __init__(self):
        self.data_provider = DataProvider()
        self.month_names = {12: "December", 3: "March", 9: "September"}
    
    def extract_template_data(self, country_code: str, target_month: int, target_year: int) -> Dict[str, Any]:
        forecast_data = self.data_provider.get_forecast_data()
        historical_data = self.data_provider.get_historical_data()
        
        country_name = self.data_provider.get_country_name(country_code)
        month_name = self.month_names[target_month].lower()
        
        month_data = self.data_provider.get_monthly_forecast_distribution(target_month, target_year)
        target_country = month_data[month_data['isoab'] == country_code]
        
        if target_country.empty:
            raise ValueError(f"No data for country {country_code} in {target_month}/{target_year}")
        
        target_row = target_country.iloc[0]
        probability = target_row['outcome_p']
        predicted_fatalities = target_row['predicted']
        
        risk_category = self.data_provider.categorize_probability(probability)
        intensity_category = self.data_provider.categorize_intensity(predicted_fatalities)
        
        prob_percentile = (month_data['outcome_p'] <= probability).mean() * 100
        pred_percentile = (month_data['predicted'] <= predicted_fatalities).mean() * 100
        
        cohort_countries = self.data_provider.get_cohort_countries(
            risk_category, intensity_category, target_month, target_year
        )
        
        example_cohorts = [c for c in cohort_countries if c != country_code][:3]
        
        if len(example_cohorts) < 3:
            similarity_label = "most similar" if example_cohorts else "generally similar"
            
            all_countries = month_data[month_data['isoab'] != country_code].copy()
            all_countries['distance'] = abs(all_countries['predicted'] - predicted_fatalities)
            all_countries = all_countries.sort_values('distance')
            
            remaining = all_countries[~all_countries['isoab'].isin(example_cohorts)]
            
            needed = 3 - len(example_cohorts)
            fallback_countries = remaining['isoab'].head(needed).tolist()
            
            example_cohorts.extend(fallback_countries)
        else:
            similarity_label = "most similar"
        
        example_cohort_names = [self.data_provider.get_country_name(c) for c in example_cohorts]
        
        historical_points = self._get_historical_monthly_data(historical_data, country_code, target_month)
        
        historical_avg = sum(historical_points) / len(historical_points) if historical_points else 0
        
        trend_slope = 0
        if len(historical_points) >= 3:
            years = list(range(len(historical_points)))
            trend_slope = np.polyfit(years, historical_points, 1)[0]
        
        country_covariates = self.data_provider.get_country_covariates(country_code)
        covariate_data = self.data_provider.get_covariate_data()
        
        covariate_analysis = {}
        if country_covariates:
            covariate_columns = [
                'wdi_sp_dyn_imrt_in',
                'vdem_v2x_ex_military'
            ]
            
            for col in covariate_columns:
                if col in country_covariates and col in covariate_data.columns:
                    country_value = country_covariates[col]
                    if not pd.isna(country_value):
                        col_data = covariate_data[col].dropna()
                        percentile = (col_data <= country_value).mean() * 100
                        covariate_analysis[col] = {
                            'value': country_value,
                            'percentile': percentile
                        }
        
        trend_desc = self._get_trend_description(trend_slope)
        forecast_vs_historical = self._get_forecast_comparison(predicted_fatalities, historical_avg)
        covariate_desc = self._get_covariate_description(covariate_analysis)
        
        cohort_prefix = f"{similarity_label} countries" if similarity_label == "generally similar" else "comparable countries"
        
        return {
            'country': country_name,
            'country_code': country_code,
            'country_upper': country_name.upper(),
            'month': month_name,
            'month_title': month_name.title(),
            'month_title_lower': month_name.lower(),
            'year': target_year,
            'probability': probability,
            'probability_percent': f"{probability:.1%}",
            'predicted_fatalities': f"{predicted_fatalities:.1f}",
            'risk_category': risk_category,
            'intensity_category': intensity_category,
            'prob_percentile': f"{prob_percentile:.0f}",
            'pred_percentile': f"{pred_percentile:.0f}",
            'example_cohorts': example_cohort_names,
            'cohort_str': ", ".join(example_cohort_names[:2]) if example_cohort_names else "similar countries",
            'similarity_label': similarity_label,
            'cohort_prefix': cohort_prefix,
            'historical_avg': f"{historical_avg:.1f}",
            'trend_slope': trend_slope,
            'trend_desc': trend_desc,
            'forecast_vs_historical': forecast_vs_historical,
            'covariate_analysis': covariate_analysis,
            'covariate_desc': covariate_desc
        }
    
    def _get_historical_monthly_data(self, historical_data: pd.DataFrame, country_code: str, target_month: int) -> list[float]:
        country_historical = historical_data[historical_data['isoab'] == country_code].copy()
        
        if country_historical.empty:
            return []
        
        values = []
        for year in range(2020, 2026):
            for month in range(1, 13):
                if year == 2025 and month >= 9:
                    break
                
                year_month_data = country_historical[
                    (country_historical['Year'] == year) & 
                    (country_historical['Month'] == month)
                ]
                
                if not year_month_data.empty:
                    fatalities = year_month_data['total_fatalities'].sum()
                    values.append(fatalities)
                else:
                    values.append(0)
        
        return values
    
    def _get_trend_description(self, trend_slope: float) -> str:
        if abs(trend_slope) > 5:
            if trend_slope > 0:
                return f"increasing (slope: +{trend_slope:.1f} fatalities/month)"
            else:
                return f"decreasing (slope: {trend_slope:.1f} fatalities/month)"
        else:
            return "relatively stable"
    
    def _get_forecast_comparison(self, predicted: float, historical_avg: float) -> str:
        if historical_avg == 0:
            return "higher than"
        
        ratio = predicted / historical_avg
        if ratio > 1.1:
            return "higher than"
        elif ratio < 0.9:
            return "lower than"
        else:
            return "consistent with"
    
    def _get_covariate_description(self, covariate_analysis: Dict[str, Dict[str, float]]) -> str:
        covariate_labels = {
            'wdi_sp_dyn_imrt_in': 'infant mortality',
            'vdem_v2x_ex_military': 'military executive power'
        }
        
        descriptions = []
        for col, label in covariate_labels.items():
            if col in covariate_analysis:
                percentile = covariate_analysis[col]['percentile']
                if percentile >= 80:
                    level = "much higher than average"
                elif percentile >= 60:
                    level = "higher than average"
                elif percentile <= 20:
                    level = "much lower than average"
                elif percentile <= 40:
                    level = "lower than average"
                else:
                    level = "about average"
                descriptions.append(f"{label} is {level}")
        
        return '; '.join(descriptions) if descriptions else 'limited covariate data available'

if __name__ == "__main__":
    extractor = DataExtractor()
    
    test_cases = [
        ("NGA", 9, 2026),
        ("NER", 9, 2026),
        ("ETH", 12, 2025)
    ]
    
    for country_code, month, year in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {country_code} - {month}/{year}")
        print('='*60)
        
        try:
            data = extractor.extract_template_data(country_code, month, year)
            print(f"Country: {data['country']}")
            print(f"Probability: {data['probability_percent']}")
            print(f"Predicted: {data['predicted_fatalities']}")
            print(f"Risk: {data['risk_category']}")
            print(f"Cohort ({data['similarity_label']}): {data['cohort_str']}")
            print(f"Historical avg: {data['historical_avg']}")
            print(f"Trend: {data['trend_desc']}")
            print(f"Forecast vs historical: {data['forecast_vs_historical']}")
            print(f"Covariates: {data['covariate_desc']}")
        except Exception as e:
            print(f"ERROR: {e}")