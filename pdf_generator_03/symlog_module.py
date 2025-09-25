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
        return f"""This figure shows the regional distribution of conflict forecasts for {month_name} {self.target_year}, with countries positioned by their probability of experiencing ≥25 fatalities (x-axis) and predicted fatalities (y-axis, symlog scale). The target country is highlighted with a prominent marker."""
    
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
        
        # Get cohort information
        risk_category, intensity_category = data_provider.get_risk_intensity_category(
            country_code, self.target_month, self.target_year
        )
        cohort_countries = data_provider.get_cohort_countries(
            risk_category, intensity_category, self.target_month, self.target_year
        )
        
        # Create figure with two subplots
        fig = plt.figure(figsize=(12, 6))
        ax_main = plt.subplot(1, 4, (1, 3))  # Main plot takes 3/4 width
        ax_cohort = plt.subplot(1, 4, 4)     # Cohort plot takes 1/4 width
        
        # Plot main scatter plot
        for category, color in self.prob_colors.items():
            category_data = month_data[month_data['prob_category'] == category]
            ax_main.scatter(category_data['outcome_p'], category_data['predicted'], 
                       alpha=0.7, s=30, color=color, edgecolor='gray', linewidth=0.5)
        
        if not target_country.empty:
            target_row = target_country.iloc[0]
            ax_main.scatter(target_row['outcome_p'], target_row['predicted'], 
                       s=120, color='darkred', edgecolor='black', linewidth=3, 
                       zorder=10, marker='o')
            
            ax_main.annotate(f"{country_name}", 
                        (target_row['outcome_p'], target_row['predicted']),
                        xytext=(15, 15), textcoords='offset points',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9, edgecolor='black'),
                        fontsize=11, ha='left', fontweight='bold', zorder=11)
        
        ax_main.set_yscale('symlog', linthresh=1)
        ax_main.set_ylim(-0.5, 12000)
        
        prob_boundaries = [0.01, 0.50, 0.99]
        prob_labels = ["1%", "50%", "99%"]
        for boundary, label in zip(prob_boundaries, prob_labels):
            ax_main.axvline(x=boundary, color='blue', linestyle='--', alpha=0.7, linewidth=1)
            ax_main.text(boundary, 10000, label, rotation=90, 
                    verticalalignment='top', horizontalalignment='right', 
                    color='blue', fontsize=9)
        
        intensity_boundaries = [1, 10, 100, 1000, 10000]
        intensity_labels = ["1", "10", "100", "1,000", "10,000"]
        for boundary, label in zip(intensity_boundaries, intensity_labels):
            ax_main.axhline(y=boundary, color='green', linestyle='--', alpha=0.7, linewidth=1)
            ax_main.text(ax_main.get_xlim()[1] * 0.95, boundary, label, 
                    verticalalignment='bottom', horizontalalignment='right', 
                    color='green', fontsize=9)
        
        ax_main.set_xlabel('Probability of ≥25 Fatalities', fontsize=12)
        ax_main.set_ylabel('Predicted Fatalities (Symlog Scale)', fontsize=12)
        ax_main.set_xlim(-0.05, 1.05)
        ax_main.grid(True, alpha=0.3)
        
        # Plot cohort composition
        if cohort_countries:
            cohort_data = month_data[month_data['isoab'].isin(cohort_countries)].copy()
            
            # Check if this is the lowest cohort (Near-certain no conflict, 0 fatalities)
            is_lowest_cohort = (risk_category == "Near-certain no conflict" and intensity_category == "0")
            
            if is_lowest_cohort:
                # For lowest cohort, just show summary text
                ax_cohort.text(0.5, 0.5, f"{country_name}\nis one of\n{len(cohort_countries)}\ncountries\nin this cohort", 
                              ha='center', va='center', fontsize=10, 
                              bbox=dict(boxstyle="round,pad=0.5", facecolor='lightblue', alpha=0.7),
                              transform=ax_cohort.transAxes)
                ax_cohort.set_xlim(0, 1)
                ax_cohort.set_ylim(0, 1)
                ax_cohort.axis('off')
            else:
                # For other cohorts, show bar chart
                cohort_data = cohort_data.sort_values('predicted', ascending=True)
                
                colors = ['darkred' if iso == country_code else 'lightblue' for iso in cohort_data['isoab']]
                
                bars = ax_cohort.barh(range(len(cohort_data)), cohort_data['predicted'], color=colors, alpha=0.8)
                
                # Add country labels
                for i, (idx, row) in enumerate(cohort_data.iterrows()):
                    country_name_short = data_provider.get_country_name(row['isoab'])
                    # Truncate long country names
                    if len(country_name_short) > 12:
                        country_name_short = country_name_short[:9] + "..."
                    
                    ax_cohort.text(row['predicted'] + max(cohort_data['predicted']) * 0.02, i, 
                                  country_name_short, va='center', ha='left', fontsize=8,
                                  weight='bold' if row['isoab'] == country_code else 'normal')
                
                ax_cohort.set_xlabel('Predicted\nFatalities', fontsize=9)
                ax_cohort.set_ylim(-0.5, len(cohort_data) - 0.5)
                ax_cohort.set_yticks([])
                ax_cohort.grid(True, alpha=0.3, axis='x')
        
        month_name = self.month_names[self.target_month]
        fig.suptitle(f'Conflict Forecast Distribution - {month_name} {self.target_year}', fontsize=14, y=0.95)
        
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