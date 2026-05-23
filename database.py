"""
SBIR Pipeline - Database Layer
SQLite-backed local data store for SBIR solicitations, awards, and topics.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sbir_pipeline.db")


def get_db():
    """Return a database connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # Invalidate schema cache to pick up recent ALTER TABLE changes
    try:
        conn.execute("PRAGMA schema_version")
    except:
        pass
    return conn


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS solicitations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id     TEXT UNIQUE,
                title           TEXT NOT NULL,
                agency          TEXT,
                branch          TEXT,
                phase           TEXT,
                program         TEXT,
                open_date       TEXT,
                close_date      TEXT,
                solicitation_number TEXT,
                description     TEXT,
                url             TEXT,
                source          TEXT,
                favorited       INTEGER DEFAULT 0,
                score           REAL DEFAULT 0,
                notes           TEXT,
                status          TEXT DEFAULT 'open',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS awards (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id     TEXT UNIQUE,
                title           TEXT NOT NULL,
                agency          TEXT,
                branch          TEXT,
                company         TEXT,
                amount          REAL,
                award_year      INTEGER,
                phase           TEXT,
                program         TEXT,
                abstract        TEXT,
                keywords        TEXT,
                pi_name         TEXT,
                url             TEXT,
                source          TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS topics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id     TEXT UNIQUE,
                topic_number    TEXT,
                title           TEXT NOT NULL,
                agency          TEXT,
                branch          TEXT,
                phase           TEXT,
                description     TEXT,
                objective       TEXT,
                phase1_desc     TEXT,
                phase2_desc     TEXT,
                phase3_desc     TEXT,
                keywords        TEXT,
                tech_areas      TEXT,
                focus_areas     TEXT,
                itar            INTEGER DEFAULT 0,
                cmmc_level      TEXT,
                ref_docs        TEXT,
                tech_contact    TEXT,
                url             TEXT,
                close_date      TEXT,
                open_date       TEXT,
                release_date    TEXT,
                solicitation_year TEXT,
                solicitation_status TEXT,
                solicitation_id INTEGER REFERENCES solicitations(id) ON DELETE SET NULL,
                source          TEXT,
                favorited       INTEGER DEFAULT 0,
                score           REAL DEFAULT 0,
                notes           TEXT,
                topic_status    TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ingest_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source      TEXT NOT NULL,
                records_added   INTEGER DEFAULT 0,
                records_updated INTEGER DEFAULT 0,
                errors      TEXT,
                started_at  TEXT DEFAULT (datetime('now')),
                finished_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_sol_agency ON solicitations(agency);
            CREATE INDEX IF NOT EXISTS idx_sol_close ON solicitations(close_date);
            CREATE INDEX IF NOT EXISTS idx_sol_source ON solicitations(source);
            CREATE INDEX IF NOT EXISTS idx_sol_favorited ON solicitations(favorited);
            CREATE INDEX IF NOT EXISTS idx_awards_agency ON awards(agency);
            CREATE INDEX IF NOT EXISTS idx_awards_year ON awards(award_year);
            CREATE INDEX IF NOT EXISTS idx_topics_agency ON topics(agency);

            -- ── SBIR Capture ────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS projects (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id        INTEGER REFERENCES topics(id) ON DELETE SET NULL,
                name            TEXT NOT NULL,
                description     TEXT,
                stage           TEXT DEFAULT 'Identified',
                lead            TEXT,
                due_date        TEXT,
                checklist_type  TEXT DEFAULT 'dod',
                source          TEXT,
                notes           TEXT,
                gdrive_folder_id TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS project_files (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename        TEXT NOT NULL,
                local_path      TEXT,
                file_size       INTEGER DEFAULT 0,
                mime_type       TEXT,
                category        TEXT DEFAULT 'general',
                storage_backend TEXT DEFAULT 'local',
                gdrive_file_id  TEXT,
                gdrive_web_link TEXT,
                uploaded_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS project_checklist_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                category        TEXT DEFAULT 'General',
                label           TEXT NOT NULL,
                completed       INTEGER DEFAULT 0,
                sort_order      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS project_activity_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                event_type      TEXT NOT NULL,
                description     TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- ── Users & per-user topic prefs ────────────────────────────────
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                email         TEXT,
                password_hash TEXT NOT NULL,
                role          TEXT DEFAULT 'user',
                is_active     INTEGER DEFAULT 1,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_topic_prefs (
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                topic_id     INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                favorited    INTEGER DEFAULT 0,
                topic_status TEXT DEFAULT '',
                PRIMARY KEY (user_id, topic_id)
            );

            CREATE INDEX IF NOT EXISTS idx_utp_user ON user_topic_prefs(user_id);
            CREATE INDEX IF NOT EXISTS idx_utp_topic ON user_topic_prefs(topic_id);

            -- ── Audit log ────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT DEFAULT (datetime('now')),
                user_id     INTEGER,
                username    TEXT,
                action_type TEXT NOT NULL,
                detail      TEXT,
                ip_address  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action_type);

            -- ── App settings (key-value store) ───────────────────────────────
            CREATE TABLE IF NOT EXISTS app_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            -- ── COLLABORATION FEATURES ──────────────────────────────────────
            CREATE TABLE IF NOT EXISTS project_members (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role            TEXT DEFAULT 'viewer',
                added_at        TEXT DEFAULT (datetime('now')),
                added_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE(project_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS project_comments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                file_id         INTEGER REFERENCES project_files(id) ON DELETE SET NULL,
                user_id         INTEGER NOT NULL REFERENCES users(id),
                comment_text    TEXT NOT NULL,
                mentions        TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                is_deleted      INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                type            TEXT NOT NULL,
                actor_user_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                message         TEXT,
                is_read         INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS shared_documents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                doc_type        TEXT NOT NULL,
                external_url    TEXT NOT NULL,
                external_id     TEXT,
                title           TEXT,
                added_by_user_id INTEGER REFERENCES users(id),
                added_at        TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_projects_topic ON projects(topic_id);
            CREATE INDEX IF NOT EXISTS idx_projects_stage ON projects(stage);
            CREATE INDEX IF NOT EXISTS idx_pfiles_project ON project_files(project_id);
            CREATE INDEX IF NOT EXISTS idx_pchecklist_project ON project_checklist_items(project_id);
            CREATE INDEX IF NOT EXISTS idx_plog_project ON project_activity_log(project_id);
            CREATE INDEX IF NOT EXISTS idx_pmembers_project ON project_members(project_id);
            CREATE INDEX IF NOT EXISTS idx_pmembers_user ON project_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_pcomments_project ON project_comments(project_id);
            CREATE INDEX IF NOT EXISTS idx_pcomments_user ON project_comments(user_id);
            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
            CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
            CREATE INDEX IF NOT EXISTS idx_sdocs_project ON shared_documents(project_id);

            -- ── Capture Planning ──────────────────────────────────────────────
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

            CREATE INDEX IF NOT EXISTS idx_capture_plan_lead ON capture_plans(capture_lead_id);
            CREATE INDEX IF NOT EXISTS idx_capture_plan_solicitation ON capture_plans(solicitation_id);
            CREATE INDEX IF NOT EXISTS idx_capture_plan_stage ON capture_plans(stage);
            CREATE INDEX IF NOT EXISTS idx_capture_plan_access_user ON capture_plan_access(user_id);
            CREATE INDEX IF NOT EXISTS idx_capture_plan_access_plan ON capture_plan_access(capture_plan_id);

            -- ── Project Team Management ───────────────────────────────────────
            CREATE TABLE IF NOT EXISTS project_team_members (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role                TEXT DEFAULT 'team-member',
                status              TEXT DEFAULT 'active',
                added_by_user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
                added_at            TEXT DEFAULT (datetime('now')),
                UNIQUE(project_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS project_team_invitations (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                invited_user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                invited_by_user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE SET NULL,
                status              TEXT DEFAULT 'pending',
                invited_at          TEXT DEFAULT (datetime('now')),
                responded_at        TEXT,
                UNIQUE(project_id, invited_user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_ptm_project ON project_team_members(project_id);
            CREATE INDEX IF NOT EXISTS idx_ptm_user ON project_team_members(user_id);
            CREATE INDEX IF NOT EXISTS idx_pti_project ON project_team_invitations(project_id);
            CREATE INDEX IF NOT EXISTS idx_pti_invited_user ON project_team_invitations(invited_user_id);
            CREATE INDEX IF NOT EXISTS idx_pti_status ON project_team_invitations(status);

            -- ── Role Change History ──────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS role_change_history (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_changed_to     TEXT NOT NULL,
                changed_by_user_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                reason              TEXT,
                changed_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_role_change_user ON role_change_history(user_id);
            CREATE INDEX IF NOT EXISTS idx_role_change_changed_by ON role_change_history(changed_by_user_id);

            -- ── Proposal Scoring & Ranking ────────────────────────────────────
            CREATE TABLE IF NOT EXISTS scoring_criteria (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_plan_id         INTEGER NOT NULL REFERENCES capture_plans(id) ON DELETE CASCADE,
                name                    TEXT NOT NULL,
                description             TEXT,
                weight                  REAL DEFAULT 1.0,
                max_score               REAL DEFAULT 10.0,
                scoring_guidance        TEXT,
                display_order           INTEGER DEFAULT 0,
                is_active               INTEGER DEFAULT 1,
                created_by_user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at              TEXT DEFAULT (datetime('now')),
                updated_at              TEXT DEFAULT (datetime('now')),
                UNIQUE(capture_plan_id, name)
            );

            CREATE TABLE IF NOT EXISTS proposal_scores (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id              INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                scoring_criterion_id    INTEGER NOT NULL REFERENCES scoring_criteria(id) ON DELETE CASCADE,
                score_value             REAL NOT NULL,
                comments                TEXT,
                scored_by_user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                scored_at               TEXT DEFAULT (datetime('now')),
                updated_at              TEXT DEFAULT (datetime('now')),
                UNIQUE(project_id, scoring_criterion_id)
            );

            CREATE TABLE IF NOT EXISTS proposal_rankings (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                capture_plan_id         INTEGER NOT NULL REFERENCES capture_plans(id) ON DELETE CASCADE,
                project_id              INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                final_score             REAL NOT NULL,
                rank                    INTEGER NOT NULL,
                percentile              REAL,
                scores_complete         INTEGER DEFAULT 0,
                last_scored_at          TEXT,
                updated_at              TEXT DEFAULT (datetime('now')),
                UNIQUE(capture_plan_id, project_id)
            );

            CREATE TABLE IF NOT EXISTS scoring_templates (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                name                    TEXT NOT NULL UNIQUE,
                description             TEXT,
                is_default              INTEGER DEFAULT 0,
                created_by_user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at              TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS scoring_template_criteria (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id             INTEGER NOT NULL REFERENCES scoring_templates(id) ON DELETE CASCADE,
                name                    TEXT NOT NULL,
                description             TEXT,
                weight                  REAL DEFAULT 1.0,
                max_score               REAL DEFAULT 10.0,
                scoring_guidance        TEXT,
                display_order           INTEGER DEFAULT 0,
                UNIQUE(template_id, name)
            );

            CREATE INDEX IF NOT EXISTS idx_scoring_criteria_capture_plan
            ON scoring_criteria(capture_plan_id);
            CREATE INDEX IF NOT EXISTS idx_scoring_criteria_active
            ON scoring_criteria(is_active);
            CREATE INDEX IF NOT EXISTS idx_proposal_scores_project
            ON proposal_scores(project_id);
            CREATE INDEX IF NOT EXISTS idx_proposal_scores_criterion
            ON proposal_scores(scoring_criterion_id);
            CREATE INDEX IF NOT EXISTS idx_proposal_scores_scorer
            ON proposal_scores(scored_by_user_id);
            CREATE INDEX IF NOT EXISTS idx_proposal_rankings_capture_plan
            ON proposal_rankings(capture_plan_id);
            CREATE INDEX IF NOT EXISTS idx_proposal_rankings_project
            ON proposal_rankings(project_id);
            CREATE INDEX IF NOT EXISTS idx_proposal_rankings_score
            ON proposal_rankings(final_score DESC);
            CREATE INDEX IF NOT EXISTS idx_scoring_templates_default
            ON scoring_templates(is_default);
            CREATE INDEX IF NOT EXISTS idx_template_criteria_template
            ON scoring_template_criteria(template_id);

            -- ── Task Management System ────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS tasks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                title           TEXT NOT NULL,
                description     TEXT,
                project_id      INTEGER REFERENCES projects(id) ON DELETE SET NULL,
                deliverable     TEXT,
                created_by_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assigned_to_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                start_date      TEXT,
                end_date        TEXT,
                expire_date     TEXT,
                status          TEXT DEFAULT 'active',
                priority        TEXT DEFAULT 'normal',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON tasks(created_by_id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_end_date ON tasks(end_date);
        """)

    # ── Migration: add new columns to existing databases ──────────────────────
    new_user_cols = [
        ("last_login_at",           "TEXT"),
        ("last_login_ip",           "TEXT"),
        ("failed_login_attempts",   "INTEGER DEFAULT 0"),
        ("locked_at",               "TEXT"),
        ("is_capture_manager",      "INTEGER DEFAULT 0"),
    ]
    with get_db() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        for col, col_type in new_user_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                print(f"[DB] Migrated: added users.{col}")

    new_topic_cols = [
        ("objective",            "TEXT"),
        ("phase1_desc",          "TEXT"),
        ("phase2_desc",          "TEXT"),
        ("phase3_desc",          "TEXT"),
        ("keywords",             "TEXT"),
        ("tech_areas",           "TEXT"),
        ("focus_areas",          "TEXT"),
        ("itar",                 "INTEGER DEFAULT 0"),
        ("cmmc_level",           "TEXT"),
        ("ref_docs",             "TEXT"),
        ("favorited",            "INTEGER DEFAULT 0"),
        ("score",                "REAL DEFAULT 0"),
        ("notes",                "TEXT"),
        ("close_date",           "TEXT"),
        ("open_date",            "TEXT"),
        ("release_date",         "TEXT"),
        ("solicitation_year",    "TEXT"),
        ("solicitation_status",  "TEXT"),
        ("topic_status",         "TEXT DEFAULT ''"),
    ]
    # ── Migrate project_files table ───────────────────────────────────────────
    new_pfile_cols = [
        ("storage_backend", "TEXT DEFAULT 'local'"),
        ("gdrive_file_id",  "TEXT"),
        ("gdrive_web_link", "TEXT"),
        ("uploaded_by_user_id", "INTEGER REFERENCES users(id)"),
    ]
    with get_db() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(project_files)")}
        for col, col_type in new_pfile_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE project_files ADD COLUMN {col} {col_type}")
                print(f"[DB] Migrated: added project_files.{col}")

    # ── Migrate projects table ────────────────────────────────────────────────
    new_proj_cols = [
        ("gdrive_folder_id", "TEXT"),
        ("owner_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("is_shared", "INTEGER DEFAULT 0"),
        ("capture_plan_id", "INTEGER REFERENCES capture_plans(id) ON DELETE SET NULL"),
    ]
    with get_db() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(projects)")}
        for col, col_type in new_proj_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {col_type}")
                print(f"[DB] Migrated: added projects.{col}")
    with get_db() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(topics)")}
        for col, col_type in new_topic_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE topics ADD COLUMN {col} {col_type}")
                print(f"[DB] Migrated: added topics.{col}")

    # ── Migrate project_checklist_items table (add task scheduling cols) ─────
    new_checklist_cols = [
        ("assigned_to_id",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("start_date",      "TEXT"),
        ("end_date",        "TEXT"),
        ("estimated_hours", "REAL DEFAULT 0"),
        ("actual_hours",    "REAL DEFAULT 0"),
    ]
    with get_db() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(project_checklist_items)")}
        for col, col_type in new_checklist_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE project_checklist_items ADD COLUMN {col} {col_type}")
                print(f"[DB] Migrated: added project_checklist_items.{col}")

    print(f"[DB] Database initialized at {DB_PATH}")


# ── Solicitations ──────────────────────────────────────────────────────────────

def upsert_solicitation(data: dict) -> tuple[bool, bool]:
    """Insert or update a solicitation. Returns (inserted, updated)."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM solicitations WHERE external_id = ?",
            (data.get("external_id"),)
        ).fetchone()
        now = datetime.utcnow().isoformat()
        if existing:
            conn.execute("""
                UPDATE solicitations SET
                    title=?, agency=?, branch=?, phase=?, program=?,
                    open_date=?, close_date=?, solicitation_number=?,
                    description=?, url=?, source=?, status=?, updated_at=?
                WHERE external_id=?
            """, (
                data.get("title"), data.get("agency"), data.get("branch"),
                data.get("phase"), data.get("program"),
                data.get("open_date"), data.get("close_date"),
                data.get("solicitation_number"),
                data.get("description"), data.get("url"),
                data.get("source"), data.get("status", "open"),
                now, data.get("external_id")
            ))
            return False, True
        else:
            conn.execute("""
                INSERT INTO solicitations
                    (external_id, title, agency, branch, phase, program,
                     open_date, close_date, solicitation_number,
                     description, url, source, status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data.get("external_id"), data.get("title"),
                data.get("agency"), data.get("branch"),
                data.get("phase"), data.get("program"),
                data.get("open_date"), data.get("close_date"),
                data.get("solicitation_number"),
                data.get("description"), data.get("url"),
                data.get("source"), data.get("status", "open"),
                now, now
            ))
            return True, False


def get_solicitations(agency=None, phase=None, program=None,
                       favorited=None, source=None, status=None,
                       keyword=None, limit=200, offset=0):
    """Query solicitations with optional filters."""
    sql = "SELECT * FROM solicitations WHERE 1=1"
    params = []
    if agency:
        sql += " AND agency = ?"
        params.append(agency)
    if phase:
        sql += " AND phase = ?"
        params.append(phase)
    if program:
        sql += " AND program = ?"
        params.append(program)
    if favorited is not None:
        sql += " AND favorited = ?"
        params.append(1 if favorited else 0)
    if source:
        sql += " AND source = ?"
        params.append(source)
    if status:
        sql += " AND status = ?"
        params.append(status)
    if keyword:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    sql += " ORDER BY close_date ASC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_solicitation(sol_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM solicitations WHERE id=?", (sol_id,)).fetchone()
    return dict(row) if row else None


def toggle_favorite(sol_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT favorited FROM solicitations WHERE id=?", (sol_id,)).fetchone()
        if not row:
            return False
        new_val = 0 if row["favorited"] else 1
        conn.execute("UPDATE solicitations SET favorited=?, updated_at=? WHERE id=?",
                     (new_val, datetime.utcnow().isoformat(), sol_id))
    return bool(new_val)


def set_score(sol_id: int, score: float):
    with get_db() as conn:
        conn.execute("UPDATE solicitations SET score=?, updated_at=? WHERE id=?",
                     (score, datetime.utcnow().isoformat(), sol_id))


def set_notes(sol_id: int, notes: str):
    with get_db() as conn:
        conn.execute("UPDATE solicitations SET notes=?, updated_at=? WHERE id=?",
                     (notes, datetime.utcnow().isoformat(), sol_id))


# ── Awards ─────────────────────────────────────────────────────────────────────

def upsert_award(data: dict) -> tuple[bool, bool]:
    """Insert or update an award. Returns (inserted, updated)."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM awards WHERE external_id = ?",
            (data.get("external_id"),)
        ).fetchone()
        now = datetime.utcnow().isoformat()
        if existing:
            conn.execute("""
                UPDATE awards SET
                    title=?, agency=?, branch=?, company=?, amount=?,
                    award_year=?, phase=?, program=?, abstract=?,
                    keywords=?, pi_name=?, url=?, source=?, updated_at=?
                WHERE external_id=?
            """, (
                data.get("title"), data.get("agency"), data.get("branch"),
                data.get("company"), data.get("amount"),
                data.get("award_year"), data.get("phase"), data.get("program"),
                data.get("abstract"), data.get("keywords"), data.get("pi_name"),
                data.get("url"), data.get("source"), now,
                data.get("external_id")
            ))
            return False, True
        else:
            conn.execute("""
                INSERT INTO awards
                    (external_id, title, agency, branch, company, amount,
                     award_year, phase, program, abstract, keywords,
                     pi_name, url, source, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data.get("external_id"), data.get("title"),
                data.get("agency"), data.get("branch"),
                data.get("company"), data.get("amount"),
                data.get("award_year"), data.get("phase"), data.get("program"),
                data.get("abstract"), data.get("keywords"),
                data.get("pi_name"), data.get("url"),
                data.get("source"), now, now
            ))
            return True, False


def get_awards(agency=None, phase=None, program=None, year=None,
               source=None, keyword=None, limit=200, offset=0):
    sql = "SELECT * FROM awards WHERE 1=1"
    params = []
    if agency:
        sql += " AND agency = ?"
        params.append(agency)
    if phase:
        sql += " AND phase = ?"
        params.append(phase)
    if program:
        sql += " AND program = ?"
        params.append(program)
    if year:
        sql += " AND award_year = ?"
        params.append(year)
    if source:
        sql += " AND source = ?"
        params.append(source)
    if keyword:
        sql += " AND (title LIKE ? OR abstract LIKE ? OR keywords LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    sql += " ORDER BY award_year DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_award(award_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM awards WHERE id=?", (award_id,)).fetchone()
    return dict(row) if row else None


# ── Topics ─────────────────────────────────────────────────────────────────────

def upsert_topic(data: dict) -> tuple[bool, bool]:
    """Insert or update a topic. Returns (inserted, updated)."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM topics WHERE external_id = ?",
            (data.get("external_id"),)
        ).fetchone()
        now = datetime.utcnow().isoformat()
        if existing:
            conn.execute("""
                UPDATE topics SET
                    topic_number=?, title=?, agency=?, branch=?, phase=?,
                    description=?, objective=?, phase1_desc=?, phase2_desc=?,
                    phase3_desc=?, keywords=?, tech_areas=?, focus_areas=?,
                    itar=?, cmmc_level=?, ref_docs=?,
                    tech_contact=?, url=?,
                    close_date=?, open_date=?, release_date=?,
                    solicitation_year=?, solicitation_status=?,
                    source=?, updated_at=?
                WHERE external_id=?
            """, (
                data.get("topic_number"), data.get("title"),
                data.get("agency"), data.get("branch"), data.get("phase"),
                data.get("description"), data.get("objective"),
                data.get("phase1_desc"), data.get("phase2_desc"),
                data.get("phase3_desc"), data.get("keywords"),
                data.get("tech_areas"), data.get("focus_areas"),
                1 if data.get("itar") else 0,
                data.get("cmmc_level"), data.get("ref_docs"),
                data.get("tech_contact"), data.get("url"),
                data.get("close_date"), data.get("open_date"),
                data.get("release_date"), data.get("solicitation_year"),
                data.get("solicitation_status"),
                data.get("source"), now,
                data.get("external_id")
            ))
            return False, True
        else:
            conn.execute("""
                INSERT INTO topics
                    (external_id, topic_number, title, agency, branch, phase,
                     description, objective, phase1_desc, phase2_desc,
                     phase3_desc, keywords, tech_areas, focus_areas,
                     itar, cmmc_level, ref_docs,
                     tech_contact, url,
                     close_date, open_date, release_date,
                     solicitation_year, solicitation_status,
                     source, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data.get("external_id"), data.get("topic_number"),
                data.get("title"), data.get("agency"), data.get("branch"),
                data.get("phase"), data.get("description"),
                data.get("objective"), data.get("phase1_desc"),
                data.get("phase2_desc"), data.get("phase3_desc"),
                data.get("keywords"), data.get("tech_areas"),
                data.get("focus_areas"),
                1 if data.get("itar") else 0,
                data.get("cmmc_level"), data.get("ref_docs"),
                data.get("tech_contact"), data.get("url"),
                data.get("close_date"), data.get("open_date"),
                data.get("release_date"), data.get("solicitation_year"),
                data.get("solicitation_status"),
                data.get("source"), now, now
            ))
            return True, False


def get_topics(agency=None, phase=None, source=None, keyword=None,
               favorited=None, topic_status=None, limit=200, offset=0,
               user_id=None):
    # When a user_id is provided, overlay per-user prefs via LEFT JOIN
    if user_id:
        sql = """
            SELECT t.id, t.external_id, t.topic_number, t.title, t.agency, t.branch,
                   t.phase, t.description, t.objective, t.phase1_desc, t.phase2_desc,
                   t.phase3_desc, t.keywords, t.tech_areas, t.focus_areas, t.itar,
                   t.cmmc_level, t.ref_docs, t.tech_contact, t.url,
                   t.close_date, t.open_date, t.release_date, t.solicitation_year,
                   t.solicitation_status, t.solicitation_id, t.source, t.score,
                   t.notes, t.created_at, t.updated_at,
                   COALESCE(utp.favorited, 0) as favorited,
                   COALESCE(utp.topic_status, '') as topic_status
            FROM topics t
            LEFT JOIN user_topic_prefs utp ON t.id = utp.topic_id AND utp.user_id = ?
            WHERE 1=1
        """
        params = [user_id]
        fav_col    = "COALESCE(utp.favorited, 0)"
        status_col = "COALESCE(utp.topic_status, '')"
    else:
        sql = "SELECT * FROM topics WHERE 1=1"
        params = []
        fav_col    = "favorited"
        status_col = "topic_status"

    if agency:
        sql += " AND t.agency = ?" if user_id else " AND agency = ?"
        params.append(agency)
    if phase:
        sql += " AND t.phase = ?" if user_id else " AND phase = ?"
        params.append(phase)
    if source:
        sql += " AND t.source = ?" if user_id else " AND source = ?"
        params.append(source)
    if favorited is not None:
        sql += f" AND {fav_col} = ?"
        params.append(1 if favorited else 0)
    if topic_status is not None:
        sql += f" AND {status_col} = ?"
        params.append(topic_status)
    if keyword:
        if user_id:
            sql += " AND (t.title LIKE ? OR t.description LIKE ? OR t.keywords LIKE ?)"
        else:
            sql += " AND (title LIKE ? OR description LIKE ? OR keywords LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    sql += f" ORDER BY {fav_col} DESC, t.score DESC, t.created_at DESC LIMIT ? OFFSET ?" if user_id \
        else " ORDER BY favorited DESC, score DESC, created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_topic(topic_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
    return dict(row) if row else None


def toggle_topic_favorite(topic_id: int) -> bool:
    """Toggle favorited flag. Returns the new boolean value."""
    with get_db() as conn:
        row = conn.execute("SELECT favorited FROM topics WHERE id=?", (topic_id,)).fetchone()
        if not row:
            return False
        new_val = 0 if row["favorited"] else 1
        conn.execute("UPDATE topics SET favorited=?, updated_at=? WHERE id=?",
                     (new_val, datetime.utcnow().isoformat(), topic_id))
    return bool(new_val)


def set_topic_score(topic_id: int, score: float):
    with get_db() as conn:
        conn.execute("UPDATE topics SET score=?, updated_at=? WHERE id=?",
                     (score, datetime.utcnow().isoformat(), topic_id))


def set_topic_notes(topic_id: int, notes: str):
    with get_db() as conn:
        conn.execute("UPDATE topics SET notes=?, updated_at=? WHERE id=?",
                     (notes, datetime.utcnow().isoformat(), topic_id))


def set_topic_status(topic_id: int, status: str) -> str:
    """Toggle topic_status between the given value and '' (clear).
    Returns the new status value."""
    allowed = {"nominated", "passed", ""}
    if status not in allowed:
        status = ""
    with get_db() as conn:
        row = conn.execute("SELECT topic_status FROM topics WHERE id=?", (topic_id,)).fetchone()
        if not row:
            return ""
        # Toggle: if already set to this status, clear it
        new_val = "" if row["topic_status"] == status else status
        conn.execute("UPDATE topics SET topic_status=?, updated_at=? WHERE id=?",
                     (new_val, datetime.utcnow().isoformat(), topic_id))
    return new_val


# ── Full-text search ───────────────────────────────────────────────────────────

def full_search(keyword: str, limit=100):
    """Search across all three tables and return grouped results."""
    kw = f"%{keyword}%"
    with get_db() as conn:
        sols = conn.execute("""
            SELECT 'solicitation' as type, id, title, agency, phase, close_date as date_field
            FROM solicitations
            WHERE title LIKE ? OR description LIKE ?
            LIMIT ?
        """, (kw, kw, limit)).fetchall()
        awards = conn.execute("""
            SELECT 'award' as type, id, title, agency, phase, award_year as date_field
            FROM awards
            WHERE title LIKE ? OR abstract LIKE ? OR keywords LIKE ?
            LIMIT ?
        """, (kw, kw, kw, limit)).fetchall()
        topics = conn.execute("""
            SELECT 'topic' as type, id, title, agency, phase, NULL as date_field
            FROM topics
            WHERE title LIKE ? OR description LIKE ?
            LIMIT ?
        """, (kw, kw, limit)).fetchall()
    return {
        "solicitations": [dict(r) for r in sols],
        "awards": [dict(r) for r in awards],
        "topics": [dict(r) for r in topics],
    }


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_stats(user_id=None):
    with get_db() as conn:
        topic_count = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        noted_count = conn.execute("SELECT COUNT(*) FROM topics WHERE notes IS NOT NULL AND notes != ''").fetchone()[0]
        itar_count  = conn.execute("SELECT COUNT(*) FROM topics WHERE itar=1").fetchone()[0]
        if user_id:
            fav_count       = conn.execute("SELECT COUNT(*) FROM user_topic_prefs WHERE user_id=? AND favorited=1", (user_id,)).fetchone()[0]
            nominated_count = conn.execute("SELECT COUNT(*) FROM user_topic_prefs WHERE user_id=? AND topic_status='nominated'", (user_id,)).fetchone()[0]
            passed_count    = conn.execute("SELECT COUNT(*) FROM user_topic_prefs WHERE user_id=? AND topic_status='passed'", (user_id,)).fetchone()[0]
        else:
            fav_count       = conn.execute("SELECT COUNT(*) FROM topics WHERE favorited=1").fetchone()[0]
            nominated_count = conn.execute("SELECT COUNT(*) FROM topics WHERE topic_status='nominated'").fetchone()[0]
            passed_count    = conn.execute("SELECT COUNT(*) FROM topics WHERE topic_status='passed'").fetchone()[0]
        branches = conn.execute("""
            SELECT branch, COUNT(*) as cnt FROM topics
            WHERE branch IS NOT NULL AND branch != ''
            GROUP BY branch ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        recent_log = conn.execute("""
            SELECT source, records_added, records_updated, started_at, finished_at
            FROM ingest_log ORDER BY id DESC LIMIT 5
        """).fetchall()
    return {
        "topic_count":      topic_count,
        "favorited_count":  fav_count,
        "noted_count":      noted_count,
        "itar_count":       itar_count,
        "nominated_count":  nominated_count,
        "passed_count":     passed_count,
        "top_agencies":     [dict(r) for r in branches],
        "recent_ingestions":[dict(r) for r in recent_log],
    }


# ── Ingest log ─────────────────────────────────────────────────────────────────

def delete_ingest_log(log_id: int):
    """Delete a single ingest log entry."""
    with get_db() as conn:
        conn.execute("DELETE FROM ingest_log WHERE id=?", (log_id,))


# ── SBIR Capture — Projects ────────────────────────────────────────────────────

# Standard DoD SBIR checklist (Phase I, per Section 3.0 BAA Preface)
DOD_STANDARD_CHECKLIST = [
    ("Pre-Submission",  "SAM.gov registration verified"),
    ("Pre-Submission",  "SBA Company Registry confirmed"),
    ("Pre-Submission",  "DSIP portal registration complete"),
    ("Pre-Submission",  "CMMC/cybersecurity requirements reviewed"),
    ("Pre-Submission",  "ITAR/EAR export control review completed"),
    ("Volume 1 — Cover Sheet",  "Technical abstract drafted (≤3,000 characters)"),
    ("Volume 1 — Cover Sheet",  "Anticipated benefits/commercial applications drafted (≤3,000 characters)"),
    ("Volume 2 — Technical",    "1. Identification and Significance of Problem/Opportunity"),
    ("Volume 2 — Technical",    "2. Phase I Technical Objectives"),
    ("Volume 2 — Technical",    "3. Phase I Statement of Work"),
    ("Volume 2 — Technical",    "4. Related Work"),
    ("Volume 2 — Technical",    "5. Relationship with Future Research or R&D"),
    ("Volume 2 — Technical",    "6. Commercialization Strategy"),
    ("Volume 2 — Technical",    "7. Key Personnel identified"),
    ("Volume 2 — Technical",    "8. Foreign Citizens disclosure reviewed"),
    ("Volume 2 — Technical",    "9. Facilities/Equipment listed"),
    ("Volume 2 — Technical",    "10. Subcontractors/Consultants identified"),
    ("Volume 2 — Technical",    "11. Prior, Current, or Pending Support disclosed"),
    ("Volume 2 — Technical",    "12. Data Rights assertion completed"),
    ("Volume 3 — Cost",         "Cost volume prepared and reviewed"),
    ("Volume 3 — Cost",         "Budget narrative complete"),
    ("Volume 4 — CCR",          "Company Commercialization Report (CCR) submitted (if applicable)"),
    ("Volume 5 — Supporting",   "Supporting documents compiled"),
    ("Volume 6 — FWA",          "Fraud, Waste, and Abuse training completed and certified"),
    ("Volume 7 — Foreign",      "Foreign affiliations disclosure completed"),
    ("Final Submission",        "Proposal reviewed against all requirements"),
    ("Final Submission",        "Submitted via DSIP portal"),
]

STAGES = [
    "Identified",
    "Qualified",
    "In Progress",
    "Submitted",
]


def create_project(data: dict) -> int:
    """Create a new project and seed its checklist. Returns new project id."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO projects
                (topic_id, name, description, stage, lead, due_date,
                 checklist_type, source, notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.get("topic_id"), data.get("name"), data.get("description"),
            data.get("stage", "Identified"), data.get("lead"),
            data.get("due_date"), data.get("checklist_type", "dod"),
            data.get("source"), data.get("notes"), now, now
        ))
        project_id = cur.lastrowid

        # Seed checklist
        if data.get("checklist_type", "dod") == "dod":
            for i, (category, label) in enumerate(DOD_STANDARD_CHECKLIST):
                conn.execute("""
                    INSERT INTO project_checklist_items
                        (project_id, category, label, sort_order)
                    VALUES (?,?,?,?)
                """, (project_id, category, label, i))
        # Log creation
        conn.execute("""
            INSERT INTO project_activity_log (project_id, event_type, description)
            VALUES (?, 'created', ?)
        """, (project_id, f"Project created with stage: {data.get('stage', 'Identified')}"))

    return project_id


def get_projects(stage=None, keyword=None, limit=200, offset=0) -> list:
    sql = """
        SELECT p.*,
               t.title as topic_title, t.topic_number, t.agency, t.branch, t.phase,
               t.close_date as topic_close_date,
               (SELECT COUNT(*) FROM project_checklist_items WHERE project_id=p.id) as checklist_total,
               (SELECT COUNT(*) FROM project_checklist_items WHERE project_id=p.id AND completed=1) as checklist_done,
               (SELECT COUNT(*) FROM project_files WHERE project_id=p.id) as file_count
        FROM projects p
        LEFT JOIN topics t ON p.topic_id = t.id
        WHERE 1=1
    """
    params = []
    if stage:
        sql += " AND p.stage = ?"
        params.append(stage)
    if keyword:
        sql += " AND (p.name LIKE ? OR p.description LIKE ? OR t.title LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    sql += " ORDER BY p.updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> dict | None:
    sql = """
        SELECT p.*,
               t.title as topic_title, t.topic_number, t.agency, t.branch, t.phase,
               t.url as topic_url, t.close_date as topic_close_date,
               (SELECT COUNT(*) FROM project_checklist_items WHERE project_id=p.id) as checklist_total,
               (SELECT COUNT(*) FROM project_checklist_items WHERE project_id=p.id AND completed=1) as checklist_done
        FROM projects p
        LEFT JOIN topics t ON p.topic_id = t.id
        WHERE p.id = ?
    """
    with get_db() as conn:
        row = conn.execute(sql, (project_id,)).fetchone()
    return dict(row) if row else None


def update_project(project_id: int, data: dict):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute("""
            UPDATE projects SET
                name=?, description=?, lead=?, due_date=?, notes=?, updated_at=?
            WHERE id=?
        """, (
            data.get("name"), data.get("description"),
            data.get("lead"), data.get("due_date"),
            data.get("notes"), now, project_id
        ))


def set_project_stage(project_id: int, stage: str):
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        old = conn.execute("SELECT stage FROM projects WHERE id=?", (project_id,)).fetchone()
        conn.execute("UPDATE projects SET stage=?, updated_at=? WHERE id=?",
                     (stage, now, project_id))
        conn.execute("""
            INSERT INTO project_activity_log (project_id, event_type, description)
            VALUES (?, 'stage_change', ?)
        """, (project_id,
              f"Stage changed from '{old['stage'] if old else '?'}' to '{stage}'"))


def delete_project(project_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))


# ── SBIR Capture — Checklist ───────────────────────────────────────────────────

def get_checklist(project_id: int) -> list:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM project_checklist_items
            WHERE project_id=?
            ORDER BY sort_order, id
        """, (project_id,)).fetchall()
    return [dict(r) for r in rows]


def toggle_checklist_item(item_id: int, project_id: int) -> bool:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        row = conn.execute(
            "SELECT completed, label FROM project_checklist_items WHERE id=? AND project_id=?",
            (item_id, project_id)
        ).fetchone()
        if not row:
            return False
        new_val = 0 if row["completed"] else 1
        conn.execute(
            "UPDATE project_checklist_items SET completed=? WHERE id=?",
            (new_val, item_id)
        )
        action = "completed" if new_val else "unchecked"
        conn.execute("""
            INSERT INTO project_activity_log (project_id, event_type, description)
            VALUES (?, 'checklist', ?)
        """, (project_id, f"{action.capitalize()}: {row['label']}"))
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
    return bool(new_val)


def add_checklist_item(project_id: int, label: str, category: str = "Custom") -> int:
    with get_db() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM project_checklist_items WHERE project_id=?",
            (project_id,)
        ).fetchone()[0]
        cur = conn.execute("""
            INSERT INTO project_checklist_items (project_id, category, label, sort_order)
            VALUES (?,?,?,?)
        """, (project_id, category, label, max_order + 1))
        return cur.lastrowid


def delete_checklist_item(item_id: int, project_id: int):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM project_checklist_items WHERE id=? AND project_id=?",
            (item_id, project_id)
        )


# ── SBIR Capture — Files ───────────────────────────────────────────────────────

def set_project_gdrive_folder(project_id: int, folder_id: str):
    with get_db() as conn:
        conn.execute("UPDATE projects SET gdrive_folder_id=? WHERE id=?",
                     (folder_id, project_id))


def add_project_file(project_id: int, filename: str, local_path: str = None,
                     file_size: int = 0, mime_type: str = None,
                     category: str = "general",
                     storage_backend: str = "local",
                     gdrive_file_id: str = None,
                     gdrive_web_link: str = None) -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO project_files
                (project_id, filename, local_path, file_size, mime_type,
                 category, storage_backend, gdrive_file_id, gdrive_web_link)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (project_id, filename, local_path, file_size, mime_type,
              category, storage_backend, gdrive_file_id, gdrive_web_link))
        file_id = cur.lastrowid
        conn.execute("""
            INSERT INTO project_activity_log (project_id, event_type, description)
            VALUES (?, 'file_upload', ?)
        """, (project_id, f"File uploaded: {filename} ({category})"))
        conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
    return file_id


def get_project_files(project_id: int) -> list:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM project_files
            WHERE project_id=?
            ORDER BY uploaded_at DESC
        """, (project_id,)).fetchall()
    return [dict(r) for r in rows]


def get_project_file(file_id: int, project_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM project_files WHERE id=? AND project_id=?",
            (file_id, project_id)
        ).fetchone()
    return dict(row) if row else None


def delete_project_file(file_id: int, project_id: int) -> str | None:
    """Delete file record. Returns local_path so caller can remove the file."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT local_path, filename FROM project_files WHERE id=? AND project_id=?",
            (file_id, project_id)
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM project_files WHERE id=?", (file_id,))
        conn.execute("""
            INSERT INTO project_activity_log (project_id, event_type, description)
            VALUES (?, 'file_delete', ?)
        """, (project_id, f"File deleted: {row['filename']}"))
    return row["local_path"]


# ── SBIR Capture — Activity Log ────────────────────────────────────────────────

def get_activity_log(project_id: int, limit: int = 50) -> list:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM project_activity_log
            WHERE project_id=?
            ORDER BY id DESC LIMIT ?
        """, (project_id, limit)).fetchall()
    return [dict(r) for r in rows]


def add_activity(project_id: int, event_type: str, description: str):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO project_activity_log (project_id, event_type, description)
            VALUES (?,?,?)
        """, (project_id, event_type, description))


# ── Capture stats ──────────────────────────────────────────────────────────────

def get_capture_stats() -> dict:
    with get_db() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        by_stage  = conn.execute("""
            SELECT stage, COUNT(*) as cnt FROM projects GROUP BY stage ORDER BY cnt DESC
        """).fetchall()
        recent    = conn.execute("""
            SELECT p.id, p.name, p.stage, p.updated_at,
                   t.topic_number, t.agency
            FROM projects p LEFT JOIN topics t ON p.topic_id=t.id
            ORDER BY p.updated_at DESC LIMIT 5
        """).fetchall()
    return {
        "total":    total,
        "by_stage": [dict(r) for r in by_stage],
        "recent":   [dict(r) for r in recent],
    }


def log_ingest(source: str, added: int, updated: int,
               errors: str = None, started_at: str = None) -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO ingest_log (source, records_added, records_updated, errors, started_at, finished_at)
            VALUES (?,?,?,?,?,?)
        """, (source, added, updated, errors, started_at or now, now))
        return cur.lastrowid


# ── Distinct filter values ─────────────────────────────────────────────────────

# ── Users ──────────────────────────────────────────────────────────────────────

def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT *, COALESCE(failed_login_attempts, 0) as failed_login_attempts
               FROM users WHERE username=?""",
            (username,)
        ).fetchone()
    return dict(row) if row else None


def get_all_users() -> list:
    with get_db() as conn:
        # Try with is_capture_manager column first
        try:
            rows = conn.execute(
                """SELECT id, username, email, role, is_active, created_at,
                          last_login_at, last_login_ip,
                          COALESCE(failed_login_attempts, 0) as failed_login_attempts,
                          locked_at, COALESCE(is_capture_manager, 0) as is_capture_manager
                   FROM users ORDER BY id"""
            ).fetchall()
        except Exception:
            # Fallback if column doesn't exist yet
            rows = conn.execute(
                """SELECT id, username, email, role, is_active, created_at,
                          last_login_at, last_login_ip,
                          COALESCE(failed_login_attempts, 0) as failed_login_attempts,
                          locked_at
                   FROM users ORDER BY id"""
            ).fetchall()

    result = []
    for row in rows:
        row_dict = dict(row)
        # Ensure is_capture_manager exists (default to 0 if missing)
        if 'is_capture_manager' not in row_dict:
            row_dict['is_capture_manager'] = 0
        result.append(row_dict)

    return result


def count_users() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def create_user(username: str, email: str, password_hash: str, role: str = "user") -> int:
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?,?,?,?)",
            (username, email or "", password_hash, role)
        )
        return cur.lastrowid


def update_user_password(user_id: int, password_hash: str):
    with get_db() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))


def set_user_active(user_id: int, active: bool):
    with get_db() as conn:
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, user_id))


