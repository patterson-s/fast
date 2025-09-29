#!/usr/bin/env python3

import json
from pathlib import Path

def create_simplified_priogrid():
    input_path = Path(r"C:\Users\spatt\Desktop\FAST\vito_01\dataprep\priogrid.json")
    output_path = Path(r"C:\Users\spatt\Desktop\FAST\vito_01\dataprep\priogrid_lookup.json")
    
    grid_mapping = {}
    
    print(f"Reading {input_path}...")
    with open(input_path, 'r') as f:
        for line in f:
            data = json.loads(line.strip())
            gid = data['gid']
            iso3 = data['iso3']
            
            if gid not in grid_mapping:
                grid_mapping[gid] = iso3
    
    print(f"Found {len(grid_mapping):,} unique grid cells")
    
    print(f"Writing to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(grid_mapping, f, indent=2)
    
    print("Done!")
    
    print("\nSample entries:")
    for i, (gid, iso3) in enumerate(list(grid_mapping.items())[:10]):
        print(f"  {gid}: {iso3}")

if __name__ == "__main__":
    create_simplified_priogrid()