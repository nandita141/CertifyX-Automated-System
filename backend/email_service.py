import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

class EmailService:
    def __init__(self, config_path=None):
        """
        Initialize Email Service.
        """
        self.base_dir = Path(__file__).resolve().parent.parent
        self.config_path = config_path or self.base_dir / "config/config.json"
        self._load_config()

    def _load_config(self):
        """Load configuration and SMTP details."""
        # Force load .env manually to avoid restarting the server every time
        self._load_env_manually()

        # 1. Load Main Config
        try:
            with open(self.config_path) as f:
                self.main_config = json.load(f)
            
            # Use configurations from config.json
            self.testing_mode = self.main_config.get("testing_mode", False)
            self.test_email = self.main_config.get("test_email", "")
            
            self.activity_log_file = self.base_dir / "output" / "certificate_generation_log.json"
            self.master_dataset = self.base_dir / self.main_config.get("master_dataset_path", "data/master_dataset.xlsx")
            
            pdf_base = self.main_config.get("pdf_folder", "output/pdf_storage")
            self.pdf_folder = self.base_dir / pdf_base / "generated"

            # Load Templates
            self.email_subject_template = self.main_config.get("email_subject", "Certificate - {student_name}")
            self.email_body_template = self.main_config.get("email_body", "Dear {student_name},\n\nPlease find your certificate attached.\n\nRegards,\nCertifyX Team")
            
        except Exception as e:
            print(f"Error loading main config for EmailService: {e}")
            self.testing_mode = False
            self.test_email = ""
            self.email_subject_template = "Certificate - {student_name}"
            self.email_body_template = "Dear {student_name},\n\nPlease find your certificate attached.\n\nRegards,\nCertifyX Team"
            self.activity_log_file = self.base_dir / "output" / "certificate_generation_log.json"
            self.master_dataset = self.base_dir / "data/master_dataset.xlsx"
            self.pdf_folder = self.base_dir / "output/pdf_storage/generated"

        # 2. Get SMTP details
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.sender_email = os.environ.get("SENDER_EMAIL", "")
        self.sender_password = os.environ.get("SENDER_PASSWORD", "")

    def _load_env_manually(self):
        """Read .env file directly into os.environ to pick up changes immediately."""
        env_path = self.base_dir / ".env"
        if env_path.exists():
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, val = line.split('=', 1)
                            # Remove quotes if present
                            val = val.strip().strip('"').strip("'")
                            os.environ[key.strip()] = val
            except Exception as e:
                print(f"Manual .env load failed: {e}")

    def log_activity(self, activity_type, data):
        """Log activity to both the activity_log table and the JSON file."""
        # 1. Log to JSON (for backward compatibility with any UI using it)
        self.activity_log_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": activity_type,
            "data": data
        }
        try:
            logs = []
            if self.activity_log_file.exists():
                with open(self.activity_log_file, 'r') as f:
                    logs = json.load(f)
            logs.append(entry)
            with open(self.activity_log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Error logging activity to JSON: {e}")

        # 2. Log to SQL Database
        try:
            from db_manager import DatabaseManager
            db = DatabaseManager()
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO activity_log (type, student_id, details) VALUES (%s, %s, %s)",
                (activity_type, str(data.get("student_id", "")), json.dumps(data))
            )
            
            # If it's a successful email, update the student record flag
            if activity_type == "email_sent":
                cursor.execute(
                    "UPDATE students SET email_sent = 1 WHERE student_id = %s",
                    (str(data.get("student_id")),)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging activity to SQL: {e}")

    def send_certificate_email(self, recipient_email, student_name, student_id, pdf_path):
        """Send an email with the certificate attached."""
        
        # Override recipient if testing_mode is enabled
        original_recipient = recipient_email
        if self.testing_mode and self.test_email:
            print(f"[TESTING MODE] Redirecting email safely to test address...")
            recipient_email = self.test_email

        # Critical Check: Don't proceed if using placeholders
        if "your-email@gmail.com" in self.sender_email or not self.sender_email:
            error_msg = "SMTP Credentials not found! Please check and SAVE your .env file."
            print(f"ERROR: {error_msg}")
            self.log_activity("email_failed", {
                "student_id": str(student_id), 
                "student_name": student_name,
                "error": error_msg
            })
            return False, error_msg

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = recipient_email
        msg['Subject'] = self.email_subject_template.format(student_name=student_name)

        body = self.email_body_template.format(student_name=student_name)
        if self.testing_mode:
            body += f"\n\n[NOTE: This is a test email redirected from {original_recipient}]"

        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                 # Secondary search in individual folder
                 individual_pdf = self.base_dir / self.main_config.get("pdf_folder", "output/pdf_storage") / "individual" / f"{student_id}_certificate.pdf"
                 if individual_pdf.exists():
                     pdf_path = individual_pdf
                 else:
                     raise FileNotFoundError(f"PDF certificate not found for ID {student_id}")
                 
            with open(pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {pdf_path.name}")
                msg.attach(part)
        except Exception as e:
            error_msg = f"Failed to attach PDF: {str(e)}"
            self.log_activity("email_failed", {"student_id": str(student_id), "student_name": student_name, "error": error_msg})
            return False, error_msg

        # Send email
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.set_debuglevel(0)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            self.log_activity("email_sent", {
                "student_id": str(student_id), 
                "student_name": student_name, 
                "recipient": recipient_email,
                "message": f"Email sent successfully {'(Test Mode)' if self.testing_mode else ''}"
            })
            return True, "Email sent successfully"
        except Exception as e:
            error_msg = f"SMTP Error: {str(e)}"
            self.log_activity("email_failed", {"student_id": str(student_id), "student_name": student_name, "error": error_msg})
            return False, error_msg

    def send_batch_emails(self, student_ids=None):
        """
        Process batches of emails using the SQL database.
        """
        try:
            from db_manager import DatabaseManager
            db = DatabaseManager()
            conn = db.get_connection()

            # Fetch students to email
            cursor = conn.cursor(dictionary=True)
            if student_ids:
                placeholders = ','.join(['%s'] * len(student_ids))
                query = f"SELECT * FROM students WHERE student_id IN ({placeholders})"
                cursor.execute(query, [str(sid).strip() for sid in student_ids])
                rows = cursor.fetchall()
            else:
                query = "SELECT * FROM students WHERE is_complete = 1"
                cursor.execute(query)
                rows = cursor.fetchall()
            
            conn.close() # Close quickly
            
            success_count = 0
            failed_count = 0
            
            self.log_activity("batch_email_started", {"count": len(rows)})
            
            if not rows:
                 return {"status": "success", "sent": 0, "failed": 0}

            for row in rows:
                sid = str(row["student_id"])
                sname = row.get("student_name", "Student")
                semail = row.get("student_email", "")
                
                # Check if email is already sent
                if row.get("email_sent") == 1:
                    self.log_activity("email_skipped", {
                        "student_id": sid, 
                        "student_name": sname, 
                        "reason": "Email already sent previously."
                    })
                    continue
                
                # Check if PDF exists before attempting to send
                pdf_path = self.pdf_folder / f"{sid}_certificate.pdf"
                
                if not pdf_path.exists():
                     # Try the secondary folder
                     pdf_path = self.base_dir / self.main_config.get("pdf_folder", "output/pdf_storage") / "individual" / f"{sid}_certificate.pdf"
                     
                if not pdf_path.exists():
                    self.log_activity("email_skipped", {
                        "student_id": sid, 
                        "student_name": sname, 
                        "reason": "PDF not generated. Please run 'Generate All' first."
                    })
                    continue
                
                success, _ = self.send_certificate_email(semail, sname, sid, pdf_path)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            
            self.log_activity("batch_email_complete", {"success": success_count, "failed": failed_count})
            return {"status": "success", "sent": success_count, "failed": failed_count}

        except Exception as e:
            error_msg = f"Batch process error: {str(e)}"
            self.log_activity("batch_email_failed", {"error": error_msg})
            return {"status": "error", "message": error_msg}