def delete_user(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))


# ── Per-user topic prefs ───────────────────────────────────────────────────────

def toggle_user_topic_favorite(user_id: int, topic_id: int) -> bool:
    """Toggle the user's favorite on a topic. Returns new boolean value."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT favorited FROM user_topic_prefs WHERE user_id=? AND topic_id=?",
            (user_id, topic_id)
        ).fetchone()
        new_val = 0 if (row and row["favorited"]) else 1
        conn.execute("""
            INSERT INTO user_topic_prefs (user_id, topic_id, favorited)
            VALUES (?,?,?)
            ON CONFLICT(user_id, topic_id) DO UPDATE SET favorited=excluded.favorited
        """, (user_id, topic_id, new_val))
    return bool(new_val)


def set_user_topic_status(user_id: int, topic_id: int, status: str) -> str:
    """Toggle topic status for a user. Returns the new status value."""
    allowed = {"nominated", "passed", ""}
    if status not in allowed:
        status = ""
    with get_db() as conn:
        row = conn.execute(
            "SELECT topic_status FROM user_topic_prefs WHERE user_id=? AND topic_id=?",
            (user_id, topic_id)
        ).fetchone()
        new_val = "" if (row and row["topic_status"] == status) else status
        conn.execute("""
            INSERT INTO user_topic_prefs (user_id, topic_id, topic_status)
            VALUES (?,?,?)
            ON CONFLICT(user_id, topic_id) DO UPDATE SET topic_status=excluded.topic_status
        """, (user_id, topic_id, new_val))
    return new_val


# ── Analytics ──────────────────────────────────────────────────────────────────

def get_analytics_data() -> dict:
    """Aggregate all data needed for the Analytics page."""
    import re
    from collections import Counter

    STOP_WORDS = {
        "the","and","for","with","that","this","from","are","have","been",
        "will","can","may","which","their","into","also","more","other",
        "using","used","use","based","new","high","system","systems",
        "data","technology","technologies","research","development",
        "support","provide","including","such","through","advanced",
        "improved","current","during","these","requirements","required",
        "ability","capabilities","capability","potential","approach",
        "program","programs","phase","topics","topic","sbir","sttr",
        "dod","navy","air","force","army","dla","darpa","oni","socom",
        "need","needs","would","could","should","small","business","company",
    }

    with get_db() as conn:

        # ── Topics by agency ──────────────────────────────────────────────
        by_agency = conn.execute("""
            SELECT COALESCE(agency,'Unknown') as label, COUNT(*) as cnt
            FROM topics
            GROUP BY label ORDER BY cnt DESC LIMIT 15
        """).fetchall()

        # ── Topics by branch/component ────────────────────────────────────
        by_branch = conn.execute("""
            SELECT COALESCE(branch,'Unknown') as label, COUNT(*) as cnt
            FROM topics WHERE branch IS NOT NULL AND branch != ''
            GROUP BY label ORDER BY cnt DESC LIMIT 20
        """).fetchall()

        # ── Topics by year ────────────────────────────────────────────────
        by_year = conn.execute("""
            SELECT COALESCE(solicitation_year,'Unknown') as yr, COUNT(*) as cnt
            FROM topics
            WHERE solicitation_year IS NOT NULL AND solicitation_year != ''
            GROUP BY yr ORDER BY yr ASC
        """).fetchall()

        # ── Topics by week AND branch (top 6 branches) ───────────────────
        top_branches_trend = [r[0] for r in conn.execute("""
            SELECT COALESCE(branch,'Unknown') as b, COUNT(*) as cnt
            FROM topics WHERE branch IS NOT NULL AND branch != ''
            GROUP BY b ORDER BY cnt DESC LIMIT 6
        """).fetchall()]

        trend_rows = conn.execute("""
            SELECT strftime('%Y-W%W', COALESCE(
                       CASE WHEN open_date GLOB '????-??-??*' THEN open_date ELSE NULL END,
                       created_at
                   )) as wk,
                   COALESCE(branch,'Unknown') as br,
                   COUNT(*) as cnt
            FROM topics
            WHERE branch IS NOT NULL AND branch != ''
            GROUP BY wk, br
            HAVING wk IS NOT NULL
            ORDER BY wk ASC
        """).fetchall()

        weeks_sorted = sorted({r[0] for r in trend_rows if r[0] and r[0] != 'Unknown'})
        trend_by_branch = {}
        for br in top_branches_trend:
            trend_by_branch[br] = {wk: 0 for wk in weeks_sorted}
        for r in trend_rows:
            if r[1] in trend_by_branch and r[0] in weeks_sorted:
                trend_by_branch[r[1]][r[0]] = r[2]

        # ── Phase distribution ────────────────────────────────────────────
        by_phase = conn.execute("""
            SELECT COALESCE(phase,'Unknown') as label, COUNT(*) as cnt
            FROM topics GROUP BY label ORDER BY cnt DESC
        """).fetchall()

        # ── Source distribution ───────────────────────────────────────────
        by_source = conn.execute("""
            SELECT COALESCE(source,'Unknown') as label, COUNT(*) as cnt
            FROM topics GROUP BY label ORDER BY cnt DESC
        """).fetchall()

        # ── Nomination/pass rates by agency ───────────────────────────────
        status_rows = conn.execute("""
            SELECT COALESCE(t.agency,'Unknown') as ag,
                   utp.topic_status,
                   COUNT(*) as cnt
            FROM user_topic_prefs utp
            JOIN topics t ON utp.topic_id = t.id
            WHERE utp.topic_status IN ('nominated','passed')
            GROUP BY ag, utp.topic_status
            ORDER BY ag
        """).fetchall()

        status_agencies = sorted({r[0] for r in status_rows})
        status_data = {
            "nominated": {ag: 0 for ag in status_agencies},
            "passed":    {ag: 0 for ag in status_agencies},
        }
        for r in status_rows:
            status_data[r[1]][r[0]] = r[2]

        # ── Tech area frequency (tags, not word-split) ────────────────────
        tech_area_rows = conn.execute("""
            SELECT tech_areas FROM topics
            WHERE tech_areas IS NOT NULL
              AND tech_areas != ''
              AND LOWER(TRIM(tech_areas)) NOT IN ('none','n/a','na','-','null')
        """).fetchall()

        tech_counter = Counter()
        for row in tech_area_rows:
            parts = re.split(r'[,;]', row[0])
            for part in parts:
                part = part.strip()
                if part and part.lower() not in ('none', 'n/a', 'na', '-', 'null', ''):
                    tech_counter[part] += 1

        top_keywords = tech_counter.most_common(30)

        # ── Summary stats ─────────────────────────────────────────────────
        total_topics = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        total_agencies = conn.execute(
            "SELECT COUNT(DISTINCT agency) FROM topics WHERE agency IS NOT NULL"
        ).fetchone()[0]
        year_range = conn.execute("""
            SELECT MIN(solicitation_year), MAX(solicitation_year)
            FROM topics WHERE solicitation_year IS NOT NULL AND solicitation_year != ''
        """).fetchone()

    return {
        "total_topics":    total_topics,
        "total_agencies":  total_agencies,
        "year_min":        year_range[0] or "—",
        "year_max":        year_range[1] or "—",
        "by_agency":       [dict(r) for r in by_agency],
        "by_branch":       [dict(r) for r in by_branch],
        "by_year":         [dict(r) for r in by_year],
        "by_phase":        [dict(r) for r in by_phase],
        "by_source":       [dict(r) for r in by_source],
        "trend_periods":   weeks_sorted,
        "trend_branches":  top_branches_trend,
        "trend_by_branch": trend_by_branch,
        "top_keywords":    top_keywords,
        "status_agencies": status_agencies,
        "status_data":     status_data,
    }


# ── Audit Log ──────────────────────────────────────────────────────────────────

def write_audit_log(action_type: str, username: str = None, user_id: int = None,
                    detail: str = None, ip_address: str = None):
    """Write a single audit log entry."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO audit_log (action_type, username, user_id, detail, ip_address)
               VALUES (?,?,?,?,?)""",
            (action_type, username, user_id, detail, ip_address)
        )


def get_audit_log(page: int = 1, per_page: int = 100,
                  action_type: str = None, username: str = None) -> dict:
    """Return paginated audit log entries, optionally filtered."""
    sql    = "SELECT * FROM audit_log WHERE 1=1"
    c_sql  = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
    params = []
    if action_type:
        sql   += " AND action_type = ?"
        c_sql += " AND action_type = ?"
        params.append(action_type)
    if username:
        sql   += " AND username LIKE ?"
        c_sql += " AND username LIKE ?"
        params.append(f"%{username}%")
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * per_page
    with get_db() as conn:
        total = conn.execute(c_sql, params).fetchone()[0]
        rows  = conn.execute(sql, params + [per_page, offset]).fetchall()
    return {
        "rows":      [dict(r) for r in rows],
        "total":     total,
        "page":      page,
        "per_page":  per_page,
        "pages":     max(1, (total + per_page - 1) // per_page),
    }


def get_audit_log_csv() -> list:
    """Return all audit log rows for CSV export."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── App Settings ───────────────────────────────────────────────────────────────

