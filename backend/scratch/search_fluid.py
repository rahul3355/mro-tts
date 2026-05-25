import os
from pypdf import PdfReader

pdf_path = "c:/Coding/mro-tts/data/fluid_power_systems_handbook.pdf"
reader = PdfReader(pdf_path)

out_lines = []
for i, page in enumerate(reader.pages):
    text = page.extract_text()
    for line in text.split("\n"):
        if any(w in line.lower() for w in ["torque", "flared", "fitting", "inch-pound", "in-lb", "70", "80", "90", "75"]):
            out_lines.append(f"Page {i+1}: {line.strip()}")

with open("c:/Coding/mro-tts/backend/scratch/fluid_text.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print(f"Extracted {len(out_lines)} lines to fluid_text.txt")
