import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from prompt_loader import PromptLoader
from data_extractor import DataExtractor
from prompt_executor import PromptExecutor
import sys

sys.path.append(str(Path(__file__).parent.parent / "pdf_generator_03"))
from data_provider import DataProvider

class SingleVariantRunner:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.loader = PromptLoader(base_dir)
        self.extractor = DataExtractor()
        self.executor = PromptExecutor()
        self.data_provider = DataProvider()
        
        self.results_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_ptb\output")
        self.results_dir.mkdir(exist_ok=True)
    
    def get_all_countries(self) -> List[str]:
        forecast_data = self.data_provider.get_forecast_data()
        return sorted(forecast_data['isoab'].unique().tolist())
    
    def get_test_cases(self, test_months: List[tuple]) -> List[tuple]:
        countries = self.get_all_countries()
        test_cases = []
        
        for country_code in countries:
            for month, year in test_months:
                test_cases.append((country_code, month, year))
        
        return test_cases
    
    def run_variant(self, variant_name: str, test_months: List[tuple]) -> Dict[str, Any]:
        test_cases = self.get_test_cases(test_months)
        
        results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "variant": variant_name,
                "test_months": [{"month": m, "year": y} for m, y in test_months],
                "total_test_cases": len(test_cases)
            },
            "results": []
        }
        
        total_tests = len(test_cases)
        current_test = 0
        entries_since_save = 0
        
        for country_code, month, year in test_cases:
            country_name = self.data_provider.get_country_name(country_code)
            current_test += 1
            
            print(f"[{current_test}/{total_tests}] {country_code} {month}/{year}")
            
            try:
                template_data = self.extractor.extract_template_data(country_code, month, year)
                variant = self.loader.load_variant(variant_name)
                result = self.executor.execute(variant, template_data)
                
                test_case = {
                    "country_code": country_code,
                    "country_name": country_name,
                    "month": month,
                    "year": year,
                    "forecast_data": {
                        "probability": template_data['probability'],
                        "probability_percent": template_data['probability_percent'],
                        "predicted_fatalities": template_data['predicted_fatalities'],
                        "risk_category": template_data['risk_category'],
                        "intensity_category": template_data['intensity_category']
                    },
                    "success": result.success,
                    "output": result.raw_output if result.success else None,
                    "error": result.error if not result.success else None
                }
                
                results["results"].append(test_case)
                entries_since_save += 1
                
                if entries_since_save >= 50:
                    self.save_intermediate_results(results, len(results["results"]))
                    entries_since_save = 0
                
            except Exception as e:
                print(f"ERROR: {country_code} {month}/{year} - {e}")
                results["results"].append({
                    "country_code": country_code,
                    "country_name": country_name,
                    "month": month,
                    "year": year,
                    "error": str(e)
                })
                entries_since_save += 1
                
                if entries_since_save >= 50:
                    self.save_intermediate_results(results, len(results["results"]))
                    entries_since_save = 0
        
        return results
    
    def save_intermediate_results(self, results: Dict[str, Any], count: int):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"intermediate_{count}entries_{timestamp}.json"
        output_path = self.results_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n>>> Intermediate results saved: {filename} <<<\n")
    
    def save_results(self, results: Dict[str, Any], filename: str):
        output_path = self.results_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_ptb")
    
    runner = SingleVariantRunner(base_dir)
    
    variant_name = "bluf_v2"
    test_months = [
        (12, 2025),
        (3, 2026),
        (9, 2026)
    ]
    
    print("Starting single variant run...")
    print(f"Variant: {variant_name}")
    print(f"Months: {test_months}")
    
    test_cases = runner.get_test_cases(test_months)
    print(f"Total test cases: {len(test_cases)}")
    print("="*80)
    
    results = runner.run_variant(variant_name, test_months)
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"Total tests: {results['metadata']['total_test_cases']}")
    print(f"Successful: {sum(1 for r in results['results'] if r.get('success', False))}")
    print(f"Failed: {sum(1 for r in results['results'] if 'error' in r or not r.get('success', True))}")
    
    output_file = runner.save_results(results, "ptb_promptv2.json")