def get_app_setting(key: str, default: str = None) -> str | None:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_app_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )


# ── Account Lockout ────────────────────────────────────────────────────────────

def increment_failed_login(user_id: int, lockout_threshold: int) -> bool:
    """Increment failed login counter. Locks account if threshold reached.
    Returns True if the account was just locked."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts = COALESCE(failed_login_attempts,0)+1 WHERE id=?",
            (user_id,)
        )
        row = conn.execute(
            "SELECT failed_login_attempts FROM users WHERE id=?", (user_id,)
        ).fetchone()
        attempts = row[0] if row else 0
        if attempts >= lockout_threshold:
            conn.execute(
                "UPDATE users SET locked_at=? WHERE id=? AND locked_at IS NULL",
                (now, user_id)
            )
            # Check if we just set it
            locked = conn.execute(
                "SELECT locked_at FROM users WHERE id=?", (user_id,)
            ).fetchone()
            return locked and locked[0] == now
    return False


def reset_failed_login(user_id: int):
    """Reset failed login counter after successful login."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts=0, locked_at=NULL WHERE id=?",
            (user_id,)
        )


def unlock_user(user_id: int):
    """Admin action: clear lockout and reset failed counter."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts=0, locked_at=NULL WHERE id=?",
            (user_id,)
        )


def record_login(user_id: int, ip_address: str):
    """Update last_login_at and last_login_ip on successful login."""
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login_at=?, last_login_ip=? WHERE id=?",
            (now, ip_address, user_id)
        )


# ── DB Stats (for admin panel) ─────────────────────────────────────────────────

def get_db_stats() -> dict:
    """Return high-level database statistics for the admin panel."""
    stats = {}
    # File size
    try:
        stats["db_size_bytes"] = os.path.getsize(DB_PATH)
        stats["db_size_mb"]    = round(stats["db_size_bytes"] / (1024 * 1024), 2)
    except Exception:
        stats["db_size_bytes"] = 0
        stats["db_size_mb"]    = 0

    with get_db() as conn:
        stats["topic_count"]   = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        stats["user_count"]    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        stats["project_count"] = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        stats["audit_count"]   = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
        stats["active_users"]  = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0]
        stats["locked_users"]  = conn.execute(
            "SELECT COUNT(*) FROM users WHERE locked_at IS NOT NULL").fetchone()[0]

        last_ingest = conn.execute(
            "SELECT source, finished_at FROM ingest_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        stats["last_ingest_source"] = last_ingest[0] if last_ingest else None
        stats["last_ingest_at"]     = last_ingest[1] if last_ingest else None

        stats["ingest_log_count"] = conn.execute(
            "SELECT COUNT(*) FROM ingest_log").fetchone()[0]

        # Recent logins
        stats["recent_logins"] = [dict(r) for r in conn.execute(
            """SELECT username, last_login_at, last_login_ip
               FROM users WHERE last_login_at IS NOT NULL
               ORDER BY last_login_at DESC LIMIT 5"""
        ).fetchall()]

        # Login failure count in last 24 hours
        stats["failed_logins_24h"] = conn.execute(
            """SELECT COUNT(*) FROM audit_log
               WHERE action_type='LOGIN_FAILED'
               AND timestamp >= datetime('now','-1 day')"""
        ).fetchone()[0]

    return stats


def get_distinct(table: str, column: str) -> list:
    allowed = {
        "solicitations": ["agency", "branch", "phase", "program", "source", "status"],
        "awards": ["agency", "branch", "phase", "program", "source", "award_year"],
        "topics": ["agency", "branch", "phase", "source"],
    }
    if table not in allowed or column not in allowed[table]:
        return []
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column}"
        ).fetchall()
    return [r[0] for r in rows]


# ── Project Sharing & Collaboration ──────────────────────────────────────────

def set_project_owner(project_id: int, user_id: int) -> bool:
    """Set the owner of a project."""
    with get_db() as conn:
        conn.execute("UPDATE projects SET owner_id = ?, is_shared = 1 WHERE id = ?",
                    (user_id, project_id))
    return True


def get_project_member_role(project_id: int, user_id: int) -> str | None:
    """Get a user's role in a project. Returns 'owner', 'editor', 'viewer', or None."""
    with get_db() as conn:
        # Check if owner
        project = conn.execute("SELECT owner_id FROM projects WHERE id = ?",
                              (project_id,)).fetchone()
        if project and project['owner_id'] == user_id:
            return 'owner'

        # Check membership
        member = conn.execute(
            "SELECT role FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        ).fetchone()
        return member['role'] if member else None


def add_project_member(project_id: int, user_id: int, role: str = 'viewer',
                       added_by_user_id: int = None) -> bool:
    """Add a user to a project with a specific role."""
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO project_members
               (project_id, user_id, role, added_by_user_id)
               VALUES (?, ?, ?, ?)""",
            (project_id, user_id, role, added_by_user_id)
        )
        conn.execute("UPDATE projects SET is_shared = 1 WHERE id = ?", (project_id,))
    return True


def remove_project_member(project_id: int, user_id: int) -> bool:
    """Remove a user from a project."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM project_members WHERE project_id = ? AND user_id = ?",
            (project_id, user_id)
        )
    return True


