import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "overrides.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if the runs table exists to detect if we need migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='runs'")
        runs_exists = cursor.fetchone() is not None
        
        if not runs_exists:
            # Create runs table
            cursor.execute("""
            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                config_version TEXT,
                batch_size INTEGER
            )
            """)
            
            # Insert legacy run
            cursor.execute("INSERT INTO runs (run_id, created_at, config_version, batch_size) VALUES ('legacy_run', datetime('now'), 'legacy', 0)")
            
            # Create new snapshots table
            cursor.execute("""
            CREATE TABLE reconciliation_snapshots_new (
                run_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                deterministic_result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, transaction_id),
                FOREIGN KEY(run_id) REFERENCES runs(run_id)
            )
            """)
            
            # Migrate existing snapshots if any
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reconciliation_snapshots'")
            if cursor.fetchone():
                cursor.execute("""
                INSERT INTO reconciliation_snapshots_new (run_id, transaction_id, deterministic_result_json, created_at)
                SELECT 'legacy_run', transaction_id, deterministic_result_json, created_at FROM reconciliation_snapshots
                """)
                cursor.execute("DROP TABLE reconciliation_snapshots")
                
            cursor.execute("ALTER TABLE reconciliation_snapshots_new RENAME TO reconciliation_snapshots")
            
            # Create new overrides table
            import uuid
            cursor.execute("""
            CREATE TABLE overrides_new (
                override_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                transaction_id TEXT NOT NULL,
                action TEXT NOT NULL,
                candidate_id TEXT,
                reviewer_note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id, transaction_id) REFERENCES reconciliation_snapshots(run_id, transaction_id)
            )
            """)
            
            # Create index for override history
            cursor.execute("CREATE INDEX idx_overrides_history ON overrides_new (run_id, transaction_id, created_at)")
            
            # Migrate existing overrides
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='overrides'")
            if cursor.fetchone():
                cursor.execute("SELECT transaction_id, action, candidate_id, timestamp FROM overrides")
                old_overrides = cursor.fetchall()
                for row in old_overrides:
                    cursor.execute("""
                    INSERT INTO overrides_new (override_id, run_id, transaction_id, action, candidate_id, reviewer_note, created_at)
                    VALUES (?, 'legacy_run', ?, ?, ?, NULL, ?)
                    """, (str(uuid.uuid4()), row['transaction_id'], row['action'], row['candidate_id'], row['timestamp']))
                    
                cursor.execute("DROP TABLE overrides")
                
            cursor.execute("ALTER TABLE overrides_new RENAME TO overrides")
            
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
