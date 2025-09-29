from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, Dict
from grid_base_module import GridOutputModule

class GridComparisonModule(GridOutputModule):
    def __init__(self, target_month_id: int):
        self.target_month_id = target_month_id
    
    def get_context(self) -> str:
        return """This figure compares the baseline and climate model forecasts for the next 12 months. The baseline model uses historical conflict patterns and spatial relationships, while the climate model incorporates drought and growing season variables."""
    
    def _get_forecast_data(self, forecast_data: pd.DataFrame, priogrid_gid: int) -> Dict[int, float]:
        grid_forecast = forecast_data[forecast_data['priogrid_gid'] == priogrid_gid].copy()
        
        forecast_points = {}
        for _, row in grid_forecast.iterrows():
            forecast_points[int(row['month_id'])] = float(row['outcome_n'])
        
        return forecast_points
    
    def generate_content(self, priogrid_gid: int, target_month_id: int, 
                        forecast_data: dict, historical_data: pd.DataFrame, 
                        output_dir: Path) -> Optional[Path]:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        baseline_points = self._get_forecast_data(forecast_data['baseline'], priogrid_gid)
        climate_points = self._get_forecast_data(forecast_data['climate'], priogrid_gid)
        
        if not baseline_points or not climate_points:
            return None
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        baseline_months = sorted(baseline_points.keys())
        baseline_values = [baseline_points[m] for m in baseline_months]
        
        climate_months = sorted(climate_points.keys())
        climate_values = [climate_points[m] for m in climate_months]
        
        ax.plot(baseline_months, baseline_values, linewidth=2, color='steelblue',
               alpha=0.8, linestyle='-', label='Baseline Forecast', marker='o', markersize=6)
        
        ax.plot(climate_months, climate_values, linewidth=2, color='forestgreen',
               alpha=0.8, linestyle='-', label='Climate Forecast', marker='s', markersize=6)
        
        target_baseline_value = baseline_points.get(target_month_id)
        target_climate_value = climate_points.get(target_month_id)
        
        if target_baseline_value is not None:
            ax.plot(target_month_id, target_baseline_value, marker='o', markersize=14, 
                   color='steelblue', alpha=1.0, zorder=5)
            
            ax.text(target_month_id, target_baseline_value, f' {target_baseline_value:.1f}',
                   fontsize=11, color='steelblue', fontweight='bold',
                   verticalalignment='bottom', horizontalalignment='left')
        
        if target_climate_value is not None:
            ax.plot(target_month_id, target_climate_value, marker='s', markersize=14, 
                   color='forestgreen', alpha=1.0, zorder=5)
            
            offset_direction = 'top' if target_climate_value > target_baseline_value else 'bottom'
            va = offset_direction
            
            ax.text(target_month_id, target_climate_value, f' {target_climate_value:.1f}',
                   fontsize=11, color='forestgreen', fontweight='bold',
                   verticalalignment=va, horizontalalignment='left')
        
        tick_positions = baseline_months
        tick_labels = [data_provider.month_id_to_string(m) for m in baseline_months]
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=9)
        
        all_values = baseline_values + climate_values
        max_value = max(all_values) if all_values else 1
        
        y_max = max_value * 1.15 if max_value > 0 else 1
        ax.set_ylim(0, y_max)
        
        ax.set_ylabel('Fatalities', fontsize=12)
        ax.set_title(f'Grid {priogrid_gid} - Baseline vs Climate Model Forecast', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        plt.tight_layout()
        
        img_path = output_dir / f"grid_comparison_{priogrid_gid}_{target_month_id}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, priogrid_gid: int, target_month_id: int,
                          forecast_data: dict, historical_data: pd.DataFrame) -> str:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        baseline_points = self._get_forecast_data(forecast_data['baseline'], priogrid_gid)
        climate_points = self._get_forecast_data(forecast_data['climate'], priogrid_gid)
        
        if not baseline_points or not climate_points:
            return "Insufficient forecast data for comparison."
        
        target_baseline = baseline_points.get(target_month_id, 0)
        target_climate = climate_points.get(target_month_id, 0)
        
        month_str = data_provider.month_id_to_string(target_month_id)
        
        diff = target_climate - target_baseline
        
        if abs(diff) < 0.1:
            relationship = "nearly identical"
            detail = ""
        elif diff > 0:
            relationship = "slightly higher"
            detail = f" ({diff:.1f} more fatalities)"
        else:
            relationship = "slightly lower"
            detail = f" ({abs(diff):.1f} fewer fatalities)"
        
        all_months = sorted(set(baseline_points.keys()) & set(climate_points.keys()))
        differences = [climate_points[m] - baseline_points[m] for m in all_months]
        avg_diff = np.mean(differences)
        
        if abs(avg_diff) < 0.1:
            overall_trend = "The models show nearly identical forecasts across all months"
        elif avg_diff > 0:
            overall_trend = "The climate model shows slightly higher fatalities on average across the forecast period"
        else:
            overall_trend = "The climate model shows slightly lower fatalities on average across the forecast period"
        
        return f"""{overall_trend}. For {month_str}, the climate forecast is {relationship}{detail} compared to the baseline forecast."""