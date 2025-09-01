import sqlite3
import json
import os
import sys 
import functools
import click
import io
import csv
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, g, flash, jsonify, session, Response, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import date, timedelta, datetime
from collections import Counter

# --- App Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-super-secret-key-that-you-should-change')

# Configuration for File Uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = os.path.join(app.instance_path, 'maintenance.db')

# --- Initial Setup ---
try:
    os.makedirs(app.instance_path)
    os.makedirs(app.config['UPLOAD_FOLDER'])
except OSError:
    pass

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# vvv --- ฟังก์ชันผู้ช่วยใหม่ที่สร้างขึ้นเพื่อลดโค้ดซ้ำซ้อน --- vvv
def _process_asset_form(request, existing_filename=None):
    """
    ประมวลผลข้อมูลจากฟอร์มสำหรับ 'add' และ 'edit' asset
    - ดึงข้อมูลจากฟอร์ม
    - จัดการไฟล์อัปโหลด
    - คืนค่าเป็น Dictionary ที่พร้อมสำหรับบันทึกลง DB
    """
    # 1. ดึงข้อมูลจากฟอร์ม
    form_data = {
        'name': request.form['name'],
        'location': request.form['location'],
        'next_pm_date': request.form.get('next_pm_date') or None,
        'pm_frequency_days': request.form.get('pm_frequency_days') or None,
        'technician_id': request.form.get('technician_id') or None,
        'custom_data': json.dumps({
            k: v for k, v in zip(request.form.getlist('custom_key'), request.form.getlist('custom_value')) if k
        })
    }

    # 2. จัดการไฟล์อัปโหลด
    image_filename = existing_filename # ใช้ไฟล์เดิมเป็นค่าเริ่มต้น
    if 'asset_image' in request.files:
        file = request.files['asset_image']
        # ถ้ามีการอัปโหลดไฟล์ใหม่ ให้บันทึกและอัปเดตชื่อไฟล์
        if file and file.filename != '' and allowed_file(file.filename):
            image_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            
    form_data['asset_image_filename'] = image_filename
    
    return form_data

def get_maintenance_points_for_asset(asset_id):
    """ดึงข้อมูลจุดบำรุงรักษาทั้งหมดของสินทรัพย์"""
    db = get_db()
    return db.execute("""
        SELECT mp.*, u.username as created_by_name 
        FROM maintenance_points mp 
        LEFT JOIN users u ON mp.created_by = u.id 
        WHERE mp.asset_id = ? 
        ORDER BY mp.created_at DESC
    """, (asset_id,)).fetchall()

def get_maintenance_point_images(maintenance_point_id):
    """ดึงรูปภาพทั้งหมดของจุดบำรุงรักษา"""
    db = get_db()
    return db.execute("""
        SELECT mpi.*, u.username as uploaded_by_name 
        FROM maintenance_point_images mpi 
        LEFT JOIN users u ON mpi.uploaded_by = u.id 
        WHERE mpi.maintenance_point_id = ? 
        ORDER BY mpi.upload_date DESC
    """, (maintenance_point_id,)).fetchall()

