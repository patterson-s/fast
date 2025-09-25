from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, Dict
from grid_base_module import GridOutputModule

class GridTemporalModule(GridOutputModule):
    def __init__(self, target_month_id: int):
        self.target_month_id = target_month_id
    
    def get_context(self) -> str:
        return """This figure shows the complete monthly fatalities trend for this grid cell over the past 5 years, with the forecast highlighted. All forecast months are shown for context."""
    
    def _get_historical_data(self, historical_data: pd.DataFrame, priogrid_gid: int) -> Dict[int, float]:
        grid_historical = historical_data[historical_data['priogrid_gid'] == priogrid_gid].copy()
        
        if grid_historical.empty:
            return {}
        
        historical_points = {}
        for _, row in grid_historical.iterrows():
            historical_points[int(row['month_id'])] = float(row['ged_sb'])
        
        return historical_points
    
    def _get_forecast_data(self, forecast_data: pd.DataFrame, priogrid_gid: int) -> Dict[int, float]:
        grid_forecast = forecast_data[forecast_data['priogrid_gid'] == priogrid_gid].copy()
        
        forecast_points = {}
        for _, row in grid_forecast.iterrows():
            forecast_points[int(row['month_id'])] = float(row['outcome_p'])
        
        return forecast_points
    
    def generate_content(self, priogrid_gid: int, target_month_id: int, 
                        forecast_data: pd.DataFrame, historical_data: pd.DataFrame, 
                        output_dir: Path) -> Optional[Path]:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        historical_points = self._get_historical_data(historical_data, priogrid_gid)
        forecast_points = self._get_forecast_data(forecast_data, priogrid_gid)
        
        if not historical_points:
            return None
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        all_points = {}
        all_points.update(historical_points)
        all_points.update(forecast_points)
        
        sorted_month_ids = sorted(all_points.keys())
        
        hist_month_ids = []
        hist_values = []
        
        for month_id in sorted_month_ids:
            if month_id in historical_points:
                hist_month_ids.append(month_id)
                hist_values.append(historical_points[month_id])
        
        if hist_month_ids:
            ax.plot(hist_month_ids, hist_values, marker='o', linewidth=2, markersize=4,
                   color='darkgray', alpha=0.8, label='Historical fatalities')
            
            if len(hist_values) >= 6:
                rolling_mean = []
                rolling_month_ids = []
                for i in range(len(hist_values)):
                    if i >= 5:
                        mean_val = sum(hist_values[max(0, i-5):i+1]) / min(6, i+1)
                        rolling_mean.append(mean_val)
                        rolling_month_ids.append(hist_month_ids[i])
                
                if rolling_mean:
                    ax.plot(rolling_month_ids, rolling_mean, linewidth=2, color='darkblue',
                           alpha=0.8, label='6-Month Rolling Average')
        
        if forecast_points:
            forecast_month_ids = sorted(forecast_points.keys())
            forecast_values = [forecast_points[m] for m in forecast_month_ids]
            
            ax.plot(forecast_month_ids, forecast_values, linewidth=2, color='steelblue',
                   alpha=0.7, linestyle='-')
            
            target_prob = forecast_points.get(target_month_id)
            if target_prob is not None:
                ax.plot(target_month_id, target_prob, marker='o', markersize=12, 
                       color='steelblue', alpha=1.0, label='Target Forecast')
                
                max_value = max(list(hist_values) + list(forecast_values)) if hist_values else max(forecast_values)
                ax.text(target_month_id, target_prob + max_value * 0.02, 
                       f"{target_prob:.3f}", ha='center', va='bottom', 
                       fontsize=10, color='steelblue', weight='bold')
            
            for month_id, prob in zip(forecast_month_ids, forecast_values):
                if month_id != target_month_id:
                    ax.plot(month_id, prob, marker='o', markersize=6, 
                           color='steelblue', alpha=0.6)
        
        tick_positions = []
        tick_labels = []
        
        for i, month_id in enumerate(hist_month_ids):
            if i % 6 == 0:
                tick_positions.append(month_id)
                tick_labels.append(data_provider.month_id_to_string(month_id))
        
        for month_id in sorted(forecast_points.keys()):
            tick_positions.append(month_id)
            tick_labels.append(data_provider.month_id_to_string(month_id))
        
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=9)
        
        ax.set_ylabel('Fatalities / Probability', fontsize=12)
        ax.set_title(f'Grid {priogrid_gid} - Monthly Trend', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        plt.tight_layout()
        
        img_path = output_dir / f"grid_temporal_{priogrid_gid}_{target_month_id}.png"
        plt.savefig(img_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, priogrid_gid: int, target_month_id: int,
                          forecast_data: pd.DataFrame, historical_data: pd.DataFrame) -> str:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        historical_points = self._get_historical_data(historical_data, priogrid_gid)
        forecast_points = self._get_forecast_data(forecast_data, priogrid_gid)
        
        if not historical_points:
            return "No historical data available for this grid cell."
        
        target_forecast = forecast_points.get(target_month_id, 0)
        
        recent_values = list(historical_points.values())[-12:] if len(historical_points) >= 12 else list(historical_points.values())
        recent_avg = np.mean(recent_values) if recent_values else 0
        
        month_str = data_provider.month_id_to_string(target_month_id)
        
        if target_forecast > recent_avg * 1.1:
            trend_desc = "higher than"
        elif target_forecast < recent_avg * 0.9:
            trend_desc = "lower than"
        else:
            trend_desc = "consistent with"
        
        return f"""The forecast probability for {month_str} ({target_forecast:.3f}) is {trend_desc} the recent historical average ({recent_avg:.3f} fatalities)."""