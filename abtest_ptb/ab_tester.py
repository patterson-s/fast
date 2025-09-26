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

class ABTester:
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
    
    def get_filtered_test_cases(self, test_months: List[tuple], exclude_lowest_risk: bool = True) -> List[tuple]:
        countries = self.get_all_countries()
        test_cases = []
        
        for country_code in countries:
            for month, year in test_months:
                try:
                    risk_category, _ = self.data_provider.get_risk_intensity_category(
                        country_code, month, year
                    )
                    
                    if exclude_lowest_risk and risk_category == "Near-certain no conflict":
                        continue
                    
                    test_cases.append((country_code, month, year, risk_category))
                    
                except Exception as e:
                    print(f"Warning: Could not get risk category for {country_code} {month}/{year}: {e}")
        
        return test_cases
    
    def run_ab_test(self, variant_names: List[str], test_months: List[tuple], exclude_lowest_risk: bool = True) -> Dict[str, Any]:
        test_cases = self.get_filtered_test_cases(test_months, exclude_lowest_risk)
        
        results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "variants": variant_names,
                "test_months": [{"month": m, "year": y} for m, y in test_months],
                "exclude_lowest_risk": exclude_lowest_risk,
                "total_test_cases": len(test_cases),
                "total_tests": len(test_cases) * len(variant_names)
            },
            "results": []
        }
        
        total_tests = len(test_cases) * len(variant_names)
        current_test = 0
        entries_since_save = 0
        
        for country_code, month, year, risk_category in test_cases:
            country_name = self.data_provider.get_country_name(country_code)
            
            try:
                template_data = self.extractor.extract_template_data(country_code, month, year)
                
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
                        "intensity_category": template_data['intensity_category'],
                        "prob_percentile": template_data['prob_percentile'],
                        "pred_percentile": template_data['pred_percentile'],
                        "cohort": template_data['cohort_str'],
                        "similarity_label": template_data['similarity_label'],
                        "cohort_prefix": template_data['cohort_prefix'],
                        "historical_avg": template_data['historical_avg'],
                        "trend_slope": template_data['trend_slope'],
                        "trend_desc": template_data['trend_desc'],
                        "forecast_vs_historical": template_data['forecast_vs_historical'],
                        "covariate_desc": template_data['covariate_desc']
                    },
                    "variants": {}
                }
                
                for variant_name in variant_names:
                    current_test += 1
                    print(f"[{current_test}/{total_tests}] {country_code} {month}/{year} ({risk_category}) - {variant_name}")
                    
                    variant = self.loader.load_variant(variant_name)
                    result = self.executor.execute(variant, template_data)
                    
                    test_case["variants"][variant_name] = {
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
        filename = f"ab_test_intermediate_{count}entries_{timestamp}.json"
        output_path = self.results_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n>>> Intermediate results saved: {filename} <<<\n")
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ab_test_{timestamp}.json"
        
        output_path = self.results_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_ptb")
    
    tester = ABTester(base_dir)
    
    variant_names = ["bluf_v1", "bluf_v2"]
    test_months = [
        (12, 2025),
        (3, 2026),
        (9, 2026)
    ]
    
    print("Starting A/B test...")
    print(f"Variants: {variant_names}")
    print(f"Months: {test_months}")
    
    test_cases = tester.get_filtered_test_cases(test_months, exclude_lowest_risk=True)
    print(f"Test cases (excluding lowest risk): {len(test_cases)}")
    
    risk_breakdown = {}
    for _, _, _, risk in test_cases:
        risk_breakdown[risk] = risk_breakdown.get(risk, 0) + 1
    
    print("\nRisk category breakdown:")
    for risk, count in sorted(risk_breakdown.items()):
        print(f"  {risk}: {count}")
    
    print("="*80)
    
    results = tester.run_ab_test(variant_names, test_months, exclude_lowest_risk=True)
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print(f"Total tests: {results['metadata']['total_tests']}")
    print(f"Successful: {sum(1 for r in results['results'] if 'error' not in r)}")
    print(f"Failed: {sum(1 for r in results['results'] if 'error' in r)}")
    
    output_file = tester.save_results(results)