def update_project_member_role(project_id: int, user_id: int, role: str) -> bool:
    """Update a project member's role."""
    with get_db() as conn:
        conn.execute(
            "UPDATE project_members SET role = ? WHERE project_id = ? AND user_id = ?",
            (role, project_id, user_id)
        )
    return True


def get_project_members(project_id: int) -> list:
    """Get all members of a project with their roles."""
    with get_db() as conn:
        members = conn.execute("""
            SELECT
                pm.id,
                pm.user_id,
                pm.role,
                pm.added_at,
                u.username,
                u.email
            FROM project_members pm
            JOIN users u ON pm.user_id = u.id
            WHERE pm.project_id = ?
            ORDER BY pm.added_at
        """, (project_id,)).fetchall()
    return [dict(m) for m in members]


def get_user_accessible_projects(user_id: int) -> list:
    """Get all projects a user can access (owned or member of)."""
    with get_db() as conn:
        projects = conn.execute("""
            SELECT DISTINCT p.*
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            WHERE p.owner_id = ? OR pm.user_id = ?
            ORDER BY p.updated_at DESC
        """, (user_id, user_id)).fetchall()
    return [dict(p) for p in projects]


# ── Project Comments ────────────────────────────────────────────────────────

def add_project_comment(project_id: int, user_id: int, comment_text: str,
                       file_id: int = None, mentions: str = None) -> int:
    """Add a comment to a project. Returns comment ID."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO project_comments
            (project_id, file_id, user_id, comment_text, mentions)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, file_id, user_id, comment_text, mentions))
        comment_id = cursor.lastrowid
    return comment_id


def get_project_comments(project_id: int, file_id: int = None) -> list:
    """Get comments on a project or specific file."""
    with get_db() as conn:
        if file_id:
            comments = conn.execute("""
                SELECT
                    pc.id, pc.project_id, pc.file_id, pc.user_id,
                    pc.comment_text, pc.mentions, pc.created_at, pc.updated_at,
                    u.username, u.email
                FROM project_comments pc
                JOIN users u ON pc.user_id = u.id
                WHERE pc.project_id = ? AND pc.file_id = ? AND pc.is_deleted = 0
                ORDER BY pc.created_at DESC
            """, (project_id, file_id)).fetchall()
        else:
            comments = conn.execute("""
                SELECT
                    pc.id, pc.project_id, pc.file_id, pc.user_id,
                    pc.comment_text, pc.mentions, pc.created_at, pc.updated_at,
                    u.username, u.email
                FROM project_comments pc
                JOIN users u ON pc.user_id = u.id
                WHERE pc.project_id = ? AND pc.is_deleted = 0
                ORDER BY pc.created_at DESC
            """, (project_id,)).fetchall()
    return [dict(c) for c in comments]


def delete_comment(comment_id: int) -> bool:
    """Soft-delete a comment."""
    with get_db() as conn:
        conn.execute("UPDATE project_comments SET is_deleted = 1 WHERE id = ?",
                    (comment_id,))
    return True


def update_comment(comment_id: int, comment_text: str) -> bool:
    """Update a comment."""
    with get_db() as conn:
        conn.execute(
            "UPDATE project_comments SET comment_text = ?, updated_at = datetime('now') WHERE id = ?",
            (comment_text, comment_id)
        )
    return True


# ── Notifications ───────────────────────────────────────────────────────────

def create_notification(user_id: int, ntype: str, project_id: int = None,
                       actor_user_id: int = None, message: str = None) -> int:
    """Create a notification for a user. Returns notification ID."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO notifications
            (user_id, type, project_id, actor_user_id, message)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, ntype, project_id, actor_user_id, message))
        notif_id = cursor.lastrowid
    return notif_id


