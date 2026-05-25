import os
import glob
from pypdf import PdfReader

DATA_DIR = "c:/Coding/mro-tts/data"
pdf_files = sorted(glob.glob(os.path.join(DATA_DIR, "mro_*.pdf")))

print(f"Found {len(pdf_files)} PDF files to check:\n")

for pdf_path in pdf_files:
    filename = os.path.basename(pdf_path)
    print("=" * 60)
    print(f"FILE: {filename}")
    print("=" * 60)
    
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        print(f"Total Pages: {num_pages}")
        
        # Extract metadata
        meta = reader.metadata
        print("Metadata:")
        if meta:
            for k, v in meta.items():
                print(f"  {k}: {v}")
        else:
            print("  No metadata found.")
            
        # Analyze first page content
        first_page_text = reader.pages[0].extract_text()
        print("\n--- FIRST PAGE PREVIEW (First 400 chars) ---")
        print(first_page_text[:400].strip())
        print("-" * 44)
        
        # Analyze TOC or Chapter headings
        chapters = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            for line in text.split("\n"):
                line_strip = line.strip().upper()
                if "CHAPTER" in line_strip or "APPENDIX" in line_strip or "GLOSSARY" in line_strip or "REFERENCES" in line_strip:
                    chapters.append((i + 1, line.strip()))
                    
        print(f"\nDetected Division Headers (Total: {len(chapters)}):")
        # Print a unique subset to avoid duplicates per page
        seen_headers = set()
        for page_num, ch_title in chapters:
            if ch_title not in seen_headers:
                print(f"  Page {page_num:2d}: {ch_title}")
                seen_headers.add(ch_title)
                
        # Check text density - print avg characters per page
        total_chars = 0
        for page in reader.pages:
            total_chars += len(page.extract_text())
        avg_chars = total_chars / num_pages if num_pages > 0 else 0
        print("\nText Metrics:")
        print(f"  Total Characters: {total_chars}")
        print(f"  Avg Characters/Page: {avg_chars:.1f} (~{int(avg_chars/5)} words/page)")
        
    except Exception as e:
        print(f"Error checking PDF: {e}")
    print("\n")
