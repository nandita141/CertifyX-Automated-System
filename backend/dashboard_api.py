from flask import Blueprint, jsonify, send_from_directory, request
from pathlib import Path
import os
import json
import sys
import pandas as pd
from datetime import datetime
import shutil
import zipfile

# Import certificate engine directly
sys.path.insert(0, str(Path(__file__).parent))
from certificate_engine import generate_all_certificates
from email_service import EmailService

from db_manager import DatabaseManager

dashboard_api = Blueprint("dashboard_api", __name__)
db = DatabaseManager()

# BASE PATH & CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "config/config.json") as f:
    CONFIG = json.load(f)

with open(BASE_DIR / "config/certificate_config.json") as f:
    CERT_CONFIG = json.load(f)

DATA_FILE = BASE_DIR / CONFIG["master_dataset_path"]
PDF_DIR = BASE_DIR / CONFIG["pdf_folder"]
GENERATED_DIR = PDF_DIR / "generated"
DOWNLOAD_DIR = BASE_DIR / CONFIG["download_folder"]
DRAFT_DIR = BASE_DIR / CONFIG["draft_folder"]
EMAIL_DIR = BASE_DIR / CONFIG.get("email_folder", "output/email_queue")
DOCX_DIR = PDF_DIR / "docx"
INDIVIDUAL_DIR = PDF_DIR / "individual"
ACTIVITY_LOG = BASE_DIR / "output" / "certificate_generation_log.json"

