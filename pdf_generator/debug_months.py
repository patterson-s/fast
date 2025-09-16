#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

FORECAST_PARQUET = r"C:\Users\spatt\Desktop\FAST\data\FAST-Forecast.parquet"

def debug_month_mapping():
    df = pd.read_parquet(FORECAST_PARQUET)
    
    print("Debugging month mapping for SOM...")
    som_data = df[df['isoab'] == 'SOM'].copy()
    
    if som_data.empty:
        print("No SOM data found!")
        return
    
    print(f"Total SOM rows: {len(som_data)}")
    print(f"Outcome_n range: {som_data['outcome_n'].min()} to {som_data['outcome_n'].max()}")
    print()
    
    print("Sample of outcome_n and dates:")
    sample_data = som_data[['outcome_n', 'dates']].drop_duplicates().sort_values('outcome_n').head(15)
    for _, row in sample_data.iterrows():
        date_str = pd.to_datetime(row['dates']).strftime("%B %Y") if pd.notnull(row['dates']) else "No date"
        month_index = row['outcome_n'] - 550
        print(f"outcome_n: {row['outcome_n']}, month_index: {month_index}, date: {date_str}")
    
    print("\nLooking for specific months we want:")
    target_months = ['December 2025', 'March 2026', 'September 2026']
    
    for target_month in target_months:
        print(f"\nSearching for {target_month}:")
        for _, row in som_data.iterrows():
            if pd.notnull(row['dates']):
                date_obj = pd.to_datetime(row['dates'])
                date_str = date_obj.strftime("%B %Y")
                if date_str == target_month:
                    month_index = row['outcome_n'] - 550
                    print(f"  Found: outcome_n={row['outcome_n']}, month_index={month_index}")
                    break
        else:
            print(f"  Not found!")
    
    print("\nAll unique dates in data:")
    unique_dates = som_data['dates'].drop_duplicates().sort_values()
    for date in unique_dates.head(20):
        if pd.notnull(date):
            date_obj = pd.to_datetime(date)
            print(f"  {date_obj.strftime('%B %Y')}")

if __name__ == "__main__":
    debug_month_mapping()