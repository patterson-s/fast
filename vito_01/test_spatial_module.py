#!/usr/bin/env python3

import sys
from pathlib import Path

def main():
    if len(sys.argv) >= 2:
        priogrid_gid = int(sys.argv[1])
    else:
        priogrid_gid = 152235
        print(f"Using default grid: {priogrid_gid}")
    
    if len(sys.argv) >= 3:
        target_month_id = int(sys.argv[2])
    else:
        target_month_id = 561
        print(f"Using default month_id: {target_month_id}")
    
    print(f"\nTesting spatial module for grid {priogrid_gid}, month_id {target_month_id}")
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\vito_01")
    output_dir = base_dir / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    from GridDataProvider import GridDataProvider
    from grid_spatial_module import GridSpatialModule
    
    data_provider = GridDataProvider()
    
    print("\nLoading data...")
    baseline_forecast = data_provider.get_baseline_forecast()
    climate_forecast = data_provider.get_climate_forecast()
    historical_data = data_provider.get_historical_data()
    
    forecast_data = {
        'baseline': baseline_forecast,
        'climate': climate_forecast
    }
    
    print("\nCreating spatial module...")
    spatial_module = GridSpatialModule(target_month_id)
    
    print("\nTesting context...")
    context = spatial_module.get_context()
    print(f"Context: {context}")
    
    print("\nGenerating visualization...")
    img_path = spatial_module.generate_content(
        priogrid_gid, target_month_id,
        forecast_data, historical_data, output_dir
    )
    
    if img_path:
        print(f"Generated image: {img_path}")
    else:
        print("Failed to generate image")
    
    print("\nGenerating interpretation...")
    interpretation = spatial_module.get_interpretation(
        priogrid_gid, target_month_id,
        forecast_data, historical_data
    )
    print(f"Interpretation: {interpretation}")
    
    print("\nTest complete!")

if __name__ == "__main__":
    main()