def save_maintenance_point_image(file, maintenance_point_id, description='', image_type='reference'):
    """บันทึกรูปภาพของจุดบำรุงรักษา"""
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(f"mp_{maintenance_point_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        db = get_db()
        db.execute("""
            INSERT INTO maintenance_point_images 
            (maintenance_point_id, image_filename, image_description, image_type, uploaded_by) 
            VALUES (?, ?, ?, ?, ?)
        """, (maintenance_point_id, filename, description, image_type, session.get('user_id')))
        db.commit()
        return filename
    return None

# --- Parts Management Helper Functions ---
def get_all_parts():
    """ดึงข้อมูลอะไหล่ทั้งหมด"""
    db = get_db()
    return db.execute("""
        SELECT p.*, u.username as created_by_name 
        FROM parts p 
        LEFT JOIN users u ON p.created_by = u.id 
        ORDER BY p.part_name ASC
    """).fetchall()

def get_parts_low_stock():
    """ดึงอะไหล่ที่มีสต็อกต่ำ"""
    db = get_db()
    return db.execute("""
        SELECT * FROM parts 
        WHERE current_stock <= minimum_stock 
        ORDER BY (current_stock - minimum_stock) ASC
    """).fetchall()

def get_part_by_id(part_id):
    """ดึงข้อมูลอะไหล่ตาม ID"""
    db = get_db()
    return db.execute("SELECT * FROM parts WHERE id = ?", (part_id,)).fetchone()

def get_part_transactions(part_id):
    """ดึงประวัติการเคลื่อนไหวของอะไหล่"""
    db = get_db()
    return db.execute("""
        SELECT pt.*, u.username as created_by_name 
        FROM parts_transactions pt 
        LEFT JOIN users u ON pt.created_by = u.id 
        WHERE pt.part_id = ? 
        ORDER BY pt.transaction_date DESC
    """, (part_id,)).fetchall()

def add_part_transaction(part_id, transaction_type, quantity, reference_type=None, reference_id=None, unit_cost=None, notes=''):
    """เพิ่มการเคลื่อนไหวของอะไหล่และอัปเดตสต็อก"""
    db = get_db()
    
    # เพิ่มรายการเคลื่อนไหว
    db.execute("""
        INSERT INTO parts_transactions 
        (part_id, transaction_type, quantity, reference_type, reference_id, unit_cost, notes, created_by) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (part_id, transaction_type, quantity, reference_type, reference_id, unit_cost, notes, session.get('user_id')))
    
    # อัปเดตสต็อกปัจจุบัน
    if transaction_type == 'in':
        db.execute("UPDATE parts SET current_stock = current_stock + ? WHERE id = ?", (quantity, part_id))
    elif transaction_type == 'out':
        db.execute("UPDATE parts SET current_stock = current_stock - ? WHERE id = ?", (quantity, part_id))
    elif transaction_type == 'adjustment':
        db.execute("UPDATE parts SET current_stock = ? WHERE id = ?", (quantity, part_id))
    
    # อัปเดตเวลาแก้ไข
    db.execute("UPDATE parts SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (part_id,))
    db.commit()

def get_parts_for_maintenance(maintenance_id):
    """ดึงอะไหล่ที่ใช้ในงานซ่อมบำรุง"""
    db = get_db()
    return db.execute("""
        SELECT mpu.*, p.part_number, p.part_name 
        FROM maintenance_parts_used mpu 
        JOIN parts p ON mpu.part_id = p.id 
        WHERE mpu.maintenance_history_id = ?
    """, (maintenance_id,)).fetchall()
# ^^^ --- จบส่วนของฟังก์ชันผู้ช่วย --- ^^^


# --- Database Connection ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def init_database():
    """Checks if the database exists, and if not, creates it and the tables."""
    
    # --- สร้าง Path ไปยังโฟลเดอร์ instance ---
    # ส่วนนี้จะซับซ้อนขึ้นเพื่อรองรับการทำงานใน .exe
    if getattr(sys, 'frozen', False):
        # ถ้ากำลังรันใน .exe ให้ใช้ path ของ .exe
        application_path = os.path.dirname(sys.executable)
    else:
        # ถ้ารันเป็นสคริปต์ปกติ ให้ใช้ path ของไฟล์ .py
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    instance_path = os.path.join(application_path, 'instance')
    db_path = os.path.join(instance_path, 'maintenance.db')

    # --- ตรวจสอบและสร้างฐานข้อมูล ---
    if not os.path.exists(db_path):
        print("Database not found. Creating a new one...")
        try:
            os.makedirs(instance_path, exist_ok=True)
            
            # --- สร้าง Path ไปยัง schema.sql ที่ถูกต้อง ---
            # ใช้หลักการเดียวกับข้างบนเพื่อหา schema.sql
            schema_path = os.path.join(application_path, 'schema.sql')

            db = sqlite3.connect(db_path)
            with open(schema_path, mode='r', encoding='utf-8') as f:
                db.cursor().executescript(f.read())
            db.commit()
            db.close()
            print(f"Database created successfully at {db_path}")
        except Exception as e:
            print(f"An error occurred while creating the database: {e}")

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- CLI Commands (No Changes) ---
@app.cli.command('init-db')
def init_db_command():
    db = sqlite3.connect(DATABASE)
    with app.open_resource('schema.sql', mode='r', encoding='utf-8') as f:
        db.cursor().executescript(f.read())
    
    # Add sample parts data if parts table is empty
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM parts")
    if cursor.fetchone()[0] == 0:
        sample_parts = [
            ('FILTER001', 'กรองอากาศ', 'กรองอากาศสำหรับเครื่องปรับอากาศ', 'ระบบปรับอากาศ', 'ABC Filter Co.', 150.00, 5, 20, 'ชั้น A1', 'บริษัท ฟิลเตอร์ จำกัด', '02-123-4567', 'เปลี่ยนทุก 3 เดือน'),
            ('BELT002', 'สายพาน V-Belt', 'สายพานสำหรับเครื่องจักร', 'เครื่องจักร', 'Gates Corporation', 350.00, 3, 15, 'ชั้น B2', 'บริษัท เกตส์ ไทย', '02-234-5678', 'ตรวจสอบความตึงเป็นประจำ'),
            ('OIL003', 'น้ำมันหล่อลื่น', 'น้ำมันหล่อลื่นเกรดอุตสาหกรรม', 'น้ำมันหล่อลื่น', 'Shell', 450.00, 10, 25, 'คลัง C', 'บริษัท เชลล์', '02-345-6789', 'เก็บในที่แห้ง'),
            ('BEARING004', 'ลูกปืน', 'ลูกปืนขนาด 6203', 'เครื่องจักร', 'SKF', 280.00, 8, 12, 'ชั้น A3', 'บริษัท เอสเคเอฟ', '02-456-7890', 'ใช้จาระบีคุณภาพดี'),
            ('SCREW005', 'สกรูสแตนเลส', 'สกรูสแตนเลส M6x20', 'ฮาร์ดแวร์', 'Local Supplier', 15.00, 50, 200, 'ชั้น D1', 'ร้านเหล็ก ABC', '02-567-8901', 'สต็อกจำนวนมาก'),
        ]
        
        for part_data in sample_parts:
            cursor.execute("""
                INSERT INTO parts 
                (part_number, part_name, description, category, manufacturer, unit_price, 
                 minimum_stock, current_stock, location, supplier, supplier_contact, notes, created_by) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, part_data)
        
        print('Sample parts data added successfully!')
    
    db.commit()
    db.close()
    print('Initialized the database.')


@app.cli.command('create-admin')
@click.argument('username')
@click.argument('password')
def create_admin_command(username, password):
    db = sqlite3.connect(DATABASE)
    try:
        db.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')", (username, generate_password_hash(password)))
        db.commit()
        print(f"Admin user '{username}' created successfully.")
    except db.IntegrityError:
        print(f"Error: User '{username}' already exists.")
    finally:
        db.close()

# --- Decorators and Helpers (No Changes) ---
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('user_id') is None: return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get('role') != 'admin':
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

def get_all_technicians():
    db = get_db()
    technicians = db.execute("SELECT id, username FROM users WHERE role = 'technician' ORDER BY username").fetchall()
    return technicians

# --- File Upload Serving Route (NEW) ---
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Provides access to uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Parts Management Routes ---
@app.route('/parts')
@login_required
def parts_index():
    """หน้าแสดงรายการอะไหล่ทั้งหมด"""
    search_query = request.args.get('q', '')
    category_filter = request.args.get('category', '')
    
    db = get_db()
    base_sql = """
        SELECT p.*, u.username as created_by_name 
        FROM parts p 
        LEFT JOIN users u ON p.created_by = u.id 
        WHERE 1=1
    """
    params = []
    
    if search_query:
        search_term = f"%{search_query}%"
        base_sql += " AND (p.part_number LIKE ? OR p.part_name LIKE ? OR p.description LIKE ?)"
        params.extend([search_term, search_term, search_term])
    
    if category_filter:
        base_sql += " AND p.category = ?"
        params.append(category_filter)
    
    base_sql += " ORDER BY p.part_name ASC"
    
    parts = db.execute(base_sql, params).fetchall()
    low_stock_parts = get_parts_low_stock()
    
    # ดึงหมวดหมู่ทั้งหมดสำหรับ filter
    categories = db.execute("SELECT DISTINCT category FROM parts WHERE category IS NOT NULL ORDER BY category").fetchall()
    
    return render_template('parts/index.html', 
                         parts=parts, 
                         low_stock_parts=low_stock_parts,
                         categories=categories,
                         search_query=search_query,
                         category_filter=category_filter)

@app.route('/parts/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_part():
    """เพิ่มอะไหล่ใหม่"""
    if request.method == 'POST':
        part_number = request.form['part_number']
        part_name = request.form['part_name']
        description = request.form.get('description', '')
        category = request.form.get('category', '')
        manufacturer = request.form.get('manufacturer', '')
        unit_price = float(request.form.get('unit_price', 0))
        minimum_stock = int(request.form.get('minimum_stock', 0))
        current_stock = int(request.form.get('current_stock', 0))
        location = request.form.get('location', '')
        supplier = request.form.get('supplier', '')
        supplier_contact = request.form.get('supplier_contact', '')
        notes = request.form.get('notes', '')
        
        db = get_db()
        try:
            cursor = db.execute("""
                INSERT INTO parts 
                (part_number, part_name, description, category, manufacturer, 
                 unit_price, minimum_stock, current_stock, location, supplier, 
                 supplier_contact, notes, created_by) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (part_number, part_name, description, category, manufacturer,
                  unit_price, minimum_stock, current_stock, location, supplier,
                  supplier_contact, notes, session['user_id']))
            
            part_id = cursor.lastrowid
            
            # เพิ่มรายการเริ่มต้นหากมีสต็อกเริ่มต้น
            if current_stock > 0:
                add_part_transaction(part_id, 'in', current_stock, 'initial', None, unit_price, 'สต็อกเริ่มต้น')
            
            db.commit()
            flash(f'เพิ่มอะไหล่ "{part_name}" เรียบร้อยแล้ว', 'success')
            return redirect(url_for('parts_index'))
            
        except sqlite3.IntegrityError:
            flash('รหัสอะไหล่นี้มีอยู่ในระบบแล้ว', 'error')
    
    return render_template('parts/add.html')

@app.route('/parts/<int:part_id>')
@login_required
def part_detail(part_id):
    """หน้ารายละเอียดอะไหล่"""
    part = get_part_by_id(part_id)
    if not part:
        flash('ไม่พบอะไหล่ที่ต้องการ', 'error')
        return redirect(url_for('parts_index'))
    
    transactions = get_part_transactions(part_id)
    return render_template('parts/detail.html', part=part, transactions=transactions)

@app.route('/parts/<int:part_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_part(part_id):
    """แก้ไขข้อมูลอะไหล่"""
    part = get_part_by_id(part_id)
    if not part:
        flash('ไม่พบอะไหล่ที่ต้องการ', 'error')
        return redirect(url_for('parts_index'))
    
    if request.method == 'POST':
        part_number = request.form['part_number']
        part_name = request.form['part_name']
        description = request.form.get('description', '')
        category = request.form.get('category', '')
        manufacturer = request.form.get('manufacturer', '')
        unit_price = float(request.form.get('unit_price', 0))
        minimum_stock = int(request.form.get('minimum_stock', 0))
        location = request.form.get('location', '')
        supplier = request.form.get('supplier', '')
        supplier_contact = request.form.get('supplier_contact', '')
        notes = request.form.get('notes', '')
        
        db = get_db()
        try:
            db.execute("""
                UPDATE parts SET 
                part_number = ?, part_name = ?, description = ?, category = ?, 
                manufacturer = ?, unit_price = ?, minimum_stock = ?, location = ?, 
                supplier = ?, supplier_contact = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (part_number, part_name, description, category, manufacturer,
                  unit_price, minimum_stock, location, supplier, supplier_contact,
                  notes, part_id))
            db.commit()
            flash(f'อัปเดตข้อมูลอะไหล่ "{part_name}" เรียบร้อยแล้ว', 'success')
            return redirect(url_for('part_detail', part_id=part_id))
            
        except sqlite3.IntegrityError:
            flash('รหัสอะไหล่นี้มีอยู่ในระบบแล้ว', 'error')
    
    return render_template('parts/edit.html', part=part)

@app.route('/parts/<int:part_id>/stock', methods=['POST'])
@login_required
@admin_required
def adjust_stock(part_id):
    """ปรับปรุงสต็อกอะไหล่"""
    part = get_part_by_id(part_id)
    if not part:
        flash('ไม่พบอะไหล่ที่ต้องการ', 'error')
        return redirect(url_for('parts_index'))
    
    transaction_type = request.form['transaction_type']
    quantity = int(request.form['quantity'])
    unit_cost = float(request.form.get('unit_cost', 0)) if request.form.get('unit_cost') else None
    notes = request.form.get('notes', '')
    
    if transaction_type == 'adjustment':
        # สำหรับการปรับปรุงสต็อก quantity คือจำนวนใหม่
        add_part_transaction(part_id, transaction_type, quantity, 'manual', None, unit_cost, notes)
    else:
        # สำหรับการเข้า/ออก quantity คือจำนวนที่เปลี่ยนแปลง
        add_part_transaction(part_id, transaction_type, quantity, 'manual', None, unit_cost, notes)
    
    flash('อัปเดตสต็อกเรียบร้อยแล้ว', 'success')
    return redirect(url_for('part_detail', part_id=part_id))

@app.route('/parts/<int:part_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_part(part_id):
    """ลบอะไหล่"""
    part = get_part_by_id(part_id)
    if not part:
        flash('ไม่พบอะไหล่ที่ต้องการ', 'error')
        return redirect(url_for('parts_index'))
    
    db = get_db()
    # ตรวจสอบว่าอะไหล่นี้ถูกใช้ในงานซ่อมบำรุงหรือไม่
    used_count = db.execute("SELECT COUNT(*) as count FROM maintenance_parts_used WHERE part_id = ?", (part_id,)).fetchone()['count']
    
    if used_count > 0:
        flash('ไม่สามารถลบอะไหล่นี้ได้ เนื่องจากมีการใช้งานในระบบแล้ว', 'error')
        return redirect(url_for('part_detail', part_id=part_id))
    
    # ลบข้อมูลการเคลื่อนไหวและอะไหล่
    db.execute("DELETE FROM parts_transactions WHERE part_id = ?", (part_id,))
    db.execute("DELETE FROM parts WHERE id = ?", (part_id,))
    db.commit()
    
    flash(f'ลบอะไหล่ "{part["part_name"]}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('parts_index'))

# --- Authentication Routes (No Changes) ---
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        db = get_db()
        error = None
        if not username: error = 'Username is required.'
        elif not password: error = 'Password is required.'
        elif db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"User {username} is already registered."
        if error is None:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, generate_password_hash(password)))
            db.commit()
            flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))
        flash(error, 'error')
    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
        else:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('คุณได้ออกจากระบบแล้ว', 'success')
    return redirect(url_for('login'))