def get_user_notifications(user_id: int, unread_only: bool = False) -> list:
    """Get notifications for a user."""
    with get_db() as conn:
        query = """
            SELECT
                n.id, n.user_id, n.project_id, n.type, n.actor_user_id,
                n.message, n.is_read, n.created_at,
                u.username, u.email, p.name as project_name
            FROM notifications n
            LEFT JOIN users u ON n.actor_user_id = u.id
            LEFT JOIN projects p ON n.project_id = p.id
            WHERE n.user_id = ?
        """
        params = [user_id]
        if unread_only:
            query += " AND n.is_read = 0"
        query += " ORDER BY n.created_at DESC LIMIT 50"

        notifs = conn.execute(query, params).fetchall()
    return [dict(n) for n in notifs]


def mark_notification_read(notification_id: int) -> bool:
    """Mark a notification as read."""
    with get_db() as conn:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?",
                    (notification_id,))
    return True


def mark_all_notifications_read(user_id: int) -> bool:
    """Mark all notifications as read for a user."""
    with get_db() as conn:
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?",
                    (user_id,))
    return True


def get_unread_notification_count(user_id: int) -> int:
    """Get count of unread notifications for a user."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        ).fetchone()
    return row['cnt'] if row else 0


# ── Shared Documents ────────────────────────────────────────────────────────

def add_shared_document(project_id: int, doc_type: str, external_url: str,
                       external_id: str = None, title: str = None,
                       added_by_user_id: int = None) -> int:
    """Link a shared document (SharePoint/Drive) to a project. Returns document ID."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO shared_documents
            (project_id, doc_type, external_url, external_id, title, added_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, doc_type, external_url, external_id, title, added_by_user_id))
        doc_id = cursor.lastrowid
    return doc_id


