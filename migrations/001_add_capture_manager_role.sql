ALTER TABLE users ADD COLUMN is_capture_manager INTEGER DEFAULT 0;

CREATE TABLE IF NOT EXISTS role_change_history (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_changed_to       TEXT NOT NULL,
    changed_by_user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    changed_at            TEXT DEFAULT (datetime('now')),
    reason                TEXT
);

CREATE INDEX IF NOT EXISTS idx_role_change_user ON role_change_history(user_id);
CREATE INDEX IF NOT EXISTS idx_role_change_date ON role_change_history(changed_at);
