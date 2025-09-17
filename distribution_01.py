#!/usr/bin/env python3

import pandas as pd
from pathlib import Path
from config import DEF_PARQUET
from data_loader import load_dataframe
from utils import categorize_prob_single, categorize_band_single

def analyze_category_combinations():
    df = load_dataframe(DEF_PARQUET)
    
    df['prob_category'] = df['outcome_p'].apply(categorize_prob_single)
    df['band_category'] = df['predicted'].apply(categorize_band_single)
    
    crosstab = pd.crosstab(
        df['prob_category'], 
        df['band_category'], 
        margins=True
    )
    
    total_records = len(df)
    
    print("FAST-cm Forecast Category Distribution")
    print("=" * 50)
    print(f"Total country-month records: {total_records:,}")
    print()
    
    print("Cross-tabulation: Conflict Likelihood vs Conflict Intensity")
    print("-" * 80)
    print(crosstab)
    print()
    
    print("Percentage Distribution:")
    print("-" * 30)
    pct_crosstab = pd.crosstab(
        df['prob_category'], 
        df['band_category'], 
        normalize='all'
    ) * 100
    print(pct_crosstab.round(2))
    print()
    
    print("Non-zero combinations (count, percentage):")
    print("-" * 45)
    for prob_cat in df['prob_category'].unique():
        for band_cat in df['band_category'].unique():
            count = len(df[(df['prob_category'] == prob_cat) & (df['band_category'] == band_cat)])
            if count > 0:
                pct = (count / total_records) * 100
                print(f"{prob_cat} + {band_cat}: {count:,} ({pct:.2f}%)")

if __name__ == "__main__":
    analyze_category_combinations()