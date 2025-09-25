from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from typing import Optional, Dict, List
from base_module import OutputModule

class CovariateDistributionModule(OutputModule):
    def __init__(self):
        # Removed military expenditure variables
        self.covariate_columns = [
            'wdi_sp_dyn_imrt_in',
            'vdem_v2x_ex_military'
        ]
        self.covariate_labels = {
            'wdi_sp_dyn_imrt_in': 'Infant Mortality Rate',
            'vdem_v2x_ex_military': 'Military Executive Power'
        }
        self.colors = ['red', 'blue']
    
    def get_context(self) -> str:
        return """This figure shows where the target country sits within the regional distribution for key covariates. Each colored curve represents the probability density of a covariate across all countries, with the target country's position marked by a vertical line."""
    
    def _normalize_data(self, data: pd.DataFrame) -> Dict[str, np.ndarray]:
        normalized = {}
        for col in self.covariate_columns:
            if col in data.columns:
                values = data[col].dropna()
                if len(values) > 0:
                    normalized[col] = (values - values.mean()) / values.std()
        return normalized
    
    def _get_percentile(self, value: float, distribution: np.ndarray) -> float:
        return stats.percentileofscore(distribution, value)
    
    def generate_content(self, country_code: str, forecast_data: pd.DataFrame, 
                        historical_data: pd.DataFrame, output_dir: Path) -> Optional[Path]:
        
        from data_provider import DataProvider
        data_provider = DataProvider()
        
        covariate_data = data_provider.get_covariate_data()
        country_covariates = data_provider.get_country_covariates(country_code)
        
        if country_covariates is None:
            return None
        
        country_name = data_provider.get_country_name(country_code)
        
        normalized_data = self._normalize_data(covariate_data)
        
        if not normalized_data:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        for i, col in enumerate(self.covariate_columns):
            if col in normalized_data and col in country_covariates:
                distribution = normalized_data[col]
                
                country_value = country_covariates[col]
                if pd.isna(country_value):
                    continue
                    
                col_data = covariate_data[col].dropna()
                normalized_country_value = (country_value - col_data.mean()) / col_data.std()
                
                kde = stats.gaussian_kde(distribution)
                x_range = np.linspace(distribution.min() - 1, distribution.max() + 1, 200)
                density = kde(x_range)
                
                color = self.colors[i % len(self.colors)]
                label = self.covariate_labels[col]
                
                ax.plot(x_range, density, color=color, alpha=0.7, linewidth=2, label=label)
                
                country_density = kde(normalized_country_value)
                ax.axvline(normalized_country_value, color=color, linestyle='--', alpha=0.8)
                ax.plot(normalized_country_value, country_density, 'o', color=color, 
                       markersize=8, markeredgecolor='black', markeredgewidth=1)
                
                percentile = self._get_percentile(country_value, col_data)
                ax.text(normalized_country_value, country_density + 0.02, 
                       f'{percentile:.0f}%', ha='center', va='bottom', 
                       fontsize=9, color=color, weight='bold')
        
        ax.set_xlabel('Standardized Values (Z-scores)', fontsize=12)
        ax.set_ylabel('Probability Density', fontsize=12)
        ax.set_title(f'{country_name} - Covariate Distributions', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right')
        
        plt.tight_layout()
        
        img_path = output_dir / f"covariate_distribution_{country_code}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, country_code: str, forecast_data: pd.DataFrame, 
                          historical_data: pd.DataFrame) -> str:
        from data_provider import DataProvider
        data_provider = DataProvider()
        
        covariate_data = data_provider.get_covariate_data()
        country_covariates = data_provider.get_country_covariates(country_code)
        
        if country_covariates is None:
            return "No covariate data available for this country."
        
        interpretations = []
        
        for col in self.covariate_columns:
            if col in country_covariates and col in covariate_data.columns:
                country_value = country_covariates[col]
                if pd.isna(country_value):
                    continue
                
                col_data = covariate_data[col].dropna()
                percentile = self._get_percentile(country_value, col_data)
                label = self.covariate_labels[col]
                
                if percentile >= 80:
                    position = "very high"
                elif percentile >= 60:
                    position = "high"
                elif percentile >= 40:
                    position = "moderate"
                elif percentile >= 20:
                    position = "low"
                else:
                    position = "very low"
                
                interpretations.append(f"{label}: {position} ({percentile:.0f}th percentile)")
        
        if interpretations:
            return "Country profile: " + "; ".join(interpretations) + "."
        else:
            return "Insufficient covariate data available for interpretation."