# --- Main Application Routes ---
@app.route('/')
@login_required
def index():
    db = get_db()
    search_query = request.args.get('q', '')
    base_sql = "SELECT * FROM assets"
    params = []
    if search_query:
        search_term = f"%{search_query}%"
        base_sql += " WHERE name LIKE ? OR location LIKE ? OR custom_data LIKE ?"
        params.extend([search_term, search_term, search_term])
    base_sql += " ORDER BY id DESC"
    assets = db.execute(base_sql, params).fetchall()
    pm_due_assets = db.execute('SELECT * FROM assets WHERE next_pm_date IS NOT NULL AND next_pm_date != "" AND date(next_pm_date) <= date("now", "+7 days") ORDER BY next_pm_date ASC').fetchall()
    technicians = get_all_technicians()
    return render_template('index.html', assets=assets, pm_due_assets=pm_due_assets, technicians=technicians, search_query=search_query)

# vvv --- แก้ไขฟังก์ชัน add_asset ให้เรียกใช้ฟังก์ชันผู้ช่วย --- vvv
@app.route('/add_asset', methods=['POST'])
@login_required
@admin_required
def add_asset():
    # เรียกใช้ฟังก์ชันผู้ช่วยเพื่อประมวลผลข้อมูลจากฟอร์ม
    asset_data = _process_asset_form(request)
    
    # --- Database Insert ---
    db = get_db()
    db.execute(
        'INSERT INTO assets (name, location, custom_data, next_pm_date, pm_frequency_days, technician_id, asset_image_filename) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (asset_data['name'], asset_data['location'], asset_data['custom_data'], 
         asset_data['next_pm_date'], asset_data['pm_frequency_days'], 
         asset_data['technician_id'], asset_data['asset_image_filename'])
    )
    db.commit()
    flash(f'สินทรัพย์ "{asset_data["name"]}" ถูกเพิ่มเข้าระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))
# ^^^ --- จบการแก้ไข add_asset --- ^^^


# vvv --- แก้ไขฟังก์ชัน edit_asset ให้เรียกใช้ฟังก์ชันผู้ช่วย --- vvv
@app.route('/edit_asset/<int:asset_id>', methods=('GET', 'POST'))
@login_required
@admin_required
def edit_asset(asset_id):
    db = get_db()
    asset_row = db.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()

    if request.method == 'POST':
        # ส่งชื่อไฟล์รูปปัจจุบันเข้าไปในฟังก์ชันผู้ช่วย
        current_image = asset_row['asset_image_filename'] if asset_row else None
        asset_data = _process_asset_form(request, existing_filename=current_image)
        
        # --- Database Update ---
        db.execute(
            'UPDATE assets SET name = ?, location = ?, custom_data = ?, next_pm_date = ?, pm_frequency_days = ?, technician_id = ?, asset_image_filename = ? WHERE id = ?',
            (asset_data['name'], asset_data['location'], asset_data['custom_data'], 
             asset_data['next_pm_date'], asset_data['pm_frequency_days'], 
             asset_data['technician_id'], asset_data['asset_image_filename'], 
             asset_id)
        )
        db.commit()
        flash(f'ข้อมูลสินทรัพย์ "{asset_data["name"]}" ถูกอัปเดตเรียบร้อยแล้ว', 'success')
        return redirect(url_for('asset_detail', asset_id=asset_id))
    
    # ส่วนของ GET request ไม่มีการเปลี่ยนแปลง
    asset = dict(asset_row)
    asset['custom_data'] = json.loads(asset['custom_data'])
    technicians = get_all_technicians()
    return render_template('edit_asset.html', asset=asset, technicians=technicians)
# ^^^ --- จบการแก้ไข edit_asset --- ^^^

# ... (my-tasks route is unchanged) ...
@app.route('/my-tasks')
@login_required
def my_tasks():
    db = get_db()
    tasks = db.execute("""
        SELECT id, name, location, next_pm_date 
        FROM assets WHERE technician_id = ? AND next_pm_date IS NOT NULL AND next_pm_date != '' AND date(next_pm_date) <= date('now', '+7 days')
        ORDER BY next_pm_date ASC
    """, (session['user_id'],)).fetchall()
    return render_template('my_tasks.html', tasks=tasks)


@app.route('/asset/<int:asset_id>')
@login_required
def asset_detail(asset_id):
    db = get_db()
    asset_row = db.execute('SELECT a.*, u.username as technician_name FROM assets a LEFT JOIN users u ON a.technician_id = u.id WHERE a.id = ?', (asset_id,)).fetchone()
    if not asset_row: return "Asset not found", 404
    asset = dict(asset_row)
    asset['custom_data'] = json.loads(asset['custom_data'])
    is_pm_due = bool(asset.get('next_pm_date') and asset['next_pm_date'] != '' and date.fromisoformat(asset['next_pm_date']) <= date.today())
    history = db.execute('SELECT * FROM maintenance_history WHERE asset_id = ? ORDER BY date DESC', (asset_id,)).fetchall()
    
    # ดึงข้อมูลจุดบำรุงรักษา
    maintenance_points = get_maintenance_points_for_asset(asset_id)
    
    # ดึงรูปภาพสำหรับแต่ละจุดบำรุงรักษา
    for point in maintenance_points:
        point_dict = dict(point)
        point_dict['images'] = get_maintenance_point_images(point['id'])
        maintenance_points[maintenance_points.index(point)] = point_dict
    
    return render_template('asset_detail.html', asset=asset, history=history, is_pm_due=is_pm_due, maintenance_points=maintenance_points)

@app.route('/delete_asset/<int:asset_id>', methods=['POST'])
@login_required
@admin_required
def delete_asset(asset_id):
    db = get_db()
    asset = db.execute('SELECT name, asset_image_filename FROM assets WHERE id = ?', (asset_id,)).fetchone()
    if asset:
        asset_name = asset['name']
        # --- Delete associated image file ---
        if asset['asset_image_filename']:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], asset['asset_image_filename']))
            except OSError as e:
                print(f"Error deleting file {asset['asset_image_filename']}: {e}")
        
        db.execute('DELETE FROM maintenance_history WHERE asset_id = ?', (asset_id,))
        db.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
        db.commit()
        flash(f'สินทรัพย์ "{asset_name}" และข้อมูลที่เกี่ยวข้องถูกลบออกจากระบบเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่พบสินทรัพย์ที่ต้องการลบ', 'error')
    return redirect(url_for('index'))

