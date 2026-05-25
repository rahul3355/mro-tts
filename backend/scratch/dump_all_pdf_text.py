import os
import glob
from pypdf import PdfReader

DATA_DIR = "c:/Coding/mro-tts/data"
pdf_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.pdf")))

out = []
for pdf_path in pdf_files:
    filename = os.path.basename(pdf_path)
    out.append("=" * 80)
    out.append(f"PDF: {filename}")
    out.append("=" * 80)
    
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        out.append(f"--- PAGE {i+1} ---")
        out.append(text)
        out.append("\n")

with open("c:/Coding/mro-tts/backend/scratch/all_pdf_text.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Done dumping all PDF texts.")
