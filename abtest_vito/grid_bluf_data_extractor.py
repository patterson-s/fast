import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

sys.path.append(str(Path(__file__).parent.parent / "vito_01"))
from GridDataProvider import GridDataProvider

class GridBLUFDataExtractor:
    def __init__(self):
        self.data_provider = GridDataProvider()
    
    def extract_bluf_data(self, priogrid_gid: int, target_month_id: int) -> Dict[str, Any]:
        baseline_forecast = self.data_provider.get_baseline_forecast()
        climate_forecast = self.data_provider.get_climate_forecast()
        historical_data = self.data_provider.get_historical_data()
        
        country_name = self.data_provider.get_country_name(priogrid_gid)
        month_str = self.data_provider.month_id_to_string(target_month_id)
        
        baseline_target = baseline_forecast[
            (baseline_forecast['priogrid_gid'] == priogrid_gid) & 
            (baseline_forecast['month_id'] == target_month_id)
        ]
        
        climate_target = climate_forecast[
            (climate_forecast['priogrid_gid'] == priogrid_gid) & 
            (climate_forecast['month_id'] == target_month_id)
        ]
        
        if baseline_target.empty:
            raise ValueError(f"No baseline forecast for grid {priogrid_gid} at month {target_month_id}")
        
        baseline_row = baseline_target.iloc[0]
        baseline_prob = float(baseline_row['outcome_p'])
        baseline_fatalities = float(baseline_row['outcome_n'])
        
        climate_prob = None
        climate_fatalities = None
        if not climate_target.empty:
            climate_row = climate_target.iloc[0]
            climate_prob = float(climate_row['outcome_p'])
            climate_fatalities = float(climate_row['outcome_n'])
        
        risk_category = self._categorize_risk(baseline_prob)
        
        historical_avg, historical_trend = self._get_historical_context(
            historical_data, priogrid_gid
        )
        
        neighbor_context = self._get_neighbor_context(
            baseline_forecast, priogrid_gid, target_month_id
        )
        
        country_rank = self._get_country_rank(
            baseline_forecast, priogrid_gid, target_month_id, country_name
        )
        
        global_category = self._get_global_category(baseline_fatalities)
        
        climate_diff = None
        if climate_fatalities is not None:
            climate_diff = climate_fatalities - baseline_fatalities
        
        return {
            'grid_id': priogrid_gid,
            'country': country_name,
            'month_str': month_str,
            'baseline_prob': baseline_prob,
            'baseline_prob_percent': f"{baseline_prob:.1%}",
            'baseline_fatalities': baseline_fatalities,
            'baseline_fatalities_str': f"{baseline_fatalities:.1f}",
            'climate_prob': climate_prob,
            'climate_fatalities': climate_fatalities,
            'climate_diff': climate_diff,
            'climate_diff_str': self._format_climate_diff(climate_diff),
            'risk_category': risk_category,
            'historical_avg': historical_avg,
            'historical_avg_str': f"{historical_avg:.1f}",
            'historical_trend': historical_trend,
            'forecast_vs_historical': self._compare_forecast_to_historical(
                baseline_fatalities, historical_avg
            ),
            'neighbor_avg': neighbor_context['avg'],
            'neighbor_avg_str': f"{neighbor_context['avg']:.1f}",
            'neighbor_max': neighbor_context['max'],
            'neighbor_max_str': f"{neighbor_context['max']:.1f}",
            'neighbor_comparison': neighbor_context['comparison'],
            'country_rank': country_rank['rank'],
            'country_total': country_rank['total'],
            'country_higher': country_rank['higher'],
            'country_lower': country_rank['lower'],
            'global_category': global_category['name'],
            'global_category_range': global_category['range'],
            'global_category_count': global_category['count']
        }
    
    def _categorize_risk(self, probability: float) -> str:
        if probability >= 0.95:
            return "Near-certain conflict"
        elif probability >= 0.75:
            return "Highly probable conflict"
        elif probability >= 0.50:
            return "Probable conflict"
        elif probability >= 0.25:
            return "Possible conflict"
        elif probability >= 0.05:
            return "Unlikely conflict"
        else:
            return "Near-certain no conflict"
    
    def _get_historical_context(self, historical_data: pd.DataFrame, 
                                 priogrid_gid: int) -> tuple[float, str]:
        grid_hist = historical_data[historical_data['priogrid_gid'] == priogrid_gid].copy()
        
        if grid_hist.empty:
            return 0.0, "no historical data"
        
        grid_hist = grid_hist.sort_values('month_id')
        values = grid_hist['ged_sb'].values
        
        avg = float(np.mean(values))
        
        if len(values) < 6:
            return avg, "limited data"
        
        recent_values = values[-12:]
        recent_avg = np.mean(recent_values)
        
        if len(values) >= 12:
            trend_slope = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
            
            if abs(trend_slope) < 1:
                trend = "stable"
            elif trend_slope > 0:
                trend = "increasing"
            else:
                trend = "decreasing"
        else:
            trend = "stable"
        
        if recent_avg > 100:
            level = "high"
        elif recent_avg > 10:
            level = "moderate"
        elif recent_avg > 0:
            level = "low"
        else:
            level = "minimal"
        
        return avg, f"{level} and {trend}"
    
    def _get_neighbor_context(self, forecast_data: pd.DataFrame, 
                               priogrid_gid: int, target_month_id: int) -> Dict[str, Any]:
        from grid_spatial_module import GridSpatialModule
        
        spatial = GridSpatialModule(target_month_id)
        neighbor_gids = spatial._get_neighbors(priogrid_gid)
        
        if not neighbor_gids:
            return {'avg': 0.0, 'max': 0.0, 'comparison': 'no neighbors'}
        
        neighbor_values = []
        for neighbor_gid in neighbor_gids:
            neighbor_data = forecast_data[
                (forecast_data['priogrid_gid'] == neighbor_gid) & 
                (forecast_data['month_id'] == target_month_id)
            ]
            if not neighbor_data.empty:
                neighbor_values.append(float(neighbor_data.iloc[0]['outcome_n']))
        
        if not neighbor_values:
            return {'avg': 0.0, 'max': 0.0, 'comparison': 'no neighbor data'}
        
        avg = float(np.mean(neighbor_values))
        max_val = float(max(neighbor_values))
        
        focal_data = forecast_data[
            (forecast_data['priogrid_gid'] == priogrid_gid) & 
            (forecast_data['month_id'] == target_month_id)
        ]
        
        if focal_data.empty:
            comparison = "similar to neighbors"
        else:
            focal_val = float(focal_data.iloc[0]['outcome_n'])
            
            if focal_val > avg * 1.5:
                comparison = "substantially higher than neighbors"
            elif focal_val > avg * 1.2:
                comparison = "higher than neighbors"
            elif focal_val < avg * 0.5:
                comparison = "substantially lower than neighbors"
            elif focal_val < avg * 0.8:
                comparison = "lower than neighbors"
            else:
                comparison = "similar to neighbors"
        
        return {'avg': avg, 'max': max_val, 'comparison': comparison}
    
    def _get_country_rank(self, forecast_data: pd.DataFrame, priogrid_gid: int,
                          target_month_id: int, country_name: Optional[str]) -> Dict[str, Any]:
        if not country_name:
            return {'rank': 0, 'total': 0, 'higher': 0, 'lower': 0}
        
        focal_data = forecast_data[
            (forecast_data['priogrid_gid'] == priogrid_gid) & 
            (forecast_data['month_id'] == target_month_id)
        ]
        
        if focal_data.empty:
            return {'rank': 0, 'total': 0, 'higher': 0, 'lower': 0}
        
        focal_value = float(focal_data.iloc[0]['outcome_n'])
        
        country_forecast = forecast_data[forecast_data['month_id'] == target_month_id].copy()
        country_grids = []
        
        for _, row in country_forecast.iterrows():
            grid_country = self.data_provider.get_country_name(int(row['priogrid_gid']))
            if grid_country == country_name:
                country_grids.append((int(row['priogrid_gid']), float(row['outcome_n'])))
        
        if not country_grids:
            return {'rank': 0, 'total': 0, 'higher': 0, 'lower': 0}
        
        country_grids.sort(key=lambda x: x[1], reverse=True)
        
        rank = next((i + 1 for i, (gid, _) in enumerate(country_grids) if gid == priogrid_gid), 0)
        total = len(country_grids)
        higher = rank - 1
        lower = total - rank
        
        return {'rank': rank, 'total': total, 'higher': higher, 'lower': lower}
    
    def _get_global_category(self, fatalities: float) -> Dict[str, Any]:
        if fatalities == 0:
            return {
                'name': 'lowest',
                'range': '0 fatalities',
                'count': 0
            }
        elif fatalities <= 10:
            return {
                'name': 'second lowest',
                'range': '1-10 fatalities',
                'count': 0
            }
        elif fatalities <= 100:
            return {
                'name': 'second highest',
                'range': '11-100 fatalities',
                'count': 0
            }
        else:
            return {
                'name': 'highest',
                'range': '101-1000 fatalities',
                'count': 0
            }
    
    def _compare_forecast_to_historical(self, forecast: float, historical: float) -> str:
        if historical == 0:
            if forecast > 0:
                return "higher than"
            else:
                return "consistent with"
        
        ratio = forecast / historical
        
        if ratio > 1.2:
            return "higher than"
        elif ratio < 0.8:
            return "lower than"
        else:
            return "consistent with"
    
    def _format_climate_diff(self, diff: Optional[float]) -> str:
        if diff is None:
            return "no climate data"
        
        if abs(diff) < 1:
            return "nearly identical"
        elif diff > 0:
            return f"{diff:.1f} higher"
        else:
            return f"{abs(diff):.1f} lower"


