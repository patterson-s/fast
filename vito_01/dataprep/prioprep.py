import pandas as pd
import country_converter as coco
from pathlib import Path

def main():
    # Path to your input CSV
    input_path = Path(r"C:\Users\spatt\Desktop\FAST\vito_01\dataprep\priogrid.csv")
    output_path = input_path.with_name("priogrid.json")

    # Load the CSV
    df = pd.read_csv(input_path)

    # Convert gwno to ISO3 codes
    df["iso3"] = coco.convert(names=df["gwno"], src="gwcode", to="ISO3")

    # Save to JSON (records orientation makes sense for downstream use)
    df.to_json(output_path, orient="records", lines=True)

    print(f"Saved enriched JSON to {output_path}")

if __name__ == "__main__":
    main()
