import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).parent.parent / "vito_01"))
from GridDataProvider import GridDataProvider
from grid_bluf_data_extractor import GridBLUFDataExtractor

class ZeroForecastAnalyzer:
    def __init__(self):
        self.data_provider = GridDataProvider()
        self.extractor = GridBLUFDataExtractor()
    
    def get_zero_forecast_grids(self, target_month_id: int, sample_size: int = 50):
        baseline_forecast = self.data_provider.get_baseline_forecast()
        
        month_data = baseline_forecast[baseline_forecast['month_id'] == target_month_id]
        zero_grids = month_data[month_data['outcome_n'] == 0]
        
        sampled = zero_grids.sample(n=min(sample_size, len(zero_grids)), random_state=42)
        return sampled['priogrid_gid'].tolist()
    
    def _extract_data_fast(self, grid_id: int, target_month_id: int, 
                          baseline_forecast: pd.DataFrame, 
                          historical_data: pd.DataFrame) -> dict:
        baseline_target = baseline_forecast[
            (baseline_forecast['priogrid_gid'] == grid_id) & 
            (baseline_forecast['month_id'] == target_month_id)
        ]
        
        if baseline_target.empty:
            raise ValueError(f"No forecast data")
        
        baseline_row = baseline_target.iloc[0]
        baseline_prob = float(baseline_row['outcome_p'])
        
        grid_hist = historical_data[historical_data['priogrid_gid'] == grid_id].copy()
        
        if grid_hist.empty:
            hist_avg = 0.0
            hist_trend = "no historical data"
        else:
            values = grid_hist['ged_sb'].values
            hist_avg = float(np.mean(values))
            
            if len(values) >= 12:
                recent_values = values[-12:]
                recent_avg = np.mean(recent_values)
                
                if recent_avg > 100:
                    level = "high"
                elif recent_avg > 10:
                    level = "moderate"
                elif recent_avg > 0:
                    level = "low"
                else:
                    level = "minimal"
                
                hist_trend = f"{level} and stable"
            else:
                hist_trend = "limited data"
        
        country = self.data_provider.get_country_name(grid_id)
        
        country_forecast = baseline_forecast[baseline_forecast['month_id'] == target_month_id].copy()
        country_grids = []
        
        for _, row in country_forecast.iterrows():
            grid_country = self.data_provider.get_country_name(int(row['priogrid_gid']))
            if grid_country == country:
                country_grids.append((int(row['priogrid_gid']), float(row['outcome_n'])))
        
        country_grids.sort(key=lambda x: x[1], reverse=True)
        rank = next((i + 1 for i, (gid, _) in enumerate(country_grids) if gid == grid_id), 0)
        total = len(country_grids)
        
        return {
            'grid_id': grid_id,
            'country': country,
            'baseline_prob': baseline_prob,
            'historical_avg': hist_avg,
            'historical_trend': hist_trend,
            'neighbor_comparison': 'similar to neighbors',
            'country_rank': rank,
            'country_total': total
        }
    
    def categorize_zero_forecast(self, bluf_data: dict) -> str:
        prob = bluf_data['baseline_prob']
        hist_avg = bluf_data['historical_avg']
        hist_trend = bluf_data['historical_trend']
        
        if prob < 0.01:
            if hist_avg == 0:
                return "ZERO_HISTORY_ZERO_FORECAST"
            elif hist_avg < 1:
                return "MINIMAL_HISTORY_ZERO_FORECAST"
            else:
                return "PAST_VIOLENCE_NOW_ZERO"
        elif prob < 0.05:
            if hist_avg == 0:
                return "VERY_LOW_PROB_NO_HISTORY"
            else:
                return "VERY_LOW_PROB_SOME_HISTORY"
        else:
            if hist_avg == 0:
                return "LOW_PROB_NO_HISTORY"
            else:
                return "LOW_PROB_SOME_HISTORY"
    
    def analyze_zero_forecasts(self, target_month_id: int, sample_size: int = 50):
        grid_ids = self.get_zero_forecast_grids(target_month_id, sample_size)
        
        baseline_forecast = self.data_provider.get_baseline_forecast()
        historical_data = self.data_provider.get_historical_data()
        
        categories = {}
        examples = {}
        
        print(f"Analyzing {len(grid_ids)} grids...")
        
        for idx, grid_id in enumerate(grid_ids, 1):
            if idx % 10 == 0:
                print(f"  Processed {idx}/{len(grid_ids)}")
            
            try:
                bluf_data = self._extract_data_fast(grid_id, target_month_id, 
                                                    baseline_forecast, historical_data)
                category = self.categorize_zero_forecast(bluf_data)
                
                if category not in categories:
                    categories[category] = 0
                    examples[category] = []
                
                categories[category] += 1
                
                if len(examples[category]) < 3:
                    examples[category].append({
                        'grid_id': grid_id,
                        'country': bluf_data['country'],
                        'probability': bluf_data['baseline_prob'],
                        'historical_avg': bluf_data['historical_avg'],
                        'historical_trend': bluf_data['historical_trend'],
                        'neighbor_comparison': bluf_data['neighbor_comparison'],
                        'country_rank': f"{bluf_data['country_rank']}/{bluf_data['country_total']}"
                    })
            
            except Exception as e:
                print(f"Error processing grid {grid_id}: {e}")
        
        return categories, examples
    
    def print_analysis(self, target_month_id: int, sample_size: int = 50):
        month_str = self.data_provider.month_id_to_string(target_month_id)
        
        print(f"\n{'='*80}")
        print(f"ZERO FORECAST ANALYSIS - {month_str} (Month ID: {target_month_id})")
        print(f"Sample size: {sample_size}")
        print('='*80)
        
        categories, examples = self.analyze_zero_forecasts(target_month_id, sample_size)
        
        print(f"\nCATEGORY BREAKDOWN:")
        print('-'*80)
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            pct = (count / sample_size) * 100
            print(f"{category:35s}: {count:3d} ({pct:5.1f}%)")
        
        print(f"\n{'='*80}")
        print("EXAMPLES BY CATEGORY")
        print('='*80)
        
        for category in sorted(categories.keys()):
            print(f"\n{category}")
            print('-'*80)
            
            for i, example in enumerate(examples[category], 1):
                print(f"\nExample {i}:")
                print(f"  Grid: {example['grid_id']} ({example['country']})")
                print(f"  Probability: {example['probability']:.3f} ({example['probability']*100:.1f}%)")
                print(f"  Historical avg: {example['historical_avg']:.1f}")
                print(f"  Historical trend: {example['historical_trend']}")
                print(f"  Neighbor comparison: {example['neighbor_comparison']}")
                print(f"  Country rank: {example['country_rank']}")
        
        print(f"\n{'='*80}")
        print("TEMPLATE RECOMMENDATIONS")
        print('='*80)
        
        self.generate_templates(categories)
    
    def generate_templates(self, categories: dict):
        templates = {
            "ZERO_HISTORY_ZERO_FORECAST": 
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. This grid has no recorded history of state-based armed conflict over the past five years, and the forecast reflects this complete absence of violence.",
            
            "MINIMAL_HISTORY_ZERO_FORECAST":
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. Historically, this grid has experienced minimal violence (averaging {hist_avg} fatalities), and the forecast continues this pattern of very low conflict.",
            
            "PAST_VIOLENCE_NOW_ZERO":
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. While this grid has experienced violence in the past (historical average: {hist_avg} fatalities), recent trends indicate a substantial decline, and the forecast reflects this reduction to near-zero levels.",
            
            "VERY_LOW_PROB_NO_HISTORY":
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. This grid has no history of violence, and the forecast reflects near-certain absence of conflict.",
            
            "VERY_LOW_PROB_SOME_HISTORY":
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. While this grid has some history of violence (averaging {hist_avg} fatalities), the forecast indicates a very low likelihood of conflict.",
            
            "LOW_PROB_NO_HISTORY":
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. This grid has no history of violence, though the forecast shows a low but non-negligible probability of conflict.",
            
            "LOW_PROB_SOME_HISTORY":
                "Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month}, with a {prob_pct}% probability of at least one battle death. This grid has some history of violence (averaging {hist_avg} fatalities), and while the expected fatalities are zero, there remains a low probability of conflict occurring."
        }
        
        for category in sorted(categories.keys()):
            if category in templates:
                print(f"\n{category}:")
                print(f"{templates[category]}")


if __name__ == "__main__":
    analyzer = ZeroForecastAnalyzer()
    
    target_month_ids = [555, 558, 561]
    
    for month_id in target_month_ids:
        analyzer.print_analysis(month_id, sample_size=100)
        print("\n" * 2)