import pandas as pd
from pathlib import Path

# ================= PATHS =================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

STUDENT_FILE = DATA_DIR / "OIP-Final List 2025.xlsx"
SUPERVISOR_FILE = DATA_DIR / "Selection List_OIP 2025.xlsx"
OUTPUT_FILE = DATA_DIR / "master_dataset.xlsx"

MERGE_KEY = "student_id"

# ================= READ FILES =================
df_student = pd.read_excel(STUDENT_FILE)
df_supervisor = pd.read_excel(SUPERVISOR_FILE)

# ================= SELECT REQUIRED COLUMNS =================
df_student = df_student[
    [
        "student_id",
        "student_name",
        "father_name",
        "Programme",
        "department",
        "institute_name",
        "AddressofCom",
        "student_email",
        "student_contact"
    ]
]

df_supervisor = df_supervisor[
    [
        "student_id",
        "supervisor_name",
        "supervisor_email"
    ]
]

# ================= MERGE =================
master_df = pd.merge(
    df_student,
    df_supervisor,
    on=MERGE_KEY,
    how="inner"
)

# ================= WEB FORM COLUMNS =================
master_df["internship_start_date"] = ""
master_df["internship_end_date"] = ""
master_df["no_of_weeks"] = ""
master_df["focused_on"] = ""
master_df["contributed_towards"] = ""

# ================= SAVE =================
master_df.to_excel(OUTPUT_FILE, index=False)

print("MASTER DATASET CREATED SUCCESSFULLY")
print(master_df.columns.tolist())
