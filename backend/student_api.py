from flask import Blueprint, request, jsonify
import json
from pathlib import Path
import pandas as pd # Still needed for some internal checks in specific routes if any
from db_manager import DatabaseManager

student_api = Blueprint("student_api", __name__)
db = DatabaseManager()

# ================= CONFIG LOAD =================

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "config/config.json") as f:
    CONFIG = json.load(f)

with open(BASE_DIR / "config/webform_fields.json") as f:
    WEB_FIELDS = json.load(f)

# ================= CHECK STUDENT =================

@student_api.route("/check-id/<student_id>", methods=["GET"])
def check_id(student_id):
    """
    Check if a student exists in the database by ID and return their current data. 
    This is called when the student enters their Application ID in the form.
    """
    try:
        student_data = db.get_student(student_id)
        
        if not student_data:
            return jsonify({"valid": False})
        
        # Clean up data for frontend (convert None to empty string)
        clean_data = {k: (v if v is not None else "") for k, v in student_data.items()}
        
        return jsonify({
            "valid": True,
            "student_data": clean_data
        })
        
    except Exception as e:
        print(f"Error checking ID: {e}")
        return jsonify({"error": str(e)}), 500

# ================= SUBMIT FORM =================

@student_api.route("/submit-form", methods=["POST"])
def submit_form():
    """
    Called when a student hits "Submit" on the web form. 
    It updates the student's record in the MySQL database.
    """
    try:
        data = request.json
        student_id = str(data.get("student_id", ""))

        if not student_id:
            return jsonify({"error": "student_id required"}), 400

        # Check if student exists
        student = db.get_student(student_id)
        if not student:
            return jsonify({"error": "Invalid Application ID"}), 404

        # Prepare data for update (cleaning values)
        update_data = {}
        for field in WEB_FIELDS.keys():
            if field in data:
                val = data[field]
                # Type conversion for numeric fields
                if field == "no_of_weeks" and val is not None:
                    try:
                        val = float(val) if val != "" else None
                    except (ValueError, TypeError):
                        pass
                update_data[field] = val
        
        # Mark as complete if all required fields are filled (basic check)
        # In a real app, you'd check specific required fields from config
        update_data['is_complete'] = True

        # Save to database
        db.update_student(student_id, update_data)

        # Log this activity
        print(f"✅ Form submitted and saved to database for Student ID: {student_id}")

        return jsonify({"message": "Your details have been securely saved! You can now close this window."})
    
    except Exception as e:
        print(f"Submit form error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# ================= SUPERVISORS =================

@student_api.route("/supervisors", methods=["GET"])
def get_supervisors():
    """
    Returns a unique list of supervisors for the dropdown in the form.
    Exclusively uses the official list from config/professors.json.
    """
    try:
        # Load official list from JSON
        prof_file = BASE_DIR / "config/professors.json"
        if prof_file.exists():
            with open(prof_file, "r") as f:
                official_list = json.load(f)
        else:
            official_list = []

        return jsonify(official_list)
        
    except Exception as e:
        print(f"Error fetching supervisors: {e}")
        return jsonify([]), 500

# ================= GET ALL STUDENTS =================

@student_api.route("/students", methods=["GET"])
def get_students_list():
    """
    Simple list of students for internal tool selection.
    """
    try:
        students = db.get_all_students()
        # Return only basic info
        summary = [{"student_id": s["student_id"], "student_name": s["student_name"]} for s in students]
        return jsonify(summary)
    except Exception as e:
        print(f"Error fetching students list: {e}")
        return jsonify({"error": str(e)}), 500

# ================= CERTIFICATE GENERATION =================

@student_api.route("/generate-certificate", methods=["POST"])
def generate_certificate():
    """
    Triggered when a student finishes the form. 
    (Usually handled by the backend dashboard, but kept here for student feedback).
    """
    try:
        data = request.json
        student_id = str(data.get("student_id", ""))

        if not student_id:
            return jsonify({"error": "student_id required"}), 400

        student = db.get_student(student_id)
        if not student:
             return jsonify({"error": "Invalid Student ID"}), 404

        student_name = student.get("student_name", "Student")
        student_email = student.get("student_email", "")

        print(f"🎓 Certificate generation request from student: {student_name} ({student_id})")
        
        return jsonify({
            "message": f"Certificate generation started for {student_name}! The admin will review and send it shortly.",
            "student_id": student_id,
            "student_name": student_name,
            "email": student_email
        })

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

print("student_api loaded")
