from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Optional
import pandas as pd

class OutputModule(ABC):
    @abstractmethod
    def get_context(self) -> str:
        pass
    
    @abstractmethod
    def generate_content(self, country_code: str, forecast_data: pd.DataFrame, 
                        historical_data: pd.DataFrame, output_dir: Path) -> Optional[Path]:
        pass
    
    @abstractmethod
    def get_interpretation(self, country_code: str, forecast_data: pd.DataFrame, 
                          historical_data: pd.DataFrame) -> str:
        pass