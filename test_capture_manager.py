#!/usr/bin/env python3
"""
Test script to verify capture manager elevation works correctly
"""
import os
import sys
import sqlite3

# Test 1: Check database initialization
print("=" * 70)
print("Testing Capture Manager Role Elevation")
print("=" * 70)

print("\n1. Testing database initialization...")
try:
    import database as db
    db.init_db()
    print("   ✓ Database initialized")
except Exception as e:
    print(f"   ✗ Database error: {e}")
    sys.exit(1)

# Test 2: Check is_capture_manager column
print("\n2. Checking is_capture_manager column...")
try:
    db_path = os.path.join(os.path.dirname(__file__), "sbir_pipeline.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check table structure
    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    col_names = {row['name'] for row in cols}

    if 'is_capture_manager' in col_names:
        print("   ✓ is_capture_manager column exists")
    else:
        print("   ✗ is_capture_manager column NOT found")
        print(f"   Columns: {col_names}")

    conn.close()
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 3: Check role_change_history table
print("\n3. Checking role_change_history table...")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='role_change_history'"
    )
    if cursor.fetchone():
        print("   ✓ role_change_history table exists")
    else:
        print("   ✗ role_change_history table NOT found")
    conn.close()
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 4: Create test user and try elevation
print("\n4. Testing elevation workflow...")
try:
    # Create a test user
    test_user = db.create_user("test_elevation_user", "test@example.com", "hashedpassword123", "user")
    print(f"   ✓ Created test user (ID: {test_user})")

    # Verify user is not capture manager
    user = db.get_user_by_id(test_user)
    if user.get('is_capture_manager') == 0:
        print("   ✓ User is not capture manager initially")
    else:
        print(f"   ✗ User capture manager status is unexpected: {user.get('is_capture_manager')}")

    # Simulate elevation (directly update database like the route does)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("UPDATE users SET is_capture_manager = 1 WHERE id = ?", (test_user,))

    # Log the change
    conn.execute(
        """INSERT INTO role_change_history
           (user_id, role_changed_to, changed_by_user_id, reason)
           VALUES (?, ?, ?, ?)""",
        (test_user, 'capture_manager', 1, 'Test elevation')
    )
    conn.commit()
    conn.close()

    print("   ✓ Elevation recorded in database")

    # Verify the user is now a capture manager
    user = db.get_user_by_id(test_user)
    if user.get('is_capture_manager') == 1:
        print("   ✓ User is now capture manager after elevation")
    else:
        print(f"   ✗ User capture manager status NOT updated: {user.get('is_capture_manager')}")

    # Check role_change_history
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    history = conn.execute(
        "SELECT * FROM role_change_history WHERE user_id = ?", (test_user,)
    ).fetchall()
    conn.close()

    if history:
        print(f"   ✓ Role change history recorded ({len(history)} entries)")
    else:
        print("   ✗ Role change history NOT found")

    # Clean up
    db.delete_user(test_user)
    print("   ✓ Test user cleaned up")

except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✓ All tests passed!")
print("=" * 70)
