"""
SBIR Pipeline - Flask Web Application
Local offline app for ingesting and querying SBIR solicitation data.
"""

import os
import threading
from datetime import datetime
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response, send_file
from werkzeug.utils import secure_filename

import database as db

# Allow OAuth2 over plain HTTP for local development
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

app = Flask(__name__)
app.secret_key = "sbir-pipeline-local-secret"

# Track background ingestion jobs
_jobs: dict[str, dict] = {}


# ── Jinja2 helpers ─────────────────────────────────────────────────────────────

def _file_icon(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "pdf": "bi-file-earmark-pdf",
        "doc": "bi-file-earmark-word", "docx": "bi-file-earmark-word",
        "xls": "bi-file-earmark-excel", "xlsx": "bi-file-earmark-excel",
        "ppt": "bi-file-earmark-ppt", "pptx": "bi-file-earmark-ppt",
        "txt": "bi-file-earmark-text", "md": "bi-file-earmark-text",
        "csv": "bi-file-earmark-spreadsheet",
        "png": "bi-file-earmark-image", "jpg": "bi-file-earmark-image",
        "jpeg": "bi-file-earmark-image", "gif": "bi-file-earmark-image",
        "zip": "bi-file-earmark-zip",
        "msg": "bi-envelope", "eml": "bi-envelope",
    }.get(ext, "bi-file-earmark")


def _activity_icon(event_type: str) -> str:
    return {
        "created":      "bi-plus-circle-fill",
        "stage_change": "bi-arrow-right-circle-fill",
        "checklist":    "bi-check-circle-fill",
        "file_upload":  "bi-upload",
        "file_delete":  "bi-trash3",
        "note":         "bi-chat-left-text-fill",
    }.get(event_type, "bi-dot")


def _activity_color(event_type: str) -> str:
    return {
        "created":      "#0d6efd",
        "stage_change": "#6f42c1",
        "checklist":    "#198754",
        "file_upload":  "#0d6efd",
        "file_delete":  "#dc3545",
        "note":         "#fd7e14",
    }.get(event_type, "#adb5bd")


app.jinja_env.globals.update(
    file_icon=_file_icon,
    activity_icon=_activity_icon,
    activity_color=_activity_color,
)


@app.context_processor
def inject_gdrive_status():
    try:
        from integrations import google_drive as gd
        return {
            "gdrive_connected": gd.is_connected(),
            "gdrive_has_creds": gd.has_credentials_file(),
        }
    except Exception:
        return {"gdrive_connected": False, "gdrive_has_creds": False}

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "project_uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "md", "csv", "png", "jpg", "jpeg", "gif",
    "zip", "msg", "eml",
}

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Startup ────────────────────────────────────────────────────────────────────

@app.before_request
def ensure_db():
    """Ensure DB is initialized (runs once on first request)."""
    if not hasattr(app, "_db_ready"):
        db.init_db()
        app._db_ready = True


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    stats = db.get_stats()
    capture_stats = db.get_capture_stats()
    return render_template("dashboard.html", stats=stats, jobs=_jobs,
                           capture_stats=capture_stats)


# ── Solicitations ──────────────────────────────────────────────────────────────

@app.route("/solicitations")
def solicitations():
    agency   = request.args.get("agency", "")
    phase    = request.args.get("phase", "")
    program  = request.args.get("program", "")
    source   = request.args.get("source", "")
    status   = request.args.get("status", "")
    keyword  = request.args.get("keyword", "")
    favorited = request.args.get("favorited", "")
    page     = int(request.args.get("page", 1))
    per_page = 50
    offset   = (page - 1) * per_page

    rows = db.get_solicitations(
        agency=agency or None,
        phase=phase or None,
        program=program or None,
        source=source or None,
        status=status or None,
        keyword=keyword or None,
        favorited=True if favorited == "1" else None,
        limit=per_page,
        offset=offset,
    )
    filters = {
        "agencies":  db.get_distinct("solicitations", "agency"),
        "phases":    db.get_distinct("solicitations", "phase"),
        "programs":  db.get_distinct("solicitations", "program"),
        "sources":   db.get_distinct("solicitations", "source"),
        "statuses":  db.get_distinct("solicitations", "status"),
    }
    return render_template("solicitations.html",
                           rows=rows, filters=filters, page=page, per_page=per_page,
                           agency=agency, phase=phase, program=program,
                           source=source, status=status, keyword=keyword,
                           favorited=favorited)


