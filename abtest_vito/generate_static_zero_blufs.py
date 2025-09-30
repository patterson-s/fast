import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import sys
import numpy as np

sys.path.append(str(Path(__file__).parent.parent / "vito_01"))
from GridDataProvider import GridDataProvider
from grid_spatial_module import GridSpatialModule

class StaticZeroBLUFGenerator:
    def __init__(self, output_dir: Path):
        self.data_provider = GridDataProvider()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def categorize_zero_forecast(self, prob: float, hist_avg: float) -> str:
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
    
    def get_template(self, category: str, grid_id: int, country: str, 
                     month_str: str, prob: float, hist_avg: float, 
                     neighbor_comparison: str) -> str:
        prob_pct = f"{prob*100:.1f}"
        hist_avg_str = f"{hist_avg:.1f}"
        
        templates = {
            "ZERO_HISTORY_ZERO_FORECAST": 
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. This grid has no recorded history of state-based armed conflict over the past five years, and the forecast reflects this complete absence of violence. The grid's forecast is {neighbor_comparison}, consistent with the low-violence character of the surrounding area.",
            
            "MINIMAL_HISTORY_ZERO_FORECAST":
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. Historically, this grid has experienced minimal violence (averaging {hist_avg_str} fatalities), and the forecast continues this pattern of very low conflict. The grid is {neighbor_comparison}.",
            
            "PAST_VIOLENCE_NOW_ZERO":
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. While this grid has experienced violence in the past (historical average: {hist_avg_str} fatalities), recent trends indicate a substantial decline, and the forecast reflects this reduction to near-zero levels. Spatially, the grid is {neighbor_comparison}.",
            
            "VERY_LOW_PROB_NO_HISTORY":
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. This grid has no history of violence, and the forecast reflects near-certain absence of conflict. Spatially, the grid is {neighbor_comparison}.",
            
            "VERY_LOW_PROB_SOME_HISTORY":
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. While this grid has some history of violence (averaging {hist_avg_str} fatalities), the forecast indicates a very low likelihood of conflict. The grid is {neighbor_comparison}.",
            
            "LOW_PROB_NO_HISTORY":
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. This grid has no history of violence, though the forecast shows a low but non-negligible probability of conflict. The grid's forecast is {neighbor_comparison}.",
            
            "LOW_PROB_SOME_HISTORY":
                f"Grid {grid_id} ({country}) has a forecast of 0.0 fatalities in {month_str}, with a {prob_pct}% probability of at least one battle death. This grid has some history of violence (averaging {hist_avg_str} fatalities), and while the expected fatalities are zero, there remains a low probability of conflict occurring. Spatially, the grid is {neighbor_comparison}."
        }
        
        return templates.get(category, templates["ZERO_HISTORY_ZERO_FORECAST"])
    
    def get_neighbor_comparison(self, baseline_forecast, spatial_module, 
                                grid_id: int, month_id: int) -> str:
        try:
            neighbor_gids = spatial_module._get_neighbors(grid_id)
            
            if not neighbor_gids:
                return "in an isolated area"
            
            neighbor_values = []
            for neighbor_gid in neighbor_gids:
                neighbor_data = baseline_forecast[
                    (baseline_forecast['priogrid_gid'] == neighbor_gid) & 
                    (baseline_forecast['month_id'] == month_id)
                ]
                if not neighbor_data.empty:
                    neighbor_values.append(float(neighbor_data.iloc[0]['outcome_n']))
            
            if not neighbor_values:
                return "similar to its neighbors"
            
            avg = float(np.mean(neighbor_values))
            
            if avg < 0.1:
                return "similar to its neighbors"
            elif avg < 1:
                return "similar to its low-violence neighbors"
            else:
                return "lower than its neighbors"
        
        except Exception:
            return "similar to its neighbors"
    
    def generate_all_zero_blufs(self, target_month_ids: List[int]) -> Dict:
        baseline_forecast = self.data_provider.get_baseline_forecast()
        historical_data = self.data_provider.get_historical_data()
        
        results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "target_months": target_month_ids,
                "generation_type": "static_zero_blufs"
            },
            "results": []
        }
        
        total = 0
        successful = 0
        
        for month_id in target_month_ids:
            spatial_module = GridSpatialModule(month_id)
            
            month_data = baseline_forecast[baseline_forecast['month_id'] == month_id]
            zero_grids = month_data[month_data['outcome_n'] == 0]
            
            print(f"\nProcessing month {month_id}: {len(zero_grids)} zero grids")
            
            for idx, (_, row) in enumerate(zero_grids.iterrows(), 1):
                if idx % 500 == 0:
                    print(f"  Processed {idx}/{len(zero_grids)}")
                
                total += 1
                grid_id = int(row['priogrid_gid'])
                prob = float(row['outcome_p'])
                
                try:
                    country = self.data_provider.get_country_name(grid_id)
                    month_str = self.data_provider.month_id_to_string(month_id)
                    
                    grid_hist = historical_data[historical_data['priogrid_gid'] == grid_id]
                    hist_avg = float(grid_hist['ged_sb'].mean()) if not grid_hist.empty else 0.0
                    
                    neighbor_comparison = self.get_neighbor_comparison(
                        baseline_forecast, spatial_module, grid_id, month_id
                    )
                    
                    category = self.categorize_zero_forecast(prob, hist_avg)
                    
                    bluf_text = self.get_template(
                        category, grid_id, country, month_str, 
                        prob, hist_avg, neighbor_comparison
                    )
                    
                    self.save_individual_bluf(grid_id, month_id, bluf_text, 
                                             country, month_str, prob, category)
                    
                    successful += 1
                    
                    results["results"].append({
                        "grid_id": grid_id,
                        "month_id": month_id,
                        "category": category,
                        "success": True
                    })
                
                except Exception as e:
                    print(f"  Error processing grid {grid_id}: {e}")
                    results["results"].append({
                        "grid_id": grid_id,
                        "month_id": month_id,
                        "success": False,
                        "error": str(e)
                    })
        
        results["metadata"]["total"] = total
        results["metadata"]["successful"] = successful
        
        return results
    
    def save_individual_bluf(self, grid_id: int, month_id: int, bluf_text: str,
                            country: str, month_str: str, prob: float, category: str):
        filename = f"bluf_{grid_id}_{month_id}.json"
        output_path = self.output_dir / filename
        
        data = {
            "grid_id": grid_id,
            "month_id": month_id,
            "country": country,
            "month_str": month_str,
            "bluf_text": bluf_text,
            "generated_at": datetime.now().isoformat(),
            "generation_type": "static_zero",
            "category": category,
            "forecast_data": {
                "baseline_prob": prob,
                "baseline_fatalities": 0.0,
                "risk_category": "Near-certain no conflict"
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    output_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_vito\output")
    
    generator = StaticZeroBLUFGenerator(output_dir)
    
    target_month_ids = [555, 558, 561]
    
    print("Starting static zero BLUF generation...")
    print(f"Target months: {target_month_ids}")
    print("="*80)
    
    results = generator.generate_all_zero_blufs(target_month_ids)
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"Total: {results['metadata']['total']}")
    print(f"Successful: {results['metadata']['successful']}")
    print(f"Failed: {results['metadata']['total'] - results['metadata']['successful']}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = output_dir / f"static_zero_blufs_{timestamp}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSummary saved to: {summary_file}")