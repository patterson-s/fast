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
        return """This figure shows the complete monthly fatalities trend for this grid cell over the past 5 years, with baseline model forecast. The target forecast month is highlighted. The probability bar shows the predicted probability of at least one battle death."""
    
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
            forecast_points[int(row['month_id'])] = float(row['outcome_n'])
        
        return forecast_points
    
    def _get_outcome_p(self, forecast_data: pd.DataFrame, priogrid_gid: int, target_month_id: int) -> Optional[float]:
        grid_forecast = forecast_data[
            (forecast_data['priogrid_gid'] == priogrid_gid) & 
            (forecast_data['month_id'] == target_month_id)
        ]
        
        if grid_forecast.empty or 'outcome_p' not in grid_forecast.columns:
            return None
        
        return float(grid_forecast.iloc[0]['outcome_p'])
    
    def generate_content(self, priogrid_gid: int, target_month_id: int, 
                        forecast_data: dict, historical_data: pd.DataFrame, 
                        output_dir: Path) -> Optional[Path]:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        historical_points = self._get_historical_data(historical_data, priogrid_gid)
        baseline_points = self._get_forecast_data(forecast_data['baseline'], priogrid_gid)
        outcome_p = self._get_outcome_p(forecast_data['baseline'], priogrid_gid, target_month_id)
        
        if not historical_points:
            return None
        
        fig = plt.figure(figsize=(8, 4))
        gs = fig.add_gridspec(1, 2, width_ratios=[9, 1], wspace=0.15)
        
        ax_time = fig.add_subplot(gs[0])
        ax_prob = fig.add_subplot(gs[1])
        
        sorted_hist_months = sorted(historical_points.keys())
        hist_values = [historical_points[m] for m in sorted_hist_months]
        
        if hist_values:
            ax_time.plot(sorted_hist_months, hist_values, marker='o', linewidth=1.5, markersize=3,
                   color='darkgray', alpha=0.8, label='Historical')
            
            if len(hist_values) >= 6:
                rolling_mean = []
                rolling_month_ids = []
                for i in range(len(hist_values)):
                    if i >= 5:
                        mean_val = sum(hist_values[max(0, i-5):i+1]) / min(6, i+1)
                        rolling_mean.append(mean_val)
                        rolling_month_ids.append(sorted_hist_months[i])
                
                if rolling_mean:
                    ax_time.plot(rolling_month_ids, rolling_mean, linewidth=1.5, color='darkblue',
                           alpha=0.8, label='6-mo avg')
        
        if baseline_points:
            baseline_months = sorted(baseline_points.keys())
            baseline_values = [baseline_points[m] for m in baseline_months]
            
            ax_time.plot(baseline_months, baseline_values, linewidth=1.5, color='steelblue',
                   alpha=0.7, linestyle='-', label='Forecast')
            
            forecast_start_month = min(baseline_months)
            ax_time.axvline(x=forecast_start_month, color='gray', linewidth=1.5, 
                      linestyle='--', alpha=0.8, zorder=1)
            
            target_baseline_value = baseline_points.get(target_month_id)
            if target_baseline_value is not None:
                ax_time.plot(target_month_id, target_baseline_value, marker='o', markersize=8, 
                       color='steelblue', alpha=1.0, zorder=10)
        
        tick_positions = []
        tick_labels = []
        
        for i, month_id in enumerate(sorted_hist_months):
            if i % 6 == 0:
                tick_positions.append(month_id)
                tick_labels.append(data_provider.month_id_to_string(month_id))
        
        forecast_label_months = [552, 555, 561]
        for month_id in forecast_label_months:
            if month_id in baseline_points:
                tick_positions.append(month_id)
                tick_labels.append(data_provider.month_id_to_string(month_id))
        
        ax_time.set_xticks(tick_positions)
        ax_time.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
        ax_time.tick_params(axis='y', labelsize=8)
        
        all_values = hist_values + baseline_values
        max_value = max(all_values) if all_values else 1
        
        y_max = max_value * 1.1 if max_value > 0 else 1
        ax_time.set_ylim(0, y_max)
        
        ax_time.set_ylabel('Fatalities', fontsize=9)
        ax_time.grid(True, alpha=0.3)
        ax_time.legend(loc='upper left', fontsize=8, framealpha=0.9)
        
        if outcome_p is not None:
            cmap = plt.cm.RdYlGn_r
            gradient = np.linspace(0, 1, 256).reshape(-1, 1)
            ax_prob.imshow(gradient, aspect='auto', cmap=cmap, origin='lower', extent=[0, 1, 0, 1])
            
            ax_prob.axhline(y=outcome_p, color='black', linewidth=2, linestyle='-')
            ax_prob.plot([0.5], [outcome_p], marker='D', markersize=8, color='black', 
                        markeredgewidth=1.5, markerfacecolor='yellow', zorder=10)
            
            ax_prob.text(0.5, outcome_p + 0.05, f'{outcome_p:.2f}', fontsize=8, 
                        ha='center', va='bottom', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
            
            ax_prob.set_ylim(0, 1)
            ax_prob.set_xlim(0, 1)
            ax_prob.set_yticks([0, 0.5, 1.0])
            ax_prob.set_yticklabels(['0', '0.5', '1'], fontsize=8)
            ax_prob.set_xticks([])
            ax_prob.set_ylabel('P(≥1 death)', fontsize=8)
        else:
            ax_prob.text(0.5, 0.5, 'N/A', ha='center', va='center', fontsize=9)
            ax_prob.set_xlim(0, 1)
            ax_prob.set_ylim(0, 1)
            ax_prob.set_xticks([])
            ax_prob.set_yticks([])
        
        plt.tight_layout()
        
        img_path = output_dir / f"grid_temporal_{priogrid_gid}_{target_month_id}.png"
        plt.savefig(img_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, priogrid_gid: int, target_month_id: int,
                          forecast_data: dict, historical_data: pd.DataFrame) -> str:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        historical_points = self._get_historical_data(historical_data, priogrid_gid)
        baseline_points = self._get_forecast_data(forecast_data['baseline'], priogrid_gid)
        outcome_p = self._get_outcome_p(forecast_data['baseline'], priogrid_gid, target_month_id)
        
        if not historical_points:
            return "No historical data available for this grid cell."
        
        target_baseline = baseline_points.get(target_month_id, 0)
        
        recent_values = list(historical_points.values())[-12:] if len(historical_points) >= 12 else list(historical_points.values())
        recent_avg = np.mean(recent_values) if recent_values else 0
        
        month_str = data_provider.month_id_to_string(target_month_id)
        
        if target_baseline > recent_avg * 1.1:
            trend_desc = "higher than"
        elif target_baseline < recent_avg * 0.9:
            trend_desc = "lower than"
        else:
            trend_desc = "consistent with"
        
        base_interpretation = f"""The baseline forecast for {month_str} ({target_baseline:.1f} fatalities) is {trend_desc} the recent historical average ({recent_avg:.1f} fatalities)."""
        
        if outcome_p is not None:
            prob_interpretation = f""" The predicted probability of at least one battle death is {outcome_p:.2f}."""
            return base_interpretation + prob_interpretation
        
        return base_interpretation