from docx import Document
from pathlib import Path
import re
import pandas as pd
import json

def verify_fix():
    print("--- DIAGNOSTIC START ---")
    
    # 1. Check Config on Disk
    try:
        with open("config/certificate_config.json", "r") as f:
            cfg = json.load(f)
            print(f"Config 'convert_to_words': {cfg.get('convert_to_words')}")
    except Exception as e:
        print(f"Failed to read config: {e}")

    # 2. Check Engine Code search
    try:
        with open("backend/certificate_engine.py", "r") as f:
            code = f.read()
            if 'if column in self.cert_config.get("convert_to_words"' in code:
                print("Engine Code: verified (contains dynamic check)")
            else:
                print("Engine Code: FAILED (missing dynamic check)")
                
            if 'if num2words:' in code and 'print(f"WARNING:' in code:
                print("Engine Code: verified (contains logging)")
            else:
                 print("Engine Code: FAILED (missing logging)")
    except Exception as e:
        print(f"Failed to read engine code: {e}")

    # 3. Check Generated DOCX
    docx_dir = Path("output/pdf_storage/docx")
    files = list(docx_dir.glob("*.docx"))
    valid_files = [f for f in files if not f.name.startswith("~$")]
    
    if not valid_files:
        print("No valid DOCX files found.")
        return

    latest_file = max(valid_files, key=lambda f: f.stat().st_mtime)
    print(f"Latest File: {latest_file.name}")
    print(f"Modified: {latest_file.stat().st_mtime}")
    
    try:
        doc = Document(latest_file)
        full_text = "\n".join([p.text for p in doc.paragraphs])
        
        # Search for weeks pattern
        # "completed 6 weeks" or "completed six weeks"
        matches = re.findall(r"completed\s+(\w+)\s+weeks", full_text, re.IGNORECASE)
        
        if matches:
            print(f"Found matches for 'completed [X] weeks': {matches}")
            if any(m.isdigit() for m in matches):
                print("RESULT: FAILURE (Found digits)")
            else:
                print("RESULT: SUCCESS (Found words)")
        else:
            print("No 'completed ... weeks' phrase found. Dumping context around 'weeks':")
            matches_ctx = re.findall(r".{20}weeks.{20}", full_text)
            for m in matches_ctx:
                print(f"  ...{m}...")

    except Exception as e:
        print(f"DOCX Read Error: {e}")

    print("--- DIAGNOSTIC END ---")

if __name__ == "__main__":
    verify_fix()
