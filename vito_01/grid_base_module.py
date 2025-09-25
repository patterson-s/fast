from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import pandas as pd

class GridOutputModule(ABC):
    @abstractmethod
    def get_context(self) -> str:
        pass
    
    @abstractmethod
    def generate_content(self, priogrid_gid: int, target_month_id: int, 
                        forecast_data: pd.DataFrame, historical_data: pd.DataFrame, 
                        output_dir: Path) -> Optional[Path]:
        pass
    
    @abstractmethod
    def get_interpretation(self, priogrid_gid: int, target_month_id: int,
                          forecast_data: pd.DataFrame, historical_data: pd.DataFrame) -> str:
        pass