if __name__ == "__main__":
    extractor = GridBLUFDataExtractor()
    
    test_cases = [
        (174669, 561),
        (152235, 561),
        (158723, 555)
    ]
    
    for grid_id, month_id in test_cases:
        print(f"\n{'='*80}")
        print(f"Testing Grid {grid_id}, Month {month_id}")
        print('='*80)
        
        try:
            data = extractor.extract_bluf_data(grid_id, month_id)
            
            print(f"Grid: {data['grid_id']} ({data['country']})")
            print(f"Month: {data['month_str']}")
            print(f"\nBaseline Forecast:")
            print(f"  Probability: {data['baseline_prob_percent']}")
            print(f"  Fatalities: {data['baseline_fatalities_str']}")
            print(f"  Risk: {data['risk_category']}")
            print(f"\nClimate Comparison:")
            print(f"  Difference: {data['climate_diff_str']}")
            print(f"\nHistorical Context:")
            print(f"  Average: {data['historical_avg_str']}")
            print(f"  Trend: {data['historical_trend']}")
            print(f"  Forecast vs Historical: {data['forecast_vs_historical']}")
            print(f"\nSpatial Context:")
            print(f"  Neighbor avg: {data['neighbor_avg_str']}")
            print(f"  Neighbor max: {data['neighbor_max_str']}")
            print(f"  Comparison: {data['neighbor_comparison']}")
            print(f"\nCountry Ranking:")
            print(f"  Rank: {data['country_rank']}/{data['country_total']}")
            print(f"  Higher: {data['country_higher']}, Lower: {data['country_lower']}")
            print(f"\nGlobal Category:")
            print(f"  {data['global_category']} ({data['global_category_range']})")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()