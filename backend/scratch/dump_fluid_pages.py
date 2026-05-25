import os
from pypdf import PdfReader

pdf_path = "c:/Coding/mro-tts/data/fluid_power_systems_handbook.pdf"
reader = PdfReader(pdf_path)

for page_idx in [18, 19, 20, 21]:
    if page_idx < len(reader.pages):
        text = reader.pages[page_idx].extract_text()
        clean_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(f"--- PAGE {page_idx + 1} ---")
        print(clean_text)
        print("\n" + "="*80 + "\n")
