DROP TABLE IF EXISTS assets;
DROP TABLE IF EXISTS maintenance_history;

CREATE TABLE assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    custom_data TEXT NOT NULL DEFAULT '{}',
    next_pm_date TEXT,
    pm_frequency_days INTEGER
);

CREATE TABLE maintenance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL,
    cost REAL,
    FOREIGN KEY (asset_id) REFERENCES assets (id)
);