"""
Database migration runner for CaptureIQ.
Tracks and applies SQL migrations in order.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sbir_pipeline.db")
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def get_db():
    """Return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_migrations_table():
    """Create the migrations tracking table if it doesn't exist."""
    try:
        conn = get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                filename        TEXT UNIQUE NOT NULL,
                applied_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: Could not create migrations table: {e}")
        # Continue anyway, the table might already exist


def get_applied_migrations():
    """Return set of migration filenames that have been applied."""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT filename FROM schema_migrations ORDER BY filename"
        ).fetchall()
        conn.close()
        return {row['filename'] for row in rows}
    except Exception:
        return set()  # No migrations applied yet


def get_pending_migrations():
    """Return list of migration files that haven't been applied yet."""
    if not os.path.exists(MIGRATIONS_DIR):
        return []

    applied = get_applied_migrations()
    pending = []

    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if filename.endswith('.sql') and filename not in applied:
            pending.append(filename)

    return pending


def run_migration(filename):
    """Execute a single migration file."""
    filepath = os.path.join(MIGRATIONS_DIR, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Migration file not found: {filepath}")

    # Read migration SQL
    with open(filepath, 'r') as f:
        sql = f.read()

    # Execute migration
    conn = get_db()
    try:
        # Execute each statement separately (SQLite doesn't like executescript for some things)
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement:
                conn.execute(statement)

        # Record that migration was applied
        conn.execute(
            "INSERT INTO schema_migrations (filename) VALUES (?)",
            (filename,)
        )
        conn.commit()

        print(f"✓ Applied migration: {filename}")
        conn.close()
        return True

    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        print(f"✗ Failed to apply migration {filename}: {e}")
        raise


def apply_pending_migrations():
    """Apply all pending migrations in order."""
    init_migrations_table()
    pending = get_pending_migrations()

    if not pending:
        print("No pending migrations.")
        return

    print(f"Found {len(pending)} pending migration(s):")
    for filename in pending:
        print(f"  - {filename}")

    for filename in pending:
        run_migration(filename)

    print(f"\n✓ All migrations applied successfully!")


if __name__ == '__main__':
    apply_pending_migrations()
