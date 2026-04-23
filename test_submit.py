#!/usr/bin/env python
import sys
sys.path.insert(0, 'backend')

from student_api import submit_form, load_data, WEB_FIELDS
from flask import Flask, request
import json

# Create a test app context
app = Flask(__name__)

print("=" * 60)
print("🧪 Testing Submit Form Function")
print("=" * 60)

# Test data
test_data = {
    "student_id": "20252756",
    "supervisor_name": "Amit Kumar Agrawal",
    "internship_start_date": "2026-02-13",
    "internship_end_date": "2026-03-28",
    "no_of_weeks": "7",
    "focused_on": "test",
    "contributed_towards": "test"
}

print("\n Test Payload:")
print(json.dumps(test_data, indent=2))

print("\n Loading master dataset...")
try:
    df = load_data()
    print(f" Dataset loaded: {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")
    
    # Check if student exists
    student_id = "20252756"
    if student_id in df["student_id"].astype(str).values:
        print(f" Student {student_id} found")
        idx = df[df["student_id"].astype(str) == student_id].index[0]
        print(f"   Index: {idx}")
        print(f"   Current data: {df.iloc[idx].to_dict()}")
    else:
        print(f" Student {student_id} not found")
        
except Exception as e:
    print(f" Error loading data: {e}")
    import traceback
    traceback.print_exc()

print("\n WEB_FIELDS (allowed to update):")
print(json.dumps(WEB_FIELDS, indent=2))

print("\n Simulating submit_form...")
try:
    with app.test_request_context(
        '/submit-form',
        method='POST',
        data=json.dumps(test_data),
        content_type='application/json'
    ):
        result = submit_form()
        print(f"Result: {result}")
except Exception as e:
    print(f"Error during submit: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
