import sqlite3
import json
import os
from flask import Flask, render_template, request, redirect, url_for, g, flash, jsonify
from datetime import date, timedelta

app = Flask(__name__)
app.secret_key = 'a-super-secret-key-that-you-should-change'
# จัดเก็บฐานข้อมูลในโฟลเดอร์ instance เพื่อความเป็นระเบียบ
DATABASE = os.path.join(app.instance_path, 'maintenance.db')

# สร้าง instance folder ถ้ายังไม่มี
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# -------------------
# Database Connection and Initialization
# -------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables. This will overwrite existing data."""
    with sqlite3.connect(DATABASE) as conn:
        with app.open_resource('schema.sql', mode='r') as f:
            conn.cursor().executescript(f.read())
    print('Initialized the database. All previous data was removed.')

# -------------------
# Routes
# -------------------
@app.route('/')
def index():
    db = get_db()
    assets = db.execute('SELECT * FROM assets ORDER BY id DESC').fetchall()
    
    # ดึงรายการที่ถึงกำหนด PM
    pm_due_assets = db.execute(
        'SELECT * FROM assets WHERE next_pm_date IS NOT NULL AND next_pm_date != "" AND date(next_pm_date) <= date("now", "+7 days") ORDER BY next_pm_date ASC'
    ).fetchall()

    return render_template('index.html', assets=assets, pm_due_assets=pm_due_assets)

@app.route('/add_asset', methods=['POST'])
def add_asset():
    name = request.form['name']
    location = request.form['location']
    next_pm_date = request.form.get('next_pm_date') or None
    pm_frequency_days = request.form.get('pm_frequency_days') or None
    
    custom_data = {}
    keys = request.form.getlist('custom_key')
    values = request.form.getlist('custom_value')
    for i in range(len(keys)):
        if keys[i]:
            custom_data[keys[i]] = values[i]
    custom_data_json = json.dumps(custom_data)
    
    db = get_db()
    db.execute(
        'INSERT INTO assets (name, location, custom_data, next_pm_date, pm_frequency_days) VALUES (?, ?, ?, ?, ?)',
        (name, location, custom_data_json, next_pm_date, pm_frequency_days)
    )
    db.commit()
    flash(f'สินทรัพย์ "{name}" ถูกเพิ่มเข้าระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))

@app.route('/asset/<int:asset_id>')
def asset_detail(asset_id):
    db = get_db()
    asset_row = db.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()
    
    if not asset_row:
        return "Asset not found", 404

    asset = dict(asset_row)
    asset['custom_data'] = json.loads(asset['custom_data'])

    is_pm_due = False
    if asset.get('next_pm_date') and asset['next_pm_date'] != '':
        pm_date = date.fromisoformat(asset['next_pm_date'])
        if pm_date <= date.today():
            is_pm_due = True

    history = db.execute('SELECT * FROM maintenance_history WHERE asset_id = ? ORDER BY date DESC', (asset_id,)).fetchall()
    
    return render_template('asset_detail.html', asset=asset, history=history, is_pm_due=is_pm_due)

@app.route('/edit_asset/<int:asset_id>', methods=['GET', 'POST'])
def edit_asset(asset_id):
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        next_pm_date = request.form.get('next_pm_date') or None
        pm_frequency_days = request.form.get('pm_frequency_days') or None
        
        custom_data = {}
        keys = request.form.getlist('custom_key')
        values = request.form.getlist('custom_value')
        for i in range(len(keys)):
            if keys[i]:
                custom_data[keys[i]] = values[i]
        custom_data_json = json.dumps(custom_data)

        db.execute(
            'UPDATE assets SET name = ?, location = ?, custom_data = ?, next_pm_date = ?, pm_frequency_days = ? WHERE id = ?',
            (name, location, custom_data_json, next_pm_date, pm_frequency_days, asset_id)
        )
        db.commit()
        flash(f'ข้อมูลสินทรัพย์ "{name}" ถูกอัปเดตเรียบร้อยแล้ว', 'success')
        return redirect(url_for('asset_detail', asset_id=asset_id))

    asset_row = db.execute('SELECT * FROM assets WHERE id = ?', (asset_id,)).fetchone()
    asset = dict(asset_row)
    asset['custom_data'] = json.loads(asset['custom_data'])
    
    return render_template('edit_asset.html', asset=asset)

@app.route('/perform_pm/<int:asset_id>', methods=['POST'])
def perform_pm(asset_id):
    db = get_db()
    asset = db.execute('SELECT pm_frequency_days FROM assets WHERE id = ?', (asset_id,)).fetchone()
    
    if asset and asset['pm_frequency_days']:
        frequency = int(asset['pm_frequency_days'])
        new_next_pm_date = date.today() + timedelta(days=frequency)
        
        db.execute('UPDATE assets SET next_pm_date = ? WHERE id = ?', (new_next_pm_date.isoformat(), asset_id))
        
        description = f"ดำเนินการบำรุงรักษาเชิงป้องกัน (PM) ตามรอบ {frequency} วัน"
        db.execute('INSERT INTO maintenance_history (asset_id, description, cost) VALUES (?, ?, ?)', (asset_id, description, 0))
        
        db.commit()
        flash('ดำเนินการ PM และอัปเดตกำหนดการครั้งถัดไปเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่สามารถดำเนินการได้: ไม่ได้ตั้งค่าความถี่ในการทำ PM', 'error')

    return redirect(url_for('asset_detail', asset_id=asset_id))

@app.route('/add_maintenance/<int:asset_id>', methods=['POST'])
def add_maintenance(asset_id):
    description = request.form['description']
    cost_str = request.form.get('cost')
    cost = float(cost_str) if cost_str else None
    db = get_db()
    db.execute('INSERT INTO maintenance_history (asset_id, description, cost) VALUES (?, ?, ?)', (asset_id, description, cost))
    db.commit()
    flash('เพิ่มประวัติการซ่อมบำรุงเรียบร้อยแล้ว', 'success')
    return redirect(url_for('asset_detail', asset_id=asset_id))

@app.route('/delete_asset/<int:asset_id>', methods=['POST'])
def delete_asset(asset_id):
    db = get_db()
    asset = db.execute('SELECT name FROM assets WHERE id = ?', (asset_id,)).fetchone()
    asset_name = asset['name'] if asset else 'ไม่พบข้อมูล'
    db.execute('DELETE FROM maintenance_history WHERE asset_id = ?', (asset_id,))
    db.execute('DELETE FROM assets WHERE id = ?', (asset_id,))
    db.commit()
    flash(f'สินทรัพย์ "{asset_name}" ถูกลบออกจากระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    """Renders the calendar dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/pm_events')
def pm_events_api():
    """Provides PM schedule data as a JSON feed for the calendar."""
    db = get_db()
    # ดึงข้อมูลเฉพาะสินทรัพย์ที่มีการตั้งค่าวันที่ PM ไว้
    query = """
        SELECT id, name, next_pm_date
        FROM assets
        WHERE next_pm_date IS NOT NULL AND next_pm_date != ''
    """
    assets_with_pm = db.execute(query).fetchall()
    
    events = []
    for asset in assets_with_pm:
        events.append({
            'title': asset['name'],
            'start': asset['next_pm_date'],
            'url': url_for('asset_detail', asset_id=asset['id']), # ทำให้คลิกที่ Event แล้วไปหน้ารายละเอียดได้
            'color': '#28a745' # กำหนดสีของ Event เป็นสีเขียว
        })
        
    return jsonify(events)

if __name__ == '__main__':
    app.run(debug=True)