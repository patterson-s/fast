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
        return f"""This figure shows the historical trend for {month_name} fatalities over the past 5 years, with our forecast for {month_name} {self.target_year} highlighted. The other forecast months are shown for additional context."""
    
    def _get_historical_monthly_data(self, historical_data: pd.DataFrame, country_code: str) -> Dict[str, float]:
        country_historical = historical_data[historical_data['isoab'] == country_code].copy()
        
        if country_historical.empty:
            return {}
        
        country_historical['total_fatalities'] = (
            country_historical['ucdp_ged_ns_best_sum'] + 
            country_historical['ucdp_ged_sb_best_sum'] + 
            country_historical['ucdp_ged_os_best_sum']
        )
        
        historical_points = {}
        target_months = [12, 3, 9]  # Dec, Mar, Sep
        
        for year in range(self.target_year - 5, self.target_year + 1):
            for month in target_months:
                # Only include data that is actually historical (past)
                # Skip Sept 2025 (no data) and any future dates
                if year == 2025 and month == 9:  # Sept 2025 - no data
                    continue
                if year == 2025 and month > 12:  # Future months in 2025
                    continue  
                if year > 2025:  # All of 2026+ is future
                    continue
                    
                date_key = f"{year}-{month:02d}"
                year_month_data = country_historical[
                    (country_historical['year'] == year) & 
                    (country_historical['month'] == month)
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
        # Map months to outcome_n and date strings
        month_mappings = {
            12: (552, "2025-12"),  # Dec 2025
            3: (555, "2026-03"),   # Mar 2026  
            9: (561, "2026-09")    # Sep 2026
        }
        
        for month, (outcome_n, date_key) in month_mappings.items():
            month_data = country_forecast[country_forecast['outcome_n'] == outcome_n]
            if not month_data.empty:
                forecast_points[date_key] = float(month_data['predicted'].iloc[0])
            else:
                forecast_points[date_key] = 0.0
        
        return forecast_points
    
    def generate_content(self, country_code: str, forecast_data: pd.DataFrame, 
                        historical_data: pd.DataFrame, output_dir: Path) -> Optional[Path]:
        
        historical_points = self._get_historical_monthly_data(historical_data, country_code)
        forecast_points = self._get_forecast_data(forecast_data, country_code)
        
        if not historical_points:
            return None
        
        country_name = historical_data[historical_data['isoab'] == country_code]['name'].iloc[0] if len(historical_data[historical_data['isoab'] == country_code]) > 0 else country_code
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create chronological sequence of all data points
        from datetime import datetime
        
        all_points = {}
        all_points.update(historical_points)
        all_points.update(forecast_points)
        
        # Sort by date
        sorted_dates = sorted(all_points.keys())
        
        # Convert to x-positions (months since start)
        start_date = datetime.strptime(sorted_dates[0], "%Y-%m")
        x_positions = []
        y_values = []
        date_labels = []
        is_forecast = []
        
        for date_str in sorted_dates:
            date_obj = datetime.strptime(date_str, "%Y-%m")
            months_since_start = (date_obj.year - start_date.year) * 12 + (date_obj.month - start_date.month)
            
            x_positions.append(months_since_start)
            y_values.append(all_points[date_str])
            date_labels.append(date_str)
            is_forecast.append(date_str in forecast_points)
        
        # Calculate max value for label positioning
        max_value = max(y_values) if y_values else 100
        
        # Split into historical and forecast segments
        hist_x = []
        hist_y = []
        forecast_x = []
        forecast_y = []
        target_forecast_x = None
        target_forecast_y = None
        
        target_date_key = f"{self.target_year}-{self.target_month:02d}"
        
        for i, (x, y, date_str, is_fc) in enumerate(zip(x_positions, y_values, date_labels, is_forecast)):
            if is_fc:
                forecast_x.append(x)
                forecast_y.append(y)
                if date_str == target_date_key:
                    target_forecast_x = x
                    target_forecast_y = y
            else:
                hist_x.append(x)
                hist_y.append(y)
        
        # Plot historical line
        if hist_x:
            ax.plot(hist_x, hist_y, marker='o', linewidth=3, markersize=8, 
                   color='darkred', alpha=0.9, label='Historical')
            
            # Add labels only for target month historical points
            for x, y, date_str in zip(hist_x, hist_y, [d for d, is_fc in zip(date_labels, is_forecast) if not is_fc]):
                month = int(date_str.split('-')[1])
                if month == self.target_month and y > 0:
                    ax.text(x, y + max_value * 0.02, f"{int(y)}", 
                           ha='center', va='bottom', fontsize=9, color='darkred')
        
        # Plot forecast points (connected with blue line)
        if forecast_x:
            # Sort forecast points by x position for proper line connection
            forecast_data = list(zip(forecast_x, forecast_y, [d for d, is_fc in zip(date_labels, is_forecast) if is_fc]))
            forecast_data.sort(key=lambda x: x[0])
            
            sorted_forecast_x = [item[0] for item in forecast_data]
            sorted_forecast_y = [item[1] for item in forecast_data]
            sorted_forecast_dates = [item[2] for item in forecast_data]
            
            # Draw connecting line for all forecast points
            ax.plot(sorted_forecast_x, sorted_forecast_y, linewidth=3, color='steelblue', 
                   alpha=0.5, linestyle='-')
            
            # Plot individual forecast points
            for x, y, date_str in forecast_data:
                if date_str == target_date_key:
                    # Target forecast: prominent
                    ax.plot(x, y, marker='o', markersize=12, color='steelblue', alpha=1.0, 
                           label=f'Target Forecast ({self.month_names[self.target_month]})')
                    ax.text(x, y + max_value * 0.02, f"{int(y)}", 
                           ha='center', va='bottom', fontsize=10, color='steelblue', weight='bold')
                else:
                    # Context forecasts: transparent
                    ax.plot(x, y, marker='o', markersize=8, color='steelblue', alpha=0.5)
        
        # Add vertical line at October 2025 to indicate forecasting period start
        oct_2025 = datetime(2025, 10, 1)
        oct_months_since_start = (oct_2025.year - start_date.year) * 12 + (oct_2025.month - start_date.month)
        ax.axvline(x=oct_months_since_start, color='gray', linestyle='--', alpha=0.7, linewidth=2)
        
        # Set up x-axis with ticks only for our target months (Dec, Mar, Sep)
        tick_positions = []
        tick_labels = []
        month_names_short = {12: "Dec", 3: "Mar", 9: "Sep"}
        
        for i, (x, date_str) in enumerate(zip(x_positions, date_labels)):
            year, month = date_str.split('-')
            month = int(month)
            if month in [12, 3, 9]:  # Only show Dec, Mar, Sep
                tick_positions.append(x)
                tick_labels.append(f"{month_names_short[month]} {year}")
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=10)
        
        month_name = self.month_names[self.target_month]
        ax.set_ylabel('Fatalities', fontsize=12)
        ax.set_title(f'{country_name} - Monthly Fatalities Trend (Emphasis: {month_name})', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
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
        
        # Calculate 5-year average for target month only
        recent_values = []
        for date_str, value in historical_points.items():
            year, month = date_str.split('-')
            year, month = int(year), int(month)
            if month == self.target_month:  # All available years for target month
                recent_values.append(value)
        
        recent_avg = np.mean(recent_values) if recent_values else 0
        
        month_name = self.month_names[self.target_month]
        
        if target_forecast > recent_avg * 1.5:
            trend_desc = "significantly higher than"
        elif target_forecast > recent_avg * 1.1:
            trend_desc = "moderately higher than"
        elif target_forecast < recent_avg * 0.5:
            trend_desc = "significantly lower than"
        elif target_forecast < recent_avg * 0.9:
            trend_desc = "moderately lower than"
        else:
            trend_desc = "consistent with"
        
        return f"""Our forecast for {month_name} {self.target_year} ({int(target_forecast)} fatalities) is {trend_desc} the 5-year historical average ({int(recent_avg)} fatalities)."""