# ... (perform_pm and add_maintenance routes are unchanged) ...
@app.route('/perform_pm/<int:asset_id>', methods=['POST'])
@login_required
def perform_pm(asset_id):
    db = get_db()
    asset = db.execute('SELECT pm_frequency_days FROM assets WHERE id = ?', (asset_id,)).fetchone()
    if asset and asset['pm_frequency_days']:
        frequency = int(asset['pm_frequency_days'])
        new_next_pm_date = date.today() + timedelta(days=frequency)
        db.execute('UPDATE assets SET next_pm_date = ? WHERE id = ?', (new_next_pm_date.isoformat(), asset_id))
        db.execute('INSERT INTO maintenance_history (asset_id, description, cost) VALUES (?, ?, ?)',(asset_id, f"ดำเนินการบำรุงรักษาเชิงป้องกัน (PM) ตามรอบ {frequency} วัน", 0))
        db.commit()
        flash('ดำเนินการ PM และอัปเดตกำหนดการครั้งถัดไปเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่สามารถดำเนินการได้: ไม่ได้ตั้งค่าความถี่ในการทำ PM', 'error')
    return redirect(url_for('asset_detail', asset_id=asset_id))

@app.route('/add_maintenance/<int:asset_id>', methods=['POST'])
@login_required
def add_maintenance(asset_id):
    description, cost_str = request.form['description'], request.form.get('cost')
    cost = float(cost_str) if cost_str else None
    db = get_db()
    db.execute('INSERT INTO maintenance_history (asset_id, description, cost) VALUES (?, ?, ?)', (asset_id, description, cost))
    db.commit()
    flash('เพิ่มประวัติการซ่อมบำรุงเรียบร้อยแล้ว', 'success')
    return redirect(url_for('asset_detail', asset_id=asset_id))

