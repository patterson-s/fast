import os
import cohere
import base64
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

class BLUFGenerator:
    def __init__(self, config_path: str = "config/llm_config.json"):
        self.config = self._load_config(config_path)
        
        api_key = os.getenv(self.config['api_key_env_var'])
        if not api_key:
            raise ValueError(f"{self.config['api_key_env_var']} environment variable not set")
        
        self.client = cohere.ClientV2(api_key)
        self.month_names = {12: "December", 3: "March", 9: "September"}
        
        self.prompt_template = self._load_prompt_template()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def _load_prompt_template(self) -> str:
        template_path = Path(self.config['prompt_template_path'])
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def extract_forecast_data(self, country_code: str, target_month: int, target_year: int, 
                            forecast_data, historical_data) -> Dict[str, Any]:
        from data_provider import DataProvider
        data_provider = DataProvider()
        
        country_name = data_provider.get_country_name(country_code)
        month_name = self.month_names[target_month].lower()
        
        month_data = data_provider.get_monthly_forecast_distribution(target_month, target_year)
        target_country = month_data[month_data['isoab'] == country_code]
        
        if target_country.empty:
            return {}
        
        target_row = target_country.iloc[0]
        probability = target_row['outcome_p']
        predicted_fatalities = target_row['predicted']
        
        risk_category = data_provider.categorize_probability(probability)
        intensity_category = data_provider.categorize_intensity(predicted_fatalities)
        
        prob_percentile = (month_data['outcome_p'] <= probability).mean() * 100
        pred_percentile = (month_data['predicted'] <= predicted_fatalities).mean() * 100
        
        cohort_countries = data_provider.get_cohort_countries(
            risk_category, intensity_category, target_month, target_year
        )
        
        example_cohorts = [c for c in cohort_countries if c != country_code][:3]
        example_cohort_names = [data_provider.get_country_name(c) for c in example_cohorts]
        
        from monthly_temporal_module import MonthlyTemporalModule
        temporal_module = MonthlyTemporalModule(target_month, target_year)
        historical_points = temporal_module._get_historical_monthly_data(historical_data, country_code)
        
        target_month_values = []
        for date_str, value in historical_points.items():
            year, month = date_str.split('-')
            if int(month) == target_month:
                target_month_values.append(value)
        
        historical_avg = sum(target_month_values) / len(target_month_values) if target_month_values else 0
        
        trend_slope = 0
        if len(target_month_values) >= 3:
            years = list(range(len(target_month_values)))
            trend_slope = np.polyfit(years, target_month_values, 1)[0]
        
        country_covariates = data_provider.get_country_covariates(country_code)
        covariate_data = data_provider.get_covariate_data()
        
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
        
        return {
            'country': country_name,
            'country_code': country_code,
            'month': month_name,
            'year': target_year,
            'probability': probability,
            'predicted_fatalities': predicted_fatalities,
            'risk_category': risk_category,
            'intensity_category': intensity_category,
            'prob_percentile': prob_percentile,
            'pred_percentile': pred_percentile,
            'example_cohorts': example_cohort_names,
            'historical_avg': historical_avg,
            'trend_slope': trend_slope,
            'covariate_analysis': covariate_analysis
        }
    
    def encode_image(self, image_path: Path) -> str:
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def create_prompt(self, data: Dict[str, Any]) -> str:
        if abs(data['trend_slope']) > 5:
            if data['trend_slope'] > 0:
                trend_desc = f"increasing (slope: +{data['trend_slope']:.1f} fatalities/year)"
            else:
                trend_desc = f"decreasing (slope: {data['trend_slope']:.1f} fatalities/year)"
        else:
            trend_desc = "relatively stable"
        
        ratio = data['predicted_fatalities'] / data['historical_avg'] if data['historical_avg'] > 0 else float('inf')
        if ratio > 1.5:
            forecast_vs_historical = "significantly higher than"
        elif ratio > 1.1:
            forecast_vs_historical = "moderately higher than"
        elif ratio < 0.5:
            forecast_vs_historical = "significantly lower than"
        elif ratio < 0.9:
            forecast_vs_historical = "moderately lower than"
        else:
            forecast_vs_historical = "in line with"
        
        covariate_desc = []
        covariate_labels = {
            'wdi_sp_dyn_imrt_in': 'infant mortality',
            'vdem_v2x_ex_military': 'military executive power'
        }
        
        for col, label in covariate_labels.items():
            if col in data['covariate_analysis']:
                percentile = data['covariate_analysis'][col]['percentile']
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
                covariate_desc.append(f"{label} is {level}")
        
        cohort_str = ", ".join(data['example_cohorts'][:2]) if data['example_cohorts'] else "similar countries"
        
        template_vars = {
            'country_upper': data['country'].upper(),
            'country': data['country'],
            'month_title': data['month'].title(),
            'month_title_lower': data['month'].lower(),
            'year': data['year'],
            'probability_percent': f"{data['probability']:.1%}",
            'prob_percentile': f"{data['prob_percentile']:.0f}",
            'predicted_fatalities': f"{data['predicted_fatalities']:.1f}",
            'pred_percentile': f"{data['pred_percentile']:.0f}",
            'risk_category': data['risk_category'],
            'cohort_str': cohort_str,
            'historical_avg': f"{data['historical_avg']:.1f}",
            'trend_desc': trend_desc,
            'forecast_vs_historical': forecast_vs_historical,
            'covariate_desc': '; '.join(covariate_desc) if covariate_desc else 'limited covariate data available'
        }
        
        return self.prompt_template.format(**template_vars)
    
    def _format_bluf(self, raw_bluf: str, data: Dict[str, Any]) -> str:
        sentences = []
        
        lines = raw_bluf.replace('\n\n', '\n').replace('\n', ' ').strip()
        
        import re
        sentence_list = re.split(r'(?<=\.)\s+(?=[A-Z])', lines)
        
        for sentence in sentence_list:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:
                sentences.append(sentence)
        
        single_paragraph = ' '.join(sentences)
        
        header = f"**BLUF Summary for {data['country']}, {data['month'].title()} {data['year']}:**"
        
        return f"{header}\n{single_paragraph}"
    
    def generate_bluf(self, country_code: str, target_month: int, target_year: int, 
                     forecast_data, historical_data, image_paths: Optional[List[Path]] = None) -> str:
        
        data = self.extract_forecast_data(country_code, target_month, target_year, 
                                        forecast_data, historical_data)
        
        if not data:
            return "Unable to generate BLUF: insufficient data available."
        
        prompt = self.create_prompt(data)
        
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            response = self.client.chat(
                model=self.config['model'],
                messages=messages,
                temperature=self.config['temperature']
            )
            
            if hasattr(response, 'message'):
                if hasattr(response.message, 'content') and isinstance(response.message.content, list):
                    raw_bluf = response.message.content[0].text
                else:
                    raw_bluf = str(response.message.content)
            else:
                raw_bluf = str(response)
            
            return self._format_bluf(raw_bluf, data)
            
        except Exception as e:
            print(f"Error generating BLUF: {e}")
            return f"Error generating BLUF summary: {str(e)}"
    
    def test_generation(self, country_code: str = "NGA", target_month: int = 9, target_year: int = 2026):
        from data_provider import DataProvider
        
        data_provider = DataProvider()
        forecast_data = data_provider.get_forecast_data()
        historical_data = data_provider.get_historical_data()
        
        bluf = self.generate_bluf(country_code, target_month, target_year, 
                                forecast_data, historical_data)
        
        print(f"BLUF for {country_code} {target_month}/{target_year}:")
        print("=" * 50)
        print(bluf)
        return bluf

if __name__ == "__main__":
    generator = BLUFGenerator()
    generator.test_generation("NER", 9, 2026)