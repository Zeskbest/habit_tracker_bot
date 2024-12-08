import sqlite3
from datetime import datetime

DB_FILE = "series.db"


def init_db():
    """Initialize the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Existing series table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            count INTEGER DEFAULT 0
        )
    ''')
    # New series_log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS series_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (series_name) REFERENCES series (name)
        )
    ''')
    conn.commit()
    conn.close()


def real_series(name: str, tg_id: int):
    return f"{tg_id}_{name}"


def log_increment(series_name: str, tg_id: int):
    """Log increments in series_log"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO series_log (series_name) VALUES (?)", (real_series(series_name, tg_id),))
    conn.commit()
    conn.close()


def get_all_series(tg_id: int):
    """Get all series"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, count FROM series WHERE name LIKE ?", (f"{tg_id}_%",))
    names = cursor.fetchall()
    conn.close()
    no_tg_id_names = [name[len(f"{tg_id}_"):] for name, _ in names]
    return no_tg_id_names


def add_series(name: str, tg_id: int):
    """Add a new series"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO series (name) VALUES (?)", (real_series(name, tg_id),))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def delete_series(name: str, tg_id: int):
    """Delete a series by name"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM series WHERE name = ?", (real_series(name, tg_id),))
    conn.commit()
    conn.close()


def update_series(name: str, tg_id: int, increment: int):
    """Update counter for a series"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE series SET count = count + ? WHERE name = ? RETURNING count", (increment, real_series(name, tg_id)))
    ((count,),) = cursor.fetchall()
    conn.commit()
    conn.close()
    return count


def get_logs(series_name: str, tg_id: int, period: str):
    """Get logs from the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    time_filters = {
        "day": "datetime('now', '-1 day')",
        "week": "datetime('now', '-7 days')",
        "weekday": "datetime('now', '-100 years')",
        "month": "datetime('now', '-1 month')",
        "year": "datetime('now', '-1 year')",
        "all": "datetime('now', '-100 years')",
    }

    query = f'''
        SELECT timestamp
        FROM series_log
        WHERE series_name = ? AND timestamp >= {time_filters[period]}
    '''
    cursor.execute(query, (real_series(series_name, tg_id),))
    logs = [datetime.fromisoformat(row[0]) for row in cursor.fetchall()]
    conn.close()
    return logs
