#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import random

def main():
    target_month_id = 561
    
    print(f"Generating sample reports for month_id {target_month_id}")
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\vito_01")
    samples_dir = base_dir / "sample_reports"
    samples_dir.mkdir(exist_ok=True)
    
    from GridDataProvider import GridDataProvider
    from grid_pdf_renderer import GridPDFRenderer
    from grid_temporal_module import GridTemporalModule
    from grid_comparison_module import GridComparisonModule
    from grid_spatial_module import GridSpatialModule
    
    data_provider = GridDataProvider()
    
    baseline_forecast = data_provider.get_baseline_forecast()
    climate_forecast = data_provider.get_climate_forecast()
    historical_data = data_provider.get_historical_data()
    
    target_data = baseline_forecast[baseline_forecast['month_id'] == target_month_id].copy()
    
    categories = {
        'zero': (0, 0),
        'low': (0.01, 10),
        'medium': (10.01, 100),
        'high': (100.01, 1000),
        'very_high': (1000.01, 100000)
    }
    
    samples_per_category = 2
    
    selected_grids = []
    
    for cat_name, (min_val, max_val) in categories.items():
        cat_grids = target_data[
            (target_data['outcome_n'] >= min_val) & 
            (target_data['outcome_n'] <= max_val)
        ]
        
        if len(cat_grids) == 0:
            print(f"No grids found in category {cat_name} ({min_val}-{max_val})")
            continue
        
        sample_size = min(samples_per_category, len(cat_grids))
        sampled = cat_grids.sample(n=sample_size, random_state=42)
        
        for _, row in sampled.iterrows():
            grid_id = int(row['priogrid_gid'])
            forecast_val = float(row['outcome_n'])
            country = data_provider.get_country_name(grid_id)
            selected_grids.append({
                'gid': grid_id,
                'category': cat_name,
                'forecast': forecast_val,
                'country': country
            })
    
    print(f"\nSelected {len(selected_grids)} grids:")
    for grid in selected_grids:
        print(f"  Grid {grid['gid']:6d} ({grid['country']:20s}) - {grid['category']:10s} - {grid['forecast']:8.1f} fatalities")
    
    pdf_renderer = GridPDFRenderer(samples_dir)
    
    forecast_data = {
        'baseline': baseline_forecast,
        'climate': climate_forecast
    }
    
    modules = [
        GridTemporalModule(target_month_id),
        GridComparisonModule(target_month_id),
        GridSpatialModule(target_month_id)
    ]
    
    print("\nGenerating reports...")
    for i, grid in enumerate(selected_grids, 1):
        print(f"{i}/{len(selected_grids)}: Grid {grid['gid']} ({grid['country']})...")
        
        try:
            output_file = pdf_renderer.create_grid_report(
                grid['gid'], target_month_id,
                modules, forecast_data, historical_data
            )
            print(f"  ✓ Generated: {output_file.name}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\nAll reports saved to: {samples_dir}")

if __name__ == "__main__":
    main()