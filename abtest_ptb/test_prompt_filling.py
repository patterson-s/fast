from pathlib import Path
from prompt_loader import PromptLoader
from data_extractor import DataExtractor

def fill_prompt(template: str, data: dict) -> str:
    filled = template
    for key, value in data.items():
        placeholder = "{" + key + "}"
        filled = filled.replace(placeholder, str(value))
    return filled

def main():
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\abtest_ptb")
    
    loader = PromptLoader(base_dir)
    extractor = DataExtractor()
    
    country_code = "NGA"
    target_month = 9
    target_year = 2026
    
    print(f"Testing prompt filling for: {country_code} {target_month}/{target_year}")
    print("="*80)
    
    data = extractor.extract_template_data(country_code, target_month, target_year)
    
    print("\nEXTRACTED DATA:")
    print("-"*80)
    for key, value in data.items():
        if key not in ['covariate_analysis', 'example_cohorts']:
            print(f"{key:25s}: {value}")
    
    print("\n" + "="*80)
    print("VARIANT 1 (SINGLE USER PROMPT)")
    print("="*80)
    
    v1 = loader.load_variant("bluf_v1")
    v1_filled = fill_prompt(v1.user_prompt, data)
    print(v1_filled)
    
    print("\n" + "="*80)
    print("VARIANT 2 (SYSTEM + USER PROMPT)")
    print("="*80)
    
    v2 = loader.load_variant("bluf_v2")
    
    print("\n--- SYSTEM PROMPT ---")
    print(v2.system_prompt)
    
    print("\n--- USER PROMPT ---")
    v2_user_filled = fill_prompt(v2.user_prompt, data)
    print(v2_user_filled)
    
    print("\n" + "="*80)
    print("COMPARISON:")
    print("="*80)
    print(f"V1 total length: {len(v1_filled)} chars")
    print(f"V2 system length: {len(v2.system_prompt)} chars")
    print(f"V2 user length: {len(v2_user_filled)} chars")
    print(f"V2 total length: {len(v2.system_prompt) + len(v2_user_filled)} chars")
    print(f"\nSimilarity type: {data['similarity_label']}")
    print(f"Cohort prefix: {data['cohort_prefix']}")

if __name__ == "__main__":
    main()