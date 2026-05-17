import sys
import os
from pathlib import Path

# Ensure the backend directory is in the Python path
sys.path.append(str(Path(__file__).resolve().parent / "backend"))

def print_help():
    print("="*40)
    print("   Certify X - Command Line Interface")
    print("="*40)
    print("Usage:")
    print("  python main.py server      - Run the Flask Backend API & Dashboard")
    print("  python main.py generate [id...] - Generate certificates (for all or specific student IDs)")
    print("  python main.py mail [id...]     - Send certificates via email (for all or specific student IDs)")
    print("  python main.py help            - Show this help message\n")

def run_server():
    print("Starting the web server...")
    print("Dashboard will be available at: http://127.0.0.1:5000/dashboard")
    print("Student Form will be available at: http://127.0.0.1:5000/form")
    print("-" * 40)
    
    # Import app here so we don't load Flask if we're just generating
    from app import app
    app.run(host="127.0.0.1", port=5000, debug=True)

def run_generation():
    print("Starting certificate generation from terminal...")
    from certificate_engine import generate_all_certificates
    import json
    
    student_ids = sys.argv[2:] if len(sys.argv) > 2 else None
    if student_ids:
        print(f"Targeting specific Student IDs: {', '.join(student_ids)}")
        
    # Run the exact same engine used by the dashboard
    result = generate_all_certificates(student_ids)
    
    print("\n" + "="*40)
    print("GENERATION STATUS")
    print("="*40)
    
    if result.get("status") == "success":
        print(f"  System Processed Successfully.")
        print(f"  Successfully Generated: {result.get('generated', 0)} PDF certificates.")
        print(f"  Failed: {result.get('failed', 0)}")
        folder_name = result.get('output_folder', 'generated')
        print(f"\nAll PDF certificates are stored in the output/pdf_storage/{folder_name} folder.")
    elif result.get("status") == "error":
        print(f"  Error encountered during generation:")
        print(f"  {result.get('error')}")
    else:
        print("  Finished with result:", json.dumps(result, indent=2))
        
    print("="*40 + "\n")

def run_mailing():
    print("Starting email service from terminal...")
    from email_service import EmailService
    import json
    
    service = EmailService()
    
    # Check if we're in testing mode
    if service.testing_mode:
        print(f"TESTING MODE ENABLED: Emails are being redirected safely to the configured test address.")
    
    student_ids = sys.argv[2:] if len(sys.argv) > 2 else None
    if student_ids:
        print(f"Targeting specific Student IDs: {', '.join(student_ids)}")
    else:
        print("Targeting ALL students with completed records...")

    # Run batch email process
    result = service.send_batch_emails(student_ids)
    
    print("\n" + "="*40)
    print("EMAIL SERVICE STATUS")
    print("="*40)
    
    if result.get("status") == "success":
        print(f"  Email Batch Complete.")
        print(f"  Successfully Sent: {result.get('sent', 0)}")
        print(f"  Failed: {result.get('failed', 0)}")
    else:
        print(f"  Error encountered: {result.get('error', 'Unknown error')}")
        
    print("="*40 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "server":
        run_server()
    elif command == "generate":
        run_generation()
    elif command == "mail":
        run_mailing()
    else:
        print_help()
