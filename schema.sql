-- ล้างตารางเก่าทิ้งถ้ามีอยู่ เพื่อป้องกันข้อผิดพลาด
DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS maintenance_history;
DROP TABLE IF EXISTS users;

-- สร้างตารางสำหรับผู้ใช้งาน พร้อมคอลัมน์ role
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL DEFAULT 'technician'
);

-- สร้างตารางสำหรับสินทรัพย์ พร้อมคอลัมน์สำหรับ PM และผู้รับผิดชอบ
CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    custom_data TEXT NOT NULL DEFAULT '{}',
    next_pm_date TEXT,
    pm_frequency_days INTEGER,
    technician_id INTEGER,
    asset_image_filename TEXT,
    FOREIGN KEY(technician_id) REFERENCES users(id)
);

-- สร้างตารางสำหรับประวัติการซ่อมบำรุง
CREATE TABLE maintenance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,
    cost REAL,
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);

-- สร้างตารางสำหรับจุดที่ต้องบำรุงรักษา (Maintenance Points)
CREATE TABLE maintenance_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    point_name TEXT NOT NULL,
    description TEXT,
    maintenance_procedure TEXT,
    frequency_days INTEGER,
    last_checked_date DATE,
    next_check_date DATE,
    status TEXT DEFAULT 'active', -- active, inactive, completed
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (asset_id) REFERENCES assets (id),
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- สร้างตารางสำหรับเก็บรูปภาพของจุดบำรุงรักษา
CREATE TABLE maintenance_point_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maintenance_point_id INTEGER NOT NULL,
    image_filename TEXT NOT NULL,
    image_description TEXT,
    image_type TEXT DEFAULT 'reference', -- reference, before, after, issue
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER,
    FOREIGN KEY (maintenance_point_id) REFERENCES maintenance_points (id),
    FOREIGN KEY (uploaded_by) REFERENCES users (id)
);

-- สร้างตารางสำหรับการจัดการอะไหล่ (Parts Stock)
CREATE TABLE parts (
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
);

-- สร้างตารางสำหรับประวัติการเคลื่อนไหวของอะไหล่
CREATE TABLE parts_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL, -- 'in', 'out', 'adjustment'
    quantity INTEGER NOT NULL,
    reference_type TEXT, -- 'maintenance', 'purchase', 'adjustment', 'return'
    reference_id INTEGER, -- ID ของ maintenance_history หรือ purchase order
    unit_cost REAL,
    notes TEXT,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (part_id) REFERENCES parts (id),
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- สร้างตารางสำหรับเชื่อมโยงอะไหล่กับงานซ่อมบำรุง
CREATE TABLE maintenance_parts_used (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    maintenance_history_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity_used INTEGER NOT NULL,
    unit_cost REAL,
    notes TEXT,
    FOREIGN KEY (maintenance_history_id) REFERENCES maintenance_history (id),
    FOREIGN KEY (part_id) REFERENCES parts (id)
);