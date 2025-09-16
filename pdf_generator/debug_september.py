#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

FORECAST_PARQUET = r"C:\Users\spatt\Desktop\FAST\data\FAST-Forecast.parquet"

def debug_september_mapping():
    df = pd.read_parquet(FORECAST_PARQUET)
    
    print("Debugging September 2026 mapping for SOM...")
    som_data = df[df['isoab'] == 'SOM'].copy()
    
    print("All outcome_n values and their corresponding dates:")
    for _, row in som_data.iterrows():
        date_str = pd.to_datetime(row['dates']).strftime("%B %Y") if pd.notnull(row['dates']) else "No date"
        month_index = row['outcome_n'] - 550
        print(f"outcome_n: {row['outcome_n']}, month_index: {month_index}, date: {date_str}, probability: {row['outcome_p']:.3f}, predicted: {row['predicted']:.1f}")
    
    print("\nSpecifically checking September 2026:")
    sep_2026 = som_data[som_data['dates'].dt.strftime('%B %Y') == 'September 2026'] if not som_data.empty else pd.DataFrame()
    
    if not sep_2026.empty:
        for _, row in sep_2026.iterrows():
            month_index = row['outcome_n'] - 550
            print(f"September 2026: outcome_n={row['outcome_n']}, month_index={month_index}")
            print(f"  Probability: {row['outcome_p']:.3f}")
            print(f"  Predicted fatalities: {row['predicted']:.1f}")
    else:
        print("No September 2026 data found!")
    
    print("\nChecking what we're currently using (month_index=11):")
    current_outcome_n = 550 + 11  # 561
    current_data = som_data[som_data['outcome_n'] == current_outcome_n]
    
    if not current_data.empty:
        row = current_data.iloc[0]
        date_str = pd.to_datetime(row['dates']).strftime("%B %Y") if pd.notnull(row['dates']) else "No date"
        print(f"Using outcome_n={current_outcome_n} (month_index=11):")
        print(f"  Date: {date_str}")
        print(f"  Probability: {row['outcome_p']:.3f}")
        print(f"  Predicted fatalities: {row['predicted']:.1f}")

if __name__ == "__main__":
    debug_september_mapping()