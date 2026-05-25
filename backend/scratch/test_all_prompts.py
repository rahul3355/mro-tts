import asyncio
import os
import sys
import json
from typing import Any

# Put backend root on Python sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import httpx
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.integrations.openrouter import OpenRouterClient
from app.integrations.cohere import CohereClient
from app.integrations.pinecone import PineconeClient
from app.services.stream_manager import SSEStreamManager
from app.pipelines.process_pipeline import RAGPipelineCoordinator

PROMPTS = [
    # Category 1: Avionics & Electrical Wiring (avionics_wiring_handbook.pdf)
    {
        "id": 1,
        "category": "Avionics & Electrical Wiring",
        "transcript": "Completed bonding measurement on ground stud GP-03 for the lightning strike path. Measured resistance is 1.2 milliohms. Cleaned mating surface and verified within limits.",
        "expected": "PASS",
        "spec": "Lightning strike path bonding resistance must be ≤1.5 milliohms."
    },
    {
        "id": 2,
        "category": "Avionics & Electrical Wiring",
        "transcript": "Completed ground stud bonding resistance check on instrument panel mount bracket GP-02. Measured resistance is 3.1 milliohms. Ground connection was tightened using cadmium-plated steel washers.",
        "expected": "FAIL",
        "spec": "Primary ground bond resistance must not exceed 2.5 milliohms."
    },
    {
        "id": 3,
        "category": "Avionics & Electrical Wiring",
        "transcript": "Secured the main instrument panel wire harness bundle. The horizontal clamp intervals are spaced at 15 inches. Cushion clamps torqued to 12 inch-pounds using wrench T-14.",
        "expected": "PASS",
        "spec": "Spacing between horizontal clamps must not exceed 18 inches, and prevailing torque must be 10 to 15 inch-pounds."
    },
    {
        "id": 4,
        "category": "Avionics & Electrical Wiring",
        "transcript": "Completed pull-test on sample coupon of 20 AWG terminal lug using M22520 crimp tool. Crimp junction failed at 12 pounds of axial force.",
        "expected": "FAIL",
        "spec": "Minimum mechanical pull-test tensile value for 20 AWG crimp connections is 15.0 lbf."
    },
    # Category 2: Fluid Power Systems (fluid_power_systems_handbook.pdf)
    {
        "id": 5,
        "category": "Fluid Power Systems",
        "transcript": "Installed the replacement high-pressure hydraulic feed line. Torqued the MS flareless B-nut coupling to 120 inch-pounds. Checked ferrule seat alignment before connection.",
        "expected": "FAIL",
        "spec": "1/2-inch CRES flareless fitting B-nuts require 180–220 inch-pounds. 120 inch-pounds is under-torqued."
    },
    {
        "id": 6,
        "category": "Fluid Power Systems",
        "transcript": "Finished B-nut torquing on the landing gear actuator hydraulic return line. Torqued fitting to 75 inch-pounds. Lockwire has been applied to the connector sleeve.",
        "expected": "PASS",
        "spec": "75 inch-pounds falls within the #3 (3/16-inch) flared fitting range of 70–90 inch-pounds per new manual."
    },
    {
        "id": 7,
        "category": "Fluid Power Systems",
        "transcript": "Charged the emergency landing gear accumulator with dry nitrogen. Pre-charge pressure is at 850 PSI, matching the ambient temperature calibration requirement.",
        "expected": "PASS",
        "spec": "Accumulator pre-charge pressures must match temperature curves (typically around 800-900 PSI at room temperature)."
    },
    {
        "id": 8,
        "category": "Fluid Power Systems",
        "transcript": "Completed hydraulic reservoir servicing. Added 2 quarts of red mineral oil MIL-PRF-5606 fluid to the primary system reservoir. Cycle test is pending.",
        "expected": "PASS",
        "spec": "MIL-PRF-5606 is a valid legacy hydraulic fluid. New manual covers both mineral and phosphate ester systems."
    },
    # Category 3: Landing Gear & Brake Systems (landing_gear_brakes_handbook.pdf)
    {
        "id": 9,
        "category": "Landing Gear & Brake Systems",
        "transcript": "Replaced left main landing gear outboard carbon brake assembly. Torqued the four tie-bolts in a star pattern to 45 foot-pounds using calibrated wrench W-09. Safety wired all bolt heads in series.",
        "expected": "FAIL",
        "spec": "Wheel half tie-bolts require 150–250 foot-pounds in star pattern with safety wire. 45 ft-lbs is grossly under-torqued."
    },
    {
        "id": 10,
        "category": "Landing Gear & Brake Systems",
        "transcript": "Replaced outboard brake assembly on the right main gear. Torqued four mounting bolts to 30 foot-pounds. Safety wire applied using 0.032 inch stainless steel wire.",
        "expected": "FAIL",
        "spec": "Under-torqued. Wheel half tie-bolts require 150–250 foot-pounds. 30 ft-lbs is critically under-torqued."
    },
    {
        "id": 11,
        "category": "Landing Gear & Brake Systems",
        "transcript": "Completed landing gear shock strut servicing. Inflated main chamber with dry nitrogen to 150 PSI. Strut static extension height measured at 3.2 inches.",
        "expected": "FAIL",
        "spec": "Main gear chrome piston height must be exactly 4.50 inches at 250 PSI. Both 150 PSI and 3.2 inches are out-of-spec."
    },
    {
        "id": 12,
        "category": "Landing Gear & Brake Systems",
        "transcript": "Measured carbon brake rotor and stator wear pins. Outboard brake stack wear indicators are protruding by 0.012 inches. Stack is considered acceptable for return to service.",
        "expected": "FAIL",
        "spec": "Minimum wear limit pin height for carbon brake plates is typically 0.020 inches. Anything below 0.020 is worn out."
    },
    # Category 4: Engine & Powerplant (powerplant_maintenance_handbook.pdf)
    {
        "id": 13,
        "category": "Engine & Powerplant",
        "transcript": "Installed new spark plugs on cylinder number 3 top and bottom positions. Torqued spark plugs to 28 foot-pounds using calibrated torque wrench. Safety wired plugs in series.",
        "expected": "PASS",
        "spec": "Spark plugs thread torque must be 25 to 30 foot-pounds (300 to 360 inch-pounds)."
    },
    {
        "id": 14,
        "category": "Engine & Powerplant",
        "transcript": "Completed spark plug installation on cylinder 4 top and bottom. Plugs were tightened to 15 foot-pounds to prevent head thread damage. Safety wire completed.",
        "expected": "FAIL",
        "spec": "Under-torqued. 15 ft-lbs is below the 25 ft-lbs minimum limit."
    },
    {
        "id": 15,
        "category": "Engine & Powerplant",
        "transcript": "Installed engine oil filter housing cover. Torqued center bolt to 20 foot-pounds. Applied 0.032 inch safety wire in a clockwise lock direction to prevent fastener back out.",
        "expected": "PASS",
        "spec": "Oil filter housings require torque (typically 15-25 ft-lbs) and mandatory lockwire."
    },
    {
        "id": 16,
        "category": "Engine & Powerplant",
        "transcript": "Completed fuel nozzle installation. Torqued nozzle inlet coupler B-nuts to 120 inch-pounds. Lockwire was not applied since self-locking collars were present.",
        "expected": "PASS",
        "spec": "New manual does not specify a strict lockwire requirement for fuel nozzle couplers with self-locking collars."
    },
    # Category 5: Structural Repair (structural_repair_handbook.pdf)
    {
        "id": 17,
        "category": "Structural Repair",
        "transcript": "Executed fuselage skin crack repair. Stop-drilled the crack termination using a 0.125 inch drill bit. Deburred the stop-drill hole and checked via 10x magnifier. No microcracks noted.",
        "expected": "FAIL",
        "spec": "Stop-drill hole must be finished with a mechanical reamer to exactly 0.125 inches. Drilling and deburring alone is insufficient — reaming step is mandatory."
    },
    {
        "id": 18,
        "category": "Structural Repair",
        "transcript": "Stop-drilled fuselage skin crack at stringer 12. Utilized a 0.050 inch drill bit to minimize structural metal loss. Inspected hole surface.",
        "expected": "FAIL",
        "spec": "Stop-drill holes below 0.125 inches (1/8 inch) are too small to relieve stress concentration and fail structural repair standards."
    },
    {
        "id": 19,
        "category": "Structural Repair",
        "transcript": "Installed external doubler patch. Installed rivets type MS20470AD4. Checked edge distance, minimum distance is 0.38 inches. Rivet spacing is 0.5 inches.",
        "expected": "PASS",
        "spec": "Edge distance must be at least 2 times rivet diameter (2×0.125 in=0.25 in). 0.38 inches exceeds the minimum limit."
    },
    {
        "id": 20,
        "category": "Structural Repair",
        "transcript": "Completed external skin patch riveting. Edge distance from fastener centers to sheet edge is 0.18 inches. Used MS20470AD4 rivets.",
        "expected": "FAIL",
        "spec": "Edge distance fails (0.18<0.25 inches required minimum edge distance for 1/8 inch rivets)."
    }
]

