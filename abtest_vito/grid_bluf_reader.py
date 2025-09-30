import json
from pathlib import Path
from typing import Optional

class GridBLUFReader:
    def __init__(self, blufs_dir: Path):
        self.blufs_dir = Path(blufs_dir)
        
        if not self.blufs_dir.exists():
            raise FileNotFoundError(f"BLUF directory not found: {blufs_dir}")
    
    def get_bluf(self, grid_id: int, month_id: int) -> Optional[str]:
        filename = f"bluf_{grid_id}_{month_id}.json"
        bluf_path = self.blufs_dir / filename
        
        if not bluf_path.exists():
            return None
        
        try:
            with open(bluf_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('bluf_text')
        
        except Exception as e:
            print(f"Warning: Failed to read BLUF file {filename}: {e}")
            return None
    
    def bluf_exists(self, grid_id: int, month_id: int) -> bool:
        filename = f"bluf_{grid_id}_{month_id}.json"
        return (self.blufs_dir / filename).exists()
    
    def get_bluf_metadata(self, grid_id: int, month_id: int) -> Optional[dict]:
        filename = f"bluf_{grid_id}_{month_id}.json"
        bluf_path = self.blufs_dir / filename
        
        if not bluf_path.exists():
            return None
        
        try:
            with open(bluf_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except Exception as e:
            print(f"Warning: Failed to read BLUF file {filename}: {e}")
            return None


if __name__ == "__main__":
    output_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_vito\output")
    
    reader = GridBLUFReader(output_dir)
    
    test_cases = [
        (174669, 561),
        (152235, 561),
        (999999, 555)
    ]
    
    for grid_id, month_id in test_cases:
        print(f"\n{'='*80}")
        print(f"Grid {grid_id}, Month {month_id}")
        print('='*80)
        
        if reader.bluf_exists(grid_id, month_id):
            bluf_text = reader.get_bluf(grid_id, month_id)
            metadata = reader.get_bluf_metadata(grid_id, month_id)
            
            print(f"Status: FOUND")
            print(f"Country: {metadata.get('country')}")
            print(f"Month: {metadata.get('month_str')}")
            print(f"Generated: {metadata.get('generated_at')}")
            print(f"\nBLUF:")
            print(bluf_text)
        else:
            print(f"Status: NOT FOUND")