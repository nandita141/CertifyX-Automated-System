from docx import Document
from pathlib import Path
import re

def verify_output():
    docx_dir = Path("output/pdf_storage/docx")
    
    if not docx_dir.exists():
        print("Folder not found.")
        return

    # find the most recent file
    files = list(docx_dir.glob("*.docx"))
    if not files:
        print("No files generated yet.")
        return
        
    latest_file = max(files, key=lambda f: f.stat().st_mtime)
    print(f"Checking latest generated file: {latest_file.name}")
    
    try:
        doc = Document(latest_file)
        full_text = "\n".join([p.text for p in doc.paragraphs])
        
        # Look for the sentence about completion
        # "has successfully completed 6 weeks" vs "six weeks"
        matches = re.findall(r"(completed\s+.*?weeks)", full_text, re.IGNORECASE)
        
        if matches:
            print("\nFOUND IN DOCUMENT:")
            for m in matches:
                print(f"  -> '{m}'")
        else:
            print("\nCould not find 'completed ... weeks' phrase. Dumping first 500 chars:")
            print(full_text[:500])
            
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    verify_output()
