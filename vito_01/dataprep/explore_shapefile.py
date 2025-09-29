#!/usr/bin/env python3

from pathlib import Path
import geopandas as gpd
import pandas as pd

def main():
    shapefile_path = Path(r"C:\Users\spatt\Desktop\FAST\vito_01\dataprep\shapes\priogrid_cell.shp")
    
    print("Loading shapefile...")
    gdf = gpd.read_file(shapefile_path)
    
    print(f"\n=== SHAPEFILE INSPECTION ===")
    print(f"Total grid cells: {len(gdf):,}")
    print(f"\nColumns: {gdf.columns.tolist()}")
    print(f"\nCRS: {gdf.crs}")
    print(f"\nGeometry type: {gdf.geometry.type.unique()}")
    
    print(f"\n=== SAMPLE DATA ===")
    print(gdf.head(10))
    
    print(f"\n=== DATA TYPES ===")
    print(gdf.dtypes)
    
    print(f"\n=== GRID ID COLUMN ===")
    potential_id_cols = [col for col in gdf.columns if 'gid' in col.lower() or 'id' in col.lower()]
    print(f"Potential ID columns: {potential_id_cols}")
    
    if potential_id_cols:
        id_col = potential_id_cols[0]
        print(f"\nUsing '{id_col}' as grid identifier")
        print(f"Min ID: {gdf[id_col].min()}")
        print(f"Max ID: {gdf[id_col].max()}")
        print(f"Unique IDs: {gdf[id_col].nunique():,}")
        
        test_gid = 152235
        if test_gid in gdf[id_col].values:
            print(f"\nTest grid {test_gid} found in shapefile")
            test_row = gdf[gdf[id_col] == test_gid].iloc[0]
            print(f"Test grid geometry: {test_row.geometry}")
            print(f"Test grid bounds: {test_row.geometry.bounds}")
        else:
            print(f"\nTest grid {test_gid} NOT found in shapefile")
    
    print(f"\n=== FINDING NEIGHBORS FOR TEST GRID ===")
    if potential_id_cols:
        id_col = potential_id_cols[0]
        test_gid = 152235
        
        if test_gid in gdf[id_col].values:
            focal_geom = gdf[gdf[id_col] == test_gid].iloc[0].geometry
            
            neighbors = gdf[gdf.geometry.touches(focal_geom)]
            print(f"\nNeighbors found using touches(): {len(neighbors)}")
            if len(neighbors) > 0:
                print(f"Neighbor IDs: {sorted(neighbors[id_col].tolist())}")
            
            buffer_distance = 0.1
            neighbors_buffer = gdf[gdf.geometry.buffer(buffer_distance).intersects(focal_geom) & 
                                   (gdf[id_col] != test_gid)]
            print(f"\nNeighbors found using buffer intersection: {len(neighbors_buffer)}")
            if len(neighbors_buffer) > 0:
                print(f"Neighbor IDs: {sorted(neighbors_buffer[id_col].tolist())}")
    
    print(f"\n=== CHECKING COUNTRY INFORMATION ===")
    country_cols = [col for col in gdf.columns if 'country' in col.lower() or 'name' in col.lower()]
    print(f"Potential country columns: {country_cols}")
    
    if country_cols:
        for col in country_cols:
            print(f"\n{col} unique values: {gdf[col].nunique()}")
            print(f"Sample values: {gdf[col].head(10).tolist()}")

if __name__ == "__main__":
    main()