# Create all folders
for folder in [PDF_DIR, GENERATED_DIR, INDIVIDUAL_DIR, DOWNLOAD_DIR, DRAFT_DIR, EMAIL_DIR, DOCX_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


# ENDPOINT: GET DASHBOARD STATS


@dashboard_api.route("/api/dashboard/stats", methods=["GET"])
def get_stats():
    """Get certificate generation statistics directly from the database."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Total Students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        
        # Students complete
        cursor.execute("SELECT COUNT(*) FROM students WHERE is_complete = 1")
        students_complete = cursor.fetchone()[0]
        
        # Count generated from database (unique students)
        cursor.execute("SELECT COUNT(*) FROM students WHERE certificate_generated = 1")
        generated_count = cursor.fetchone()[0]
        
        # Count downloaded
        downloaded_count = len(list(DOWNLOAD_DIR.glob("*.pdf"))) + len(list(DOWNLOAD_DIR.glob("*.zip")))
        
        # Emails from students table (unique students who received emails)
        cursor.execute("SELECT COUNT(*) FROM students WHERE email_sent = 1")
        emails_sent = cursor.fetchone()[0]
        
        conn.close()

        return jsonify({
            "total_students": total_students,
            "students_complete": students_complete,
            "students_incomplete": total_students - students_complete,
            "certificates_generated": generated_count,
            "certificates_downloaded": downloaded_count,
            "emails_sent": emails_sent
        })
    
    except Exception as e:
        print(f"Error in stats: {e}")
        return jsonify({"error": str(e)}), 500


# ENDPOINT: GET STUDENTS LIST


@dashboard_api.route("/api/dashboard/students", methods=["GET"])
def get_students():
    """Get all students from database with their status."""
    try:
        students_raw = db.get_all_students()
        students = []
        
        for row in students_raw:
            student_id = str(row['student_id'])
            
            # Use flags directly from DB
            is_complete = bool(row.get('is_complete', 0))
            
            # Check for actual PDF file in both folders
            pdf_path_gen = GENERATED_DIR / f"{student_id}_certificate.pdf"
            pdf_path_ind = INDIVIDUAL_DIR / f"{student_id}_certificate.pdf"
            pdf_exists = pdf_path_gen.exists() or pdf_path_ind.exists()
            
            # Use the valid path for file name
            found_pdf = pdf_path_gen if pdf_path_gen.exists() else (pdf_path_ind if pdf_path_ind.exists() else None)
            generated_at = row.get('generated_at')

            students.append({
                "student_id": student_id,
                "student_name": row.get('student_name', ''),
                "is_complete": is_complete,
                "certificate_generated": pdf_exists,
                "generated_at": generated_at,
                "pdf_file": found_pdf.name if found_pdf else None,
                "supervisor_name": row.get('supervisor_name', '')
            })
        
        return jsonify(students)
    
    except Exception as e:
        print(f"Error in get_students: {e}")
        return jsonify({"error": str(e)}), 500


# ENDPOINT: GET ACTIVITY LOg

@dashboard_api.route("/api/dashboard/activity-log", methods=["GET"])
def get_activity_log():
    """Get the latest activity log"""
    try:
        if ACTIVITY_LOG.exists():
            with open(ACTIVITY_LOG, 'r') as f:
                return jsonify(json.load(f))
        else:
            return jsonify([])
            
    except Exception as e:
        print(f"Error reading activity log: {e}")
        return jsonify([])


# ENDPOINT: GENERATE ALL CERTIFICATES


import threading
import pythoncom

@dashboard_api.route("/api/dashboard/generate-all", methods=["POST"])
def generate_all():
    """Trigger batch certificate generation (Async)"""
    try:
        data = request.get_json(silent=True) or {}
        student_id_input = data.get("student_id")
        
        # Support comma-separated IDs and remove all spaces (e.g. "202 52217" -> "20252217")
        student_ids = None
        if student_id_input and isinstance(student_id_input, str):
            student_ids = [s.replace(" ", "") for s in student_id_input.split(",") if s.strip()]
            
        print(f"\n API: Starting certificate generation (Threaded)... Target: {student_ids if student_ids else 'All'}")
        
        # Clear log before starting
        if ACTIVITY_LOG.exists():
            try: ACTIVITY_LOG.unlink()
            except: pass
        
        # Run in background thread to avoid blocking UI
        def run_generation(targets=None):
            try:
                pythoncom.CoInitialize()
                result = generate_all_certificates(targets)
                print(f" Generation result: {result}")
            except Exception as e:
                print(f"Thread error: {e}")
            finally:
                pythoncom.CoUninitialize()

        thread = threading.Thread(target=run_generation, args=(student_ids,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Certificate generation started in background...",
        })
    
    except Exception as e:
        print(f" Error in generate_all: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "error": str(e)
        }), 500


# ENDPOINT: GENERATE AND EMAIL (Async)

@dashboard_api.route("/api/dashboard/generate-email", methods=["POST"])
def generate_email():
    """Trigger certificate generation and then email them (Async)"""
    try:
        data = request.get_json(silent=True) or {}
        student_ids = data.get("student_ids") # Can be single or comma separated
        
        if student_ids and isinstance(student_ids, str):
            student_ids = [s.replace(" ", "") for s in student_ids.split(",") if s.strip()]
        
        print(f"\n API: Starting generation + email... Target: {student_ids if student_ids else 'All'}")
        
        # Run in background
        def run_process(targets=None):
            try:
                pythoncom.CoInitialize()
                # 1. Generate certificates
                print("Step 1: Generating Certificates...")
                result = generate_all_certificates(targets)
                
                # 2. Send Emails
                print("Step 2: Sending Emails...")
                email_svc = EmailService()
                email_svc.send_batch_emails(targets)
                
            except Exception as e:
                print(f"Thread error in generate_email: {e}")
            finally:
                pythoncom.CoUninitialize()

        thread = threading.Thread(target=run_process, args=(student_ids,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Generation and emailing started in background...",
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ENDPOINT: SEND EMAIL FOR EXISTING CERTIFICATES (Async)

@dashboard_api.route("/api/dashboard/send-email", methods=["POST"])
def send_email():
    """Send emails for certificates that have already been generated"""
    try:
        data = request.get_json(silent=True) or {}
        student_ids = data.get("student_ids")
        
        if student_ids and isinstance(student_ids, str):
            student_ids = [s.replace(" ", "") for s in student_ids.split(",") if s.strip()]
            
        print(f"\n API: Sending core emails... Target: {student_ids if student_ids else 'All'}")
        
        def run_email_only(targets=None):
            try:
                email_svc = EmailService()
                email_svc.send_batch_emails(targets)
            except Exception as e:
                print(f"Thread error in send_email: {e}")

        thread = threading.Thread(target=run_email_only, args=(student_ids,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Email process started in background...",
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ENDPOINT: DOWNLOAD ALL (ZIP)


@dashboard_api.route("/api/dashboard/download-all", methods=["POST"])
def download_all():
    """Create and download ZIP of all certificates"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"certificates_{timestamp}.zip"
        zip_path = DOWNLOAD_DIR / zip_filename
        
        # Collect all files (PDF ONLY)
        files_to_zip = list(GENERATED_DIR.glob("*.pdf"))
        
        if not files_to_zip:
             return jsonify({"error": "No PDF certificates found. Please generate them first."}), 404
             
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in files_to_zip:
                # Store in zip with clean names
                zipf.write(f, arcname=f.name)
                
        return send_from_directory(DOWNLOAD_DIR, zip_filename, as_attachment=True)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ENDPOINT: DOWNLOAD SINGLE CERTIFICAT


@dashboard_api.route("/api/dashboard/download/<student_id>", methods=["GET"])
def download_certificate(student_id):
    """Download certificate for a specific student (PDF or DOCX fallback)"""
    try:
        # Try PDF first in both generated and individual folders
        pdf_file = GENERATED_DIR / f"{student_id}_certificate.pdf"
        if not pdf_file.exists():
            pdf_file = INDIVIDUAL_DIR / f"{student_id}_certificate.pdf"
            
        target_file = None
        if pdf_file.exists():
            target_file = pdf_file
        else:
            # Try DOCX
            docx_file = DOCX_DIR / f"{student_id}_certificate.docx"
            if docx_file.exists():
                target_file = docx_file
        
        if target_file:
            # Save a copy to DOWNLOAD_DIR so it appears in "View Downloaded"
            shutil.copy(target_file, DOWNLOAD_DIR / target_file.name)
            return send_from_directory(target_file.parent, target_file.name, as_attachment=True)
             
        return jsonify({"error": "File not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        

# ENDPOINT: DELETE ALL


@dashboard_api.route("/api/dashboard/delete-all", methods=["POST"])
def delete_all():
    """Delete all generated files and logs"""
    try:
        deleted_count = 0
        
        # Delete generated PDFs (Main folder)
        for f in GENERATED_DIR.glob("*"):
            try: f.unlink()
            except: pass
            
        # Delete generated PDFs (Individual folder)
        for f in INDIVIDUAL_DIR.glob("*"):
            try: f.unlink()
            except: pass
            
        # Delete DOCX files
        for f in DOCX_DIR.glob("*"):
            try: f.unlink()
            except: pass
            
        # Clear log
        if ACTIVITY_LOG.exists():
            try: ACTIVITY_LOG.unlink()
            except: pass
            
        # Reset database flags so dashboard shows everything as "Not Generated"
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET certificate_generated = 0, email_sent = 0, generated_at = NULL")
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success", 
            "message": "All generated files deleted and database status reset successfully!"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500





# ENDPOINT: DELETE SINGLE FILE


@dashboard_api.route("/api/dashboard/delete-file", methods=["POST"])
def delete_file():
    """Delete a single file (generated, downloaded, or email draft)"""
    try:
        data = request.json
        filename = data.get("filename")
        file_type = data.get("file_type")
        
        if not filename or not file_type:
             return jsonify({"error": "Missing filename or file_type"}), 400
             
        # Determine directory
        if file_type == "generated":
            # Check GENERATED_DIR first, then INDIVIDUAL_DIR
            if (GENERATED_DIR / filename).exists():
                target_dir = GENERATED_DIR
            elif (INDIVIDUAL_DIR / filename).exists():
                target_dir = INDIVIDUAL_DIR
            else:
                target_dir = GENERATED_DIR # Fallback
        elif file_type == "downloaded":
            target_dir = DOWNLOAD_DIR
        elif file_type == "email":
            target_dir = EMAIL_DIR
        else:
            return jsonify({"error": "Invalid file type"}), 400
            
        file_path = target_dir / filename
        
        # Security check: Ensure file is within target directory
        # Basic check to prevent ../ traversal
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
             return jsonify({"error": "Invalid filename"}), 400

        if not file_path.exists():
             return jsonify({"error": "File not found"}), 404

        file_path.unlink()
        
        # If deleting a generated PDF, also try to delete the DOCX
        if file_type == "generated" and filename.endswith(".pdf"):
            docx_name = filename.replace(".pdf", ".docx")
            docx_path = DOCX_DIR / docx_name
            if docx_path.exists():
                try: docx_path.unlink()
                except: pass

        return jsonify({"status": "success", "message": f"Deleted {filename}"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dashboard_api.route("/api/dashboard/files", methods=["GET"])
def list_files():
    """Return list of generated, individual, downloaded, and email draft files with URLs"""
    try:
        generated = []
        # Include PDFs from 'generated'
        for f in GENERATED_DIR.glob("*.pdf"):
            if f.name.startswith("~$"): continue
            generated.append({
                "name": f.name,
                "path": str(f),
                "generated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat() if hasattr(f.stat(), 'st_mtime') else None,
                "url": f"/files/generated/{f.name}",
                "download_url": f"/api/dashboard/download/{f.stem.replace('_certificate','')}",
                "display_name": f.stem.replace('_certificate', '').replace('_', ' ')
            })
            
        individual = []
        # Include PDFs from 'individual'
        for f in INDIVIDUAL_DIR.glob("*.pdf"):
            if f.name.startswith("~$"): continue
            individual.append({
                "name": f.name,
                "path": str(f),
                "generated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat() if hasattr(f.stat(), 'st_mtime') else None,
                "url": f"/files/individual/{f.name}",
                "download_url": f"/api/dashboard/download/{f.stem.replace('_certificate','')}",
                "display_name": f.stem.replace('_certificate', '').replace('_', ' ')
            })
            
        # Include DOCX (in case PDF failed)
        for f in DOCX_DIR.glob("*.docx"):
            if f.name.startswith("~$"): continue  # Skip lock files
            # Check if PDF exists for this DOCX
            pdf_path = GENERATED_DIR / f"{f.stem}.pdf"
            if not pdf_path.exists():
                try:
                    ts = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                except Exception:
                    ts = None
                generated.append({
                    "name": f.name,
                    "path": str(f),
                    "generated_at": ts,
                    "url": f"/files/docx/{f.name}",
                    "download_url": f"/files/docx/{f.name}", # Direct download for DOCX
                    "display_name": f.stem.replace('_certificate', '').replace('_', ' ')
                })

        downloaded = []
        # Include PDF and ZIP
        for f in list(DOWNLOAD_DIR.glob("*.pdf")) + list(DOWNLOAD_DIR.glob("*.zip")):
            try:
                ts = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            except Exception:
                ts = None
            downloaded.append({
                "name": f.name,
                "path": str(f),
                "downloaded_at": ts,
                "url": f"/files/downloads/{f.name}",
                "display_name": f.name
            })

        email_drafts = []
        for f in EMAIL_DIR.glob("*"):
            if f.is_file():
                try:
                    ts = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                except Exception:
                    ts = None
                email_drafts.append({
                    "name": f.name,
                    "path": str(f),
                    "created_at": ts,
                    "url": f"/files/email/{f.name}",
                    "display_name": f.name
                })

        return jsonify({
            "generated": generated,
            "individual": individual,
            "downloaded": downloaded,
            "email": email_drafts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve files directly (generated)
@dashboard_api.route('/files/generated/<path:filename>', methods=['GET'])
def serve_generated_file(filename):
    try:
        return send_from_directory(GENERATED_DIR, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve files directly (individual)
@dashboard_api.route('/files/individual/<path:filename>', methods=['GET'])
def serve_individual_file(filename):
    try:
        return send_from_directory(INDIVIDUAL_DIR, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve files directly (docx)
@dashboard_api.route('/files/docx/<path:filename>', methods=['GET'])
def serve_docx_file(filename):
    try:
        return send_from_directory(DOCX_DIR, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve files directly (downloads)
@dashboard_api.route('/files/downloads/<path:filename>', methods=['GET'])
def serve_download_file(filename):
    try:
        return send_from_directory(DOWNLOAD_DIR, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve files directly (email drafts)
@dashboard_api.route('/files/email/<path:filename>', methods=['GET'])
def serve_email_file(filename):
    try:
        return send_from_directory(EMAIL_DIR, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================================
# ENDPOINT: GET FOLDER PATHS
# ================================

@dashboard_api.route("/api/dashboard/folders", methods=["GET"])
def get_folders():
    """Return folder paths for generated, individual, downloaded, and email certificates"""
    try:
        return jsonify({
            "generated_folder": str(GENERATED_DIR),
            "individual_folder": str(INDIVIDUAL_DIR),
            "downloaded_folder": str(DOWNLOAD_DIR),
            "email_folder": str(EMAIL_DIR)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ENDPOINT: OPEN FOLDER IN EXPLORER


@dashboard_api.route("/api/dashboard/open-folder/<folder_type>", methods=["POST"])
def open_folder(folder_type):
    """Open folder in Windows Explorer"""
    try:
        import subprocess
        
        if folder_type == "generated":
            folder_path = GENERATED_DIR
        elif folder_type == "individual":
            folder_path = INDIVIDUAL_DIR
        elif folder_type == "downloaded":
            folder_path = DOWNLOAD_DIR
        elif folder_type == "email":
            folder_path = EMAIL_DIR
        else:
            return jsonify({"error": "Invalid folder type"}), 400
        
        # Create folder if it doesn't exist
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Open folder in Explorer (Windows only)
        import sys
        if sys.platform == "win32":
            subprocess.Popen(f'explorer "{str(folder_path)}"')
            return jsonify({"status": "success", "message": f"Opened folder: {folder_path}"})
        else:
            return jsonify({"error": "Open folder feature only works on Windows"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