async def run_prompt_test(coordinator, openrouter, prompt_dict) -> dict:
    connection_id = f"test-prompt-{prompt_dict['id']}"
    transcript = prompt_dict["transcript"]
    
    # Store dynamic validation outputs captured from SSE
    result_data = {
        "id": prompt_dict["id"],
        "category": prompt_dict["category"],
        "transcript": transcript,
        "expected": prompt_dict["expected"],
        "actual": "PENDING",
        "extracted_record": None,
        "issues": [],
        "references": []
    }
    
    # Listen to SSE events in the background to extract status and validation result
    async def sse_listener():
        async for event in coordinator.stream_manager.subscribe(connection_id):
            lines = event.strip().split("\n")
            for line in lines:
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.replace("data:", "").strip())
                        if "status" in data and "details" in data:
                            result_data["actual"] = data["status"]
                            result_data["issues"] = data["details"].get("issues", [])
                        elif "record" in data:
                            result_data["extracted_record"] = data["record"]
                        elif "references" in data:
                            result_data["references"] = data["references"]
                    except Exception:
                        pass

    listener_task = asyncio.create_task(sse_listener())
    await asyncio.sleep(0.1) # Let the queue instantiate
    
    # Temporarily mock transcribe_audio to return our transcript
    original_transcribe = openrouter.transcribe_audio
    async def mock_transcribe(*args: Any, **kwargs: Any) -> str:
        return transcript
    openrouter.transcribe_audio = mock_transcribe
    
    try:
        await coordinator.execute(connection_id, b"\x00" * 32000)
    except Exception as e:
        result_data["actual"] = f"CRASHED: {str(e)}"
    finally:
        openrouter.transcribe_audio = original_transcribe
        
    await asyncio.sleep(0.5)
    listener_task.cancel()
    
    return result_data