@app.route("/solicitations/<int:sol_id>")
def solicitation_detail(sol_id: int):
    sol = db.get_solicitation(sol_id)
    if not sol:
        flash("Solicitation not found.", "warning")
        return redirect(url_for("solicitations"))
    topics = db.get_topics(keyword=sol.get("solicitation_number") or sol.get("title", "")[:30])
    return render_template("solicitation_detail.html", sol=sol, topics=topics)


@app.route("/solicitations/<int:sol_id>/favorite", methods=["POST"])
def toggle_favorite(sol_id: int):
    db.toggle_favorite(sol_id)
    return redirect(request.referrer or url_for("solicitations"))


@app.route("/solicitations/<int:sol_id>/score", methods=["POST"])
def set_score(sol_id: int):
    score = float(request.form.get("score", 0))
    db.set_score(sol_id, score)
    return redirect(request.referrer or url_for("solicitation_detail", sol_id=sol_id))


@app.route("/solicitations/<int:sol_id>/notes", methods=["POST"])
def set_notes(sol_id: int):
    notes = request.form.get("notes", "")
    db.set_notes(sol_id, notes)
    return redirect(request.referrer or url_for("solicitation_detail", sol_id=sol_id))


# ── Awards ─────────────────────────────────────────────────────────────────────

@app.route("/awards")
def awards():
    agency  = request.args.get("agency", "")
    phase   = request.args.get("phase", "")
    program = request.args.get("program", "")
    year    = request.args.get("year", "")
    source  = request.args.get("source", "")
    keyword = request.args.get("keyword", "")
    page    = int(request.args.get("page", 1))
    per_page = 50
    offset  = (page - 1) * per_page

    rows = db.get_awards(
        agency=agency or None,
        phase=phase or None,
        program=program or None,
        year=int(year) if year else None,
        source=source or None,
        keyword=keyword or None,
        limit=per_page,
        offset=offset,
    )
    filters = {
        "agencies": db.get_distinct("awards", "agency"),
        "phases":   db.get_distinct("awards", "phase"),
        "programs": db.get_distinct("awards", "program"),
        "years":    db.get_distinct("awards", "award_year"),
        "sources":  db.get_distinct("awards", "source"),
    }
    return render_template("awards.html",
                           rows=rows, filters=filters, page=page, per_page=per_page,
                           agency=agency, phase=phase, program=program,
                           year=year, source=source, keyword=keyword)


@app.route("/awards/<int:award_id>")
def award_detail(award_id: int):
    award = db.get_award(award_id)
    if not award:
        flash("Award not found.", "warning")
        return redirect(url_for("awards"))
    return render_template("award_detail.html", award=award)


# ── Topics ─────────────────────────────────────────────────────────────────────

@app.route("/topics/<int:topic_id>")
def topic_detail(topic_id: int):
    import json
    topic = db.get_topic(topic_id)
    if not topic:
        flash("Topic not found.", "warning")
        return redirect(url_for("topics"))
    try:
        topic["ref_docs_parsed"] = json.loads(topic.get("ref_docs") or "[]")
    except Exception:
        topic["ref_docs_parsed"] = []
    return render_template("topic_detail.html", topic=topic)


@app.route("/topics/<int:topic_id>/favorite", methods=["POST"])
def toggle_topic_favorite(topic_id: int):
    db.toggle_topic_favorite(topic_id)
    return redirect(request.referrer or url_for("topic_detail", topic_id=topic_id))


@app.route("/topics/<int:topic_id>/score", methods=["POST"])
def set_topic_score(topic_id: int):
    score = float(request.form.get("score", 0))
    db.set_topic_score(topic_id, score)
    return redirect(request.referrer or url_for("topic_detail", topic_id=topic_id))


@app.route("/topics/<int:topic_id>/notes", methods=["POST"])
def set_topic_notes(topic_id: int):
    notes = request.form.get("notes", "")
    db.set_topic_notes(topic_id, notes)
    return redirect(request.referrer or url_for("topic_detail", topic_id=topic_id))


@app.route("/topics/<int:topic_id>/status", methods=["POST"])
def set_topic_status(topic_id: int):
    status = request.form.get("status", "")
    db.set_topic_status(topic_id, status)
    return redirect(request.referrer or url_for("topics"))


