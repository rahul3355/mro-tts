import asyncio
import sys
import os
import glob
import httpx
from pypdf import PdfReader

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.integrations.openrouter import OpenRouterClient

DATA_DIR = "c:/Coding/mro-tts/data"
PINECONE_HOST = "https://mro-tts-o133fy5.svc.aped-4627-b74a.pinecone.io"

# List of descriptive handbook PDFs to process (in dependency order)
HANDBOOK_FILES = [
    "avionics_wiring_handbook.pdf",
    "fluid_power_systems_handbook.pdf",
    "landing_gear_brakes_handbook.pdf",
    "powerplant_maintenance_handbook.pdf",
    "structural_repair_handbook.pdf"
]

# Dictionary of known run-together phrases caused by LaTeX math-mode compilation
SPACING_REPLACEMENTS = {
    # avionics_wiring_handbook
    "degreecircumferentialcontacttopreventRFleakageandmaintainthe": "degree circumferential contact to prevent RF leakage and maintain the",
    "Theinsertionandextractionofthesepinsdemand": "The insertion and extraction of these pins demand",
    "Thermalmanagementwithintheavionicsbayiscritical": "Thermal management within the avionics bay is critical",
    "connectorsutilizingremovablecrimpcontacts": "connectors utilizing removable crimp contacts",
    "statecomponentsexperience": "state components experience",
    "characteristicimpedanceofthetransmissionlineandcausingsignalreflectionsthatdegradehigh": "characteristic impedance of the transmission line and causing signal reflections that degrade high",
    
    # fluid_power_systems_handbook
    "hydraulicpressureremainsconstantregardlessofflowdemand": "hydraulic pressure remains constant regardless of flow demand",
    "systempressureexceedsthepredeterminedcrackpressure": "system pressure exceeds the predetermined crack pressure",
    "actuatorpistonareamultipliedbythehydraulicpressure": "actuator piston area multiplied by the hydraulic pressure",
    "nitrogenprechargepressurescorrespondsdirectlytotheambient": "nitrogen precharge pressures corresponds directly to the ambient",
    "cleanlinesslevelsofthehydraulicfluidmustbecontinuously": "cleanliness levels of the hydraulic fluid must be continuously",
    
    # landing_gear_brakes_handbook
    "maximumallowablewearlimitforcarbonrotorandstator": "maximum allowable wear limit for carbon rotor and stator",
    "brakekineticenertytalksaboutstoppingcapability": "brake kinetic energy talks about stopping capability",
    "thermalexpansionofbrakepistonsealsrequiresretraction": "thermal expansion of brake piston seals requires retraction",
    "decelerationratesaredirectlyproportionaltobrakelinepressure": "deceleration rates are directly proportional to brake line pressure",
    "antiskidsystemmodulateshydraulicpressuretopreventwheel": "anti-skid system modulates hydraulic pressure to prevent wheel",
    
    # powerplant_maintenance_handbook
    "compressorpressureratioiscriticaltoenginethermalefficiency": "compressor pressure ratio is critical to engine thermal efficiency",
    "turbineinlettemperaturelimitmustneverbeexceeded": "turbine inlet temperature limit must never be exceeded",
    "oilpressurespecificationsarehighlydependentonengine": "oil pressure specifications are highly dependent on engine",
    "fuelnozzlespraypatterninspectionsarerequiredto": "fuel nozzle spray pattern inspections are required to",
    "vibrationsignaturesmustbeanalyzedtoidentifyunbalance": "vibration signatures must be analyzed to identify unbalance",
    
    # structural_repair_handbook
    "ultimatetensilestrengthofsheetmetalrepairsdependson": "ultimate tensile strength of sheet metal repairs depends on",
    "compositecuringtemperaturesmuststrictlyfollowthemandated": "composite curing temperatures must strictly follow the mandated",
    "rivetspacingandedgedistancerequirementsaredefinedby": "rivet spacing and edge distance requirements are defined by",
    "fastenertorquelimitsshouldbemeasuredwithcalibrated": "fastener torque limits should be measured with calibrated",
    "corrosionmitigationrequiresprecisemetallurgicaltreatment": "corrosion mitigation requires precise metallurgical treatment"
}

def clean_extracted_text(text: str) -> str:
    """Cleans up PDF spacing defects and run-together words."""
    if not text:
        return ""
    
    # Apply replacements for known run-together LaTeX bugs
    cleaned = text
    for run_together, spaced in SPACING_REPLACEMENTS.items():
        cleaned = cleaned.replace(run_together, spaced)
    
    # Normalize spacing and remove simple header artifacts
    lines = cleaned.split("\n")
    cleaned_lines = []
    for line in lines:
        line_strip = line.strip()
        # Skip empty lines or standard footer page numbers
        if not line_strip:
            continue
        if line_strip.isdigit():
            continue
        cleaned_lines.append(line_strip)
        
    return "\n".join(cleaned_lines)

