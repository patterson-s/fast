import pandas as pd
import json

# Read the Excel files
cy_covariates = pd.read_excel(r"C:\Users\spatt\Desktop\FAST\data\cy_covariates.xlsx")
pb_forecasts = pd.read_excel(r"C:\Users\spatt\Desktop\FAST\data\pb_forecasts.xlsx")

# Get unique country mappings from pb_forecasts
country_mapping = pb_forecasts[['country_id', 'name.x', 'isoab.x']].drop_duplicates()

# Merge the datasets
merged_data = cy_covariates.merge(
    country_mapping, 
    on='country_id', 
    how='left'
)

# Save as JSON
merged_data.to_json(
    r"C:\Users\spatt\Desktop\FAST\data\cy_covariates.json", 
    orient='records', 
    indent=2
)

print(f"Merged dataset saved with {len(merged_data)} rows")