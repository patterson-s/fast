from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional
from base_module import OutputModule

class SymlogModule(OutputModule):
    def __init__(self, target_month: int, target_year: int):
        self.target_month = target_month
        self.target_year = target_year
        self.month_names = {12: "December", 3: "March", 9: "September"}
        self.prob_colors = {
            "Near-certain no conflict": "lightblue",
            "Improbable conflict": "yellow", 
            "Probable conflict": "orange",
            "Near-certain conflict": "red"
        }
        
    def get_context(self) -> str:
        month_name = self.month_names[self.target_month]
        return f"""This figure shows the global distribution of conflict forecasts for {month_name} {self.target_year}, with countries positioned by their probability of experiencing ≥25 fatalities (x-axis) and predicted fatalities (y-axis, symlog scale). The target country is highlighted with a prominent marker."""
    
    def generate_content(self, country_code: str, forecast_data: pd.DataFrame, 
                        historical_data: pd.DataFrame, output_dir: Path) -> Optional[Path]:
        
        from data_provider import DataProvider
        data_provider = DataProvider()
        
        month_data = data_provider.get_monthly_forecast_distribution(self.target_month, self.target_year)
        
        if month_data.empty:
            return None
        
        month_data['prob_category'] = month_data['outcome_p'].apply(data_provider.categorize_probability)
        
        target_country = month_data[month_data['isoab'] == country_code]
        country_name = data_provider.get_country_name(country_code)
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        for category, color in self.prob_colors.items():
            category_data = month_data[month_data['prob_category'] == category]
            ax.scatter(category_data['outcome_p'], category_data['predicted'], 
                       alpha=0.7, s=30, color=color, edgecolor='gray', linewidth=0.5)
        
        if not target_country.empty:
            target_row = target_country.iloc[0]
            ax.scatter(target_row['outcome_p'], target_row['predicted'], 
                       s=120, color='darkred', edgecolor='black', linewidth=3, 
                       zorder=10, marker='o')
            
            ax.annotate(f"{country_name}", 
                        (target_row['outcome_p'], target_row['predicted']),
                        xytext=(15, 15), textcoords='offset points',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9, edgecolor='black'),
                        fontsize=11, ha='left', fontweight='bold', zorder=11)
        
        ax.set_yscale('symlog', linthresh=1)
        ax.set_ylim(-0.5, 12000)
        
        prob_boundaries = [0.01, 0.50, 0.99]
        prob_labels = ["1%", "50%", "99%"]
        for boundary, label in zip(prob_boundaries, prob_labels):
            ax.axvline(x=boundary, color='blue', linestyle='--', alpha=0.7, linewidth=1)
            ax.text(boundary, 10000, label, rotation=90, 
                    verticalalignment='top', horizontalalignment='right', 
                    color='blue', fontsize=9)
        
        intensity_boundaries = [1, 10, 100, 1000, 10000]
        intensity_labels = ["1", "10", "100", "1,000", "10,000"]
        for boundary, label in zip(intensity_boundaries, intensity_labels):
            ax.axhline(y=boundary, color='green', linestyle='--', alpha=0.7, linewidth=1)
            ax.text(ax.get_xlim()[1] * 0.95, boundary, label, 
                    verticalalignment='bottom', horizontalalignment='right', 
                    color='green', fontsize=9)
        
        ax.set_xlabel('Probability of ≥25 Fatalities', fontsize=12)
        ax.set_ylabel('Predicted Fatalities (Symlog Scale)', fontsize=12)
        ax.set_xlim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        
        month_name = self.month_names[self.target_month]
        ax.set_title(f'Conflict Forecast Distribution - {month_name} {self.target_year}', fontsize=14, pad=20)
        
        plt.tight_layout()
        
        img_path = output_dir / f"symlog_distribution_{country_code}_{self.target_month}_{self.target_year}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, country_code: str, forecast_data: pd.DataFrame, 
                          historical_data: pd.DataFrame) -> str:
        from data_provider import DataProvider
        data_provider = DataProvider()
        
        month_data = data_provider.get_monthly_forecast_distribution(self.target_month, self.target_year)
        target_country = month_data[month_data['isoab'] == country_code]
        
        if target_country.empty:
            return "No forecast data available for this country."
        
        target_row = target_country.iloc[0]
        target_prob = target_row['outcome_p']
        target_predicted = target_row['predicted']
        country_name = data_provider.get_country_name(country_code)
        
        prob_percentile = (month_data['outcome_p'] <= target_prob).mean() * 100
        pred_percentile = (month_data['predicted'] <= target_predicted).mean() * 100
        
        prob_category = data_provider.categorize_probability(target_prob)
        pred_category = data_provider.categorize_intensity(target_predicted)
        
        month_name = self.month_names[self.target_month]
        
        return f"""For {month_name} {self.target_year}, {country_name} is forecasted with {target_prob:.3f} probability of ≥25 fatalities ({prob_percentile:.0f}th percentile) and {target_predicted:.1f} predicted fatalities ({pred_percentile:.0f}th percentile). Risk category: {prob_category}; Intensity category: {pred_category}."""