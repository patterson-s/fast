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
    
    print(f"Usage: python generate_grid_report.py <priogrid_gid> <month_id>")
    print(f"Generating report for grid {priogrid_gid}, month_id {target_month_id}")
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\vito_01")
    base_dir.mkdir(exist_ok=True)
    
    from GridDataProvider import GridDataProvider
    from grid_pdf_renderer import GridPDFRenderer
    from grid_temporal_module import GridTemporalModule
    
    data_provider = GridDataProvider()
    pdf_renderer = GridPDFRenderer(base_dir)
    
    forecast_data = data_provider.get_forecast_data()
    historical_data = data_provider.get_historical_data()
    
    modules = [
        GridTemporalModule(target_month_id)
    ]
    
    output_file = pdf_renderer.create_grid_report(
        priogrid_gid, target_month_id,
        modules, forecast_data, historical_data
    )
    
    print(f"Generated PDF report: {output_file}")

if __name__ == "__main__":
    main()