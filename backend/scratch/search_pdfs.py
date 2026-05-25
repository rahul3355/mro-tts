import os
import glob
from pypdf import PdfReader

DATA_DIR = "c:/Coding/mro-tts/data"
pdf_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.pdf")))

keywords = ["75", "70", "90", "flared", "fitting", "B-nut", "3/16"]

for pdf_path in pdf_files:
    filename = os.path.basename(pdf_path)
    print("=" * 60)
    print(f"FILE: {filename}")
    print("=" * 60)
    
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        for line in text.split("\n"):
            # Check if any keyword matches
            found = [kw for kw in keywords if kw.lower() in line.lower()]
            if found:
                clean_line = line.strip().encode('ascii', errors='ignore').decode('ascii')
                print(f"Page {i+1}: {clean_line} (Matched: {found})")
