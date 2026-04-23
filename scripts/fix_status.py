import sqlite3
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data/certify.db"
CERT_CONFIG_PATH = BASE_DIR / "config/certificate_config.json"

# Load config
with open(CERT_CONFIG_PATH) as f:
    config = json.load(f)
    REQUIRED_FIELDS = config.get("required_fields", [])

# Connect to DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Fetch all students
students = cursor.execute("SELECT * FROM students").fetchall()

print(f"Checking {len(students)} students status...")
updated_count = 0

for student in students:
    is_complete = True
    for field in REQUIRED_FIELDS:
        val = student[field]
        if val is None or str(val).strip() == "" or str(val).lower() == "nan":
            is_complete = False
            break
            
    if is_complete:
        cursor.execute("UPDATE students SET is_complete = 1 WHERE id = ?", (student['id'],))
        updated_count += 1

conn.commit()
conn.close()

print(f"✅ Successfully updated {updated_count} students to 'Complete' status.")
print("The certificates can now be generated from the dashboard.")