async def main() -> None:
    print("Initializing test clients and RAG Pipeline...")
    
    async with httpx.AsyncClient(
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=httpx.Timeout(45.0, read=90.0),
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://mro-tts.vercel.app",
            "X-Title": "mro-tts-copilot",
        },
    ) as http_client:
        openrouter = OpenRouterClient(http_client)
        cohere = CohereClient(http_client)
        pinecone = PineconeClient()
        stream_manager = SSEStreamManager()
        
        async with AsyncSessionLocal() as db_session:
            coordinator = RAGPipelineCoordinator(
                db=db_session,
                openrouter=openrouter,
                cohere=cohere,
                pinecone=pinecone,
                stream_manager=stream_manager,
            )
            
            results = []
            for prompt_dict in PROMPTS:
                print(f"Testing Prompt {prompt_dict['id']} ({prompt_dict['category']})...")
                res = await run_prompt_test(coordinator, openrouter, prompt_dict)
                results.append(res)
                print(f"  Expected: {res['expected']} | Actual: {res['actual']} | Match: {res['expected'] == res['actual']}")
                if res['issues']:
                    print(f"  Issues: {res['issues']}")
                await asyncio.sleep(1.0) # Rate limiting / pacing

            # Save the full results report as an artifact
            print("\nGenerating Markdown Report...")
            report_lines = [
                "# E2E Prompt Validation Quality Report",
                "",
                "This report summarizes the compliance validation results for all 20 test prompts compared against the generated manual PDFs.",
                "",
                "| Prompt ID | Category | Expected | Actual | Match? | Issues / Extracted |",
                "|---|---|---|---|---|---|",
            ]
            
            for r in results:
                match_symbol = "✅ PASS" if r["expected"] == r["actual"] else "❌ FAIL"
                issues_str = "; ".join(r["issues"]) if r["issues"] else "None"
                if r["extracted_record"]:
                    extracted_params = r["extracted_record"].get("compliance_parameters", [])
                    if extracted_params:
                        params_str = ", ".join([f"{p['label']}: {p['value']} ({p['spec']}) - [{p['status']}]" for p in extracted_params])
                        issues_str = f"Params: {params_str}. Issues: {issues_str}"
                
                report_lines.append(
                    f"| {r['id']} | {r['category']} | {r['expected']} | {r['actual']} | {match_symbol} | {issues_str} |"
                )
                
            report_lines.append("")
            report_lines.append("## Analysis of discrepancies (if any)")
            
            report_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "prompt_validation_report.md"))
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))
                
            print(f"Report generated successfully at: {report_path}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
