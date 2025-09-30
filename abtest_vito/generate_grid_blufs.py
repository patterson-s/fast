import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.append(str(Path(__file__).parent.parent / "vito_01"))
from GridDataProvider import GridDataProvider
from grid_bluf_data_extractor import GridBLUFDataExtractor
from grid_bluf_generator import GridBLUFGenerator

class GridBLUFBulkGenerator:
    def __init__(self, prompts_dir: Path, output_dir: Path):
        self.data_provider = GridDataProvider()
        self.prompts_dir = prompts_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self.successful = 0
        self.failed = 0
    
    def get_all_grid_month_pairs(self, target_month_ids: List[int], 
                                  exclude_zero_fatalities: bool = False) -> List[Tuple[int, int]]:
        baseline_forecast = self.data_provider.get_baseline_forecast()
        
        test_cases = []
        for month_id in target_month_ids:
            month_data = baseline_forecast[baseline_forecast['month_id'] == month_id]
            
            if exclude_zero_fatalities:
                month_data = month_data[month_data['outcome_n'] > 0]
            
            grids = month_data['priogrid_gid'].unique()
            
            for grid_id in grids:
                test_cases.append((int(grid_id), month_id))
        
        return test_cases
    
    def process_single_grid(self, grid_id: int, month_id: int) -> Dict[str, Any]:
        extractor = GridBLUFDataExtractor()
        generator = GridBLUFGenerator(self.prompts_dir)
        
        country_name = self.data_provider.get_country_name(grid_id)
        month_str = self.data_provider.month_id_to_string(month_id)
        
        try:
            bluf_data = extractor.extract_bluf_data(grid_id, month_id)
            bluf_text = generator.generate_bluf(bluf_data)
            
            self.save_individual_bluf(grid_id, month_id, bluf_text, bluf_data)
            
            with self.lock:
                self.successful += 1
            
            return {
                "grid_id": grid_id,
                "month_id": month_id,
                "country": country_name,
                "month_str": month_str,
                "bluf": bluf_text,
                "success": True,
                "forecast_data": {
                    "baseline_prob": bluf_data['baseline_prob'],
                    "baseline_fatalities": bluf_data['baseline_fatalities'],
                    "risk_category": bluf_data['risk_category']
                }
            }
            
        except Exception as e:
            with self.lock:
                self.failed += 1
            
            return {
                "grid_id": grid_id,
                "month_id": month_id,
                "country": country_name,
                "month_str": month_str,
                "success": False,
                "error": str(e)
            }
    
    def generate_all_blufs(self, target_month_ids: List[int], 
                          exclude_zero_fatalities: bool = False,
                          max_workers: int = 5) -> Dict[str, Any]:
        test_cases = self.get_all_grid_month_pairs(target_month_ids, exclude_zero_fatalities)
        
        results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "target_months": target_month_ids,
                "total_test_cases": len(test_cases),
                "max_workers": max_workers
            },
            "results": []
        }
        
        total_tests = len(test_cases)
        completed = 0
        entries_since_save = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_case = {
                executor.submit(self.process_single_grid, grid_id, month_id): (grid_id, month_id)
                for grid_id, month_id in test_cases
            }
            
            for future in as_completed(future_to_case):
                grid_id, month_id = future_to_case[future]
                completed += 1
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        print(f"[{completed}/{total_tests}] ✓ Grid {grid_id} ({result['country']}), {result['month_str']}")
                    else:
                        print(f"[{completed}/{total_tests}] ✗ Grid {grid_id} ({result['country']}), {result['month_str']} - {result['error']}")
                    
                    results["results"].append(result)
                    entries_since_save += 1
                    
                    if entries_since_save >= 50:
                        self.save_intermediate_results(results, self.successful, self.failed)
                        entries_since_save = 0
                        
                except Exception as e:
                    print(f"[{completed}/{total_tests}] ✗ Grid {grid_id} - Unexpected error: {e}")
                    results["results"].append({
                        "grid_id": grid_id,
                        "month_id": month_id,
                        "success": False,
                        "error": str(e)
                    })
                    entries_since_save += 1
                    
                    if entries_since_save >= 50:
                        self.save_intermediate_results(results, self.successful, self.failed)
                        entries_since_save = 0
        
        return results
    
    def save_individual_bluf(self, grid_id: int, month_id: int, 
                            bluf_text: str, bluf_data: Dict[str, Any]):
        filename = f"bluf_{grid_id}_{month_id}.json"
        output_path = self.output_dir / filename
        
        data = {
            "grid_id": grid_id,
            "month_id": month_id,
            "country": bluf_data['country'],
            "month_str": bluf_data['month_str'],
            "bluf_text": bluf_text,
            "generated_at": datetime.now().isoformat(),
            "forecast_data": {
                "baseline_prob": bluf_data['baseline_prob'],
                "baseline_fatalities": bluf_data['baseline_fatalities'],
                "risk_category": bluf_data['risk_category']
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def save_intermediate_results(self, results: Dict[str, Any], 
                                  successful: int, failed: int):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bulk_intermediate_{successful}success_{failed}failed_{timestamp}.json"
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n>>> Intermediate results saved: {filename} <<<")
        print(f">>> Successful: {successful}, Failed: {failed} <<<\n")
    
    def save_final_results(self, results: Dict[str, Any], filename: str = None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bulk_blufs_{timestamp}.json"
        
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nFinal results saved to: {output_path}")
        return output_path


if __name__ == "__main__":
    prompts_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_vito\bluf_01")
    output_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_vito\output")
    
    generator = GridBLUFBulkGenerator(prompts_dir, output_dir)
    
    target_month_ids = [555, 558, 561]
    exclude_zero = True
    
    print("Starting bulk BLUF generation...")
    print(f"Target months: {target_month_ids}")
    print(f"Exclude zero fatalities: {exclude_zero}")
    
    test_cases = generator.get_all_grid_month_pairs(target_month_ids, exclude_zero)
    print(f"Total test cases: {len(test_cases)}")
    print("="*80)
    
    results = generator.generate_all_blufs(target_month_ids, exclude_zero, max_workers=5)
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"Total: {results['metadata']['total_test_cases']}")
    print(f"Successful: {sum(1 for r in results['results'] if r.get('success', False))}")
    print(f"Failed: {sum(1 for r in results['results'] if not r.get('success', True))}")
    
    generator.save_final_results(results)