# --- Maintenance Points Routes ---
@app.route('/add_maintenance_point/<int:asset_id>', methods=['POST'])
@login_required
@admin_required
def add_maintenance_point(asset_id):
    print(f"DEBUG: add_maintenance_point called for asset_id={asset_id}")
    print(f"DEBUG: Form data: {dict(request.form)}")
    print(f"DEBUG: User session: {dict(session)}")
    
    point_name = request.form['point_name']
    description = request.form.get('description', '')
    maintenance_procedure = request.form.get('maintenance_procedure', '')
    frequency_days = request.form.get('frequency_days')
    frequency_days = int(frequency_days) if frequency_days else None
    
    db = get_db()
    cursor = db.execute("""
        INSERT INTO maintenance_points 
        (asset_id, point_name, description, maintenance_procedure, frequency_days, created_by) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (asset_id, point_name, description, maintenance_procedure, frequency_days, session['user_id']))
    
    maintenance_point_id = cursor.lastrowid
    
    # จัดการไฟล์รูปภาพที่อัปโหลด
    if 'point_images' in request.files:
        files = request.files.getlist('point_images')
        for file in files:
            if file and file.filename != '':
                save_maintenance_point_image(file, maintenance_point_id, 
                                           request.form.get('image_description', ''), 'reference')
    
    db.commit()
    flash(f'เพิ่มจุดบำรุงรักษา "{point_name}" เรียบร้อยแล้ว', 'success')
    return redirect(url_for('asset_detail', asset_id=asset_id))

@app.route('/edit_maintenance_point/<int:point_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_maintenance_point(point_id):
    db = get_db()
    point = db.execute('SELECT * FROM maintenance_points WHERE id = ?', (point_id,)).fetchone()
    
    if not point:
        flash('ไม่พบจุดบำรุงรักษาที่ต้องการแก้ไข', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        point_name = request.form['point_name']
        description = request.form.get('description', '')
        maintenance_procedure = request.form.get('maintenance_procedure', '')
        frequency_days = request.form.get('frequency_days')
        frequency_days = int(frequency_days) if frequency_days else None
        status = request.form.get('status', 'active')
        
        db.execute("""
            UPDATE maintenance_points 
            SET point_name = ?, description = ?, maintenance_procedure = ?, 
                frequency_days = ?, status = ?
            WHERE id = ?
        """, (point_name, description, maintenance_procedure, frequency_days, status, point_id))
        
        # จัดการไฟล์รูปภาพใหม่ที่อัปโหลด
        if 'point_images' in request.files:
            files = request.files.getlist('point_images')
            for file in files:
                if file and file.filename != '':
                    save_maintenance_point_image(file, point_id, 
                                               request.form.get('image_description', ''), 'reference')
        
        db.commit()
        flash(f'อัปเดตจุดบำรุงรักษา "{point_name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('asset_detail', asset_id=point['asset_id']))
    
    images = get_maintenance_point_images(point_id)
    return render_template('edit_maintenance_point.html', point=point, images=images)

@app.route('/delete_maintenance_point/<int:point_id>', methods=['POST'])
@login_required
@admin_required
def delete_maintenance_point(point_id):
    db = get_db()
    point = db.execute('SELECT * FROM maintenance_points WHERE id = ?', (point_id,)).fetchone()
    
    if point:
        # ลบรูปภาพที่เกี่ยวข้อง
        images = get_maintenance_point_images(point_id)
        for image in images:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image['image_filename']))
            except OSError as e:
                print(f"Error deleting image file {image['image_filename']}: {e}")
        
        # ลบข้อมูลจากฐานข้อมูล
        db.execute('DELETE FROM maintenance_point_images WHERE maintenance_point_id = ?', (point_id,))
        db.execute('DELETE FROM maintenance_points WHERE id = ?', (point_id,))
        db.commit()
        
        flash(f'ลบจุดบำรุงรักษา "{point["point_name"]}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('asset_detail', asset_id=point['asset_id']))
    else:
        flash('ไม่พบจุดบำรุงรักษาที่ต้องการลบ', 'error')
        return redirect(url_for('index'))

@app.route('/upload_point_image/<int:point_id>', methods=['POST'])
@login_required
def upload_point_image(point_id):
    if 'image' not in request.files:
        flash('ไม่พบไฟล์รูปภาพ', 'error')
        return redirect(request.referrer)
    
    file = request.files['image']
    description = request.form.get('description', '')
    image_type = request.form.get('image_type', 'reference')
    
    if save_maintenance_point_image(file, point_id, description, image_type):
        flash('อัปโหลดรูปภาพเรียบร้อยแล้ว', 'success')
    else:
        flash('เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ', 'error')
    
    return redirect(request.referrer)

@app.route('/delete_point_image/<int:image_id>', methods=['POST'])
@login_required
@admin_required
def delete_point_image(image_id):
    db = get_db()
    image = db.execute('SELECT * FROM maintenance_point_images WHERE id = ?', (image_id,)).fetchone()
    
    if image:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image['image_filename']))
        except OSError as e:
            print(f"Error deleting image file {image['image_filename']}: {e}")
        
        db.execute('DELETE FROM maintenance_point_images WHERE id = ?', (image_id,))
        db.commit()
        flash('ลบรูปภาพเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่พบรูปภาพที่ต้องการลบ', 'error')
    
    return redirect(request.referrer)

# --- Dashboard & API Routes (No Changes) ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/pm_events')
@login_required
def pm_events_api():
    db = get_db()
    assets_with_pm = db.execute("SELECT id, name, next_pm_date FROM assets WHERE next_pm_date IS NOT NULL AND next_pm_date != ''").fetchall()
    events = [{'title': asset['name'], 'start': asset['next_pm_date'], 'url': url_for('asset_detail', asset_id=asset['id'])} for asset in assets_with_pm]
    return jsonify(events)

@app.route('/reports')
@login_required
def reports():
    db = get_db()
    costs_by_month = db.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(cost) as total_cost
        FROM maintenance_history WHERE cost IS NOT NULL AND cost > 0
        GROUP BY month ORDER BY month;
    """).fetchall()
    cost_data = {
        'labels': [datetime.strptime(row['month'], '%Y-%m').strftime('%b %Y') for row in costs_by_month],
        'data': [row['total_cost'] or 0 for row in costs_by_month]
    }
    all_descriptions = db.execute("SELECT description FROM maintenance_history").fetchall()
    job_type_counts = Counter(
        'งาน PM' if 'PM' in row['description'] or 'บำรุงรักษาเชิงป้องกัน' in row['description'] 
        else 'งานซ่อมทั่วไป (CM)'
        for row in all_descriptions
    )
    job_type_data = {
        'labels': list(job_type_counts.keys()),
        'data': list(job_type_counts.values())
    }
    return render_template('reports.html', cost_data=cost_data, job_type_data=job_type_data)

