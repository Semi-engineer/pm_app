import sqlite3
import os
import sys

def update_database():
    """Add maintenance_detail_points table to existing database"""
    
    # Determine the correct path to the database
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    instance_path = os.path.join(application_path, 'instance')
    db_path = os.path.join(instance_path, 'maintenance.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='maintenance_detail_points'")
        if cursor.fetchone():
            print("Table maintenance_detail_points already exists.")
            conn.close()
            return True
        
        # Create the new table
        cursor.execute("""
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
            )
        """)
        
        conn.commit()
        conn.close()
        print("Successfully added maintenance_detail_points table to the database.")
        return True
        
    except Exception as e:
        print(f"Error updating database: {e}")
        return False

if __name__ == '__main__':
    update_database()
