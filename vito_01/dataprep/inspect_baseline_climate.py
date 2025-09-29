#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import numpy as np

def inspect_model_files():
    base_path = Path(r"C:\Users\spatt\Desktop\FAST\data\dorazio_base.parquet")
    climate_path = Path(r"C:\Users\spatt\Desktop\FAST\data\dorazio_climate.parquet")
    
    print("=== BASELINE MODEL ===")
    baseline = pd.read_parquet(base_path)
    print(f"\nShape: {baseline.shape}")
    print(f"\nColumns: {baseline.columns.tolist()}")
    print(f"\nFirst few rows:")
    print(baseline.head())
    print(f"\nData types:")
    print(baseline.dtypes)
    print(f"\nUnique grids: {baseline['priogrid_gid'].nunique():,}")
    print(f"\nUnique months: {baseline['month_id'].nunique()}")
    print(f"\nMonth IDs: {sorted(baseline['month_id'].unique())}")
    
    print("\n\n=== CLIMATE MODEL ===")
    climate = pd.read_parquet(climate_path)
    print(f"\nShape: {climate.shape}")
    print(f"\nColumns: {climate.columns.tolist()}")
    print(f"\nFirst few rows:")
    print(climate.head())
    print(f"\nData types:")
    print(climate.dtypes)
    print(f"\nUnique grids: {climate['priogrid_gid'].nunique():,}")
    print(f"\nUnique months: {climate['month_id'].nunique()}")
    print(f"\nMonth IDs: {sorted(climate['month_id'].unique())}")
    
    print("\n\n=== COMPARISON ===")
    print(f"\nSame number of rows? {len(baseline) == len(climate)}")
    print(f"\nSame grids? {set(baseline['priogrid_gid']) == set(climate['priogrid_gid'])}")
    print(f"\nSame months? {set(baseline['month_id']) == set(climate['month_id'])}")
    
    sample_grid = 152235
    sample_month = 561
    
    baseline_sample = baseline[(baseline['priogrid_gid'] == sample_grid) & 
                               (baseline['month_id'] == sample_month)]
    climate_sample = climate[(climate['priogrid_gid'] == sample_grid) & 
                            (climate['month_id'] == sample_month)]
    
    print(f"\n\n=== SAMPLE GRID {sample_grid}, MONTH {sample_month} ===")
    print("\nBaseline:")
    print(baseline_sample)
    print("\nClimate:")
    print(climate_sample)
    
    if not baseline_sample.empty and not climate_sample.empty:
        baseline_pred = baseline_sample['outcome_p'].values[0]
        climate_pred = climate_sample['outcome_p'].values[0]
        diff = climate_pred - baseline_pred
        print(f"\nBaseline prediction: {baseline_pred:.6f}")
        print(f"Climate prediction: {climate_pred:.6f}")
        print(f"Difference: {diff:.6f}")
        print(f"Percent change: {(diff/baseline_pred)*100:.2f}%")
    
    print("\n\n=== OVERALL STATISTICS ===")
    print("\nBaseline outcome_p:")
    print(baseline['outcome_p'].describe())
    print("\nClimate outcome_p:")
    print(climate['outcome_p'].describe())
    
    merged = baseline.merge(climate, on=['priogrid_gid', 'month_id'], 
                           suffixes=('_base', '_climate'))
    merged['diff'] = merged['outcome_p_climate'] - merged['outcome_p_base']
    merged['abs_diff'] = np.abs(merged['diff'])
    merged['pct_change'] = (merged['diff'] / merged['outcome_p_base']) * 100
    
    print("\n\nDifferences (climate - baseline):")
    print(merged['diff'].describe())
    print("\nAbsolute differences:")
    print(merged['abs_diff'].describe())
    print("\nPercent changes:")
    print(merged['pct_change'].describe())
    
    print(f"\nGrids where climate > baseline: {(merged['diff'] > 0).sum():,}")
    print(f"Grids where climate < baseline: {(merged['diff'] < 0).sum():,}")
    print(f"Grids where climate == baseline: {(merged['diff'] == 0).sum():,}")
    
    print("\n\n=== OUTCOME_N vs OUTCOME_P COMPARISON ===")
    print("\nBaseline outcome_n values:")
    print(baseline['outcome_n'].value_counts().head(20))
    print("\nBaseline outcome_n statistics:")
    print(baseline['outcome_n'].describe())
    
    print("\n\nClimate outcome_n values:")
    print(climate['outcome_n'].value_counts().head(20))
    print("\nClimate outcome_n statistics:")
    print(climate['outcome_n'].describe())
    
    print("\n\nRelationship between outcome_n and outcome_p (baseline):")
    sample_comparison = baseline[['outcome_n', 'outcome_p']].drop_duplicates().sort_values('outcome_n').head(30)
    print(sample_comparison)
    
    print("\n\nCases where outcome_n > 0 (baseline):")
    nonzero_baseline = baseline[baseline['outcome_n'] > 0][['priogrid_gid', 'month_id', 'outcome_n', 'outcome_p']]
    print(f"Count: {len(nonzero_baseline)}")
    print(nonzero_baseline.head(20))
    
    print("\n\nCases where outcome_p > 0 but outcome_n = 0 (baseline):")
    prob_no_count = baseline[(baseline['outcome_p'] > 0) & (baseline['outcome_n'] == 0)]
    print(f"Count: {len(prob_no_count)}")
    print(prob_no_count[['priogrid_gid', 'month_id', 'outcome_n', 'outcome_p']].head(20))

if __name__ == "__main__":
    inspect_model_files()