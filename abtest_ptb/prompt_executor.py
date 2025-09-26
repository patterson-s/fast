import os
import cohere
from typing import Dict, Any
from dataclasses import dataclass
from prompt_loader import PromptVariant

@dataclass
class ExecutionResult:
    variant_name: str
    country_code: str
    month: int
    year: int
    raw_output: str
    success: bool
    error: str = None

class PromptExecutor:
    def __init__(self):
        self.clients = {}
    
    def _get_client(self, api_key_env_var: str) -> cohere.ClientV2:
        if api_key_env_var not in self.clients:
            api_key = os.getenv(api_key_env_var)
            if not api_key:
                raise ValueError(f"{api_key_env_var} environment variable not set")
            self.clients[api_key_env_var] = cohere.ClientV2(api_key)
        return self.clients[api_key_env_var]
    
    def _fill_template(self, template: str, data: Dict[str, Any]) -> str:
        filled = template
        for key, value in data.items():
            placeholder = "{" + key + "}"
            filled = filled.replace(placeholder, str(value))
        return filled
    
    def execute(self, variant: PromptVariant, template_data: Dict[str, Any]) -> ExecutionResult:
        country_code = template_data.get('country_code', 'UNKNOWN')
        month = template_data.get('month', 0)
        year = template_data.get('year', 0)
        
        try:
            client = self._get_client(variant.api_key_env_var)
            
            user_prompt = self._fill_template(variant.user_prompt, template_data)
            
            if variant.prompt_type == 'single':
                messages = [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            elif variant.prompt_type == 'system_user':
                messages = [
                    {
                        "role": "system",
                        "content": variant.system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            else:
                raise ValueError(f"Unknown prompt_type: {variant.prompt_type}")
            
            response = client.chat(
                model=variant.model,
                messages=messages,
                temperature=variant.temperature
            )
            
            if hasattr(response, 'message'):
                if hasattr(response.message, 'content') and isinstance(response.message.content, list):
                    raw_output = response.message.content[0].text
                else:
                    raw_output = str(response.message.content)
            else:
                raw_output = str(response)
            
            return ExecutionResult(
                variant_name=variant.variant_name,
                country_code=country_code,
                month=month,
                year=year,
                raw_output=raw_output,
                success=True
            )
            
        except Exception as e:
            return ExecutionResult(
                variant_name=variant.variant_name,
                country_code=country_code,
                month=month,
                year=year,
                raw_output="",
                success=False,
                error=str(e)
            )

if __name__ == "__main__":
    from pathlib import Path
    from prompt_loader import PromptLoader
    from data_extractor import DataExtractor
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_ptb")
    
    loader = PromptLoader(base_dir)
    extractor = DataExtractor()
    executor = PromptExecutor()
    
    country_code = "NGA"
    target_month = 9
    target_year = 2026
    
    print(f"Generating BLUFs for: {country_code} {target_month}/{target_year}")
    print("="*80)
    
    data = extractor.extract_template_data(country_code, target_month, target_year)
    
    for variant_name in ["bluf_v1", "bluf_v2"]:
        print(f"\n{variant_name.upper()}:")
        print("-"*80)
        
        variant = loader.load_variant(variant_name)
        result = executor.execute(variant, data)
        
        if result.success:
            print(result.raw_output)
        else:
            print(f"ERROR: {result.error}")