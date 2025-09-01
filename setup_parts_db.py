#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3

# Connect to database
conn = sqlite3.connect('instance/maintenance.db')
cursor = conn.cursor()

print("Setting up parts management tables...")

# Create parts table
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
    print("✓ Parts table created/verified")
except Exception as e:
    print(f"Error creating parts table: {e}")

# Create parts_transactions table
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
    print("✓ Parts transactions table created/verified")
except Exception as e:
    print(f"Error creating parts_transactions table: {e}")

# Create maintenance_parts_used table
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
    print("✓ Maintenance parts used table created/verified")
except Exception as e:
    print(f"Error creating maintenance_parts_used table: {e}")

# Add sample parts data
sample_parts = [
    ('FILTER001', 'กรองอากาศ', 'กรองอากาศสำหรับเครื่องปรับอากาศ', 'ระบบปรับอากาศ', 'ABC Filter Co.', 150.00, 5, 20, 'ชั้น A1', 'บริษัท ฟิลเตอร์ จำกัด', '02-123-4567', 'เปลี่ยนทุก 3 เดือน'),
    ('BELT002', 'สายพาน V-Belt', 'สายพานสำหรับเครื่องจักร', 'เครื่องจักร', 'Gates Corporation', 350.00, 3, 15, 'ชั้น B2', 'บริษัท เกตส์ ไทย', '02-234-5678', 'ตรวจสอบความตึงเป็นประจำ'),
    ('OIL003', 'น้ำมันหล่อลื่น', 'น้ำมันหล่อลื่นเกรดอุตสาหกรรม', 'น้ำมันหล่อลื่น', 'Shell', 450.00, 10, 25, 'คลัง C', 'บริษัท เชลล์', '02-345-6789', 'เก็บในที่แห้ง'),
    ('BEARING004', 'ลูกปืน', 'ลูกปืนขนาด 6203', 'เครื่องจักร', 'SKF', 280.00, 8, 12, 'ชั้น A3', 'บริษัท เอสเคเอฟ', '02-456-7890', 'ใช้จาระบีคุณภาพดี'),
    ('SCREW005', 'สกรูสแตนเลส', 'สกรูสแตนเลส M6x20', 'ฮาร์ดแวร์', 'Local Supplier', 15.00, 50, 200, 'ชั้น D1', 'ร้านเหล็ก ABC', '02-567-8901', 'สต็อกจำนวนมาก'),
]

print("Adding sample parts...")
for part_data in sample_parts:
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO parts 
            (part_number, part_name, description, category, manufacturer, unit_price, 
             minimum_stock, current_stock, location, supplier, supplier_contact, notes, created_by) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, part_data)
        print(f"✓ Added: {part_data[1]}")
    except Exception as e:
        print(f"Error adding {part_data[1]}: {e}")

conn.commit()

# Show summary
cursor.execute("SELECT COUNT(*) FROM parts")
parts_count = cursor.fetchone()[0]
print(f"\n✅ Setup completed! Total parts in database: {parts_count}")

conn.close()
