import os
import json
import cohere
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PromptConfig:
    variant_name: str
    model: str
    temperature: float
    api_key_env_var: str
    prompt_type: str
    system_prompt: str
    user_prompt: str
    max_retries: int
    timeout_seconds: int

class GridBLUFGenerator:
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = Path(prompts_dir)
        self.config = self._load_config()
        self.client = None
    
    def _load_config(self) -> PromptConfig:
        config_path = self.prompts_dir / "config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        system_path = self.prompts_dir / config['system_prompt_path']
        user_path = self.prompts_dir / config['user_prompt_path']
        
        if not system_path.exists():
            raise FileNotFoundError(f"System prompt not found: {system_path}")
        if not user_path.exists():
            raise FileNotFoundError(f"User prompt not found: {user_path}")
        
        with open(system_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        
        with open(user_path, 'r', encoding='utf-8') as f:
            user_prompt = f.read()
        
        return PromptConfig(
            variant_name=config['variant_name'],
            model=config['model'],
            temperature=config['temperature'],
            api_key_env_var=config['api_key_env_var'],
            prompt_type=config['prompt_type'],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_retries=config['max_retries'],
            timeout_seconds=config['timeout_seconds']
        )
    
    def _get_client(self) -> cohere.ClientV2:
        if self.client is None:
            api_key = os.getenv(self.config.api_key_env_var)
            if not api_key:
                raise ValueError(f"{self.config.api_key_env_var} environment variable not set")
            self.client = cohere.ClientV2(api_key)
        return self.client
    
    def _fill_template(self, template: str, data: Dict[str, Any]) -> str:
        filled = template
        for key, value in data.items():
            placeholder = "{" + key + "}"
            filled = filled.replace(placeholder, str(value))
        return filled
    
    def generate_bluf(self, bluf_data: Dict[str, Any]) -> str:
        try:
            client = self._get_client()
            
            user_prompt = self._fill_template(self.config.user_prompt, bluf_data)
            
            messages = [
                {
                    "role": "system",
                    "content": self.config.system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
            
            response = client.chat(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature
            )
            
            if hasattr(response, 'message'):
                if hasattr(response.message, 'content') and isinstance(response.message.content, list):
                    return response.message.content[0].text
                else:
                    return str(response.message.content)
            else:
                return str(response)
        
        except Exception as e:
            raise RuntimeError(f"BLUF generation failed: {e}")


if __name__ == "__main__":
    from grid_bluf_data_extractor import GridBLUFDataExtractor
    
    prompts_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_vito\bluf_01")
    
    extractor = GridBLUFDataExtractor()
    generator = GridBLUFGenerator(prompts_dir)
    
    test_cases = [
        (174669, 561),
        (152235, 561)
    ]
    
    for grid_id, month_id in test_cases:
        print(f"\n{'='*80}")
        print(f"Grid {grid_id}, Month {month_id}")
        print('='*80)
        
        try:
            bluf_data = extractor.extract_bluf_data(grid_id, month_id)
            
            print(f"\nGenerating BLUF...")
            bluf_text = generator.generate_bluf(bluf_data)
            
            print(f"\nBLUF:")
            print(bluf_text)
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()