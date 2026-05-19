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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
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

            CREATE INDEX IF NOT EXISTS idx_projects_topic ON projects(topic_id);
            CREATE INDEX IF NOT EXISTS idx_projects_stage ON projects(stage);
            CREATE INDEX IF NOT EXISTS idx_pfiles_project ON project_files(project_id);
            CREATE INDEX IF NOT EXISTS idx_pchecklist_project ON project_checklist_items(project_id);
            CREATE INDEX IF NOT EXISTS idx_plog_project ON project_activity_log(project_id);
        """)

    # ── Migration: add new columns to existing databases ──────────────────────
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
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def get_all_users() -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, username, email, role, is_active, created_at FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


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