@app.route('/export_asset_history/<int:asset_id>')
@login_required
def export_asset_history(asset_id):
    db = get_db()
    asset = db.execute('SELECT name FROM assets WHERE id = ?', (asset_id,)).fetchone()
    if not asset:
        flash('ไม่พบสินทรัพย์ที่ต้องการ', 'error')
        return redirect(url_for('index'))
    history = db.execute('SELECT date, description, cost FROM maintenance_history WHERE asset_id = ? ORDER BY date DESC', (asset_id,)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Description', 'Cost'])
    for item in history:
        writer.writerow([item['date'], item['description'], item['cost']])
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=history_{asset['name'].replace(' ', '_')}_{asset_id}.csv"}
    )

@app.route('/setup_db')
def setup_database():
    """Setup database route for development"""
    try:
        db = get_db()
        
        # Check if parts table exists and has data
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM parts")
        parts_count = cursor.fetchone()[0]
        
        if parts_count == 0:
            # Add sample parts data
            sample_parts = [
                ('FILTER001', 'กรองอากาศ', 'กรองอากาศสำหรับเครื่องปรับอากาศ', 'ระบบปรับอากาศ', 'ABC Filter Co.', 150.00, 5, 20, 'ชั้น A1', 'บริษัท ฟิลเตอร์ จำกัด', '02-123-4567', 'เปลี่ยนทุก 3 เดือน'),
                ('BELT002', 'สายพาน V-Belt', 'สายพานสำหรับเครื่องจักร', 'เครื่องจักร', 'Gates Corporation', 350.00, 3, 15, 'ชั้น B2', 'บริษัท เกตส์ ไทย', '02-234-5678', 'ตรวจสอบความตึงเป็นประจำ'),
                ('OIL003', 'น้ำมันหล่อลื่น', 'น้ำมันหล่อลื่นเกรดอุตสาหกรรม', 'น้ำมันหล่อลื่น', 'Shell', 450.00, 10, 25, 'คลัง C', 'บริษัท เชลล์', '02-345-6789', 'เก็บในที่แห้ง'),
                ('BEARING004', 'ลูกปืน', 'ลูกปืนขนาด 6203', 'เครื่องจักร', 'SKF', 280.00, 8, 12, 'ชั้น A3', 'บริษัท เอสเคเอฟ', '02-456-7890', 'ใช้จาระบีคุณภาพดี'),
                ('SCREW005', 'สกรูสแตนเลส', 'สกรูสแตนเลส M6x20', 'ฮาร์ดแวร์', 'Local Supplier', 15.00, 50, 200, 'ชั้น D1', 'ร้านเหล็ก ABC', '02-567-8901', 'สต็อกจำนวนมาก'),
            ]
            
            for part_data in sample_parts:
                cursor.execute("""
                    INSERT INTO parts 
                    (part_number, part_name, description, category, manufacturer, unit_price, 
                     minimum_stock, current_stock, location, supplier, supplier_contact, notes, created_by) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, part_data)
            
            db.commit()
            flash('Sample parts data added successfully!', 'success')
        else:
            flash(f'Parts table already has {parts_count} items.', 'info')
            
        return redirect(url_for('parts_index'))
        
    except Exception as e:
        flash(f'Error setting up database: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/create_admin_user')
def create_admin_user():
    """Create admin user route for development"""
    try:
        db = get_db()
        username = 'admin'
        password = 'admin123'
        
        # Check if admin already exists
        existing_admin = db.execute(
            "SELECT id FROM users WHERE username = ? AND role = 'admin'", (username,)
        ).fetchone()
        
        if existing_admin:
            flash(f'Admin user "{username}" already exists!', 'info')
        else:
            # Create admin user
            db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                (username, generate_password_hash(password))
            )
            db.commit()
            flash(f'Admin user "{username}" created successfully! Password: {password}', 'success')
            
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error creating admin user: {str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        init_database()

    # ตรวจสอบว่าไม่ได้กำลังรันใน reloader process
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        webbrowser.open_new('http://127.0.0.1:5000')

    app.run(debug=True)