import sqlite3
import os
import json
from pathlib import Path

def main():
    db_path = Path(os.path.expanduser("~/.promptfoo/promptfoo.db"))
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    output_lines = []
    try:
        cursor.execute("SELECT eval_id FROM eval_results ORDER BY created_at DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            output_lines.append("No evaluations found.")
            return
        eval_id = row[0]
        output_lines.append(f"Latest Evaluation ID: {eval_id}\n")
        
        cursor.execute("SELECT test_idx, test_case, response, success, error, grading_result FROM eval_results WHERE eval_id = ? ORDER BY test_idx ASC;", (eval_id,))
        rows = cursor.fetchall()
        
        for r in rows:
            test_idx, test_case_str, response_str, success, error, grading_result_str = r
            test_case = json.loads(test_case_str)
            response = json.loads(response_str) if response_str else {}
            grading_result = json.loads(grading_result_str) if grading_result_str else {}
            
            transcript_preview = test_case.get('vars', {}).get('transcript', '')[:60]
            output = response.get('output', '')
            
            output_lines.append("="*80)
            output_lines.append(f"TEST idx: {test_idx} | Transcript: '{transcript_preview}...'")
            output_lines.append(f"Success: {success == 1} | Error: {error}")
            output_lines.append(f"Grading result reason: {grading_result.get('reason')}")
            output_lines.append("-"*80)
            output_lines.append(f"LLM Output:\n{output}")
            output_lines.append("="*80 + "\n")
            
        # Write to inspect_output.txt in UTF-8
        out_path = Path("scratch/inspect_output.txt")
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text("\n".join(output_lines), encoding="utf-8")
        print(f"Inspection complete. Written to {out_path.absolute()}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
