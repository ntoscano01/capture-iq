#!/bin/bash
set -e

echo "========================================================================"
echo "Testing Elevation Through Running Flask App"
echo "========================================================================"

BASE_URL="http://127.0.0.1:5000"
COOKIE_JAR="/tmp/cookies.txt"

# Reset the database
echo ""
echo "1. Resetting user to is_capture_manager = 0..."
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("sbir_pipeline.db")
conn.execute("UPDATE users SET is_capture_manager = 0 WHERE id = 1")
conn.commit()
conn.close()
print("   ✓ Reset complete")
EOF

# Check initial state
echo ""
echo "2. Checking initial state..."
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("sbir_pipeline.db")
conn.row_factory = sqlite3.Row
cursor = conn.execute("SELECT id, username, is_capture_manager FROM users WHERE id = 1")
row = cursor.fetchone()
print(f"   User {row['id']} ({row['username']}): is_capture_manager = {row['is_capture_manager']}")
conn.close()
EOF

# Login
echo ""
echo "3. Logging in..."
curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/login" \
  -d "username=admin&password=admin" \
  -L > /dev/null
echo "   ✓ Login complete"

# Verify we can access admin panel
echo ""
echo "4. Verifying authentication..."
ADMIN_STATUS=$(curl -s -b "$COOKIE_JAR" -o /dev/null -w "%{http_code}" "$BASE_URL/admin/users")
if [ "$ADMIN_STATUS" = "200" ]; then
    echo "   ✓ Can access admin panel (HTTP $ADMIN_STATUS)"
else
    echo "   ✗ Cannot access admin panel (HTTP $ADMIN_STATUS)"
fi

# Perform elevation
echo ""
echo "5. Requesting elevation..."
RESPONSE=$(curl -s -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/admin/users/1/elevate-capture-manager" \
  -H "Content-Type: application/json" \
  -d '{}')
echo "   Response: $RESPONSE"

# Check final state
echo ""
echo "6. Checking final state..."
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect("sbir_pipeline.db")
conn.row_factory = sqlite3.Row
cursor = conn.execute("SELECT id, username, is_capture_manager FROM users WHERE id = 1")
row = cursor.fetchone()
status = "is_capture_manager = " + str(row['is_capture_manager'])
print(f"   User {row['id']} ({row['username']}): {status}")
if row['is_capture_manager'] == 1:
    print("   ✓ ELEVATION SUCCEEDED")
else:
    print("   ✗ ELEVATION FAILED")
conn.close()
EOF

# Cleanup
rm -f "$COOKIE_JAR"

echo ""
echo "========================================================================"
