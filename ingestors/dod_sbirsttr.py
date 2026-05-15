"""
SBIR Pipeline — DoD SBIR/STTR Innovation Portal (DSIP) Ingestor
Source: https://www.dodsbirsttr.mil/topics-app/

API endpoints (verified via browser network inspection):

  Search (paginated):
    GET /topics/api/public/topics/search
        ?searchParam=<JSON>&page=<N>&size=<N>

  Topic detail (description, objectives, phase descriptions):
    GET /topics/api/public/topics/<topicId>/details

  Available BAA solicitations:
    GET /topics/api/public/topics/solicitations

  Component / tech-area dropdowns:
    GET /core/api/public/dropdown/components?includeArchived=true
    GET /core/api/public/dropdown/technologyAreas

Search response shape:
  { "total": 100, "data": [ <topic>, ... ] }

Topic object keys (from search):
  topicId, topicCode, topicTitle, component, program,
  phaseHierarchy, cycleName, solicitationNumber,
  topicStartDate, topicEndDate,
  showTpoc, topicQATpocStartDate, topicQATpocEndDate,
  releaseNumber, topicStatus, ...

Details response keys:
  description, objective, phase1Description, phase2Description,
  phase3Description, keywords, itar, technologyAreas,
  focusAreas, referenceDocuments, cmmcLevel

topicReleaseStatus values that mean open / pre-released:
  591 = OPEN, 592 = PRE_RELEASE  (hardcoded by the portal UI)
"""

import json
import re
import time
from datetime import datetime

import requests

import database as db

BASE = "https://www.dodsbirsttr.mil"
SEARCH_URL  = f"{BASE}/topics/api/public/topics/search"
DETAIL_URL  = f"{BASE}/topics/api/public/topics/{{topicId}}/details"
SOL_URL     = f"{BASE}/topics/api/public/topics/solicitations"

# Status IDs that represent "visible to public" topics (open + pre-release)
OPEN_STATUS_IDS = [591, 592]

PAGE_SIZE    = 25
REQUEST_DELAY = 0.4   # seconds between requests
MAX_PAGES    = 200    # hard safety cap

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/topics-app/",
    "Origin":  BASE,
})


# ── Public API ─────────────────────────────────────────────────────────────────

