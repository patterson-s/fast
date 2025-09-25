#!/usr/bin/env python3

import sys
from pathlib import Path
import fitz

def pdf_to_png(pdf_path: str):
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"Error: File not found: {pdf_path}")
        return
    
    print(f"Converting {pdf_file.name}...")
    
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    
    for page_num in range(page_count):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        
        output_path = pdf_file.parent / f"{pdf_file.stem}_page{page_num + 1}.png"
        pix.save(output_path)
        print(f"Saved: {output_path}")
    
    doc.close()
    print(f"Converted {page_count} page(s)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_png.py <pdf_file_path>")
        sys.exit(1)
    
    pdf_to_png(sys.argv[1])