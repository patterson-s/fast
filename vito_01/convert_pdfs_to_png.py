import sys
from pathlib import Path
from pdf2image import convert_from_path
from typing import List, Tuple

sys.path.append(str(Path(__file__).parent.parent / "vito_01"))
from GridDataProvider import GridDataProvider
from grid_pdf_renderer import GridPDFRenderer
from grid_temporal_module import GridTemporalModule
from grid_comparison_module import GridComparisonModule
from grid_spatial_module import GridSpatialModule

class PDFtoPNGConverter:
    def __init__(self, pdf_dir: Path, png_output_dir: Path, dpi: int = 150):
        self.pdf_dir = Path(pdf_dir)
        self.png_output_dir = Path(png_output_dir)
        self.dpi = dpi
        self.png_output_dir.mkdir(parents=True, exist_ok=True)
    
    def convert_pdf_to_png(self, grid_id: int, month_id: int) -> Path:
        pdf_filename = f"grid_{grid_id}_forecast_{month_id}.pdf"
        pdf_path = self.pdf_dir / pdf_filename
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        images = convert_from_path(str(pdf_path), dpi=self.dpi)
        
        if not images:
            raise ValueError(f"No pages in PDF: {pdf_path}")
        
        png_filename = f"pg_{grid_id}_{month_id}.png"
        png_path = self.png_output_dir / png_filename
        
        images[0].save(str(png_path), 'PNG')
        
        return png_path
    
    def generate_and_convert_single(self, grid_id: int, month_id: int, 
                                    data_provider: GridDataProvider,
                                    pdf_renderer: GridPDFRenderer,
                                    modules: List) -> Path:
        forecast_data = {
            'baseline': data_provider.get_baseline_forecast(),
            'climate': data_provider.get_climate_forecast()
        }
        historical_data = data_provider.get_historical_data()
        
        pdf_path = pdf_renderer.create_grid_report(
            grid_id, month_id, modules, forecast_data, historical_data
        )
        
        png_path = self.convert_pdf_to_png(grid_id, month_id)
        
        return png_path


def test_conversions():
    pdf_dir = Path(r"C:\Users\spatt\Desktop\FAST\vito_01")
    png_output_dir = Path(r"G:\My Drive\UdeM\fall2025\forecasting\vito")
    
    data_provider = GridDataProvider()
    pdf_renderer = GridPDFRenderer(pdf_dir)
    converter = PDFtoPNGConverter(pdf_dir, png_output_dir, dpi=150)
    
    test_cases = [
        (174669, 561),
        (152235, 561),
        (158456, 555)
    ]
    
    print("Testing PDF generation and PNG conversion...")
    print("="*80)
    
    for grid_id, month_id in test_cases:
        try:
            country = data_provider.get_country_name(grid_id)
            month_str = data_provider.month_id_to_string(month_id)
            
            print(f"\nGrid {grid_id} ({country}), {month_str}")
            print("-"*80)
            
            modules = [
                GridTemporalModule(month_id),
                GridComparisonModule(month_id),
                GridSpatialModule(month_id)
            ]
            
            png_path = converter.generate_and_convert_single(
                grid_id, month_id, data_provider, pdf_renderer, modules
            )
            
            print(f"✓ PNG created: {png_path.name}")
            print(f"  Full path: {png_path}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("Test complete. Check output directory:")
    print(f"  {png_output_dir}")


if __name__ == "__main__":
    test_conversions()