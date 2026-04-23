

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path
import json

from backend.certificate_engine import fill_certificate, convert_to_pdf


app = FastAPI()

# ================= CORS =================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= CONFIG =================

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "config/config.json") as f:
    CONFIG = json.load(f)

DATA_FILE = BASE_DIR / CONFIG["master_dataset_path"]
PDF_DIR = BASE_DIR / CONFIG["pdf_folder"]

# ================= GET STUDENT =================

@app.get("/student/{student_id}")
def get_student(student_id: str):
    df = pd.read_excel(DATA_FILE)

    row = df[df["student_id"].astype(str) == student_id]

    if row.empty:
        return {"error": "Student not found"}

    return row.iloc[0].to_dict()

# ================= GET SUPERVISORS =================

@app.get("/supervisors")
def get_supervisors():
    df = pd.read_excel(DATA_FILE)

    supervisors = sorted(
        df["supervisor_name"]
        .dropna()
        .unique()
        .tolist()
    )

    return supervisors

# ================= UPDATE STUDENT =================

@app.post("/update")
def update_student(data: dict):
    df = pd.read_excel(DATA_FILE)

    sid = str(data["student_id"])
    index = df[df["student_id"].astype(str) == sid].index

    if len(index) == 0:
        return {"error": "Student not found"}

    for key, value in data.items():
        if key in df.columns:
            df.loc[index, key] = value

    df.to_excel(DATA_FILE, index=False)

    return {"message": "Updated successfully"}

# ================= GENERATE CERTIFICATES =================

@app.post("/generate")
def generate_certificates():
    df = pd.read_excel(DATA_FILE)

    success = 0

    for _, row in df.iterrows():
        try:
            doc = fill_certificate(row)
            convert_to_pdf(doc)
            success += 1
        except Exception as e:
            print("Error generating certificate:", e)

    return {"generated": success}

# ================= DASHBOARD STATS =================

@app.get("/stats")
def stats():
    total = len(list(PDF_DIR.glob("*.pdf")))

    return {
        "total_certificates": total
    }
