# app/db.py
"""
Database utilities for LexiGuard.
Handles SQLite connection and schema creation for sanctions_entities and logs.
"""

import sqlite3
from pathlib import Path
from app.config import DB_PATH

# Ensure data directory exists
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

def get_connection():
    """Return a SQLite3 connection to the main database."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    """Create tables if they don’t exist."""
    con = get_connection()
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS sanctions_entities (
            id TEXT PRIMARY KEY,
            name TEXT,
            aliases TEXT,
            dob TEXT,
            country TEXT,
            program TEXT,
            source TEXT,
            raw_json TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            timestamp TEXT,
            results_json TEXT
        );
        """
    )
    con.commit()
    con.close()
    print("✅ Database initialized at", DB_PATH)

if __name__ == "__main__":
    init_db()
