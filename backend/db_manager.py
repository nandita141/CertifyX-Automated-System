import mysql.connector
import pandas as pd
from pathlib import Path
import json
import os
from dotenv import load_dotenv

class DatabaseManager:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        
        # Load config to get paths
        with open(self.base_dir / "config/config.json", "r") as f:
            self.config = json.load(f)
            
        with open(self.base_dir / "config/mapping.json", "r") as f:
            self.mapping = json.load(f)
            
        with open(self.base_dir / "config/certificate_config.json", "r") as f:
            self.cert_config = json.load(f)

        with open(self.base_dir / "config/webform_fields.json", "r") as f:
            self.web_fields = json.load(f)
            
        load_dotenv(self.base_dir / ".env")
        
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'CertifyX_Database')
        }
            
        self.excel_path = self.base_dir / self.config["master_dataset_path"]
        
    def _get_dynamic_columns(self):
        """Build the list of columns dynamically from all config files."""
        columns = set()
        
        # 1. From mapping.json
        columns.update(self.mapping.get("student_column_map", {}).values())
        columns.update(self.mapping.get("supervisor_column_map", {}).values())
        
        # 2. From certificate_config.json (placeholders)
        columns.update(self.cert_config.get("placeholders", {}).values())
        
        # 3. From webform_fields.json
        columns.update(self.web_fields.keys())
        
        # Remove any empty or None values
        columns = {str(c) for c in columns if c}
        
        # Ensure student_id is always there
        columns.add("student_id")
        
        return sorted(list(columns))

    def get_connection(self):
        """Get a connection to the MySQL database."""
        conn = mysql.connector.connect(**self.db_config)
        return conn

    def get_cursor(self, conn):
        """Get a cursor that returns results as dictionaries."""
        return conn.cursor(dictionary=True)

    def initialize_db(self):
        """Create the students table dynamically based on configuration in MySQL."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cols = self._get_dynamic_columns()
        
        # Build SQL columns string
        # Most columns are TEXT for safety, student_id is UNIQUE
        sql_cols = ["id INT AUTO_INCREMENT PRIMARY KEY"]
        for col in cols:
            if col == "student_id":
                sql_cols.append(f"`{col}` VARCHAR(255) UNIQUE NOT NULL")
            elif col == "no_of_weeks":
                sql_cols.append(f"`{col}` FLOAT")
            else:
                sql_cols.append(f"`{col}` TEXT")
        
        # Standard status tracking columns
        sql_cols.extend([
            "is_complete BOOLEAN DEFAULT 0",
            "certificate_generated BOOLEAN DEFAULT 0",
            "email_sent BOOLEAN DEFAULT 0",
            "generated_at TEXT",
            "last_updated DATETIME DEFAULT CURRENT_TIMESTAMP"
        ])
        
        create_query = f"CREATE TABLE IF NOT EXISTS students ({', '.join(sql_cols)})"
        
        cursor.execute(create_query)
        
        # Log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type VARCHAR(50),
                student_id VARCHAR(50),
                details TEXT
            )
        ''')
        
        # Check for missing columns (Migration/Schema Update logic)
        dict_cursor = self.get_cursor(conn)
        dict_cursor.execute("SHOW COLUMNS FROM students")
        existing_cols = [row['Field'] for row in dict_cursor.fetchall()]
        
        for col in cols:
            if col not in existing_cols:
                print(f"➕ Adding new configured column: {col}")
                if col == "no_of_weeks":
                    cursor.execute(f"ALTER TABLE students ADD COLUMN {col} REAL")
                else:
                    cursor.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")
        
        conn.commit()
        conn.close()
        print(f"Database initialized successfully for {self.db_config['database']}")

    def migrate_from_excel(self):
        """Import data from Excel into the dynamic MySQL database."""
        if not self.excel_path.exists():
            print(f"Excel file not found: {self.excel_path}")
            return False
            
        print(f"Syncing Excel data to MySQL Database...")
        
        try:
            df = pd.read_excel(self.excel_path)
            
            # Basic cleanup
            if 'student_id' not in df.columns:
                print("❌ Fatal: Master dataset missing 'student_id' column")
                return False
                
            df['student_id'] = df['student_id'].astype(str)
            df = df.where(pd.notnull(df), None)
            
            conn = self.get_connection()
            db_cols = self._get_dynamic_columns()
            
            for _, row in df.iterrows():
                student_info = row.to_dict()
                student_id = str(student_info.get('student_id'))
                
                # Only include columns that are actually in our config/schema
                filtered_info = {k: v for k, v in student_info.items() if k in db_cols}
                
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM students WHERE student_id = %s", (student_id,))
                check = cursor.fetchone()
                
                cols = list(filtered_info.keys())
                vals = [filtered_info[k] for k in cols]
                
                if not check:
                    placeholders = ", ".join(["%s"] * len(cols))
                    col_names = ", ".join([f"`{c}`" for c in cols])
                    query = f"INSERT INTO students ({col_names}) VALUES ({placeholders})"
                    cursor.execute(query, vals)
                else:
                    update_str = ", ".join([f"`{col}` = %s" for col in cols])
                    query = f"UPDATE students SET {update_str}, last_updated = CURRENT_TIMESTAMP WHERE student_id = %s"
                    cursor.execute(query, vals + [student_id])
            
            conn.commit()
            conn.close()
            print("Secure sync successful!")
            return True
            
        except Exception as e:
            print(f"Sync failed: {e}")
            return False

    def get_student(self, student_id):
        conn = self.get_connection()
        cursor = self.get_cursor(conn)
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (str(student_id),))
        row = cursor.fetchone()
        conn.close()
        return row if row else None

    def update_student(self, student_id, data):
        """
        Called when a student hits "Submit" on the web form. 
        It updates the student's record in the MySQL database.
        """
        conn = self.get_connection()
        db_cols = self._get_dynamic_columns()
        
        updates = []
        params = []
        for key, value in data.items():
            if key in db_cols or key in ['is_complete', 'certificate_generated', 'email_sent']:
                updates.append(f"`{key}` = %s")
                params.append(value)
        
        if updates:
            query = f"UPDATE students SET {', '.join(updates)}, last_updated = CURRENT_TIMESTAMP WHERE student_id = %s"
            params.append(str(student_id))
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            
        conn.close()
        return True

    def get_all_students(self):
        conn = self.get_connection()
        cursor = self.get_cursor(conn)
        cursor.execute("SELECT * FROM students ORDER BY last_updated DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

if __name__ == "__main__":
    manager = DatabaseManager()
    manager.initialize_db()
    manager.migrate_from_excel()