def get_available_baas() -> list[str]:
    """Return the list of BAA cycle names available on the portal."""
    try:
        r = SESSION.get(SOL_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data if isinstance(data, list) else data.get("data") or data.get("content") or []
        names = []
        for item in items:
            name = item.get("solicitationCycleName") or item.get("cycleName") or item.get("name") or ""
            if name:
                names.append(name)
        return names
    except Exception as e:
        print(f"[DoD SBIR] Could not fetch BAA list: {e}")
        return []


def probe_endpoints(baa: str = "DOD_SBIR_2026_P1_CBZ") -> dict:
    """
    Diagnostic: test the key API endpoints and return their HTTP status.
    Accessible via /api/dod/probe in the web UI.
    """
    results = {}
    tests = {
        "search": (SEARCH_URL, {"searchParam": _build_search_param(baa), "page": 0, "size": 1}),
        "solicitations": (SOL_URL, {}),
    }
    for label, (url, params) in tests.items():
        try:
            r = SESSION.get(url, params=params, timeout=12)
            results[url] = {
                "label": label,
                "status": r.status_code,
                "content_type": r.headers.get("Content-Type", ""),
                "preview": r.text[:150],
            }
        except Exception as e:
            results[url] = {"label": label, "status": "error", "error": str(e)}
    return results


def ingest(baa: str = "DOD_SBIR_2026_P1_CBZ",
           keyword: str = "",
           fetch_details: bool = True,
           max_records: int = 500,
           progress_cb=None) -> dict:
    """
    Pull all topics for the given BAA from the DoD SBIR/STTR portal and
    upsert them into the local SQLite database.

    Parameters
    ----------
    baa            : BAA cycle identifier, e.g. "DOD_SBIR_2026_P1_CBZ"
    keyword        : Optional text filter applied client-side after fetching
    fetch_details  : If True, also call the /details endpoint for each topic
                     to retrieve description, objectives and keywords
                     (adds one HTTP request per topic — disable for speed)
    max_records    : Hard cap on total records upserted per run
    progress_cb    : Optional callable(added, updated)
    """
    added = updated = 0
    errors: list[str] = []
    started_at = datetime.utcnow().isoformat()
    kw_lower = keyword.lower() if keyword else ""

    # Create parent Solicitation record for this BAA
    _upsert_baa_solicitation(baa)

    print(f"[DoD SBIR] Starting ingest for BAA={baa}  (fetch_details={fetch_details})")

    for page in range(MAX_PAGES):
        if added + updated >= max_records:
            break

        # ── Fetch page of topics ──────────────────────────────────────────────
        search_param = _build_search_param(baa)
        params = {"searchParam": search_param, "page": page, "size": PAGE_SIZE}

        try:
            resp = SESSION.get(SEARCH_URL, params=params, timeout=20)
            resp.raise_for_status()
            raw = resp.json()
        except requests.HTTPError as e:
            errors.append(f"HTTP {e.response.status_code} on page {page}: {e.response.text[:200]}")
            break
        except Exception as e:
            errors.append(f"Request error page {page}: {e}")
            break

        items = raw.get("data") or []
        total = raw.get("total", 0)

        if not items:
            print(f"[DoD SBIR]  page {page}: no items returned (total={total})")
            break

        print(f"[DoD SBIR]  page {page}: {len(items)} topics  (total={total})")

        # ── Process each topic ────────────────────────────────────────────────
        for item in items:
            if added + updated >= max_records:
                break

            topic_id   = item.get("topicId", "")
            topic_code = item.get("topicCode", "")

            # Optional: fetch full description from detail endpoint
            detail = {}
            if fetch_details and topic_id:
                detail = _fetch_detail(topic_id, errors)
                time.sleep(REQUEST_DELAY)

            # Build combined description
            description = _build_description(item, detail)

            # Apply keyword filter
            if kw_lower:
                haystack = (
                    item.get("topicTitle", "") + " " + description
                ).lower()
                if kw_lower not in haystack:
                    continue

            try:
                record = _parse_topic(item, detail, baa)
                ins, upd = db.upsert_topic(record)
                if ins:
                    added += 1
                if upd:
                    updated += 1
                if progress_cb:
                    progress_cb(added, updated)
            except Exception as e:
                errors.append(f"DB error ({topic_code}): {e}")

        # Detect last page
        fetched_so_far = (page + 1) * PAGE_SIZE
        if fetched_so_far >= total or len(items) < PAGE_SIZE:
            print(f"[DoD SBIR]  reached last page ({page})")
            break

        if not fetch_details:
            time.sleep(REQUEST_DELAY)

    db.log_ingest(
        source=f"dod_sbirsttr/{baa}",
        added=added,
        updated=updated,
        errors="; ".join(errors[:5]) if errors else None,
        started_at=started_at,
    )
    print(f"[DoD SBIR] Done — added={added}  updated={updated}  errors={len(errors)}")
    return {"added": added, "updated": updated, "errors": errors}


# ── Private helpers ────────────────────────────────────────────────────────────

def _build_search_param(baa: str) -> str:
    """Build the JSON searchParam string expected by the search endpoint."""
    return json.dumps({
        "searchText": None,
        "components": None,
        "programYear": None,
        "solicitationCycleNames": [baa],
        "releaseNumbers": [],
        "topicReleaseStatus": OPEN_STATUS_IDS,
        "modernizationPriorities": None,
        "sortBy": "finalTopicCode,asc",
    }, separators=(",", ":"))


def _fetch_detail(topic_id: str, errors: list) -> dict:
    """Fetch /topics/{topicId}/details and return the parsed JSON (or {})."""
    url = DETAIL_URL.format(topicId=topic_id)
    try:
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
        errors.append(f"Detail {topic_id}: HTTP {r.status_code}")
    except Exception as e:
        errors.append(f"Detail {topic_id}: {e}")
    return {}


def _build_description(item: dict, detail: dict) -> str:
    """
    Return the background description field only.
    Objective and phase descriptions are stored in their own columns.
    Falls back to any summary field on the search item.
    """
    desc = detail.get("description", "") or ""
    if desc:
        return _strip_html(desc)[:8000]
    # Fallback to anything in the search item
    for key in ("topicDescription", "abstract", "summary"):
        val = item.get(key, "")
        if val:
            return str(val)[:8000]
    return ""


def _parse_topic(item: dict, detail: dict, baa: str) -> dict:
    """Map raw API fields to our DB topic schema."""
    import json as _json
    topic_code = item.get("topicCode", "")
    topic_id   = item.get("topicId", "")

    # Stable external_id
    if topic_code:
        ext_id = "dod_" + topic_code.lower().replace("-", "_")
    else:
        import hashlib
        ext_id = "dod_" + hashlib.md5(topic_id.encode()).hexdigest()[:12]

    # Phase: parse from phaseHierarchy JSON string
    phase = _parse_phase(item.get("phaseHierarchy", ""), baa)

    # Keywords — semicolon-separated string from API
    keywords_raw = detail.get("keywords") or ""
    if isinstance(keywords_raw, list):
        keywords_raw = "; ".join(str(k) for k in keywords_raw)

    # Technology areas and focus areas — lists of strings
    tech_areas_raw  = detail.get("technologyAreas") or []
    focus_areas_raw = detail.get("focusAreas") or []
    tech_areas  = "; ".join(tech_areas_raw)  if isinstance(tech_areas_raw, list)  else str(tech_areas_raw)
    focus_areas = "; ".join(focus_areas_raw) if isinstance(focus_areas_raw, list) else str(focus_areas_raw)

    # Reference documents — store as JSON string
    ref_docs_raw = detail.get("referenceDocuments") or []
    ref_docs = _json.dumps(ref_docs_raw) if ref_docs_raw else None

    # Individual section texts (HTML stripped)
    objective   = _strip_html(detail.get("objective",          "") or "")
    phase1_desc = _strip_html(detail.get("phase1Description",  "") or "")
    phase2_desc = _strip_html(detail.get("phase2Description",  "") or "")
    phase3_desc = _strip_html(detail.get("phase3Description",  "") or "")

    # Background description
    description = _strip_html(detail.get("description", "") or "")

    # ITAR and CMMC
    itar       = bool(detail.get("itar", False))
    cmmc_level = str(detail.get("cmmcLevel", "") or "")

    # TPOC: only exposed during pre-release period (showTpoc flag)
    tech_contact = ""
    if item.get("showTpoc"):
        name  = item.get("tpocName", "")
        email = item.get("tpocEmail", "")
        phone = item.get("tpocPhone", "")
        tech_contact = " | ".join(p for p in [name, email, phone] if p)[:200]

    return {
        "external_id":   ext_id,
        "topic_number":  topic_code,
        "title":         str(item.get("topicTitle", "Untitled"))[:500],
        "agency":        "DOD",
        "branch":        str(item.get("component", ""))[:200],
        "phase":         phase,
        "description":   description[:8000],
        "objective":     objective[:4000],
        "phase1_desc":   phase1_desc[:4000],
        "phase2_desc":   phase2_desc[:4000],
        "phase3_desc":   phase3_desc[:2000],
        "keywords":      keywords_raw[:1000],
        "tech_areas":    tech_areas[:500],
        "focus_areas":   focus_areas[:500],
        "itar":          itar,
        "cmmc_level":    cmmc_level[:100],
        "ref_docs":      ref_docs,
        "tech_contact":  tech_contact,
        "url":           f"{BASE}/topics-app/?baa={baa}",
        "source":        "dod_sbirsttr",
    }


def _parse_phase(phase_hierarchy: str, baa: str) -> str:
    """
    Derive a human-readable phase from the phaseHierarchy JSON string.
    Falls back to inferring from the BAA name (P1 → I, P2 → II).
    """
    if phase_hierarchy:
        try:
            config = json.loads(phase_hierarchy).get("config", [])
            display_vals = [c.get("displayValue", "") for c in config]
            # If any entry is simply "I" or "1", it's Phase I
            if any(v in ("I", "1", "PI") for v in display_vals):
                return "I"
            # Otherwise show the first display value
            if display_vals:
                return display_vals[0]
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fallback: infer from BAA name
    baa_upper = baa.upper()
    if "_P1_" in baa_upper or "PHASE1" in baa_upper:
        return "I"
    if "_P2_" in baa_upper or "PHASE2" in baa_upper:
        return "II"
    return ""


def _strip_html(html: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;",  "&", text)
    text = re.sub(r"&lt;",   "<", text)
    text = re.sub(r"&gt;",   ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"\s+",    " ", text).strip()
    return text


def _upsert_baa_solicitation(baa: str):
    """Create/update a parent Solicitation record for the BAA."""
    phase = ""
    baa_upper = baa.upper()
    if "_P1_" in baa_upper:
        phase = "I"
    elif "_P2_" in baa_upper:
        phase = "II"

    program = ""
    if "SBIR" in baa_upper:
        program = "SBIR"
    elif "STTR" in baa_upper:
        program = "STTR"

    try:
        db.upsert_solicitation({
            "external_id":          f"dod_baa_{baa.lower()}",
            "title":                f"DoD {program} — {baa.replace('_', ' ')}",
            "agency":               "DOD",
            "branch":               "",
            "program":              program,
            "phase":                phase,
            "solicitation_number":  baa,
            "url":                  f"{BASE}/topics-app/?baa={baa}",
            "source":               "dod_sbirsttr",
            "status":               "open",
        })
    except Exception:
        pass
