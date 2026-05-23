#!/usr/bin/env python3
"""
Diagnostic script to identify startup issues
"""
import sys
import os

print("=" * 70)
print("CaptureIQ Diagnostic Script")
print("=" * 70)

# Step 1: Check Python version
print(f"\n1. Python Version: {sys.version}")

# Step 2: Check database
print("\n2. Checking database...")
try:
    import database as db
    db.init_db()
    users = db.get_all_users()
    print(f"   ✓ Database OK - {len(users)} user(s) found")

    # Verify is_capture_manager column
    if users:
        user = users[0]
        if 'is_capture_manager' in user:
            print(f"   ✓ is_capture_manager column exists")
        else:
            print(f"   ✗ is_capture_manager column MISSING")
            print(f"   Available columns: {list(user.keys())}")
except Exception as e:
    print(f"   ✗ Database error: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Check app.py syntax
print("\n3. Checking app.py syntax...")
try:
    import py_compile
    py_compile.compile('app.py', doraise=True)
    print("   ✓ app.py syntax OK")
except Exception as e:
    print(f"   ✗ Syntax error in app.py: {e}")

# Step 4: Check imports (without Flask)
print("\n4. Checking local imports...")
try:
    import database
    print("   ✓ database module OK")
except Exception as e:
    print(f"   ✗ Error importing database: {e}")

# Step 5: Check migration tables
print("\n5. Checking migration tables...")
try:
    import sqlite3
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "sbir_pipeline.db"))

    # Check capture_plans table
    cursor = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='capture_plans'
    """)
    if cursor.fetchone():
        print("   ✓ capture_plans table exists")
    else:
        print("   ✗ capture_plans table missing")

    # Check capture_plan_access table
    cursor = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='capture_plan_access'
    """)
    if cursor.fetchone():
        print("   ✓ capture_plan_access table exists")
    else:
        print("   ✗ capture_plan_access table missing")

    # Check role_change_history table
    cursor = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='role_change_history'
    """)
    if cursor.fetchone():
        print("   ✓ role_change_history table exists")
    else:
        print("   ✗ role_change_history table missing")

    conn.close()
except Exception as e:
    print(f"   ✗ Error checking tables: {e}")

print("\n" + "=" * 70)
print("Diagnostic complete. Check output above for any ✗ errors.")
print("=" * 70)