def get_shared_documents(project_id: int) -> list:
    """Get all shared documents linked to a project."""
    with get_db() as conn:
        docs = conn.execute("""
            SELECT
                sd.id, sd.project_id, sd.doc_type, sd.external_url,
                sd.external_id, sd.title, sd.added_by_user_id, sd.added_at,
                u.username
            FROM shared_documents sd
            LEFT JOIN users u ON sd.added_by_user_id = u.id
            WHERE sd.project_id = ?
            ORDER BY sd.added_at DESC
        """, (project_id,)).fetchall()
    return [dict(d) for d in docs]


def remove_shared_document(document_id: int) -> bool:
    """Remove a shared document link from a project."""
    with get_db() as conn:
        conn.execute("DELETE FROM shared_documents WHERE id = ?", (document_id,))
    return True


# ── Helper Functions ────────────────────────────────────────────────────────────

def get_project_comment(comment_id: int) -> dict | None:
    """Get a single comment by ID."""
    with get_db() as conn:
        comment = conn.execute(
            "SELECT * FROM project_comments WHERE id = ?",
            (comment_id,)
        ).fetchone()
    return dict(comment) if comment else None




def log_activity(project_id: int, event_type: str, description: str = None) -> bool:
    """Log activity to project activity log."""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO project_activity_log (project_id, event_type, description)
                VALUES (?, ?, ?)
            """, (project_id, event_type, description))
        return True
    except Exception as e:
        print(f"[DB] Error logging activity: {e}")
        return False


# ── Capture Plans ────────────────────────────────────────────────────────────────

def create_capture_plan(capture_name: str, capture_lead_id: int, created_by_user_id: int,
                       solicitation_id: int = None, customer_name: str = None,
                       customer_website: str = None, estimated_release_date: str = None,
                       proposal_due_date: str = None, target_contract_value: float = None,
                       stage: str = 'pre-release', confidence_level: str = 'medium',
                       win_probability: int = 50) -> int:
    """Create a new capture plan."""
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO capture_plans
            (capture_name, capture_lead_id, created_by_user_id, solicitation_id,
             customer_name, customer_website, estimated_release_date, proposal_due_date,
             target_contract_value, stage, confidence_level, win_probability)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (capture_name, capture_lead_id, created_by_user_id, solicitation_id,
              customer_name, customer_website, estimated_release_date, proposal_due_date,
              target_contract_value, stage, confidence_level, win_probability))
        return cur.lastrowid


def get_capture_plan(plan_id: int) -> dict | None:
    """Get a capture plan by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM capture_plans WHERE id = ?", (plan_id,)).fetchone()
    return dict(row) if row else None


def get_capture_plans_by_user(user_id: int, include_archived: bool = False) -> list:
    """Get all capture plans accessible to a user (led or has access)."""
    with get_db() as conn:
        query = """
            SELECT DISTINCT cp.* FROM capture_plans cp
            LEFT JOIN capture_plan_access cpa ON cp.id = cpa.capture_plan_id
            WHERE (cp.capture_lead_id = ? OR cpa.user_id = ?)
        """
        params = [user_id, user_id]

        if not include_archived:
            query += " AND cp.is_archived = 0"

        query += " ORDER BY cp.updated_at DESC"

        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_capture_plans_by_stage(stage: str, user_id: int = None) -> list:
    """Get capture plans by stage, optionally filtered by user."""
    with get_db() as conn:
        if user_id:
            query = """
                SELECT DISTINCT cp.* FROM capture_plans cp
                LEFT JOIN capture_plan_access cpa ON cp.id = cpa.capture_plan_id
                WHERE cp.stage = ? AND (cp.capture_lead_id = ? OR cpa.user_id = ?)
                AND cp.is_archived = 0
                ORDER BY cp.updated_at DESC
            """
            rows = conn.execute(query, (stage, user_id, user_id)).fetchall()
        else:
            query = """
                SELECT * FROM capture_plans
                WHERE stage = ? AND is_archived = 0
                ORDER BY updated_at DESC
            """
            rows = conn.execute(query, (stage,)).fetchall()
    return [dict(r) for r in rows]


def update_capture_plan(plan_id: int, **kwargs) -> bool:
    """Update capture plan fields."""
    allowed_fields = {
        'capture_name', 'customer_name', 'customer_website', 'estimated_release_date',
        'proposal_due_date', 'target_contract_value', 'stage', 'confidence_level',
        'win_probability', 'is_archived'
    }

    fields_to_update = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not fields_to_update:
        return False

    fields_to_update['updated_at'] = 'datetime("now")'

    with get_db() as conn:
        set_clause = ', '.join([f"{k} = ?" if k != 'updated_at' else f"{k} = {v}"
                                for k, v in fields_to_update.items()])
        values = [v for k, v in fields_to_update.items() if k != 'updated_at']
        values.append(plan_id)

        conn.execute(f"UPDATE capture_plans SET {set_clause} WHERE id = ?", values)

    return True


