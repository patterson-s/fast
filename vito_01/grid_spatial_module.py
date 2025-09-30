from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import Optional, Dict, List
import geopandas as gpd
from grid_base_module import GridOutputModule

class GridSpatialModule(GridOutputModule):
    def __init__(self, target_month_id: int):
        self.target_month_id = target_month_id
        self.shapefile_path = Path(r"C:\Users\spatt\Desktop\FAST\vito_01\dataprep\shapes\priogrid_cell.shp")
        self.gdf = None
    
    def _load_shapefile(self):
        if self.gdf is None:
            self.gdf = gpd.read_file(self.shapefile_path)
    
    def _get_neighbors(self, priogrid_gid: int) -> List[int]:
        self._load_shapefile()
        
        focal_row = self.gdf[self.gdf['gid'] == priogrid_gid]
        if focal_row.empty:
            return []
        
        focal_geom = focal_row.iloc[0].geometry
        neighbors = self.gdf[self.gdf.geometry.touches(focal_geom)]
        
        return neighbors['gid'].tolist()
    
    def _get_geographic_position(self, focal_gid: int, neighbor_gid: int) -> str:
        self._load_shapefile()
        
        focal_row = self.gdf[self.gdf['gid'] == focal_gid].iloc[0]
        neighbor_row = self.gdf[self.gdf['gid'] == neighbor_gid].iloc[0]
        
        focal_x = focal_row['xcoord']
        focal_y = focal_row['ycoord']
        neighbor_x = neighbor_row['xcoord']
        neighbor_y = neighbor_row['ycoord']
        
        if neighbor_y > focal_y:
            ns = 'N'
        elif neighbor_y < focal_y:
            ns = 'S'
        else:
            ns = ''
        
        if neighbor_x > focal_x:
            ew = 'E'
        elif neighbor_x < focal_x:
            ew = 'W'
        else:
            ew = ''
        
        return ns + ew
    
    def _get_forecast_value(self, forecast_data: pd.DataFrame, priogrid_gid: int, month_id: int) -> Optional[float]:
        grid_data = forecast_data[
            (forecast_data['priogrid_gid'] == priogrid_gid) & 
            (forecast_data['month_id'] == month_id)
        ]
        
        if grid_data.empty:
            return None
        
        return float(grid_data.iloc[0]['outcome_n'])
    
    def _get_color_for_value(self, value: Optional[float]) -> str:
        if value is None:
            return '#FFFFFF'
        
        if value == 0:
            return '#E8F5E9'
        elif value <= 10:
            return '#90EE90'
        elif value <= 100:
            return '#FFD700'
        elif value <= 1000:
            return '#FF8C42'
        else:
            return '#FF6B6B'
    
    def get_context(self) -> str:
        return """This figure shows the focal grid cell and its 8 geographic neighbors, with baseline forecast values for the target month. Cells are color-coded by forecast fatality level (0, 1-10, 11-100, 101-1000, 1001+). Cells from different countries are indicated with bold borders and labels."""
    
    def generate_content(self, priogrid_gid: int, target_month_id: int, 
                        forecast_data: dict, historical_data: pd.DataFrame, 
                        output_dir: Path) -> Optional[Path]:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        baseline_forecast = forecast_data['baseline']
        
        neighbor_gids = self._get_neighbors(priogrid_gid)
        if len(neighbor_gids) != 8:
            return None
        
        focal_country = data_provider.get_country_name(priogrid_gid)
        focal_value = self._get_forecast_value(baseline_forecast, priogrid_gid, target_month_id)
        
        grid_data = {}
        grid_data['CENTER'] = {
            'gid': priogrid_gid,
            'value': focal_value,
            'country': focal_country
        }
        
        for neighbor_gid in neighbor_gids:
            position = self._get_geographic_position(priogrid_gid, neighbor_gid)
            neighbor_value = self._get_forecast_value(baseline_forecast, neighbor_gid, target_month_id)
            neighbor_country = data_provider.get_country_name(neighbor_gid)
            
            grid_data[position] = {
                'gid': neighbor_gid,
                'value': neighbor_value,
                'country': neighbor_country
            }
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-0.5, 3.5)
        ax.set_aspect('equal')
        ax.axis('off')
        
        positions = {
            'NW': (0.5, 2), 'N': (1.5, 2), 'NE': (2.5, 2),
            'W': (0.5, 1), 'CENTER': (1.5, 1), 'E': (2.5, 1),
            'SW': (0.5, 0), 'S': (1.5, 0), 'SE': (2.5, 0)
        }
        
        for pos_name, (x, y) in positions.items():
            if pos_name not in grid_data:
                continue
            
            cell = grid_data[pos_name]
            value = cell['value']
            country = cell['country']
            gid = cell['gid']
            
            color = self._get_color_for_value(value)
            
            rect = mpatches.Rectangle((x, y), 1, 1, 
                                     linewidth=1.5, 
                                     edgecolor='#000000', 
                                     facecolor=color)
            ax.add_patch(rect)
            
            if value is not None:
                value_text = f"{value:.1f}"
            else:
                value_text = "N/A"
            
            ax.text(x + 0.5, y + 0.6, value_text, 
                   ha='center', va='center', 
                   fontsize=13, fontweight='bold')
            
            ax.text(x + 0.5, y + 0.4, f"{gid}", 
                   ha='center', va='center', 
                   fontsize=7, style='italic', color='gray')
            
            if country:
                country_short = country[:12] + '...' if len(country) > 12 else country
                ax.text(x + 0.5, y + 0.15, country_short, 
                       ha='center', va='center', 
                       fontsize=8)
        
        adjacent_pairs = [
            ('NW', 'N'), ('N', 'NE'),
            ('NW', 'W'), ('N', 'CENTER'), ('NE', 'E'),
            ('W', 'CENTER'), ('CENTER', 'E'),
            ('W', 'SW'), ('CENTER', 'S'), ('E', 'SE'),
            ('SW', 'S'), ('S', 'SE')
        ]
        
        for pos1, pos2 in adjacent_pairs:
            if pos1 not in grid_data or pos2 not in grid_data:
                continue
            
            country1 = grid_data[pos1]['country']
            country2 = grid_data[pos2]['country']
            
            if country1 and country2 and country1 != country2:
                x1, y1 = positions[pos1]
                x2, y2 = positions[pos2]
                
                if x1 == x2:
                    line_x = [x1, x1 + 1]
                    line_y = [max(y1, y2), max(y1, y2)]
                else:
                    line_x = [max(x1, x2), max(x1, x2)]
                    line_y = [y1, y1 + 1]
                
                ax.plot(line_x, line_y, 'r--', linewidth=2, zorder=10)
        
        legend_elements = [
            mpatches.Patch(facecolor='#E8F5E9', edgecolor='black', label='0'),
            mpatches.Patch(facecolor='#90EE90', edgecolor='black', label='1-10'),
            mpatches.Patch(facecolor='#FFD700', edgecolor='black', label='11-100'),
            mpatches.Patch(facecolor='#FF8C42', edgecolor='black', label='101-1k'),
            mpatches.Patch(facecolor='#FF6B6B', edgecolor='black', label='1k+'),
            plt.Line2D([0], [0], color='red', linewidth=2, linestyle='--', label='Border')
        ]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.15, 0.5), 
                 fontsize=8, frameon=False)
        
        plt.tight_layout()
        
        img_path = output_dir / f"grid_spatial_{priogrid_gid}_{target_month_id}.png"
        plt.savefig(img_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return img_path
    
    def get_interpretation(self, priogrid_gid: int, target_month_id: int,
                          forecast_data: dict, historical_data: pd.DataFrame) -> str:
        
        from GridDataProvider import GridDataProvider
        data_provider = GridDataProvider()
        
        baseline_forecast = forecast_data['baseline']
        
        neighbor_gids = self._get_neighbors(priogrid_gid)
        if not neighbor_gids:
            return "Unable to identify neighboring grid cells."
        
        focal_country = data_provider.get_country_name(priogrid_gid)
        focal_value = self._get_forecast_value(baseline_forecast, priogrid_gid, target_month_id)
        
        neighbor_values = []
        cross_border_count = 0
        
        for neighbor_gid in neighbor_gids:
            neighbor_value = self._get_forecast_value(baseline_forecast, neighbor_gid, target_month_id)
            neighbor_country = data_provider.get_country_name(neighbor_gid)
            
            if neighbor_value is not None:
                neighbor_values.append(neighbor_value)
            
            if neighbor_country != focal_country:
                cross_border_count += 1
        
        month_str = data_provider.month_id_to_string(target_month_id)
        
        if not neighbor_values:
            neighborhood_desc = "No forecast data available for neighboring cells"
        else:
            avg_neighbor = np.mean(neighbor_values)
            max_neighbor = max(neighbor_values)
            
            if focal_value is None:
                focal_comparison = "No forecast available for focal cell"
            elif focal_value > avg_neighbor * 1.2:
                focal_comparison = f"The focal cell forecast ({focal_value:.1f}) is higher than the neighborhood average ({avg_neighbor:.1f})"
            elif focal_value < avg_neighbor * 0.8:
                focal_comparison = f"The focal cell forecast ({focal_value:.1f}) is lower than the neighborhood average ({avg_neighbor:.1f})"
            else:
                focal_comparison = f"The focal cell forecast ({focal_value:.1f}) is similar to the neighborhood average ({avg_neighbor:.1f})"
            
            neighborhood_desc = f"{focal_comparison}. Maximum neighbor forecast: {max_neighbor:.1f}"
        
        if cross_border_count == 0:
            border_desc = "All neighboring cells are within the same country"
        elif cross_border_count == 1:
            border_desc = "1 neighboring cell is from a different country"
        else:
            border_desc = f"{cross_border_count} neighboring cells are from different countries"
        
        country_rank_desc = ""
        if focal_country and focal_value is not None:
            country_forecast = baseline_forecast[baseline_forecast['month_id'] == target_month_id].copy()
            country_grids = []
            for _, row in country_forecast.iterrows():
                grid_country = data_provider.get_country_name(int(row['priogrid_gid']))
                if grid_country == focal_country:
                    country_grids.append((int(row['priogrid_gid']), float(row['outcome_n'])))
            
            if country_grids:
                country_grids.sort(key=lambda x: x[1], reverse=True)
                country_rank = next((i + 1 for i, (gid, _) in enumerate(country_grids) if gid == priogrid_gid), None)
                total_country_grids = len(country_grids)
                
                if country_rank:
                    grids_more = country_rank - 1
                    grids_less = total_country_grids - country_rank
                    
                    country_rank_desc = f" Within {focal_country}, this grid is {country_rank} out of {total_country_grids}, meaning {grids_more} grids are forecasted to experience more conflict and {grids_less} are expected to experience less conflict."
        
        global_rank_desc = ""
        if focal_value is not None:
            all_forecast = baseline_forecast[baseline_forecast['month_id'] == target_month_id].copy()
            
            if focal_value == 0:
                category_name = "lowest"
                category_range = "0 fatalities"
                bucket_grids = all_forecast[all_forecast['outcome_n'] == 0]
            elif focal_value <= 10:
                category_name = "second lowest"
                category_range = "1-10 fatalities"
                bucket_grids = all_forecast[(all_forecast['outcome_n'] > 0) & (all_forecast['outcome_n'] <= 10)]
            elif focal_value <= 100:
                category_name = "second highest"
                category_range = "11-100 fatalities"
                bucket_grids = all_forecast[(all_forecast['outcome_n'] > 10) & (all_forecast['outcome_n'] <= 100)]
            else:
                category_name = "highest"
                category_range = "101-1000 fatalities"
                bucket_grids = all_forecast[(all_forecast['outcome_n'] > 100) & (all_forecast['outcome_n'] <= 1000)]
            
            bucket_total = len(bucket_grids)
            
            if bucket_total > 0:
                global_rank_desc = f" Regionally, this grid is among {bucket_total} grids in the {category_name} category, which spans from {category_range} per month."
        
        return f"""For {month_str}: {neighborhood_desc}. {border_desc}.{country_rank_desc}{global_rank_desc}"""