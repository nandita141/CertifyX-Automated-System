from flask import Flask, send_from_directory
from pathlib import Path
from student_api import student_api
from dashboard_api import dashboard_api

app = Flask(__name__)

# Register APIs
app.register_blueprint(student_api)
app.register_blueprint(dashboard_api)

# Serve frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
print("Frontend path:", FRONTEND_DIR)


@app.route("/")
def home():
    return "Server working!"

@app.route("/form")
def serve_form():
    return send_from_directory(FRONTEND_DIR, "studentform.html")

@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory(FRONTEND_DIR, "dashboard.html")

# Serve static files (logo, css, js, etc)
@app.route("/<path:filename>", methods=["GET"])
def serve_static(filename):
    """Serve static files from frontend directory"""
    try:
        return send_from_directory(FRONTEND_DIR, filename)
    except Exception:
        return "File not found", 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
