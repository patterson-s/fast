#!/usr/bin/env python3

import sys
from pathlib import Path

def main():
    if len(sys.argv) >= 2:
        country_code = sys.argv[1].upper()
    else:
        country_code = "NGA"  # Nigeria for testing
        print(f"Using default country: {country_code}")
    
    if len(sys.argv) >= 3:
        target_month = int(sys.argv[2])
    else:
        target_month = 9  # September for testing
        print(f"Using default month: {target_month}")
    
    if len(sys.argv) >= 4:
        target_year = int(sys.argv[3])
    else:
        target_year = 2026
        print(f"Using default year: {target_year}")
    
    print(f"Usage: python generate_monthly_report.py <ISO3> <month> <year>")
    print(f"Generating report for {country_code}, month {target_month}, year {target_year}")
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\pdf_generator_03")
    base_dir.mkdir(exist_ok=True)
    
    from data_provider import DataProvider
    from pdf_renderer import PDFRenderer
    from monthly_temporal_module import MonthlyTemporalModule
    from covariate_distribution_module import CovariateDistributionModule
    from symlog_module import SymlogModule
    
    # Initialize components
    data_provider = DataProvider()
    pdf_renderer = PDFRenderer(base_dir)
    
    # Get data
    forecast_data = data_provider.get_forecast_data()
    historical_data = data_provider.get_historical_data()
    country_name = data_provider.get_country_name(country_code)
    
    # Create modules
    modules = [
        MonthlyTemporalModule(target_month, target_year),
        CovariateDistributionModule(),
        SymlogModule(target_month, target_year)
    ]
    
    # Generate report
    output_file = pdf_renderer.create_monthly_report(
        country_code, country_name, target_month, target_year,
        modules, forecast_data, historical_data
    )
    
    print(f"Generated PDF report: {output_file}")

if __name__ == "__main__":
    main()