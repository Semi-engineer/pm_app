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

-- สร้างตารางสำหรับจุดรายละเอียดการบำรุงรักษา
CREATE TABLE maintenance_detail_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location_detail TEXT,
    image_filename TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);