#!/usr/bin/env python3
"""
Apply Chunk 2 migration for capture plans
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sbir_pipeline.db")

def apply_migration():
    """Apply the migration directly"""
    # Read migration file
    with open("migrations/002_add_capture_plans.sql", "r") as f:
        sql = f.read()

    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)

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
