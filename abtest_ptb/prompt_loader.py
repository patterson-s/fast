from pathlib import Path
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PromptVariant:
    variant_name: str
    model: str
    temperature: float
    api_key_env_var: str
    prompt_type: str
    user_prompt: str
    system_prompt: Optional[str]
    template_variables: list[str]
    max_retries: int
    timeout_seconds: int
    config_path: Path

class PromptLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
    
    def load_variant(self, variant_dir: str) -> PromptVariant:
        variant_path = self.base_dir / variant_dir
        config_path = variant_path / "config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        prompt_type = config['prompt_type']
        
        if prompt_type == 'single':
            user_prompt = self._load_prompt_file(variant_path / config['user_prompt_path'])
            system_prompt = None
        elif prompt_type == 'system_user':
            system_prompt = self._load_prompt_file(variant_path / config['system_prompt_path'])
            user_prompt = self._load_prompt_file(variant_path / config['user_prompt_path'])
        else:
            raise ValueError(f"Unknown prompt_type: {prompt_type}")
        
        return PromptVariant(
            variant_name=config['variant_name'],
            model=config['model'],
            temperature=config['temperature'],
            api_key_env_var=config['api_key_env_var'],
            prompt_type=prompt_type,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            template_variables=config['template_variables'],
            max_retries=config['max_retries'],
            timeout_seconds=config['timeout_seconds'],
            config_path=config_path
        )
    
    def _load_prompt_file(self, prompt_path: Path) -> str:
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def list_variants(self) -> list[str]:
        variants = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and (item / "config.json").exists():
                variants.append(item.name)
        return sorted(variants)

if __name__ == "__main__":
    loader = PromptLoader(Path(r"C:\Users\spatt\Desktop\FAST\abtest_ptb"))
    
    print("Available variants:")
    for variant in loader.list_variants():
        print(f"  - {variant}")
    
    print("\nLoading bluf_v1:")
    v1 = loader.load_variant("bluf_v1")
    print(f"  Variant: {v1.variant_name}")
    print(f"  Type: {v1.prompt_type}")
    print(f"  Model: {v1.model}")
    print(f"  User prompt length: {len(v1.user_prompt)} chars")
    print(f"  System prompt: {v1.system_prompt is not None}")
    
    print("\nLoading bluf_v2:")
    v2 = loader.load_variant("bluf_v2")
    print(f"  Variant: {v2.variant_name}")
    print(f"  Type: {v2.prompt_type}")
    print(f"  Model: {v2.model}")
    print(f"  User prompt length: {len(v2.user_prompt)} chars")
    print(f"  System prompt: {v2.system_prompt is not None}")
    print(f"  System prompt length: {len(v2.system_prompt) if v2.system_prompt else 0} chars")