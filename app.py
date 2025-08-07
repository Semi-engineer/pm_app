import sqlite3
import json
import os
import functools
import click
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, g, flash, jsonify, session, Response
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta, datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = 'a-super-secret-key-that-you-should-change'
DATABASE = os.path.join(app.instance_path, 'maintenance.db')

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# --- Database Connection ---
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- CLI Commands ---
@app.cli.command('init-db')
def init_db_command():
    db = sqlite3.connect(DATABASE)
    with app.open_resource('schema.sql', mode='r', encoding='utf-8') as f:
        db.cursor().executescript(f.read())
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

# --- Decorators and Helpers ---
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
    """Returns a list of all users with the 'technician' role."""
    db = get_db()
    technicians = db.execute("SELECT id, username FROM users WHERE role = 'technician' ORDER BY username").fetchall()
    return technicians

# --- Authentication Routes ---
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

@app.route('/add_asset', methods=['POST'])
@login_required
@admin_required
def add_asset():
    name, location = request.form['name'], request.form['location']
    next_pm_date = request.form.get('next_pm_date') or None
    pm_frequency_days = request.form.get('pm_frequency_days') or None
    technician_id = request.form.get('technician_id') or None
    custom_data = {k: v for k, v in zip(request.form.getlist('custom_key'), request.form.getlist('custom_value')) if k}
    db = get_db()
    db.execute('INSERT INTO assets (name, location, custom_data, next_pm_date, pm_frequency_days, technician_id) VALUES (?, ?, ?, ?, ?, ?)',
               (name, location, json.dumps(custom_data), next_pm_date, pm_frequency_days, technician_id))
    db.commit()
    flash(f'สินทรัพย์ "{name}" ถูกเพิ่มเข้าระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))

@app.route('/edit_asset/<int:asset_id>', methods=('GET', 'POST'))
@login_required
@admin_required
def edit_asset(asset_id):
    db = get_db()
    if request.method == 'POST':
        name, location = request.form['name'], request.form['location']
        next_pm_date = request.form.get('next_pm_date') or None
        pm_frequency_days = request.form.get('pm_frequency_days') or None
        technician_id = request.form.get('technician_id') or None
        custom_data = {k: v for k, v in zip(request.form.getlist('custom_key'), request.form.getlist('custom_value')) if k}
        db.execute('UPDATE assets SET name = ?, location = ?, custom_data = ?, next_pm_date = ?, pm_frequency_days = ?, technician_id = ? WHERE id = ?',
                   (name, location, json.dumps(custom_data), next_pm_date, pm_frequency_days, technician_id, asset_id))
        db.commit()
        flash(f'ข้อมูลสินทรัพย์ "{name}" ถูกอัปเดตเรียบร้อยแล้ว', 'success')
        return redirect(url_for('asset_detail', asset_id=asset_id))
    asset_row = db.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()
    asset = dict(asset_row)
    asset['custom_data'] = json.loads(asset['custom_data'])
    technicians = get_all_technicians()
    return render_template('edit_asset.html', asset=asset, technicians=technicians)

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
    return render_template('asset_detail.html', asset=asset, history=history, is_pm_due=is_pm_due)

@app.route('/delete_asset/<int:asset_id>', methods=['POST'])
@login_required
@admin_required
def delete_asset(asset_id):
    db = get_db()
    asset = db.execute('SELECT name FROM assets WHERE id = ?', (asset_id,)).fetchone()
    asset_name = asset['name'] if asset else ''
    db.execute('DELETE FROM maintenance_history WHERE asset_id = ?', (asset_id,))
    db.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
    db.commit()
    flash(f'สินทรัพย์ "{asset_name}" ถูกลบออกจากระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))

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

if __name__ == '__main__':
    app.run(debug=True)