def chunk_page_text(page_text: str, target_size: int = 900, overlap_chars: int = 200) -> list[str]:
    """Splits page text into clean paragraph-aligned chunks with overlap, ensuring no lines are cut in half."""
    if not page_text:
        return []
        
    lines = page_text.split("\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        line_len = len(line) + 1
        if current_length + line_len > target_size and current_chunk:
            # Save the current chunk
            chunk_str = "\n".join(current_chunk)
            chunks.append(chunk_str)
            
            # Start new chunk with overlap from the end of the current chunk
            overlap_lines = []
            overlap_len = 0
            # Walk backwards through the current chunk to gather overlap lines
            for prev_line in reversed(current_chunk):
                if overlap_len + len(prev_line) + 1 > overlap_chars:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_len += len(prev_line) + 1
                
            current_chunk = overlap_lines + [line]
            current_length = sum(len(l) + 1 for l in current_chunk)
        else:
            current_chunk.append(line)
            current_length += line_len
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

async def main() -> None:
    print("=" * 60)
    print("MRO Semantic Vector Ingestion Service")
    print("=" * 60)

    # 1. Setup HTTP Clients
    async with httpx.AsyncClient(
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=httpx.Timeout(30.0, read=60.0),
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://mro-tts.vercel.app",
            "X-Title": "mro-tts-copilot",
        }
    ) as http_client:
        openrouter = OpenRouterClient(http_client)
        headers = {
            "Api-Key": settings.PINECONE_API_KEY,
            "Content-Type": "application/json",
        }

        # 2. Delete ALL existing documents in Pinecone default namespace
        print("CLEARING DATABASE: Deleting all existing vectors in Pinecone index...")
        delete_url = f"{PINECONE_HOST}/vectors/delete"
        try:
            response = await http_client.post(delete_url, json={"deleteAll": True}, headers=headers)
            response.raise_for_status()
            print("  SUCCESS: Pinecone database cleared.")
        except Exception as delete_e:
            print(f"  WARNING: Failed to clear Pinecone database: {delete_e}")
            # If the database is empty or doesn't support deleteAll this might fail, proceed anyway

        # 3. Extract and Process each PDF
        vectors_payload = []
        global_chunk_count = 0

        for filename in HANDBOOK_FILES:
            pdf_path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(pdf_path):
                print(f"\nWARNING: Handbook PDF {filename} not found in {DATA_DIR}. Skipping.")
                continue
                
            print(f"\nProcessing {filename}...")
            
            try:
                reader = PdfReader(pdf_path)
                num_pages = len(reader.pages)
                print(f"  Total Pages: {num_pages}")
                
                for page_idx in range(num_pages):
                    page_num = page_idx + 1
                    raw_text = reader.pages[page_idx].extract_text()
                    page_text = clean_extracted_text(raw_text)
                    
                    if not page_text:
                        continue
                        
                    # Split page text into smaller paragraph-level chunks
                    page_chunks = chunk_page_text(page_text, target_size=900, overlap_chars=200)
                    
                    for chunk_idx, sub_text in enumerate(page_chunks):
                        # Prepend source context headers
                        contextual_header = f"DOCUMENT SOURCE: {filename} (Page {page_num})\n"
                        chunk_text = f"{contextual_header}{sub_text}"
                        
                        # Generate unique vector ID
                        vector_id = f"{filename.replace('.pdf', '')}-p{page_num}-c{chunk_idx+1}"
                        
                        print(f"  Generating embedding for {vector_id} ({len(chunk_text)} chars)...")
                        try:
                            embedding = await openrouter.get_embedding(chunk_text)
                            
                            vectors_payload.append({
                                "id": vector_id,
                                "values": embedding,
                                "metadata": {
                                    "text": chunk_text,
                                    "doc_path": filename
                                }
                            })
                            global_chunk_count += 1
                            
                            # Throttle slightly to respect API rate limits
                            await asyncio.sleep(0.05)
                            
                        except Exception as emb_e:
                            print(f"    ERROR generating embedding for {vector_id}: {emb_e}")
                            continue
                            
            except Exception as pdf_e:
                print(f"  ERROR parsing PDF {filename}: {pdf_e}")
                continue

        # 4. Upsert vectors in batches to Pinecone
        if not vectors_payload:
            print("\nERROR: No vectors generated. Ingestion aborted.")
            return

        print(f"\nTotal semantic chunks generated: {global_chunk_count}")
        print(f"Upserting vectors in batches to Pinecone Index at: {PINECONE_HOST}...")

        upsert_url = f"{PINECONE_HOST}/vectors/upsert"

        # Pinecone upsert limit is 2MB per request, batching by 50 vectors is very safe
        batch_size = 50
        for i in range(0, len(vectors_payload), batch_size):
            batch = vectors_payload[i:i + batch_size]
            payload = {"vectors": batch}
            
            print(f"  Upserting batch {i//batch_size + 1} ({len(batch)} vectors)...")
            try:
                response = await http_client.post(upsert_url, json=payload, headers=headers)
                response.raise_for_status()
                print(f"    Batch {i//batch_size + 1} upserted successfully.")
            except Exception as upsert_e:
                print(f"    ERROR upserting batch {i//batch_size + 1}: {upsert_e}")
                if 'response' in locals() and response is not None:
                    print(f"    Response body: {response.text}")
                return

        print("\nSUCCESS: All semantic handbook chunks have been successfully ingested into Pinecone!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
