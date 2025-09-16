#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

FORECAST_PARQUET = r"C:\Users\spatt\Desktop\FAST\data\FAST-Forecast.parquet"
HISTORICAL_CSV = r"C:\Users\spatt\Desktop\FAST\analysis\views_px_fatalities002_cm_ALL_20150101_20251201.csv"

def test_seasonal_comparison():
    # Load data
    forecast_df = pd.read_parquet(FORECAST_PARQUET)
    historical_df = pd.read_csv(HISTORICAL_CSV)
    
    country_code = "SOM"
    
    # Get forecast data
    forecast_data = forecast_df[forecast_df['isoab'] == country_code]
    forecast_values = {
        'December': forecast_data[forecast_data['outcome_n'] == 552]['predicted'].iloc[0] if len(forecast_data[forecast_data['outcome_n'] == 552]) > 0 else 0,
        'March': forecast_data[forecast_data['outcome_n'] == 555]['predicted'].iloc[0] if len(forecast_data[forecast_data['outcome_n'] == 555]) > 0 else 0,
        'September': forecast_data[forecast_data['outcome_n'] == 561]['predicted'].iloc[0] if len(forecast_data[forecast_data['outcome_n'] == 561]) > 0 else 0
    }
    
    # Get historical data
    historical_data = historical_df[historical_df['isoab'] == country_code].copy()
    historical_data['total_fatalities'] = (
        historical_data['ucdp_ged_ns_best_sum'] + 
        historical_data['ucdp_ged_sb_best_sum'] + 
        historical_data['ucdp_ged_os_best_sum']
    )
    
    # Extract data for specific years and months
    def get_historical_values(year_ranges):
        values = {}
        for year_label, (dec_year, mar_year, sep_year) in year_ranges.items():
            dec_val = historical_data[(historical_data['year'] == dec_year) & (historical_data['month'] == 12)]['total_fatalities'].sum()
            mar_val = historical_data[(historical_data['year'] == mar_year) & (historical_data['month'] == 3)]['total_fatalities'].sum()
            sep_val = historical_data[(historical_data['year'] == sep_year) & (historical_data['month'] == 9)]['total_fatalities'].sum()
            
            values[year_label] = {
                'December': dec_val,
                'March': mar_val, 
                'September': sep_val
            }
        return values
    
    year_ranges = {
        '2023/2024': (2023, 2024, 2024),
        '2020/2021': (2020, 2021, 2021), 
        '2015/2016': (2015, 2016, 2016)
    }
    
    historical_values = get_historical_values(year_ranges)
    
    # Print debug info
    print("Forecast values:", forecast_values)
    print("Historical values:", historical_values)
    
    # Create the plot
    months = ['December', 'March', 'September']  # Corrected order
    x = np.arange(len(months))
    width = 0.2
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot bars for each year group (forecast moved to rightmost position)
    colors = ['green', 'orange', 'darkred', 'steelblue']
    year_order = ['2015/2016', '2020/2021', '2023/2024']
    
    # Map months to their specific years for labeling
    month_year_mapping = {
        'September': {'2015/2016': '2016', '2020/2021': '2021', '2023/2024': '2024', 'forecast': '2026'},
        'March': {'2015/2016': '2016', '2020/2021': '2021', '2023/2024': '2024', 'forecast': '2026'},
        'December': {'2015/2016': '2015', '2020/2021': '2020', '2023/2024': '2023', 'forecast': '2025'}
    }
    
    # Historical bars (left to right: oldest to newest)
    for i, (year_label, color) in enumerate(zip(year_order, colors[:3])):
        hist_vals = [historical_values[year_label][month] for month in months]
        bars = ax.bar(x - 1.5*width + i*width, hist_vals, width, color=color, alpha=0.8)
        
        # Add value labels on each bar
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + max(hist_vals)*0.01,
                       f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    # Forecast bars (rightmost)
    forecast_vals = [forecast_values[month] for month in months]
    bars = ax.bar(x + 1.5*width, forecast_vals, width, color=colors[3], alpha=0.8)
    
    # Add value labels on forecast bars
    for j, bar in enumerate(bars):
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height + max(forecast_vals)*0.01,
                   f'{int(height)}', ha='center', va='bottom', fontsize=9, weight='bold')
    
    # Create custom x-axis labels for each bar
    all_x_positions = []
    all_labels = []
    
    for month_idx, month in enumerate(months):
        base_x = x[month_idx]
        # Add labels for each bar in this month group (just years)
        for i, year_label in enumerate(year_order):
            all_x_positions.append(base_x - 1.5*width + i*width)
            specific_year = month_year_mapping[month][year_label]
            all_labels.append(specific_year)
        
        # Add forecast label (just year)
        all_x_positions.append(base_x + 1.5*width)
        forecast_year = month_year_mapping[month]['forecast']
        all_labels.append(forecast_year)
    
    ax.set_ylabel('Fatalities', fontsize=12)
    ax.set_title(f'Seasonal Fatality Comparison - {country_code}', fontsize=14)
    ax.set_xticks(all_x_positions)
    ax.set_xticklabels(all_labels, fontsize=10, rotation=45, ha='right')
    
    # Add month labels below the year labels
    for month_idx, month in enumerate(months):
        base_x = x[month_idx]
        ax.text(base_x, ax.get_ylim()[0] - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.15, 
               month, ha='center', va='top', fontsize=12, weight='bold')
    
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('seasonal_comparison_test.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    test_seasonal_comparison()