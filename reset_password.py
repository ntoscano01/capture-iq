"""
Utility script to reset a user's password directly in the database.
Run this from the sbir-pipeline folder while the app is NOT running:

    python3 reset_password.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash, check_password_hash
import database as db

def reset_password(username: str, new_password: str):
    db.init_db()
    user = db.get_user_by_username(username)
    if not user:
        print(f"ERROR: No user found with username '{username}'")
        return False

    new_hash = generate_password_hash(new_password)
    with db.get_db() as conn:
        conn.execute(
            """UPDATE users
               SET password_hash=?, failed_login_attempts=0, locked_at=NULL
               WHERE username=?""",
            (new_hash, username)
        )

    # Verify
    updated = db.get_user_by_username(username)
    if check_password_hash(updated["password_hash"], new_password):
        print(f"✓ Password for '{username}' has been reset successfully.")
        print(f"  Account unlocked and failed attempts cleared.")
        return True
    else:
        print("ERROR: Password reset failed — hash verification mismatch.")
        return False


if __name__ == "__main__":
    print("=== CaptureIQ Password Reset ===\n")
    print("Stop the app (Ctrl+C in the terminal running app.py) before continuing.\n")

    username = input("Username to reset [admin]: ").strip() or "admin"
    import getpass
    new_pw = getpass.getpass(f"New password for '{username}': ")
    if not new_pw:
        print("ERROR: Password cannot be empty.")
        sys.exit(1)
    confirm = getpass.getpass("Confirm new password: ")
    if new_pw != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    reset_password(username, new_pw)
