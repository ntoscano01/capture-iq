-- Chunk 2: Capture Plans CRUD & Project Linking
-- Create capture_plans and capture_plan_access tables

CREATE TABLE IF NOT EXISTS capture_plans (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitation_id         INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    capture_name            TEXT NOT NULL,
    capture_lead_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    customer_name           TEXT,
    customer_website        TEXT,
    estimated_release_date  TEXT,
    proposal_due_date       TEXT,
    target_contract_value   REAL,
    stage                   TEXT DEFAULT 'pre-release',
    confidence_level        TEXT DEFAULT 'medium',
    win_probability         INTEGER DEFAULT 50,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now')),
    created_by_user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_archived             INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS capture_plan_access (
    capture_plan_id         INTEGER NOT NULL REFERENCES capture_plans(id) ON DELETE CASCADE,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level            TEXT DEFAULT 'viewer',
    added_at                TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (capture_plan_id, user_id)
);

-- Add capture_plan_id to projects table (link projects to capture plans)
ALTER TABLE projects ADD COLUMN capture_plan_id INTEGER REFERENCES capture_plans(id) ON DELETE SET NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_capture_plan_lead ON capture_plans(capture_lead_id);
CREATE INDEX IF NOT EXISTS idx_capture_plan_solicitation ON capture_plans(solicitation_id);
CREATE INDEX IF NOT EXISTS idx_capture_plan_stage ON capture_plans(stage);
CREATE INDEX IF NOT EXISTS idx_capture_plan_access_user ON capture_plan_access(user_id);
CREATE INDEX IF NOT EXISTS idx_capture_plan_access_plan ON capture_plan_access(capture_plan_id);
CREATE INDEX IF NOT EXISTS idx_project_capture_plan ON projects(capture_plan_id);
