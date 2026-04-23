# 🎓 CertifyX - Automated Internship Certificate System

CertifyX is a professional-grade, Python-based automation engine designed to manage student data, generate high-quality internship certificates from Word templates, and distribute them via secure SMTP email services. 

Integrated with **MySQL** for robust data persistence and featuring a **Real-time Admin Dashboard**.

---

## Key Features

- **Dynamic Data Management**: Powered by MySQL with automatic schema synchronization based on JSON configurations.
- **Bulk PDF Generation**: Converts DOCX templates to professional PDF certificates using high-fidelity conversion.
- **Smart Email Distribution**: Automated batch emailing with attachment support and SMTP TLS encryption.
- **Admin Dashboard**: Real-time monitoring of generation status, email delivery, and student records.
- **Security First**: Sensitive credentials managed via environment variables (`.env`) and secure "App Passwords".
- **Excel Synchronization**: One-click sync from master Excel datasets to the MySQL database.

---

## Technology Stack

- **Backend**: Python 3.x, Flask (REST API)
- **Database**: MySQL (Relational Database Management)
- **Data Handling**: Pandas, Pathlib
- **Email**: SMTP, SSL/TLS, MIME Protocol
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Modern Glassmorphism UI)
- **Automation**: Docx-Mailmerge, Python-comtypes

---

## Project Structure

```text
certify_x_2/
├── backend/            # Core logic (Flask API, Email Service, DB Manager)
├── config/             # JSON mapping and certificate configurations
├── data/               # (Ignored) Master datasets and Excel files
├── frontend/           # Web UI for Dashboard and Student Form
├── output/             # (Ignored) Generated PDFs and logs
├── templates/          # (Ignored) Official DOCX certificate templates
├── .env                # (Ignored) Private credentials
└── README.md           # Project documentation
```

---

## Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/nandita141/CertifyX-Automated-System.git
   ```

2. **Setup Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Create a `.env` file in the root directory:
   ```env
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=CertifyX_Database
   SENDER_EMAIL=your_email@gmail.com
   SENDER_PASSWORD=your_app_password
   ```

4. **Run the Application**:
   ```bash
   python backend/app.py
   ```

---

## Security Note
This project follows strict security practices. Data files, certificate templates, and environment variables are excluded from the repository via `.gitignore` to protect sensitive information and institutional standards.


