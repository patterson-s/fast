from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import numpy as np
from base_module import OutputModule

class MonthlyTemporalModule(OutputModule):
    def __init__(self, target_month: int, target_year: int):
        self.target_month = target_month
        self.target_year = target_year
        self.month_names = {12: "December", 3: "March", 9: "September"}
        
    def get_context(self) -> str:
        month_name = self.month_names[self.target_month]
        return f"""This figure shows the complete monthly fatalities trend over the past 5 years, with our forecast for {month_name} {self.target_year} highlighted. All forecast months are shown for context."""
    
    def _get_historical_monthly_data(self, historical_data: pd.DataFrame, country_code: str) -> Dict[str, float]:
        country_historical = historical_data[historical_data['isoab'] == country_code].copy()
        
        if country_historical.empty:
            return {}
        
        historical_points = {}
        
        for year in range(2020, 2026):
            for month in range(1, 13):
                if year == 2025 and month >= 9:
                    continue
                    
                date_key = f"{year}-{month:02d}"
                year_month_data = country_historical[
                    (country_historical['Year'] == year) & 
                    (country_historical['Month'] == month)
                ]
                
                if not year_month_data.empty:
                    fatalities = year_month_data['total_fatalities'].sum()
                    historical_points[date_key] = fatalities
                else:
                    historical_points[date_key] = 0
        
        return historical_points
    
    def _get_forecast_data(self, forecast_data: pd.DataFrame, country_code: str) -> Dict[str, float]:
        country_forecast = forecast_data[forecast_data['isoab'] == country_code]
        
        forecast_points = {}
        
        target_months = {
            (2025, 12): "2025-12",
            (2026, 3): "2026-03", 
            (2026, 9): "2026-09"
        }
        
        for _, row in country_forecast.iterrows():
            date_obj = pd.Timestamp(row['dates'])
            date_key = f"{date_obj.year}-{date_obj.month:02d}"
            
            if (date_obj.year, date_obj.month) in target_months:
                forecast_points[date_key] = float(row['predicted'])
        
        return forecast_points
    
    def generate_content(self, country_code: str, forecast_data: pd.DataFrame, 
                        historical_data: pd.DataFrame, output_dir: Path) -> Optional[Path]:
        
        from data_provider import DataProvider
        data_provider = DataProvider()
        
        historical_points = self._get_historical_monthly_data(historical_data, country_code)
        forecast_points = self._get_forecast_data(forecast_data, country_code)
        
        if not historical_points:
            return None
        
        risk_category, intensity_category = data_provider.get_risk_intensity_category(
            country_code, self.target_month, self.target_year
        )
        
        cohort_countries = data_provider.get_cohort_countries(
            risk_category, intensity_category, self.target_month, self.target_year
        )
        
        country_name = data_provider.get_country_name(country_code)
        
        fig, ax = plt.subplots(figsize=(9, 5))
        
        all_points = {}
        all_points.update(historical_points)
        all_points.update(forecast_points)
        
        sorted_dates = sorted(all_points.keys())
        
        start_date = datetime.strptime(sorted_dates[0], "%Y-%m")
        x_positions = []
        y_values = []
        date_labels = []
        is_forecast = []
        is_target_month = []
        
        for date_str in sorted_dates:
            date_obj = datetime.strptime(date_str, "%Y-%m")
            months_since_start = (date_obj.year - start_date.year) * 12 + (date_obj.month - start_date.month)
            
            x_positions.append(months_since_start)
            y_values.append(all_points[date_str])
            date_labels.append(date_str)
            is_forecast.append(date_str in forecast_points)
            is_target_month.append(date_obj.month == self.target_month)
        
        max_value = max(y_values) if y_values else 100
        
        hist_x = []
        hist_y = []
        
        hist_data_points = []
        for x, y, date_str, is_fc, is_target in zip(
            x_positions, y_values, date_labels, is_forecast, is_target_month
        ):
            if not is_fc:
                hist_data_points.append((x, y, date_str, is_target))
        
        hist_data_points.sort(key=lambda item: item[2])
        
        if hist_data_points:
            hist_x = [item[0] for item in hist_data_points]
            hist_y = [item[1] for item in hist_data_points]
            
            ax.plot(hist_x, hist_y, marker='o', linewidth=1.5, markersize=3, 
                   color='darkgray', alpha=0.8, label='Historical (all months)')
            
            if len(hist_y) >= 6:
                rolling_mean = []
                rolling_x = []
                for i in range(len(hist_y)):
                    if i >= 5:
                        mean_val = sum(hist_y[max(0, i-5):i+1]) / min(6, i+1)
                        rolling_mean.append(mean_val)
                        rolling_x.append(hist_x[i])
    
                if rolling_mean:
                    ax.plot(rolling_x, rolling_mean, linewidth=1.5, color='darkblue', 
                        alpha=0.8, label='6-Month Rolling Average')
        
        target_forecast_x = None
        target_forecast_y = None
        target_date_key = f"{self.target_year}-{self.target_month:02d}"
        
        forecast_data_points = [(x, y, date_str) for x, y, date_str, is_fc in 
                               zip(x_positions, y_values, date_labels, is_forecast) if is_fc]
        
        if forecast_data_points:
            forecast_data_points.sort(key=lambda x: x[0])
            
            sorted_forecast_x = [item[0] for item in forecast_data_points]
            sorted_forecast_y = [item[1] for item in forecast_data_points]
            
            ax.plot(sorted_forecast_x, sorted_forecast_y, linewidth=1.5, color='steelblue', 
                   alpha=0.7, linestyle='-')
            
            for x, y, date_str in forecast_data_points:
                if date_str == target_date_key:
                    ax.plot(x, y, marker='o', markersize=8, color='steelblue', alpha=1.0, 
                           label=f'Target Forecast ({self.month_names[self.target_month]})')
                    ax.text(x, y + max_value * 0.02, f"{int(y)}", 
                           ha='center', va='bottom', fontsize=10, color='steelblue', weight='bold')
                    target_forecast_x = x
                    target_forecast_y = y
                else:
                    ax.plot(x, y, marker='o', markersize=4, color='steelblue', alpha=0.6)
        
        tick_positions = []
        tick_labels = []
        
        for i, (x, date_str, is_fc) in enumerate(zip(x_positions, date_labels, is_forecast)):
            if not is_fc and i % 6 == 0:
                year, month = date_str.split('-')
                month_name = datetime(int(year), int(month), 1).strftime('%b')
                tick_positions.append(x)
                tick_labels.append(f"{month_name} {year}")
        
        forecast_ticks = []
        for x, date_str, is_fc in zip(x_positions, date_labels, is_forecast):
            if is_fc:
                year, month = date_str.split('-')
                month_name = datetime(int(year), int(month), 1).strftime('%b')
                forecast_ticks.append((x, f"{month_name} {year}"))
        
        for x, label in forecast_ticks:
            tick_positions.append(x)
            tick_labels.append(label)
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=10)
        
        month_name = self.month_names[self.target_month]
        ax.set_ylabel('Fatalities', fontsize=10)
        ax.set_title(f'{country_name} - Complete Monthly Fatalities', fontsize=13, pad=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=11)
        
        ax.set_xlim(min(x_positions) - 2, max(x_positions) + 2)
        
        plt.tight_layout()
        
        img_path = output_dir / f"monthly_temporal_{country_code}_{self.target_month}_{self.target_year}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, country_code: str, forecast_data: pd.DataFrame, 
                          historical_data: pd.DataFrame) -> str:
        historical_points = self._get_historical_monthly_data(historical_data, country_code)
        forecast_points = self._get_forecast_data(forecast_data, country_code)
        
        if not historical_points:
            return "No historical data available for analysis."
        
        target_date_key = f"{self.target_year}-{self.target_month:02d}"
        target_forecast = forecast_points.get(target_date_key, 0)
        
        recent_values = []
        for date_str, value in historical_points.items():
            year, month = date_str.split('-')
            year, month = int(year), int(month)
            if month == self.target_month:
                recent_values.append(value)
        
        recent_avg = np.mean(recent_values) if recent_values else 0
        
        if len(recent_values) >= 3:
            years = list(range(len(recent_values)))
            trend_slope = np.polyfit(years, recent_values, 1)[0]
            if abs(trend_slope) > 5:
                if trend_slope > 0:
                    trend_text = f" The historical trend shows increasing violence (slope: +{trend_slope:.1f} fatalities/year)."
                else:
                    trend_text = f" The historical trend shows decreasing violence (slope: {trend_slope:.1f} fatalities/year)."
            else:
                trend_text = " The historical trend is relatively stable."
        else:
            trend_text = ""
        
        month_name = self.month_names[self.target_month]
        
        if target_forecast > recent_avg * 1.1:
            trend_desc = "higher than"
        elif target_forecast < recent_avg * 0.9:
            trend_desc = "lower than"
        else:
            trend_desc = "consistent with"
        
        return f"""Our forecast for {month_name} {self.target_year} ({int(target_forecast)} fatalities) is {trend_desc} the 5-year historical average ({int(recent_avg)} fatalities).{trend_text}"""