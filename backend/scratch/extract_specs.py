import re

with open("c:/Coding/mro-tts/backend/scratch/all_pdf_text.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Regular expression to match numbers followed by units
units = r"(?:inch-pounds|in-lbs|ft-lbs|foot-pounds|psi|inches|inch|mm|milliohms|ohms|amps|amperes|lbf|pounds|deg|C|F|degrees)"
pattern = re.compile(rf"\b\d+(?:\.\d+)?\s*{units}\b", re.IGNORECASE)

lines = text.split("\n")
matched_lines = []
for line_num, line in enumerate(lines, 1):
    if pattern.search(line):
        # Find which PDF it belongs to
        pdf_name = "Unknown"
        for i in range(line_num - 1, -1, -1):
            if lines[i].startswith("PDF:"):
                pdf_name = lines[i].replace("PDF:", "").strip()
                break
        matched_lines.append(f"{pdf_name} (Line {line_num}): {line.strip()}")

with open("c:/Coding/mro-tts/backend/scratch/extracted_specs.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(matched_lines))

print(f"Extracted {len(matched_lines)} matches to extracted_specs.txt")
