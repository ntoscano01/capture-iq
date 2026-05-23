#!/usr/bin/env python3
"""
Direct migration application script
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sbir_pipeline.db")

def apply_migration():
    """Apply the migration directly"""
    # Read migration file
    with open("migrations/001_add_capture_manager_role.sql", "r") as f:
        sql = f.read()

    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)
    # Don't change journal mode, just work with default

    try:
        # Execute each statement separately
        for statement in sql.split(';'):
            statement = statement.strip()
            if statement:
                print(f"Executing: {statement[:60]}...")
                conn.execute(statement)

        conn.commit()
        print("✓ Migration applied successfully!")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    apply_migration()
