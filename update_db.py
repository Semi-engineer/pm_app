# update_db.py
import sqlite3

DATABASE = 'instance/maintenance.db' # ตรวจสอบให้แน่ใจว่า path ถูกต้อง
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

try:
    # เพิ่มคอลัมน์สำหรับเก็บวันที่ PM ครั้งถัดไป (เก็บเป็น TEXT รูปแบบ YYYY-MM-DD)
    cursor.execute("ALTER TABLE assets ADD COLUMN next_pm_date TEXT")
    print("Column 'next_pm_date' added successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not add column 'next_pm_date': {e}")

try:
    # เพิ่มคอลัมน์สำหรับเก็บความถี่ในการทำ PM (เป็นจำนวนวัน)
    cursor.execute("ALTER TABLE assets ADD COLUMN pm_frequency_days INTEGER")
    print("Column 'pm_frequency_days' added successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not add column 'pm_frequency_days': {e}")

# เพิ่มตารางใหม่สำหรับจุดบำรุงรักษา
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            point_name TEXT NOT NULL,
            description TEXT,
            maintenance_procedure TEXT,
            frequency_days INTEGER,
            last_checked_date DATE,
            next_check_date DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (asset_id) REFERENCES assets (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)
    print("Table 'maintenance_points' created successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not create table 'maintenance_points': {e}")

# เพิ่มตารางใหม่สำหรับรูปภาพจุดบำรุงรักษา
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_point_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maintenance_point_id INTEGER NOT NULL,
            image_filename TEXT NOT NULL,
            image_description TEXT,
            image_type TEXT DEFAULT 'reference',
            upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            FOREIGN KEY (maintenance_point_id) REFERENCES maintenance_points (id),
            FOREIGN KEY (uploaded_by) REFERENCES users (id)
        )
    """)
    print("Table 'maintenance_point_images' created successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not create table 'maintenance_point_images': {e}")

# เพิ่มตารางใหม่สำหรับการจัดการอะไหล่
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT UNIQUE NOT NULL,
            part_name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            manufacturer TEXT,
            unit_price REAL DEFAULT 0,
            minimum_stock INTEGER DEFAULT 0,
            current_stock INTEGER DEFAULT 0,
            location TEXT,
            supplier TEXT,
            supplier_contact TEXT,
            notes TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)
    print("Table 'parts' created successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not create table 'parts': {e}")

# เพิ่มตารางสำหรับประวัติการเคลื่อนไหวของอะไหล่
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parts_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reference_type TEXT,
            reference_id INTEGER,
            unit_cost REAL,
            notes TEXT,
            transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (part_id) REFERENCES parts (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)
    print("Table 'parts_transactions' created successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not create table 'parts_transactions': {e}")

# เพิ่มตารางสำหรับเชื่อมโยงอะไหล่กับงานซ่อมบำรุง
try:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_parts_used (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maintenance_history_id INTEGER NOT NULL,
            part_id INTEGER NOT NULL,
            quantity_used INTEGER NOT NULL,
            unit_cost REAL,
            notes TEXT,
            FOREIGN KEY (maintenance_history_id) REFERENCES maintenance_history (id),
            FOREIGN KEY (part_id) REFERENCES parts (id)
        )
    """)
    print("Table 'maintenance_parts_used' created successfully.")
except sqlite3.OperationalError as e:
    print(f"Could not create table 'maintenance_parts_used': {e}")

conn.commit()
conn.close()