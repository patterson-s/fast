# ============== generate_batch_reports.py ==============
#!/usr/bin/env python3

import sys
from pathlib import Path
import random
from typing import List, Tuple, Dict
import pandas as pd

def get_all_country_month_combinations(data_provider) -> List[Tuple[str, int, int, str]]:
    forecast_data = data_provider.get_forecast_data()
    
    month_mappings = {
        552: (12, 2025),
        555: (3, 2026),
        561: (9, 2026)
    }
    
    combinations = []
    
    for outcome_n, (month, year) in month_mappings.items():
        month_data = forecast_data[forecast_data['outcome_n'] == outcome_n]
        
        for _, row in month_data.iterrows():
            country_code = row['isoab']
            prob = row['outcome_p']
            risk_category = data_provider.categorize_probability(prob)
            
            combinations.append((country_code, month, year, risk_category))
    
    return combinations

def sample_by_risk_category(combinations: List[Tuple[str, int, int, str]]) -> List[Tuple[str, int, int]]:
    risk_groups = {
        "Near-certain conflict": [],
        "Probable conflict": [],
        "Improbable conflict": [],
        "Near-certain no conflict": []
    }
    
    for combo in combinations:
        country_code, month, year, risk_category = combo
        risk_groups[risk_category].append((country_code, month, year))
    
    sampling_weights = {
        "Near-certain conflict": 40,
        "Probable conflict": 35,
        "Improbable conflict": 15,
        "Near-certain no conflict": 10
    }
    
    sampled = []
    
    for risk_category, weight in sampling_weights.items():
        available = risk_groups[risk_category]
        if available:
            sample_size = min(weight, len(available))
            sampled.extend(random.sample(available, sample_size))
    
    return sampled

def main():
    random.seed(42)
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\pdf_generator_03")
    output_dir = Path(r"C:\Users\spatt\Desktop\FAST\pdf_generator_03\evalatelier")
    output_dir.mkdir(exist_ok=True)
    
    from data_provider import DataProvider
    from pdf_renderer import PDFRenderer
    from monthly_temporal_module import MonthlyTemporalModule
    from covariate_distribution_module import CovariateDistributionModule
    from symlog_module import SymlogModule
    
    data_provider = DataProvider()
    pdf_renderer = PDFRenderer(output_dir)
    
    forecast_data = data_provider.get_forecast_data()
    historical_data = data_provider.get_historical_data()
    
    print("Getting all country-month combinations...")
    all_combinations = get_all_country_month_combinations(data_provider)
    print(f"Found {len(all_combinations)} total combinations")
    
    print("Sampling by risk category...")
    sampled_combinations = sample_by_risk_category(all_combinations)
    print(f"Selected {len(sampled_combinations)} samples for generation")
    
    risk_counts = {}
    for combo in all_combinations:
        risk_category = combo[3]
        if combo[:3] in sampled_combinations:
            risk_counts[risk_category] = risk_counts.get(risk_category, 0) + 1
    
    print("Sample distribution by risk category:")
    for risk, count in risk_counts.items():
        print(f"  {risk}: {count}")
    
    print("\nGenerating reports...")
    successful = 0
    failed = 0
    
    for i, (country_code, target_month, target_year) in enumerate(sampled_combinations, 1):
        try:
            country_name = data_provider.get_country_name(country_code)
            
            modules = [
                MonthlyTemporalModule(target_month, target_year),
                CovariateDistributionModule(),
                SymlogModule(target_month, target_year)
            ]
            
            output_file = pdf_renderer.create_monthly_report(
                country_code, country_name, target_month, target_year,
                modules, forecast_data, historical_data
            )
            
            print(f"[{i}/{len(sampled_combinations)}] Generated: {output_file.name}")
            successful += 1
            
        except Exception as e:
            print(f"[{i}/{len(sampled_combinations)}] FAILED {country_code} {target_month}/{target_year}: {e}")
            failed += 1
    
    print(f"\nBatch generation complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Output directory: {output_dir}")

if __name__ == "__main__":
    main()