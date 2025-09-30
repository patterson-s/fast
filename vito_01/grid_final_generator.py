#!/usr/bin/env python3

from pathlib import Path
import fitz
from typing import List, Tuple
import sys
import warnings
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings('ignore')

sys.path.append(str(Path(__file__).parent))
from GridDataProvider import GridDataProvider
from grid_pdf_renderer import GridPDFRenderer
from grid_temporal_module import GridTemporalModule
from grid_comparison_module import GridComparisonModule
from grid_spatial_module import GridSpatialModule

def pdf_to_png(pdf_path: Path, output_dir: Path, grid_id: int, month_id: int) -> Path:
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=300)
    
    png_filename = f"pg_{grid_id}_{month_id}.png"
    png_path = output_dir / png_filename
    pix.save(png_path)
    doc.close()
    
    return png_path

def get_all_grid_forecasts(data_provider: GridDataProvider, 
                           target_month_ids: List[int]) -> List[Tuple[int, int]]:
    baseline_forecast = data_provider.get_baseline_forecast()
    
    forecasts = []
    for month_id in target_month_ids:
        month_data = baseline_forecast[baseline_forecast['month_id'] == month_id]
        grids = month_data['priogrid_gid'].unique()
        
        for grid_id in grids:
            forecasts.append((int(grid_id), month_id))
    
    return forecasts

def process_single_grid(grid_id: int, month_id: int, temp_dir: Path, output_dir: Path) -> Tuple[bool, str]:
    try:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
        data_provider = GridDataProvider()
        pdf_renderer = GridPDFRenderer(temp_dir)
        
        forecast_data = {
            'baseline': data_provider.get_baseline_forecast(),
            'climate': data_provider.get_climate_forecast()
        }
        historical_data = data_provider.get_historical_data()
        
        modules = [
            GridTemporalModule(month_id),
            GridComparisonModule(month_id),
            GridSpatialModule(month_id)
        ]
        
        pdf_file = pdf_renderer.create_grid_report(
            grid_id, month_id, modules, forecast_data, historical_data
        )
        
        png_file = pdf_to_png(pdf_file, output_dir, grid_id, month_id)
        
        pdf_file.unlink()
        
        return (True, png_file.name)
        
    except Exception as e:
        return (False, str(e))
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

def main():
    temp_dir = Path(r"C:\Users\spatt\Desktop\FAST\vito_01\temp_pdfs")
    output_dir = Path(r"G:\My Drive\UdeM\fall2025\forecasting\vito")
    
    temp_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    data_provider = GridDataProvider()
    target_month_ids = [555, 558, 561]
    
    all_forecasts = get_all_grid_forecasts(data_provider, target_month_ids)
    total = len(all_forecasts)
    
    print(f"Processing {total} grid-month combinations with 5 workers...")
    
    successful = 0
    failed = 0
    
    with ProcessPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(process_single_grid, grid_id, month_id, temp_dir, output_dir): (grid_id, month_id)
            for grid_id, month_id in all_forecasts
        }
        
        for future in as_completed(futures):
            grid_id, month_id = futures[future]
            success, result = future.result()
            
            if success:
                successful += 1
            else:
                failed += 1
            
            if (successful + failed) % 100 == 0:
                print(f"[{successful + failed}/{total}] Success: {successful}, Failed: {failed}")
    
    if temp_dir.exists() and not any(temp_dir.iterdir()):
        temp_dir.rmdir()
    
    print(f"\nComplete: {successful} successful, {failed} failed")
    print(f"Output: {output_dir}")

if __name__ == "__main__":
    main()