#!/usr/bin/env python3

from pathlib import Path
import fitz
from typing import List, Tuple

def pdf_to_png(pdf_path: Path, output_dir: Path) -> Path:
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=300)
    
    png_path = output_dir / f"{pdf_path.stem}.png"
    pix.save(png_path)
    doc.close()
    
    return png_path

def get_all_forecasts(data_provider) -> List[Tuple[str, int, int]]:
    forecast_data = data_provider.get_forecast_data()
    
    month_mappings = {
        552: (12, 2025),
        555: (3, 2026),
        561: (9, 2026)
    }
    
    forecasts = []
    
    for outcome_n, (month, year) in month_mappings.items():
        month_data = forecast_data[forecast_data['outcome_n'] == outcome_n]
        
        for _, row in month_data.iterrows():
            country_code = row['isoab']
            forecasts.append((country_code, month, year))
    
    return forecasts

def main():
    temp_dir = Path(r"C:\Users\spatt\Desktop\FAST\pdf_generator_03\temp_pdfs")
    output_dir = Path(r"G:\My Drive\UdeM\fall2025\forecasting\ptb")
    
    temp_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    from data_provider import DataProvider
    from pdf_renderer import PDFRenderer
    from monthly_temporal_module import MonthlyTemporalModule
    from covariate_distribution_module import CovariateDistributionModule
    from symlog_module import SymlogModule
    
    data_provider = DataProvider()
    pdf_renderer = PDFRenderer(temp_dir)
    
    forecast_data = data_provider.get_forecast_data()
    historical_data = data_provider.get_historical_data()
    
    print("Getting all forecast combinations...")
    all_forecasts = get_all_forecasts(data_provider)
    print(f"Found {len(all_forecasts)} total forecasts to generate")
    
    print("\nGenerating reports...")
    successful = 0
    failed = 0
    
    for i, (country_code, target_month, target_year) in enumerate(all_forecasts, 1):
        try:
            country_name = data_provider.get_country_name(country_code)
            
            modules = [
                MonthlyTemporalModule(target_month, target_year),
                CovariateDistributionModule(),
                SymlogModule(target_month, target_year)
            ]
            
            pdf_file = pdf_renderer.create_monthly_report(
                country_code, country_name, target_month, target_year,
                modules, forecast_data, historical_data
            )
            
            png_file = pdf_to_png(pdf_file, output_dir)
            
            pdf_file.unlink()
            
            print(f"[{i}/{len(all_forecasts)}] Generated: {png_file.name}")
            successful += 1
            
        except Exception as e:
            print(f"[{i}/{len(all_forecasts)}] FAILED {country_code} {target_month}/{target_year}: {e}")
            failed += 1
    
    temp_dir.rmdir()
    
    print(f"\nFinal generation complete:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Output directory: {output_dir}")

if __name__ == "__main__":
    main()