@app.route("/topics/<int:topic_id>/export/pdf")
def export_topic_pdf(topic_id: int):
    """Generate and stream a PDF of the topic detail."""
    import json as _json
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    topic = db.get_topic(topic_id)
    if not topic:
        flash("Topic not found.", "warning")
        return redirect(url_for("topics"))

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.85*inch, rightMargin=0.85*inch,
                            topMargin=0.85*inch, bottomMargin=0.85*inch)

    styles = getSampleStyleSheet()
    navy   = colors.HexColor("#003087")
    gold   = colors.HexColor("#c8972b")

    title_style = ParagraphStyle("TopicTitle",
                                 fontName="Helvetica-Bold", fontSize=14,
                                 textColor=navy, leading=18, spaceAfter=4)
    meta_style  = ParagraphStyle("Meta",
                                 fontName="Helvetica", fontSize=9,
                                 textColor=colors.HexColor("#6c757d"), spaceAfter=8)
    section_style = ParagraphStyle("Section",
                                   fontName="Helvetica-Bold", fontSize=11,
                                   textColor=navy, spaceBefore=14, spaceAfter=4)
    body_style  = ParagraphStyle("Body",
                                 fontName="Helvetica", fontSize=9,
                                 leading=13, spaceAfter=6)

    def _safe(text):
        """Escape XML special chars for ReportLab Paragraph."""
        if not text:
            return ""
        return (str(text)
                .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    story = []

    # Header bar
    story.append(Paragraph(_safe(topic.get("title", "Untitled Topic")), title_style))
    meta_parts = []
    if topic.get("topic_number"):
        meta_parts.append(f"#{topic['topic_number']}")
    if topic.get("agency"):
        meta_parts.append(topic["agency"])
    if topic.get("branch"):
        meta_parts.append(topic["branch"])
    if topic.get("phase"):
        meta_parts.append(f"Phase {topic['phase']}")
    if topic.get("source"):
        meta_parts.append(topic["source"])
    story.append(Paragraph("  ·  ".join(meta_parts), meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=gold, spaceAfter=10))

    # Quick-facts table
    facts = []
    if topic.get("close_date"):
        facts.append(("Close Date", topic["close_date"]))
    if topic.get("open_date"):
        facts.append(("Open Date", topic["open_date"]))
    if topic.get("solicitation_year"):
        facts.append(("Sol. Year", topic["solicitation_year"]))
    if topic.get("solicitation_status"):
        facts.append(("Status", topic["solicitation_status"]))
    if topic.get("tech_areas"):
        facts.append(("Tech Area", topic["tech_areas"]))
    if topic.get("itar"):
        facts.append(("ITAR", "Yes"))
    if topic.get("cmmc_level"):
        facts.append(("CMMC Level", topic["cmmc_level"]))
    if topic.get("tech_contact"):
        facts.append(("TPOC", topic["tech_contact"]))
    if topic.get("url"):
        facts.append(("Source URL", topic["url"]))

    if facts:
        tdata = [[Paragraph(f"<b>{_safe(k)}</b>", body_style),
                  Paragraph(_safe(v), body_style)]
                 for k, v in facts]
        tbl = Table(tdata, colWidths=[1.4*inch, 5.3*inch])
        tbl.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1),
             [colors.HexColor("#f8f9fa"), colors.white]),
            ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 10))

    # Sections
    sections = [
        ("Description",     topic.get("description")),
        ("Objective",       topic.get("objective")),
        ("Phase I",         topic.get("phase1_desc")),
        ("Phase II",        topic.get("phase2_desc")),
        ("Phase III",       topic.get("phase3_desc")),
    ]
    for heading, content in sections:
        if content and content.strip():
            story.append(Paragraph(heading, section_style))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#dee2e6"), spaceAfter=4))
            story.append(Paragraph(_safe(content.strip()), body_style))

    # Keywords
    if topic.get("keywords"):
        story.append(Paragraph("Keywords", section_style))
        story.append(Paragraph(_safe(topic["keywords"]), body_style))

    # Notes (if any)
    if topic.get("notes"):
        story.append(Paragraph("My Notes", section_style))
        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=gold, spaceAfter=4))
        story.append(Paragraph(_safe(topic["notes"]), body_style))

    # Footer note
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"Exported from SBIR Pipeline · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        ParagraphStyle("Footer", fontName="Helvetica", fontSize=8,
                       textColor=colors.HexColor("#adb5bd"))))

    doc.build(story)
    buf.seek(0)

    safe_num = (topic.get("topic_number") or str(topic_id)).replace("/", "-")
    filename = f"SBIR_Topic_{safe_num}.pdf"
    return Response(buf.read(), mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.route("/topics/<int:topic_id>/export/docx")
def export_topic_docx(topic_id: int):
    """Generate and stream a DOCX of the topic detail."""
    from io import BytesIO
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    topic = db.get_topic(topic_id)
    if not topic:
        flash("Topic not found.", "warning")
        return redirect(url_for("topics"))

    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1)
        section.right_margin  = Inches(1)

    NAVY = RGBColor(0x00, 0x30, 0x87)
    GOLD = RGBColor(0xC8, 0x97, 0x2B)
    GREY = RGBColor(0x6c, 0x75, 0x7d)

    def _heading(text: str, level: int = 1, color=NAVY):
        p = doc.add_heading(text, level=level)
        for run in p.runs:
            run.font.color.rgb = color
        return p

    def _para(text: str, size: int = 10, color=None, italic=False, bold=False):
        p = doc.add_paragraph()
        run = p.add_run(text or "")
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
        run.italic = italic
        run.bold   = bold
        return p

    def _add_section(title: str, content: str):
        if not content or not content.strip():
            return
        _heading(title, level=2)
        _para(content.strip(), size=10)

    # Title
    _heading(topic.get("title") or "Untitled Topic", level=1)

    # Meta line
    meta_parts = []
    if topic.get("topic_number"):
        meta_parts.append(f"#{topic['topic_number']}")
    if topic.get("agency"):
        meta_parts.append(topic["agency"])
    if topic.get("branch"):
        meta_parts.append(topic["branch"])
    if topic.get("phase"):
        meta_parts.append(f"Phase {topic['phase']}")
    if topic.get("source"):
        meta_parts.append(topic["source"])
    _para("  ·  ".join(meta_parts), size=9, color=GREY, italic=True)

    doc.add_paragraph()  # spacer

    # Key facts table
    facts = []
    for label, key in [
        ("Close Date",   "close_date"),
        ("Open Date",    "open_date"),
        ("Sol. Year",    "solicitation_year"),
        ("Status",       "solicitation_status"),
        ("Tech Area",    "tech_areas"),
        ("TPOC",         "tech_contact"),
        ("Source URL",   "url"),
    ]:
        val = topic.get(key)
        if val:
            facts.append((label, val))
    if topic.get("itar"):
        facts.append(("ITAR", "Yes"))
    if topic.get("cmmc_level"):
        facts.append(("CMMC Level", topic["cmmc_level"]))

    if facts:
        tbl = doc.add_table(rows=len(facts), cols=2)
        tbl.style = "Table Grid"
        for i, (label, value) in enumerate(facts):
            cell_l = tbl.rows[i].cells[0]
            cell_r = tbl.rows[i].cells[1]
            run_l = cell_l.paragraphs[0].add_run(label)
            run_l.bold = True
            run_l.font.size = Pt(9)
            run_l.font.color.rgb = NAVY
            run_r = cell_r.paragraphs[0].add_run(str(value))
            run_r.font.size = Pt(9)
        doc.add_paragraph()

    # Content sections
    _add_section("Description",  topic.get("description"))
    _add_section("Objective",    topic.get("objective"))
    _add_section("Phase I",      topic.get("phase1_desc"))
    _add_section("Phase II",     topic.get("phase2_desc"))
    _add_section("Phase III",    topic.get("phase3_desc"))

    if topic.get("keywords"):
        _heading("Keywords", level=2)
        _para(topic["keywords"], size=10)

    if topic.get("notes"):
        _heading("My Notes", level=2, color=GOLD)
        _para(topic["notes"], size=10)

    # Footer
    doc.add_paragraph()
    _para(
        f"Exported from SBIR Pipeline · {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        size=8, color=GREY, italic=True,
    )

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)

    safe_num = (topic.get("topic_number") or str(topic_id)).replace("/", "-")
    filename = f"SBIR_Topic_{safe_num}.docx"
    return Response(
        buf.read(),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/topics")
def topics():
    agency       = request.args.get("agency", "")
    phase        = request.args.get("phase", "")
    source       = request.args.get("source", "")
    keyword      = request.args.get("keyword", "")
    favorited    = request.args.get("favorited", "")
    topic_status = request.args.get("topic_status", "")
    page         = int(request.args.get("page", 1))
    per_page     = 50
    offset       = (page - 1) * per_page

    rows = db.get_topics(
        agency=agency or None,
        phase=phase or None,
        source=source or None,
        keyword=keyword or None,
        favorited=True if favorited == "1" else None,
        topic_status=topic_status if topic_status in ("nominated", "passed") else None,
        limit=per_page,
        offset=offset,
    )
    filters = {
        "agencies": db.get_distinct("topics", "agency"),
        "phases":   db.get_distinct("topics", "phase"),
        "sources":  db.get_distinct("topics", "source"),
    }
    return render_template("topics.html",
                           rows=rows, filters=filters, page=page, per_page=per_page,
                           agency=agency, phase=phase, source=source,
                           keyword=keyword, favorited=favorited,
                           topic_status=topic_status)


# ── Topics CSV Export ──────────────────────────────────────────────────────────

@app.route("/topics/export.csv")
def export_topics_csv():
    """Export all topics matching current filters as a CSV download."""
    agency       = request.args.get("agency", "")
    phase        = request.args.get("phase", "")
    source       = request.args.get("source", "")
    keyword      = request.args.get("keyword", "")
    favorited    = request.args.get("favorited", "")
    topic_status = request.args.get("topic_status", "")

    rows = db.get_topics(
        agency=agency or None,
        phase=phase or None,
        source=source or None,
        keyword=keyword or None,
        favorited=True if favorited == "1" else None,
        topic_status=topic_status if topic_status in ("nominated", "passed") else None,
        limit=10000,   # export all matching rows
        offset=0,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Topic #", "Title", "Agency", "Branch", "Phase", "Source",
        "Favorited", "Status"
    ])

    for row in rows:
        status_label = ""
        if row["topic_status"] == "nominated":
            status_label = "Nominated"
        elif row["topic_status"] == "passed":
            status_label = "Passed"

        writer.writerow([
            row["topic_number"] or "",
            row["title"] or "",
            row["agency"] or "",
            row["branch"] or "",
            row["phase"] or "",
            row["source"] or "",
            "Yes" if row["favorited"] else "No",
            status_label,
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=captureiq_topics.csv"},
    )


# ── Search ─────────────────────────────────────────────────────────────────────

@app.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    results = None
    if keyword:
        results = db.full_search(keyword)
    return render_template("search.html", keyword=keyword, results=results)


# ── Ingestion ──────────────────────────────────────────────────────────────────

@app.route("/ingest")
def ingest_page():
    recent_logs = []
    with db.get_db() as conn:
        rows = conn.execute("""
            SELECT id, source, records_added, records_updated, errors, started_at, finished_at
            FROM ingest_log ORDER BY id DESC LIMIT 20
        """).fetchall()
        recent_logs = [dict(r) for r in rows]
    return render_template("ingest.html", jobs=_jobs, recent_logs=recent_logs)


@app.route("/ingest/sbir-gov", methods=["POST"])
def ingest_sbir_gov():
    source_type = request.form.get("source_type", "solicitations")
    agency  = request.form.get("agency", "")
    phase   = request.form.get("phase", "")
    year    = request.form.get("year", "")
    keyword = request.form.get("keyword", "")
    max_rec = int(request.form.get("max_records", 100))

    job_id = f"sbir_gov_{source_type}_{datetime.utcnow().strftime('%H%M%S')}"
    _jobs[job_id] = {"status": "running", "source": f"sbir.gov/{source_type}", "started": datetime.utcnow().isoformat()}

    def run():
        from ingestors import sbir_gov
        try:
            if source_type == "awards":
                result = sbir_gov.ingest_awards(agency=agency, phase=phase, year=year,
                                                keyword=keyword, max_records=max_rec)
            else:
                result = sbir_gov.ingest_solicitations(agency=agency, phase=phase, year=year,
                                                       keyword=keyword, max_records=max_rec)
            _jobs[job_id].update({
                "status": "done",
                "added": result["added"],
                "updated": result["updated"],
                "errors": result["errors"][:3],
                "finished": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _jobs[job_id].update({"status": "error", "error": str(e)})

    threading.Thread(target=run, daemon=True).start()
    flash(f"Ingestion started (job: {job_id}). Refresh the page to see progress.", "info")
    return redirect(url_for("ingest_page"))


@app.route("/ingest/sbir-topics", methods=["POST"])
def ingest_sbir_topics():
    agency    = request.form.get("agency", "").strip()
    phase     = request.form.get("phase", "").strip()
    year      = request.form.get("year", "").strip()
    keyword   = request.form.get("keyword", "").strip()
    status    = request.form.get("status", "open")
    max_rec   = int(request.form.get("max_records", 100))
    fetch_det = request.form.get("fetch_details", "1") == "1"

    job_id = f"sbir_topics_{datetime.utcnow().strftime('%H%M%S')}"
    _jobs[job_id] = {
        "status": "running",
        "source": "sbir.gov/topics",
        "started": datetime.utcnow().isoformat(),
    }

    def run():
        from ingestors import sbir_gov_topics
        try:
            result = sbir_gov_topics.ingest(
                agency=agency, phase=phase, year=year,
                keyword=keyword, status=status,
                max_records=max_rec, fetch_details=fetch_det,
            )
            _jobs[job_id].update({
                "status": "done",
                "added": result["added"],
                "updated": result["updated"],
                "errors": result["errors"][:3],
                "finished": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _jobs[job_id].update({"status": "error", "error": str(e)})

    threading.Thread(target=run, daemon=True).start()
    flash(f"SBIR.gov topics ingestion started (job: {job_id}).", "info")
    return redirect(url_for("ingest_page"))


@app.route("/ingest/navy", methods=["POST"])
def ingest_navy():
    topics_url = request.form.get("topics_url", "").strip() or "https://www.navysbir.com/topics26_1.htm"
    max_topics = int(request.form.get("max_topics", 100))

    job_id = f"navy_sbir_{datetime.utcnow().strftime('%H%M%S')}"
    _jobs[job_id] = {"status": "running", "source": "navysbir.com", "started": datetime.utcnow().isoformat()}

    def run():
        from ingestors import navy_sbir
        try:
            result = navy_sbir.ingest(topics_url=topics_url, max_topics=max_topics)
            _jobs[job_id].update({
                "status": "done",
                "added": result["added"],
                "updated": result["updated"],
                "errors": result["errors"][:3],
                "finished": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _jobs[job_id].update({"status": "error", "error": str(e)})

    threading.Thread(target=run, daemon=True).start()
    flash(f"Navy SBIR ingestion started (job: {job_id}).", "info")
    return redirect(url_for("ingest_page"))


@app.route("/ingest/dod", methods=["POST"])
def ingest_dod():
    baa     = request.form.get("baa", "DOD_SBIR_2026_P1_CBZ").strip()
    keyword = request.form.get("keyword", "").strip()
    max_rec = int(request.form.get("max_records", 200))

    job_id = f"dod_{baa}_{datetime.utcnow().strftime('%H%M%S')}"
    _jobs[job_id] = {
        "status": "running",
        "source": f"dod_sbirsttr/{baa}",
        "started": datetime.utcnow().isoformat(),
    }

    def run():
        from ingestors import dod_sbirsttr
        try:
            result = dod_sbirsttr.ingest(baa=baa, keyword=keyword, max_records=max_rec)
            _jobs[job_id].update({
                "status": "done",
                "added": result["added"],
                "updated": result["updated"],
                "errors": result["errors"][:5],
                "endpoint_used": result.get("endpoint_used"),
                "finished": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            _jobs[job_id].update({"status": "error", "error": str(e)})

    threading.Thread(target=run, daemon=True).start()
    flash(f"DoD SBIR/STTR ingestion started for BAA={baa} (job: {job_id}).", "info")
    return redirect(url_for("ingest_page"))


@app.route("/api/dod/probe")
def api_dod_probe():
    """Diagnostic: test which DoD API endpoints are reachable."""
    from ingestors import dod_sbirsttr
    baa = request.args.get("baa", "DOD_SBIR_2026_P1_CBZ")
    results = dod_sbirsttr.probe_endpoints()
    return jsonify({"baa": baa, "endpoints": results})


@app.route("/api/dod/baas")
def api_dod_baas():
    """Return the list of available BAA identifiers from the DoD portal."""
    from ingestors import dod_sbirsttr
    baas = dod_sbirsttr.get_available_baas()
    return jsonify(baas)


# ── SBIR Capture — Projects ────────────────────────────────────────────────────

@app.route("/projects")
def projects():
    stage   = request.args.get("stage", "")
    keyword = request.args.get("keyword", "")
    rows = db.get_projects(
        stage=stage or None,
        keyword=keyword or None,
    )
    capture_stats = db.get_capture_stats()
    return render_template("projects.html",
                           rows=rows,
                           stages=db.STAGES,
                           capture_stats=capture_stats,
                           stage=stage,
                           keyword=keyword)


@app.route("/projects/new", methods=["POST"])
def create_project():
    topic_id = request.form.get("topic_id") or None
    if topic_id:
        try:
            topic_id = int(topic_id)
        except ValueError:
            topic_id = None

    name = request.form.get("name", "").strip()
    if not name:
        flash("Project name is required.", "warning")
        return redirect(url_for("projects"))

    project_id = db.create_project({
        "topic_id":       topic_id,
        "name":           name,
        "description":    request.form.get("description", "").strip(),
        "stage":          request.form.get("stage", "Identified"),
        "lead":           request.form.get("lead", "").strip(),
        "due_date":       request.form.get("due_date", "").strip() or None,
        "checklist_type": request.form.get("checklist_type", "dod"),
        "source":         request.form.get("source", "").strip(),
    })
    flash(f"Project '{name}' created.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>")
def project_detail(project_id: int):
    project = db.get_project(project_id)
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("projects"))
    checklist = db.get_checklist(project_id)
    files     = db.get_project_files(project_id)
    activity  = db.get_activity_log(project_id)

    # Group checklist by category
    checklist_groups = {}
    for item in checklist:
        cat = item["category"] or "General"
        checklist_groups.setdefault(cat, []).append(item)

    return render_template("project_detail.html",
                           project=project,
                           checklist_groups=checklist_groups,
                           files=files,
                           activity=activity,
                           stages=db.STAGES)


@app.route("/projects/<int:project_id>/edit", methods=["POST"])
def edit_project(project_id: int):
    db.update_project(project_id, {
        "name":        request.form.get("name", "").strip(),
        "description": request.form.get("description", "").strip(),
        "lead":        request.form.get("lead", "").strip(),
        "due_date":    request.form.get("due_date", "").strip() or None,
        "notes":       request.form.get("notes", "").strip(),
    })
    flash("Project updated.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/stage", methods=["POST"])
def set_project_stage(project_id: int):
    stage = request.form.get("stage", "Identified")
    db.set_project_stage(project_id, stage)
    flash(f"Stage updated to '{stage}'.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id: int):
    project = db.get_project(project_id)
    if project:
        # Delete uploaded files from disk
        files = db.get_project_files(project_id)
        for f in files:
            try:
                if os.path.exists(f["local_path"]):
                    os.remove(f["local_path"])
            except Exception:
                pass
        db.delete_project(project_id)
        flash(f"Project '{project['name']}' deleted.", "info")
    return redirect(url_for("projects"))


# ── SBIR Capture — Files ───────────────────────────────────────────────────────

@app.route("/projects/<int:project_id>/files/upload", methods=["POST"])
def upload_project_file(project_id: int):
    from integrations import google_drive as gd

    project = db.get_project(project_id)
    if not project:
        flash("Project not found.", "warning")
        return redirect(url_for("projects"))

    if "file" not in request.files:
        flash("No file selected.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))

    f = request.files["file"]
    if f.filename == "":
        flash("No file selected.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))

    if not _allowed_file(f.filename):
        flash(f"File type not allowed. Permitted: {', '.join(sorted(ALLOWED_EXTENSIONS))}", "warning")
        return redirect(url_for("project_detail", project_id=project_id))

    filename  = secure_filename(f.filename)
    category  = request.form.get("file_category", "general")
    dest      = request.form.get("destination", "local")

    # Always save locally first (needed for Drive upload too)
    proj_dir  = os.path.join(UPLOAD_FOLDER, str(project_id))
    os.makedirs(proj_dir, exist_ok=True)
    save_path = os.path.join(proj_dir, filename)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(save_path):
        filename  = f"{base}_{counter}{ext}"
        save_path = os.path.join(proj_dir, filename)
        counter  += 1
    f.save(save_path)
    size = os.path.getsize(save_path)

    if dest == "gdrive" and gd.is_connected():
        try:
            # Ensure project has a Drive folder
            folder_id = project.get("gdrive_folder_id")
            if not folder_id:
                folder_id = gd.get_or_create_project_folder(
                    project["name"], project_id)
                db.set_project_gdrive_folder(project_id, folder_id)

            gdrive_id, web_link = gd.upload_file(
                folder_id, save_path, filename, f.content_type)

            # Remove the temporary local copy after upload
            try:
                os.remove(save_path)
            except Exception:
                pass

            db.add_project_file(
                project_id=project_id,
                filename=filename,
                local_path=None,
                file_size=size,
                mime_type=f.content_type,
                category=category,
                storage_backend="gdrive",
                gdrive_file_id=gdrive_id,
                gdrive_web_link=web_link,
            )
            flash(f"'{filename}' uploaded to Google Drive.", "success")
        except Exception as e:
            flash(f"Drive upload failed ({e}). File saved locally instead.", "warning")
            db.add_project_file(
                project_id=project_id,
                filename=filename,
                local_path=save_path,
                file_size=size,
                mime_type=f.content_type,
                category=category,
            )
    else:
        db.add_project_file(
            project_id=project_id,
            filename=filename,
            local_path=save_path,
            file_size=size,
            mime_type=f.content_type,
            category=category,
        )
        flash(f"'{filename}' uploaded successfully.", "success")

    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/files/<int:file_id>/download")
def download_project_file(project_id: int, file_id: int):
    from integrations import google_drive as gd
    file_rec = db.get_project_file(file_id, project_id)
    if not file_rec:
        flash("File not found.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))

    if file_rec.get("storage_backend") == "gdrive":
        try:
            buf = gd.download_file(file_rec["gdrive_file_id"])
            return Response(
                buf.read(),
                mimetype=file_rec.get("mime_type") or "application/octet-stream",
                headers={"Content-Disposition":
                         f'attachment; filename="{file_rec["filename"]}"'},
            )
        except Exception as e:
            flash(f"Could not download from Google Drive: {e}", "danger")
            return redirect(url_for("project_detail", project_id=project_id))

    if not file_rec.get("local_path") or not os.path.exists(file_rec["local_path"]):
        flash("Local file not found.", "warning")
        return redirect(url_for("project_detail", project_id=project_id))
    return send_file(file_rec["local_path"], as_attachment=True,
                     download_name=file_rec["filename"])


@app.route("/projects/<int:project_id>/files/<int:file_id>/delete", methods=["POST"])
def delete_project_file(project_id: int, file_id: int):
    from integrations import google_drive as gd
    file_rec = db.get_project_file(file_id, project_id)
    if file_rec:
        if file_rec.get("storage_backend") == "gdrive" and file_rec.get("gdrive_file_id"):
            try:
                gd.delete_file(file_rec["gdrive_file_id"])
            except Exception:
                pass  # Best-effort Drive delete
        local_path = db.delete_project_file(file_id, project_id)
        if local_path:
            try:
                if os.path.exists(local_path):
                    os.remove(local_path)
            except Exception:
                pass
        flash("File deleted.", "info")
    return redirect(url_for("project_detail", project_id=project_id))


# ── SBIR Capture — Checklist ───────────────────────────────────────────────────

@app.route("/projects/<int:project_id>/checklist/<int:item_id>/toggle", methods=["POST"])
def toggle_checklist(project_id: int, item_id: int):
    db.toggle_checklist_item(item_id, project_id)
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/checklist/add", methods=["POST"])
def add_checklist_item(project_id: int):
    label    = request.form.get("label", "").strip()
    category = request.form.get("category", "Custom").strip() or "Custom"
    if label:
        db.add_checklist_item(project_id, label, category)
        flash("Checklist item added.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/checklist/<int:item_id>/delete", methods=["POST"])
def delete_checklist_item(project_id: int, item_id: int):
    db.delete_checklist_item(item_id, project_id)
    return redirect(url_for("project_detail", project_id=project_id))


# ── Google Drive Settings ──────────────────────────────────────────────────────

@app.route("/settings/gdrive")
def gdrive_settings():
    from integrations import google_drive as gd
    return render_template("gdrive_settings.html",
                           connected=gd.is_connected(),
                           has_creds=gd.has_credentials_file())


@app.route("/settings/gdrive/connect")
def gdrive_connect():
    from integrations import google_drive as gd
    if not gd.has_credentials_file():
        flash("credentials.json not found. See setup instructions.", "danger")
        return redirect(url_for("gdrive_settings"))
    redirect_uri = url_for("gdrive_callback", _external=True)
    return redirect(gd.get_auth_url(redirect_uri))


@app.route("/settings/gdrive/callback")
def gdrive_callback():
    from integrations import google_drive as gd
    code = request.args.get("code")
    if not code:
        flash("Google authorisation failed — no code returned.", "danger")
        return redirect(url_for("gdrive_settings"))
    try:
        redirect_uri = url_for("gdrive_callback", _external=True)
        gd.exchange_code(code, redirect_uri)
        flash("Google Drive connected successfully!", "success")
    except Exception as e:
        flash(f"Google Drive connection failed: {e}", "danger")
    return redirect(url_for("gdrive_settings"))


@app.route("/settings/gdrive/disconnect", methods=["POST"])
def gdrive_disconnect():
    from integrations import google_drive as gd
    gd.revoke()
    flash("Google Drive disconnected.", "info")
    return redirect(url_for("gdrive_settings"))


# ── API endpoints (JSON) ───────────────────────────────────────────────────────

@app.route("/ingest-log/<int:log_id>/delete", methods=["POST"])
def delete_ingest_log(log_id: int):
    db.delete_ingest_log(log_id)
    return redirect(url_for("ingest_page"))


@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_stats())


@app.route("/api/jobs")
def api_jobs():
    return jsonify(_jobs)


@app.route("/api/solicitations")
def api_solicitations():
    keyword = request.args.get("q", "")
    agency  = request.args.get("agency", "")
    phase   = request.args.get("phase", "")
    rows = db.get_solicitations(
        keyword=keyword or None,
        agency=agency or None,
        phase=phase or None,
        limit=100,
    )
    return jsonify(rows)


@app.route("/api/awards")
def api_awards():
    keyword = request.args.get("q", "")
    agency  = request.args.get("agency", "")
    rows = db.get_awards(keyword=keyword or None, agency=agency or None, limit=100)
    return jsonify(rows)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print("\n" + "="*60)
    print("  CaptureIQ")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("="*60 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
