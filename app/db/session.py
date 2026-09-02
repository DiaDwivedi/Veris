import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "overrides.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_snapshots (
            transaction_id TEXT PRIMARY KEY,
            deterministic_result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS overrides (
            transaction_id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            candidate_id TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(transaction_id) REFERENCES reconciliation_snapshots(transaction_id)
        )
        """)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
