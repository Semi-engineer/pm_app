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

conn.commit()
conn.close()