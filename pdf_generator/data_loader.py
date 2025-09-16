from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tempfile
from typing import Dict, Optional

class DataLoader:
    def __init__(self):
        self.forecast_path = Path(r"C:\Users\spatt\Desktop\FAST\data\FAST-Forecast.parquet")
        self.historical_path = Path(r"C:\Users\spatt\Desktop\FAST\analysis\views_px_fatalities002_cm_ALL_20150101_20251201.csv")
        self.forecast_data = None
        self.historical_data = None
    
    def load_data(self):
        if self.forecast_data is None:
            self.forecast_data = pd.read_parquet(self.forecast_path)
        if self.historical_data is None:
            self.historical_data = pd.read_csv(self.historical_path)
    
    def get_country_forecast_data(self, country_code: str, month_indices: list) -> Dict:
        self.load_data()
        
        results = {}
        country_data = self.forecast_data[self.forecast_data['isoab'] == country_code]
        
        if country_data.empty:
            return {}
        
        country_name = country_data['name'].iloc[0] if not country_data.empty else country_code
        
        for month_idx in month_indices:
            outcome_n = 550 + month_idx
            month_data = country_data[country_data['outcome_n'] == outcome_n]
            
            if not month_data.empty:
                row = month_data.iloc[0]
                results[month_idx] = {
                    'probability': float(row['outcome_p']),
                    'predicted_fatalities': float(row['predicted']),
                    'country_name': country_name
                }
            else:
                results[month_idx] = {
                    'probability': 0.0,
                    'predicted_fatalities': 0.0,
                    'country_name': country_name
                }
        
        return results
    
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
            return "1–10"
        elif predicted <= 100:
            return "11–100"
        elif predicted <= 1000:
            return "101–1,000"
        elif predicted <= 10000:
            return "1,001–10,000"
        else:
            return "10,001+"
    
    def create_average_forecast_plot(self, country_code: str, avg_probability: float, avg_fatalities: float, output_dir: Path) -> Optional[Path]:
        self.load_data()
        
        month_data = self.forecast_data[self.forecast_data['outcome_n'] == 552].copy()
        
        if month_data.empty:
            return None
        
        month_data['prob_category'] = month_data['outcome_p'].apply(self.categorize_probability)
        
        prob_colors = {
            "Near-certain no conflict": "lightblue",
            "Improbable conflict": "yellow", 
            "Probable conflict": "orange",
            "Near-certain conflict": "red"
        }
        
        target_country = month_data[month_data['isoab'] == country_code]
        country_name = target_country['name'].iloc[0] if not target_country.empty else country_code
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        for category, color in prob_colors.items():
            category_data = month_data[month_data['prob_category'] == category]
            ax.scatter(category_data['outcome_p'], category_data['predicted'], 
                       alpha=0.7, s=30, color=color, edgecolor='gray', linewidth=0.5)
        
        ax.scatter(avg_probability, avg_fatalities, 
                   s=120, color='darkred', edgecolor='black', linewidth=3, 
                   zorder=10, marker='o')
        
        ax.annotate(f"{country_name} (Avg)", 
                    (avg_probability, avg_fatalities),
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
        ax.set_xlim(-0.02, 1.02)
        ax.grid(True, alpha=0.3)
        
        ax.set_title(f'Average Conflict Forecast Position - {country_name}', fontsize=14, pad=20)
        
        plt.tight_layout()
        
        img_path = output_dir / f"average_forecast_plot_{country_code}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_similar_countries(self, target_country_code: str, target_avg_prob: float, target_avg_fatalities: float) -> list:
        self.load_data()
        
        month_indices = [2, 5, 11]
        all_countries = {}
        
        for country in self.forecast_data['isoab'].unique():
            country_data = self.get_country_forecast_data(country, month_indices)
            if len(country_data) == 3:
                total_prob = sum(month['probability'] for month in country_data.values())
                total_fatalities = sum(month['predicted_fatalities'] for month in country_data.values())
                avg_prob = total_prob / 3
                avg_fatalities = total_fatalities / 3
                country_name = list(country_data.values())[0]['country_name']
                
                all_countries[country] = {
                    'code': country,
                    'name': country_name,
                    'avg_probability': avg_prob,
                    'avg_fatalities': avg_fatalities
                }
        
        if target_country_code not in all_countries:
            return []
        
        target_country = all_countries[target_country_code]
        other_countries = {k: v for k, v in all_countries.items() if k != target_country_code}
        
        distances = []
        for country_code, country_data in other_countries.items():
            prob_diff = (country_data['avg_probability'] - target_avg_prob) ** 2
            fatalities_diff = ((country_data['avg_fatalities'] - target_avg_fatalities) / max(target_avg_fatalities, 1)) ** 2
            distance = (prob_diff + fatalities_diff) ** 0.5
            
            distances.append({
                'code': country_code,
                'name': country_data['name'],
                'avg_probability': country_data['avg_probability'],
                'avg_fatalities': country_data['avg_fatalities'],
                'distance': distance
            })
        
        distances.sort(key=lambda x: x['distance'])
        closest_4 = distances[:4]
        
        countries_below = [c for c in closest_4 if c['avg_fatalities'] < target_avg_fatalities]
        countries_above = [c for c in closest_4 if c['avg_fatalities'] > target_avg_fatalities]
        
        result = []
        
        if len(countries_below) >= 2:
            result.extend(sorted(countries_below, key=lambda x: x['avg_fatalities'], reverse=True)[:2])
        else:
            result.extend(countries_below)
        
        result.append(target_country)
        
        if len(countries_above) >= 2:
            result.extend(sorted(countries_above, key=lambda x: x['avg_fatalities'])[:2])
        else:
            result.extend(countries_above)
        
        if len(result) < 5:
            remaining_closest = [c for c in distances[:8] if c['code'] not in [r['code'] for r in result]]
            needed = 5 - len(result)
            result.extend(remaining_closest[:needed])
        
        result.sort(key=lambda x: x['avg_fatalities'])
        
        return result
    
    def create_rolling_periods_plot(self, country_code: str, output_dir: Path) -> Optional[Path]:
        self.load_data()
        
        forecast_data = self.forecast_data[self.forecast_data['isoab'] == country_code].copy()
        
        if forecast_data.empty:
            print(f"No forecast data for {country_code}")
            return None
        
        forecast_data['date'] = pd.to_datetime(forecast_data['dates'])
        forecast_total = forecast_data['predicted'].sum()
        
        historical_data = self.historical_data[self.historical_data['isoab'] == country_code].copy()
        
        if historical_data.empty:
            print(f"No historical data for {country_code}")
            return None
        
        historical_data['total_fatalities'] = (
            historical_data['ucdp_ged_ns_best_sum'] + 
            historical_data['ucdp_ged_sb_best_sum'] + 
            historical_data['ucdp_ged_os_best_sum']
        )
        
        historical_data['date'] = pd.to_datetime(historical_data[['year', 'month']].assign(day=1))
        
        periods = []
        
        periods.append({
            'period': 'Oct 2025 - Sep 2026',
            'period_num': 1,
            'fatalities': forecast_total,
            'type': 'forecast'
        })
        
        from datetime import datetime, timedelta
        
        for i in range(10):
            period_num = -i
            end_date = datetime(2025, 9, 30) - timedelta(days=365 * i)
            start_date = datetime(2024, 10, 1) - timedelta(days=365 * i)
            
            period_data = historical_data[
                (historical_data['date'] >= start_date) & 
                (historical_data['date'] <= end_date)
            ]
            
            if not period_data.empty:
                period_total = period_data['total_fatalities'].sum()
                periods.append({
                    'period': f"Oct {start_date.year} - Sep {end_date.year}",
                    'period_num': period_num,
                    'fatalities': period_total,
                    'type': 'historical'
                })
        
        periods_df = pd.DataFrame(periods)
        periods_df = periods_df.sort_values('period_num')
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        historical_periods = periods_df[periods_df['type'] == 'historical']
        forecast_periods = periods_df[periods_df['type'] == 'forecast']
        
        if not historical_periods.empty:
            ax.plot(historical_periods['period_num'], historical_periods['fatalities'], 
                   marker='o', linewidth=3, markersize=8, color='darkred', alpha=0.8,
                   label='Historical (12-month periods)')
            
            for _, row in historical_periods.iterrows():
                if row['fatalities'] > 0:
                    ax.text(row['period_num'], row['fatalities'] + max(periods_df['fatalities']) * 0.02, 
                           f"{int(row['fatalities'])}", ha='center', va='bottom', fontsize=9,
                           color='darkred')
        
        if not forecast_periods.empty and not historical_periods.empty:
            last_historical = historical_periods.iloc[-1]
            forecast_point = forecast_periods.iloc[0]
            
            ax.plot([last_historical['period_num'], forecast_point['period_num']], 
                   [last_historical['fatalities'], forecast_point['fatalities']], 
                   linewidth=3, color='steelblue', alpha=0.8, linestyle='--')
            
            ax.plot(forecast_point['period_num'], forecast_point['fatalities'], 
                   marker='o', markersize=10, color='steelblue', alpha=0.8,
                   label='Forecast')
            
            ax.text(forecast_point['period_num'], forecast_point['fatalities'] + max(periods_df['fatalities']) * 0.02, 
                   f"{int(forecast_point['fatalities'])}", ha='center', va='bottom', fontsize=9,
                   color='steelblue', weight='bold')
        
        country_name = historical_data['name'].iloc[0] if not historical_data.empty else country_code
        ax.set_xlabel('Period (12-month rolling)', fontsize=12)
        ax.set_ylabel('Total Fatalities', fontsize=12)
        ax.set_title(f'{country_name} - Rolling 12-Month Conflict Fatalities', 
                    fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        ax.set_xticks(periods_df['period_num'])
        ax.set_xticklabels([p.split(' - ')[1] for p in periods_df['period']], 
                          rotation=45, ha='right')
        
        if not forecast_periods.empty and not historical_periods.empty:
            forecast_point = forecast_periods.iloc[0]
            ax.axvline(x=forecast_point['period_num'] - 0.5, color='lightgray', 
                      linestyle=':', alpha=0.5, linewidth=1)
        
        plt.tight_layout()
        
        img_path = output_dir / f"rolling_periods_{country_code}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def create_forecast_plot(self, country_code: str, month_index: int, output_dir: Path) -> Optional[Path]:
        self.load_data()
        
        outcome_n = 550 + month_index
        month_data = self.forecast_data[self.forecast_data['outcome_n'] == outcome_n].copy()
        
        if month_data.empty:
            return None
        
        month_data['prob_category'] = month_data['outcome_p'].apply(self.categorize_probability)
        
        prob_colors = {
            "Near-certain no conflict": "lightblue",
            "Improbable conflict": "yellow", 
            "Probable conflict": "orange",
            "Near-certain conflict": "red"
        }
        
        target_country = month_data[month_data['isoab'] == country_code]
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        for category, color in prob_colors.items():
            category_data = month_data[month_data['prob_category'] == category]
            ax.scatter(category_data['outcome_p'], category_data['predicted'], 
                       alpha=0.7, s=30, color=color, edgecolor='gray', linewidth=0.5)
        
        if not target_country.empty:
            target_row = target_country.iloc[0]
            ax.scatter(target_row['outcome_p'], target_row['predicted'], 
                       s=120, color='darkred', edgecolor='black', linewidth=3, 
                       zorder=10, marker='o')
            
            ax.annotate(f"{target_row['name']}", 
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
        ax.set_xlim(-0.02, 1.02)
        ax.grid(True, alpha=0.3)
        
        month_date = pd.to_datetime(month_data['dates'].iloc[0]) if not month_data.empty else f"Month {outcome_n}"
        month_str = month_date.strftime("%B %Y") if hasattr(month_date, 'strftime') else str(month_date)
        ax.set_title(f'Conflict Forecast Distribution - {month_str}', fontsize=14, pad=20)
        
        plt.tight_layout()
        
        img_path = output_dir / f"forecast_plot_{country_code}_{month_index}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path