def add_capture_plan_access(plan_id: int, user_id: int, access_level: str = 'viewer') -> bool:
    """Add user access to a capture plan."""
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO capture_plan_access (capture_plan_id, user_id, access_level)
                VALUES (?, ?, ?)
            """, (plan_id, user_id, access_level))
            return True
        except Exception:
            # Primary key violation means user already has access
            return False


def remove_capture_plan_access(plan_id: int, user_id: int) -> bool:
    """Remove user access from a capture plan."""
    with get_db() as conn:
        conn.execute("""
            DELETE FROM capture_plan_access
            WHERE capture_plan_id = ? AND user_id = ?
        """, (plan_id, user_id))
    return True


def get_capture_plan_access(plan_id: int, user_id: int) -> dict | None:
    """Get access record for a user on a capture plan."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM capture_plan_access
            WHERE capture_plan_id = ? AND user_id = ?
        """, (plan_id, user_id)).fetchone()
    return dict(row) if row else None


def list_capture_plan_members(plan_id: int) -> list:
    """Get all users with access to a capture plan."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.id, u.username, u.email, cpa.access_level, cpa.added_at
            FROM capture_plan_access cpa
            JOIN users u ON cpa.user_id = u.id
            WHERE cpa.capture_plan_id = ?
            ORDER BY cpa.added_at DESC
        """, (plan_id,)).fetchall()
    return [dict(r) for r in rows]


def link_project_to_capture_plan(project_id: int, capture_plan_id: int) -> bool:
    """Link a project to a capture plan."""
    with get_db() as conn:
        conn.execute("""
            UPDATE projects SET capture_plan_id = ? WHERE id = ?
        """, (capture_plan_id, project_id))
    return True


def get_projects_by_capture_plan(capture_plan_id: int) -> list:
    """Get all projects linked to a capture plan."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM projects WHERE capture_plan_id = ? ORDER BY updated_at DESC
        """, (capture_plan_id,)).fetchall()
    return [dict(r) for r in rows]


# ── Project Team Management ────────────────────────────────────────────────────

def add_team_member(project_id: int, user_id: int, role: str = 'team-member',
                   added_by_user_id: int = None) -> bool:
    """Add a user to a project team."""
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO project_team_members
                (project_id, user_id, role, status, added_by_user_id)
                VALUES (?, ?, ?, 'active', ?)
            """, (project_id, user_id, role, added_by_user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error adding team member: {e}")
            return False


def remove_team_member(project_id: int, user_id: int) -> bool:
    """Remove a user from a project team."""
    with get_db() as conn:
        try:
            conn.execute(
                "DELETE FROM project_team_members WHERE project_id = ? AND user_id = ?",
                (project_id, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error removing team member: {e}")
            return False


def get_project_team_members(project_id: int) -> list:
    """Get all active team members for a project."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ptm.*, u.username, u.email
            FROM project_team_members ptm
            JOIN users u ON ptm.user_id = u.id
            WHERE ptm.project_id = ? AND ptm.status = 'active'
            ORDER BY ptm.added_at DESC
        """, (project_id,)).fetchall()
    return [dict(r) for r in rows]


def is_project_team_member(project_id: int, user_id: int) -> bool:
    """Check if a user is an active member of a project team."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT 1 FROM project_team_members
            WHERE project_id = ? AND user_id = ? AND status = 'active'
        """, (project_id, user_id)).fetchone()
    return row is not None


def get_team_member_role(project_id: int, user_id: int) -> str | None:
    """Get the role of a team member."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT role FROM project_team_members
            WHERE project_id = ? AND user_id = ? AND status = 'active'
        """, (project_id, user_id)).fetchone()
    return row['role'] if row else None


def update_team_member_role(project_id: int, user_id: int, role: str) -> bool:
    """Update a team member's role."""
    with get_db() as conn:
        try:
            conn.execute("""
                UPDATE project_team_members
                SET role = ? WHERE project_id = ? AND user_id = ? AND status = 'active'
            """, (role, project_id, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error updating team member role: {e}")
            return False


def send_team_invitation(project_id: int, invited_user_id: int,
                        invited_by_user_id: int) -> bool:
    """Send a team invitation to a user."""
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT INTO project_team_invitations
                (project_id, invited_user_id, invited_by_user_id)
                VALUES (?, ?, ?)
            """, (project_id, invited_user_id, invited_by_user_id))
            conn.commit()

            # Create notification
            create_notification(
                user_id=invited_user_id,
                ntype='team_invitation',
                project_id=project_id,
                actor_user_id=invited_by_user_id,
                message=f"You've been invited to join a project team"
            )
            return True
        except Exception as e:
            print(f"[DB] Error sending invitation: {e}")
            return False


def accept_team_invitation(project_id: int, user_id: int) -> bool:
    """Accept a team invitation and add user to team."""
    with get_db() as conn:
        try:
            # Check invitation exists
            invitation = conn.execute("""
                SELECT * FROM project_team_invitations
                WHERE project_id = ? AND invited_user_id = ? AND status = 'pending'
            """, (project_id, user_id)).fetchone()

            if not invitation:
                return False

            # Add to team
            conn.execute("""
                INSERT INTO project_team_members
                (project_id, user_id, role, status)
                VALUES (?, ?, 'team-member', 'active')
            """, (project_id, user_id))

            # Mark invitation as accepted
            conn.execute("""
                UPDATE project_team_invitations
                SET status = 'accepted', responded_at = datetime('now')
                WHERE project_id = ? AND invited_user_id = ?
            """, (project_id, user_id))

            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error accepting invitation: {e}")
            return False


def decline_team_invitation(project_id: int, user_id: int) -> bool:
    """Decline a team invitation."""
    with get_db() as conn:
        try:
            conn.execute("""
                UPDATE project_team_invitations
                SET status = 'declined', responded_at = datetime('now')
                WHERE project_id = ? AND invited_user_id = ?
            """, (project_id, user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error declining invitation: {e}")
            return False


def get_pending_invitations(user_id: int) -> list:
    """Get all pending team invitations for a user."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT pti.*, p.name as project_name, u.username as invited_by_username
            FROM project_team_invitations pti
            JOIN projects p ON pti.project_id = p.id
            JOIN users u ON pti.invited_by_user_id = u.id
            WHERE pti.invited_user_id = ? AND pti.status = 'pending'
            ORDER BY pti.invited_at DESC
        """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_project_invitations(project_id: int, status: str = 'pending') -> list:
    """Get all invitations for a project."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT pti.*, u.username, u.email
            FROM project_team_invitations pti
            JOIN users u ON pti.invited_user_id = u.id
            WHERE pti.project_id = ? AND pti.status = ?
            ORDER BY pti.invited_at DESC
        """, (project_id, status)).fetchall()
    return [dict(r) for r in rows]


# ── Proposal Scoring & Ranking System ──────────────────────────────────────

def create_scoring_criteria(capture_plan_id: int, name: str, 
                           description: str = None, weight: float = 1.0,
                           max_score: float = 10.0, guidance: str = None,
                           created_by_user_id: int = None) -> int | None:
    """Create a new scoring criterion for a capture plan."""
    with get_db() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO scoring_criteria 
                (capture_plan_id, name, description, weight, max_score, scoring_guidance, created_by_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (capture_plan_id, name, description, weight, max_score, guidance, created_by_user_id))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[DB] Error creating scoring criterion: {e}")
            return None


def get_scoring_criteria(capture_plan_id: int, active_only: bool = True) -> list:
    """Get all scoring criteria for a capture plan."""
    with get_db() as conn:
        query = "SELECT * FROM scoring_criteria WHERE capture_plan_id = ?"
        params = [capture_plan_id]
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY display_order, created_at"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def update_scoring_criteria(criterion_id: int, **updates) -> bool:
    """Update a scoring criterion."""
    allowed_fields = {'name', 'description', 'weight', 'max_score', 'scoring_guidance', 'is_active', 'display_order'}
    updates = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    with get_db() as conn:
        try:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [criterion_id]
            conn.execute(f"UPDATE scoring_criteria SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error updating criterion: {e}")
            return False


def delete_scoring_criteria(criterion_id: int) -> bool:
    """Delete a scoring criterion (cascades to scores and rankings)."""
    with get_db() as conn:
        try:
            conn.execute("DELETE FROM scoring_criteria WHERE id = ?", (criterion_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error deleting criterion: {e}")
            return False


def score_proposal(project_id: int, criterion_id: int, score_value: float,
                   comments: str = None, scored_by_user_id: int = None) -> bool:
    """Score a proposal against a criterion."""
    with get_db() as conn:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO proposal_scores
                (project_id, scoring_criterion_id, score_value, comments, scored_by_user_id, scored_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (project_id, criterion_id, score_value, comments, scored_by_user_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error scoring proposal: {e}")
            return False


def get_proposal_scores(project_id: int) -> dict:
    """Get all scores for a proposal."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ps.*, sc.name, sc.max_score, sc.weight, u.username as scored_by_username
            FROM proposal_scores ps
            JOIN scoring_criteria sc ON ps.scoring_criterion_id = sc.id
            JOIN users u ON ps.scored_by_user_id = u.id
            WHERE ps.project_id = ?
            ORDER BY sc.display_order
        """, (project_id,)).fetchall()
    
    scores_list = [dict(r) for r in rows]
    
    # Check if all criteria are scored
    if scores_list:
        capture_plan_id = conn.execute("""
            SELECT cp.id FROM capture_plans cp
            JOIN scoring_criteria sc ON sc.capture_plan_id = cp.id
            WHERE sc.id = (SELECT scoring_criterion_id FROM proposal_scores WHERE project_id = ? LIMIT 1)
        """, (project_id,)).fetchone()
        
        if capture_plan_id:
            all_criteria = get_scoring_criteria(capture_plan_id[0])
            scored_count = len(scores_list)
            total_count = len(all_criteria)
            complete = scored_count == total_count
        else:
            complete = False
    else:
        complete = False
    
    return {
        'scores': scores_list,
        'complete': complete,
        'count': len(scores_list)
    }


def get_proposal_score(project_id: int, criterion_id: int) -> dict | None:
    """Get a specific score."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT ps.*, sc.name, sc.max_score, sc.weight, u.username as scored_by_username
            FROM proposal_scores ps
            JOIN scoring_criteria sc ON ps.scoring_criterion_id = sc.id
            JOIN users u ON ps.scored_by_user_id = u.id
            WHERE ps.project_id = ? AND ps.scoring_criterion_id = ?
        """, (project_id, criterion_id)).fetchone()
    return dict(row) if row else None


def delete_proposal_score(project_id: int, criterion_id: int) -> bool:
    """Delete a score."""
    with get_db() as conn:
        try:
            conn.execute("""
                DELETE FROM proposal_scores
                WHERE project_id = ? AND scoring_criterion_id = ?
            """, (project_id, criterion_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error deleting score: {e}")
            return False


def calculate_final_score(project_id: int) -> float | None:
    """Calculate final weighted score for a proposal."""
    with get_db() as conn:
        result = conn.execute("""
            SELECT 
                SUM(ps.score_value * sc.weight) / SUM(sc.weight) as final_score
            FROM proposal_scores ps
            JOIN scoring_criteria sc ON ps.scoring_criterion_id = sc.id
            WHERE ps.project_id = ? AND sc.is_active = 1
        """, (project_id,)).fetchone()
    
    return result['final_score'] if result and result['final_score'] is not None else None


def recalculate_rankings(capture_plan_id: int) -> bool:
    """Recalculate all rankings for a capture plan."""
    with get_db() as conn:
        try:
            # Get all projects in this capture plan with their final scores
            projects = conn.execute("""
                SELECT DISTINCT p.id, p.name
                FROM projects p
                JOIN proposal_scores ps ON p.id = ps.project_id
                JOIN scoring_criteria sc ON ps.scoring_criterion_id = sc.id
                WHERE sc.capture_plan_id = ?
                GROUP BY p.id
            """, (capture_plan_id,)).fetchall()
            
            scores_data = []
            for project_row in projects:
                project_id = project_row['id']
                final_score = calculate_final_score(project_id)
                
                if final_score is not None:
                    # Check if all criteria are scored
                    all_criteria = get_scoring_criteria(capture_plan_id)
                    scored = get_proposal_scores(project_id)
                    complete = scored['complete']
                    
                    scores_data.append({
                        'project_id': project_id,
                        'final_score': final_score,
                        'scores_complete': 1 if complete else 0,
                        'last_scored_at': datetime.now().isoformat()
                    })
            
            # Sort by score descending
            scores_data.sort(key=lambda x: x['final_score'], reverse=True)
            
            # Clear existing rankings
            conn.execute("DELETE FROM proposal_rankings WHERE capture_plan_id = ?", (capture_plan_id,))
            
            # Insert new rankings
            total = len(scores_data)
            for idx, score_data in enumerate(scores_data):
                rank = idx + 1
                percentile = ((total - rank) / total * 100) if total > 0 else 0
                
                conn.execute("""
                    INSERT INTO proposal_rankings
                    (capture_plan_id, project_id, final_score, rank, percentile, scores_complete, last_scored_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (capture_plan_id, score_data['project_id'], score_data['final_score'], 
                      rank, percentile, score_data['scores_complete'], score_data['last_scored_at']))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error recalculating rankings: {e}")
            return False


def get_capture_plan_rankings(capture_plan_id: int, sort_by: str = 'rank') -> list:
    """Get ranked list of proposals for a capture plan."""
    with get_db() as conn:
        query = """
            SELECT pr.*, p.name as project_name, p.description
            FROM proposal_rankings pr
            JOIN projects p ON pr.project_id = p.id
            WHERE pr.capture_plan_id = ?
        """
        
        if sort_by == 'score':
            query += " ORDER BY pr.final_score DESC"
        elif sort_by == 'date':
            query += " ORDER BY p.created_at DESC"
        elif sort_by == 'name':
            query += " ORDER BY p.name ASC"
        else:  # default rank
            query += " ORDER BY pr.rank ASC"
        
        rows = conn.execute(query, (capture_plan_id,)).fetchall()
    return [dict(r) for r in rows]


def get_proposal_ranking(project_id: int) -> dict | None:
    """Get ranking info for a single proposal."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT pr.*, p.name as project_name
            FROM proposal_rankings pr
            JOIN projects p ON pr.project_id = p.id
            WHERE pr.project_id = ?
        """, (project_id,)).fetchone()
    return dict(row) if row else None


def get_scoring_progress(capture_plan_id: int) -> dict:
    """Get scoring progress statistics."""
    with get_db() as conn:
        # Get all projects linked to this capture plan
        all_projects = conn.execute("""
            SELECT DISTINCT p.id
            FROM projects p
            WHERE EXISTS (
                SELECT 1 FROM scoring_criteria sc
                WHERE sc.capture_plan_id = ?
            )
        """, (capture_plan_id,)).fetchall()
        
        total_proposals = len(all_projects)
        
        # Get scoring stats
        stats = conn.execute("""
            SELECT 
                COUNT(DISTINCT CASE WHEN pr.scores_complete = 1 THEN pr.project_id END) as fully_scored,
                COUNT(DISTINCT CASE WHEN pr.scores_complete = 0 AND pr.final_score IS NOT NULL THEN pr.project_id END) as partially_scored,
                AVG(pr.final_score) as average_score,
                MAX(pr.final_score) as high_score,
                MIN(pr.final_score) as low_score
            FROM proposal_rankings pr
            WHERE pr.capture_plan_id = ?
        """, (capture_plan_id,)).fetchone()
        
        fully_scored = stats['fully_scored'] or 0
        partially_scored = stats['partially_scored'] or 0
        unscored = total_proposals - fully_scored - partially_scored
        
        return {
            'total_proposals': total_proposals,
            'fully_scored': fully_scored,
            'partially_scored': partially_scored,
            'unscored': unscored,
            'average_score': stats['average_score'] or 0,
            'high_score': stats['high_score'] or 0,
            'low_score': stats['low_score'] or 0
        }


def create_scoring_template(name: str, description: str = None,
                           criteria: list = None,
                           is_default: bool = False,
                           created_by_user_id: int = None) -> int | None:
    """Create a scoring template."""
    with get_db() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO scoring_templates (name, description, is_default, created_by_user_id)
                VALUES (?, ?, ?, ?)
            """, (name, description, 1 if is_default else 0, created_by_user_id))
            template_id = cursor.lastrowid
            
            # Add criteria if provided
            if criteria:
                for idx, crit in enumerate(criteria):
                    conn.execute("""
                        INSERT INTO scoring_template_criteria
                        (template_id, name, description, weight, max_score, scoring_guidance, display_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (template_id, crit.get('name'), crit.get('description'),
                          crit.get('weight', 1.0), crit.get('max_score', 10.0),
                          crit.get('guidance'), idx))
            
            conn.commit()
            return template_id
        except Exception as e:
            print(f"[DB] Error creating template: {e}")
            return None


def get_scoring_templates() -> list:
    """Get all available scoring templates."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT st.*, COUNT(stc.id) as criteria_count
            FROM scoring_templates st
            LEFT JOIN scoring_template_criteria stc ON st.id = stc.template_id
            GROUP BY st.id
            ORDER BY st.is_default DESC, st.name
        """).fetchall()
    return [dict(r) for r in rows]


