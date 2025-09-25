import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import sys
sys.path.append('.')

from data_provider import DataProvider

def create_compact_cluster_viz(country_code: str, target_month: int, target_year: int):
    data_provider = DataProvider()
    month_data = data_provider.get_monthly_forecast_distribution(target_month, target_year)
    
    if month_data.empty:
        print("No data available")
        return None
    
    # Categorize all countries
    month_data['prob_category'] = month_data['outcome_p'].apply(data_provider.categorize_probability)
    
    # Define cluster order and colors (shortened labels)
    cluster_order = [
        "No conflict",
        "Improbable conflict", 
        "Probable conflict",
        "Certain conflict"
    ]
    
    cluster_colors = {
        "No conflict": "lightblue",
        "Improbable conflict": "yellow",
        "Probable conflict": "orange", 
        "Certain conflict": "red"
    }
    
    # Map full names to short names
    cluster_mapping = {
        "Near-certain no conflict": "No conflict",
        "Improbable conflict": "Improbable conflict",
        "Probable conflict": "Probable conflict",
        "Near-certain conflict": "Certain conflict"
    }
    
    # Count countries in each cluster (using full names, mapping to short names)
    full_cluster_counts = {}
    for full_cluster in ["Near-certain no conflict", "Improbable conflict", "Probable conflict", "Near-certain conflict"]:
        full_cluster_counts[full_cluster] = len(month_data[month_data['prob_category'] == full_cluster])
    
    cluster_counts = {}
    for full_name, short_name in cluster_mapping.items():
        cluster_counts[short_name] = full_cluster_counts[full_name]
    
    # Get target country's cluster
    target_country_data = month_data[month_data['isoab'] == country_code]
    if target_country_data.empty:
        print(f"No data for country {country_code}")
        return None
    
    target_cluster = cluster_mapping[target_country_data.iloc[0]['prob_category']]
    print(f"Target country {country_code} is in cluster: {target_cluster}")
    
    # Get countries in target cluster, sorted by predicted fatalities
    cluster_countries = month_data[month_data['prob_category'] == target_cluster].copy()
    cluster_countries = cluster_countries.sort_values('predicted', ascending=False)
    
    print(f"Countries in {target_cluster} cluster:")
    for _, row in cluster_countries.iterrows():
        name = data_provider.get_country_name(row['isoab'])
        print(f"  {row['isoab']}: {name} - {row['predicted']:.1f}")
    
    # Limit to top 5
    cluster_countries = cluster_countries.head(5)
    
    # Create figure - just the bar plot
    fig, ax_bar = plt.subplots(1, 1, figsize=(4, 6))
    
    # Left side: VERTICAL proportion bar
    total_countries = sum(cluster_counts.values())
    cumulative = 0
    
    for i, cluster in enumerate(cluster_order):
        count = cluster_counts[cluster]
        proportion = count / total_countries
        
        # Emphasize target cluster, make others transparent
        if cluster == target_cluster:
            alpha = 1.0
            edgecolor = 'black'
            linewidth = 3
        else:
            alpha = 0.6
            edgecolor = 'gray'
            linewidth = 0.5
            
        ax_bar.bar(0, proportion, bottom=cumulative, width=0.3, 
                   color=cluster_colors[cluster], alpha=alpha,
                   edgecolor=edgecolor, linewidth=linewidth)
        
        cumulative += proportion
    
    ax_bar.set_ylim(0, 1)
    ax_bar.set_xlim(-0.2, 0.2)
    ax_bar.set_ylabel('Proportion of Countries', fontsize=10)
    ax_bar.set_title('Exposure Class to Severe Conflict', fontsize=11)
    ax_bar.set_xticks([])
    
    # Add labels within each bar (no legend, no numbers)
    cumulative = 0
    for cluster in cluster_order:
        count = cluster_counts[cluster]
        proportion = count / total_countries
        
        if proportion > 0.02:  # Only show label if segment is large enough
            # Determine if this is the target cluster for emphasis
            if cluster == target_cluster:
                weight = 'bold'
                alpha_text = 1.0
            else:
                weight = 'normal' 
                alpha_text = 0.7
                
            ax_bar.text(0, cumulative + proportion/2, cluster, 
                       ha='center', va='center', fontsize=8, 
                       fontweight=weight, alpha=alpha_text,
                       rotation=0)  # Always horizontal
        
        cumulative += proportion
    
    plt.tight_layout()
    
    # Save and display
    output_path = Path("compact_cluster_test.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    return output_path

if __name__ == "__main__":
    # Debug Niger issue first
    data_provider = DataProvider()
    month_data = data_provider.get_monthly_forecast_distribution(9, 2026)
    
    print("Checking for Niger in data...")
    niger_data = month_data[month_data['isoab'] == 'NER']
    print(f"Niger found: {not niger_data.empty}")
    
    if not niger_data.empty:
        prob = niger_data.iloc[0]['outcome_p']  
        predicted = niger_data.iloc[0]['predicted']
        cluster = data_provider.categorize_probability(prob)
        print(f"Niger: prob={prob:.3f}, predicted={predicted:.1f}, cluster='{cluster}'")
        
        # Check all countries in Niger's cluster
        month_data['prob_category'] = month_data['outcome_p'].apply(data_provider.categorize_probability)
        same_cluster = month_data[month_data['prob_category'] == cluster].sort_values('predicted', ascending=False)
        print(f"\nAll countries in '{cluster}' cluster:")
        for _, row in same_cluster.iterrows():
            name = data_provider.get_country_name(row['isoab'])
            print(f"  {row['isoab']}: {name} - {row['predicted']:.1f}")
    
    # Test with Niger
    result = create_compact_cluster_viz("NER", 9, 2026)
    if result:
        print(f"Generated: {result}")