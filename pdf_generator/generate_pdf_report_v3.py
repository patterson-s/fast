#!/usr/bin/env python3

import sys
from pathlib import Path

def main():
    if len(sys.argv) == 2:
        country_code = sys.argv[1].upper()
    else:
        country_code = "SOM"
        print(f"Using default country: {country_code}")
        print("Usage: python generate_pdf_report_v3.py <ISO3>")
    
    base_dir = Path(r"C:\Users\spatt\Desktop\FAST\pdf_generator")
    base_dir.mkdir(exist_ok=True)
    
    from pdf_builder import PDFBuilder
    from data_loader import DataLoader
    
    data_loader = DataLoader()
    pdf_builder = PDFBuilder(base_dir)
    output_file = pdf_builder.create_country_report(country_code, data_loader)
    
    print(f"Generated PDF report: {output_file}")

if __name__ == "__main__":
    main()