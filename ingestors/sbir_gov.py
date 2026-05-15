"""
SBIR Pipeline - SBIR.gov API Ingestor
Pulls solicitations and awards from the public SBIR.gov REST API.

API docs: https://www.sbir.gov/api
"""

import requests
import time
from datetime import datetime
import database as db

BASE_URL = "https://www.sbir.gov/api"
DEFAULT_COUNT = 25       # records per page
MAX_PAGES = 40           # safety cap (~1000 records per run)
REQUEST_DELAY = 0.5      # seconds between requests (be polite)

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",
    "User-Agent": "SBIR-Pipeline/1.0 (local research tool)",
})


# ── Solicitations ──────────────────────────────────────────────────────────────

def _parse_solicitation(item: dict) -> dict:
    """Normalize an SBIR.gov solicitation JSON record into our schema."""
    raw_id = str(item.get("solicitation_id") or item.get("id") or "")
    return {
        "external_id": f"sbir_gov_sol_{raw_id}",
        "title": item.get("solicitation_title") or item.get("title") or "Untitled",
        "agency": item.get("agency") or "",
        "branch": item.get("branch") or "",
        "phase": item.get("phase") or "",
        "program": item.get("program") or "",
        "open_date": _clean_date(item.get("open_date") or item.get("release_date")),
        "close_date": _clean_date(item.get("close_date") or item.get("application_due_date")),
        "solicitation_number": item.get("solicitation_number") or "",
        "description": (item.get("description") or item.get("program_description") or "")[:4000],
        "url": item.get("solicitation_agency_url") or item.get("url") or
               f"https://www.sbir.gov/solicitation/{raw_id}",
        "source": "sbir.gov",
        "status": "open",
    }


def ingest_solicitations(agency: str = "", phase: str = "",
                          year: str = "", keyword: str = "",
                          max_records: int = 500,
                          progress_cb=None) -> dict:
    """
    Fetch solicitations from SBIR.gov and upsert them into the local DB.
    Returns {"added": int, "updated": int, "errors": list}
    """
    added = updated = 0
    errors = []
    start = datetime(datetime.utcnow().year, 1, 1)
    started_at = datetime.utcnow().isoformat()

    for page in range(MAX_PAGES):
        offset = page * DEFAULT_COUNT
        if added + updated >= max_records:
            break

        params = {
            "keyword": keyword,
            "agency": agency,
            "phase": phase,
            "year": year,
            "count": DEFAULT_COUNT,
            "start": offset,
        }
        try:
            resp = SESSION.get(f"{BASE_URL}/solicitations.json", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            errors.append(f"Page {page}: {e}")
            break

        # API may return a list directly or {"solicitations": [...]}
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("solicitations") or data.get("data") or []
        else:
            break

        if not items:
            break

        for item in items:
            try:
                record = _parse_solicitation(item)
                ins, upd = db.upsert_solicitation(record)
                if ins:
                    added += 1
                if upd:
                    updated += 1
            except Exception as e:
                errors.append(f"Record error: {e}")

        if progress_cb:
            progress_cb(added, updated, page + 1)

        if len(items) < DEFAULT_COUNT:
            break  # Last page

        time.sleep(REQUEST_DELAY)

    db.log_ingest("sbir.gov/solicitations", added, updated,
                  errors="; ".join(errors[:5]) if errors else None,
                  started_at=started_at)
    return {"added": added, "updated": updated, "errors": errors}


# ── Awards ─────────────────────────────────────────────────────────────────────

def _parse_award(item: dict) -> dict:
    raw_id = str(item.get("award_id") or item.get("id") or "")
    amount = None
    try:
        amount = float(str(item.get("award_amount") or "0").replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        pass

    year = None
    try:
        year_raw = item.get("award_year") or item.get("year") or ""
        year = int(str(year_raw)[:4]) if year_raw else None
    except (ValueError, TypeError):
        pass

    return {
        "external_id": f"sbir_gov_award_{raw_id}",
        "title": item.get("award_title") or item.get("title") or "Untitled",
        "agency": item.get("agency") or "",
        "branch": item.get("branch") or "",
        "company": item.get("company") or item.get("firm") or "",
        "amount": amount,
        "award_year": year,
        "phase": item.get("phase") or "",
        "program": item.get("program") or "",
        "abstract": (item.get("abstract") or "")[:4000],
        "keywords": item.get("keywords") or "",
        "pi_name": item.get("pi_name") or item.get("principal_investigator") or "",
        "url": item.get("url") or f"https://www.sbir.gov/award/{raw_id}",
        "source": "sbir.gov",
    }


def ingest_awards(agency: str = "", phase: str = "",
                  year: str = "", keyword: str = "",
                  max_records: int = 500,
                  progress_cb=None) -> dict:
    """
    Fetch awards from SBIR.gov and upsert them into the local DB.
    Returns {"added": int, "updated": int, "errors": list}
    """
    added = updated = 0
    errors = []
    started_at = datetime.utcnow().isoformat()

    for page in range(MAX_PAGES):
        offset = page * DEFAULT_COUNT
        if added + updated >= max_records:
            break

        params = {
            "keyword": keyword,
            "agency": agency,
            "phase": phase,
            "year": year,
            "count": DEFAULT_COUNT,
            "start": offset,
        }
        try:
            resp = SESSION.get(f"{BASE_URL}/awards.json", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            errors.append(f"Page {page}: {e}")
            break

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("awards") or data.get("data") or []
        else:
            break

        if not items:
            break

        for item in items:
            try:
                record = _parse_award(item)
                ins, upd = db.upsert_award(record)
                if ins:
                    added += 1
                if upd:
                    updated += 1
            except Exception as e:
                errors.append(f"Record error: {e}")

        if progress_cb:
            progress_cb(added, updated, page + 1)

        if len(items) < DEFAULT_COUNT:
            break

        time.sleep(REQUEST_DELAY)

    db.log_ingest("sbir.gov/awards", added, updated,
                  errors="; ".join(errors[:5]) if errors else None,
                  started_at=started_at)
    return {"added": added, "updated": updated, "errors": errors}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_date(raw) -> str | None:
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw[:10] if len(raw) >= 10 else raw