def apply_template_to_capture_plan(template_id: int, capture_plan_id: int) -> bool:
    """Apply a template's criteria to a capture plan."""
    with get_db() as conn:
        try:
            # Get template criteria
            template_criteria = conn.execute("""
                SELECT * FROM scoring_template_criteria
                WHERE template_id = ?
                ORDER BY display_order
            """, (template_id,)).fetchall()
            
            # Add each criterion to the capture plan
            for idx, crit in enumerate(template_criteria):
                conn.execute("""
                    INSERT INTO scoring_criteria
                    (capture_plan_id, name, description, weight, max_score, scoring_guidance, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (capture_plan_id, crit['name'], crit['description'],
                      crit['weight'], crit['max_score'], crit['scoring_guidance'], idx))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[DB] Error applying template: {e}")
            return False


# ── Task Management ────────────────────────────────────────────────────────────

def create_task(data: dict) -> int | None:
    """Create a new task. Returns the new task id."""
    with get_db() as conn:
        cur = conn.execute("""
            INSERT INTO tasks
                (title, description, project_id, deliverable,
                 created_by_id, assigned_to_id,
                 start_date, end_date, expire_date,
                 status, priority, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
        """, (
            data.get("title"), data.get("description"),
            data.get("project_id"), data.get("deliverable"),
            data.get("created_by_id"), data.get("assigned_to_id") or None,
            data.get("start_date") or None, data.get("end_date") or None,
            data.get("expire_date") or None,
            data.get("status", "active"), data.get("priority", "normal"),
        ))
        return cur.lastrowid


def get_tasks(user_id=None, assigned_to_id=None, project_id=None,
              status=None, include_expired=True, limit=200) -> list:
    """Return tasks with creator and assignee names."""
    sql = """
        SELECT t.*,
               u_c.username AS creator_name,
               u_a.username AS assignee_name,
               p.name       AS project_name,
               CASE
                 WHEN t.status NOT IN ('done','expired')
                      AND t.expire_date IS NOT NULL
                      AND t.expire_date < date('now') THEN 'expired'
                 WHEN t.status NOT IN ('done','expired')
                      AND t.end_date IS NOT NULL
                      AND t.end_date < date('now')   THEN 'overdue'
                 ELSE t.status
               END AS computed_status
        FROM tasks t
        LEFT JOIN users   u_c ON t.created_by_id  = u_c.id
        LEFT JOIN users   u_a ON t.assigned_to_id = u_a.id
        LEFT JOIN projects p  ON t.project_id     = p.id
        WHERE 1=1
    """
    params = []
    if user_id is not None:
        sql += " AND (t.created_by_id = ? OR t.assigned_to_id = ?)"
        params += [user_id, user_id]
    if assigned_to_id is not None:
        sql += " AND t.assigned_to_id = ?"
        params.append(assigned_to_id)
    if project_id is not None:
        sql += " AND t.project_id = ?"
        params.append(project_id)
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    if not include_expired:
        sql += " AND t.status != 'expired'"
    sql += " ORDER BY t.end_date IS NULL, t.end_date ASC, t.created_at DESC LIMIT ?"
    params.append(limit)
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_task(task_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("""
            SELECT t.*,
                   u_c.username AS creator_name,
                   u_a.username AS assignee_name,
                   p.name       AS project_name,
                   CASE
                     WHEN t.status NOT IN ('done','expired')
                          AND t.expire_date IS NOT NULL
                          AND t.expire_date < date('now') THEN 'expired'
                     WHEN t.status NOT IN ('done','expired')
                          AND t.end_date IS NOT NULL
                          AND t.end_date < date('now')   THEN 'overdue'
                     ELSE t.status
                   END AS computed_status
            FROM tasks t
            LEFT JOIN users    u_c ON t.created_by_id  = u_c.id
            LEFT JOIN users    u_a ON t.assigned_to_id = u_a.id
            LEFT JOIN projects p   ON t.project_id     = p.id
            WHERE t.id = ?
        """, (task_id,)).fetchone()
    return dict(row) if row else None


def update_task(task_id: int, data: dict) -> bool:
    with get_db() as conn:
        conn.execute("""
            UPDATE tasks SET
                title=?, description=?, project_id=?, deliverable=?,
                assigned_to_id=?, start_date=?, end_date=?, expire_date=?,
                status=?, priority=?, updated_at=datetime('now')
            WHERE id=?
        """, (
            data.get("title"), data.get("description"),
            data.get("project_id") or None, data.get("deliverable"),
            data.get("assigned_to_id") or None,
            data.get("start_date") or None, data.get("end_date") or None,
            data.get("expire_date") or None,
            data.get("status"), data.get("priority", "normal"),
            task_id,
        ))
    return True


def delete_task(task_id: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    return True


def expire_stale_tasks() -> int:
    """Mark tasks as expired when their expire_date has passed. Returns count updated."""
    with get_db() as conn:
        cur = conn.execute("""
            UPDATE tasks SET status='expired', updated_at=datetime('now')
            WHERE status NOT IN ('done','expired')
              AND expire_date IS NOT NULL
              AND expire_date < date('now')
        """)
        return cur.rowcount


def get_task_counts_for_user(user_id: int) -> dict:
    """Return summary counts for sidebar badge."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT
              COUNT(*) FILTER (WHERE t.status NOT IN ('done','expired')
                                 AND (t.end_date IS NULL OR t.end_date >= date('now'))
                                 AND (t.expire_date IS NULL OR t.expire_date >= date('now'))) AS active,
              COUNT(*) FILTER (WHERE t.status NOT IN ('done','expired')
                                 AND t.end_date IS NOT NULL
                                 AND t.end_date < date('now')
                                 AND (t.expire_date IS NULL OR t.expire_date >= date('now'))) AS overdue
            FROM tasks t
            WHERE t.assigned_to_id = ? OR t.created_by_id = ?
        """, (user_id, user_id)).fetchone()
    return dict(row) if row else {"active": 0, "overdue": 0}


# ── Project Checklist (enhanced with scheduling) ───────────────────────────────

def update_checklist_schedule(item_id: int, assigned_to_id, start_date, end_date,
                               estimated_hours, actual_hours) -> bool:
    """Update scheduling fields on a checklist item."""
    with get_db() as conn:
        conn.execute("""
            UPDATE project_checklist_items
            SET assigned_to_id=?, start_date=?, end_date=?,
                estimated_hours=?, actual_hours=?
            WHERE id=?
        """, (
            assigned_to_id or None,
            start_date or None,
            end_date or None,
            estimated_hours or 0,
            actual_hours or 0,
            item_id,
        ))
    return True


def get_checklist_items_for_gantt(project_id: int) -> list:
    """Return checklist items that have dates, with assignee info, for Gantt rendering."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT ci.*, u.username AS assignee_name
            FROM project_checklist_items ci
            LEFT JOIN users u ON ci.assigned_to_id = u.id
            WHERE ci.project_id = ?
              AND ci.start_date IS NOT NULL
              AND ci.end_date IS NOT NULL
            ORDER BY ci.start_date ASC, ci.sort_order ASC
        """, (project_id,)).fetchall()
    return [dict(r) for r in rows]
