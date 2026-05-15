"""
CaptureIQ — Navy SBIR Ingestor
Scrapes topics from https://www.navysbir.com/topics26_1.htm
and individual topic detail pages at navysbir.com/n26_1/DON26BZ01-NV001.htm

Listing page URL is configurable so new BAA releases can be pointed to
without changing code (pass topics_url to ingest()).
"""

import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import database as db

BASE_URL         = "https://www.navysbir.com"
DEFAULT_LIST_URL = "https://www.navysbir.com/topics26_1.htm"
REQUEST_DELAY    = 1.2   # seconds between topic fetches

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
})


# ── HTTP helper ────────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 20) -> BeautifulSoup | None:
    try:
        r = SESSION.get(url, timeout=timeout)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")
    except Exception as e:
        print(f"[NavySBIR] Fetch failed {url}: {e}")
        return None


# ── Listing page ───────────────────────────────────────────────────────────────

def _get_topic_links(list_url: str) -> list[dict]:
    """
    Parse the topics listing page and return a list of
    {topic_code, title, branch, phase, url} dicts.
    """
    soup = _get(list_url)
    if not soup:
        return []

    base = list_url.rsplit("/", 1)[0]   # e.g. https://www.navysbir.com
    topics = []
    current_branch = "Navy"
    current_phase  = "I"

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Skip non-topic links
        if not re.search(r"DON\w+-[A-Z]{2}\d{3}\.htm", href, re.IGNORECASE):
            continue

        full_url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"

        # Extract topic code from the href e.g. DON26BZ01-NV001
        code_match = re.search(r"(DON\w+-((?:NV|DV|NP)\d+))", href, re.IGNORECASE)
        if not code_match:
            continue
        full_code  = code_match.group(1).upper()   # DON26BZ01-NV001
        short_code = code_match.group(2).upper()   # NV001

        # Phase: DV = Direct to Phase II
        phase = "II" if short_code.startswith("DV") else "I"

        # Title from link text (strip trailing " -" and " Q&A")
        raw_title = a.get_text(" ", strip=True)
        raw_title = re.sub(r"\s*-\s*Q&A\s*$", "", raw_title, flags=re.IGNORECASE)
        raw_title = re.sub(r"\s*-\s*$", "", raw_title).strip()
        # The link text sometimes starts with the code "NV001 -" — remove it
        raw_title = re.sub(rf"^{re.escape(short_code)}\s*-?\s*", "", raw_title, flags=re.IGNORECASE).strip()

        # Branch: walk backwards in the soup to find the nearest section header
        # We'll detect it on the detail page too, so just approximate from URL if needed
        topics.append({
            "full_code":  full_code,
            "short_code": short_code,
            "title":      raw_title or full_code,
            "phase":      phase,
            "url":        full_url,
        })

    print(f"[NavySBIR] Found {len(topics)} topic links on listing page")
    return topics


# ── Detail page parser ─────────────────────────────────────────────────────────

# Regex to split the page text on known section headings
_SECTION_RE = re.compile(
    r"\n\s*("
    r"(?:DON\w+-(?:NV|DV|NP)\d+\s+)?TITLE"
    r"|OUSW\s*\(R&E\)\s*CRITICAL\s+TECHNOLOGY\s+AREA\(S\)"
    r"|COMPONENT\s+TECHNOLOGY\s+PRIORITY\s+AREA\(S\)"
    r"|PROJECTED\s+CMMC\s+LEVEL\s+REQUIREMENT"
    r"|OBJECTIVE"
    r"|DESCRIPTION"
    r"|PHASE\s+I(?!\s*I)"          # Phase I but not Phase II
    r"|PHASE\s+II(?!\s*I)"         # Phase II but not Phase III
    r"|PHASE\s+III\s+DUAL\s+USE\s+APPLICATIONS"
    r"|REFERENCES"
    r"|KEYWORDS"
    r")\s*:",
    re.IGNORECASE,
)

_BRANCH_MAP = {
    "MCSC":   "Marine Corps Systems Command",
    "NAVAIR": "Naval Air Systems Command",
    "NAVSEA": "Naval Sea Systems Command",
    "ONR":    "Office of Naval Research",
    "SSP":    "Strategic Systems Programs",
    "NAVWAR": "Naval Information Warfare Systems Command",
}


def _extract_section(sections: dict, *keys) -> str:
    """Return the first matching section value, stripped."""
    for k in keys:
        for sk in sections:
            if re.search(k, sk, re.IGNORECASE):
                return sections[sk].strip()
    return ""


def _parse_dates(text: str) -> dict:
    """Extract open/close/release dates from page header text."""
    dates = {}
    m = re.search(r"Opens?\s+to\s+(?:accept\s+)?proposals?\s+(\d+/\d+/\d+)", text, re.IGNORECASE)
    if m:
        dates["open_date"] = m.group(1)
    m = re.search(r"Closes?\s+(\d+/\d+/\d+)", text, re.IGNORECASE)
    if m:
        dates["close_date"] = m.group(1)
    m = re.search(r"Pre-?release\s+(\d+/\d+/\d+)", text, re.IGNORECASE)
    if m:
        dates["release_date"] = m.group(1)
    return dates


def _parse_topic_detail(url: str) -> dict | None:
    """Fetch and parse a single topic detail page. Returns a db-ready dict."""
    soup = _get(url)
    if not soup:
        return None

    # Full plain text (preserves newlines)
    full_text = soup.get_text("\n", strip=False)

    # ── Topic number & title from page header ──────────────────────────────
    topic_number = ""
    title        = ""

    # First <h1> or large bold text is typically the title
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    # Topic number from heading like "DON26BZ01-NV001 TITLE: ..."
    tn_match = re.search(r"(DON\w+-(?:NV|DV|NP)\d+)", full_text)
    if tn_match:
        topic_number = tn_match.group(1).upper()

    # ── Branch from command line (2nd line of body, e.g. "Marine Corps...") ──
    branch = "Navy"
    for abbr in _BRANCH_MAP:
        if abbr in full_text:
            branch = abbr
            break

    # ── Phase from topic number prefix ────────────────────────────────────
    phase = "I"
    if re.search(r"-DV\d+", topic_number):
        phase = "II"

    # ── Dates ──────────────────────────────────────────────────────────────
    dates = _parse_dates(full_text)

    # ── Solicitation year ──────────────────────────────────────────────────
    sol_year_m = re.search(r"FY-?(\d{2})", full_text, re.IGNORECASE)
    sol_year = "20" + sol_year_m.group(1) if sol_year_m else ""

    # ── Split text into sections ───────────────────────────────────────────
    parts    = _SECTION_RE.split(full_text)
    sections = {}
    i = 1
    while i < len(parts) - 1:
        heading = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        # Stop at the "TOPIC NOTICE" boilerplate
        content = re.split(r"\*+\s*TOPIC\s+NOTICE\s*\*+", content, flags=re.IGNORECASE)[0].strip()
        sections[heading] = content
        i += 2

    # ── Pull named fields ──────────────────────────────────────────────────
    if not title:
        raw_title = _extract_section(sections, r"TITLE")
        # Strip leading topic number
        raw_title = re.sub(r"^DON\w+-(?:NV|DV|NP)\d+\s*", "", raw_title).strip()
        title = raw_title

    tech_areas  = _extract_section(sections, r"CRITICAL\s+TECHNOLOGY")
    focus_areas = _extract_section(sections, r"COMPONENT\s+TECHNOLOGY\s+PRIORITY")
    cmmc_level  = _extract_section(sections, r"CMMC\s+LEVEL")
    objective   = _extract_section(sections, r"OBJECTIVE")
    description = _extract_section(sections, r"DESCRIPTION")
    phase1_desc = _extract_section(sections, r"PHASE\s+I(?!\s*I)")
    phase2_desc = _extract_section(sections, r"PHASE\s+II(?!\s*I)")
    phase3_desc = _extract_section(sections, r"PHASE\s+III")
    keywords    = _extract_section(sections, r"KEYWORDS")

    # ── Solicitation status ────────────────────────────────────────────────
    sol_status = "open"
    if "pre-release" in full_text.lower():
        sol_status = "pre-release"

    # ── BAA identifier ─────────────────────────────────────────────────────
    baa_match = re.search(r"(DON\d+BZ\d+|DON\d+BX\d+)", full_text, re.IGNORECASE)
    baa_id    = baa_match.group(1).upper() if baa_match else ""

    external_id = f"navysbir_{topic_number.lower().replace('-', '_')}"

    return {
        "external_id":         external_id,
        "topic_number":        topic_number,
        "title":               title[:500],
        "agency":              "DOD",
        "branch":              branch,
        "phase":               phase,
        "objective":           objective[:4000],
        "description":         description[:6000],
        "phase1_desc":         phase1_desc[:4000],
        "phase2_desc":         phase2_desc[:4000],
        "phase3_desc":         phase3_desc[:4000],
        "keywords":            keywords[:500],
        "tech_areas":          tech_areas[:300],
        "focus_areas":         focus_areas[:300],
        "cmmc_level":          cmmc_level[:100],
        "url":                 url,
        "open_date":           dates.get("open_date", ""),
        "close_date":          dates.get("close_date", ""),
        "release_date":        dates.get("release_date", ""),
        "solicitation_year":   sol_year,
        "solicitation_status": sol_status,
        "source":              "navysbir.com",
    }


# ── Main entry point ───────────────────────────────────────────────────────────

def ingest(topics_url: str = DEFAULT_LIST_URL,
           max_topics: int = 200,
           progress_cb=None) -> dict:
    """
    Scrape Navy SBIR topics from the given listing page and upsert into the DB.
    Returns {"added": int, "updated": int, "errors": list}.
    """
    added      = 0
    updated    = 0
    errors     = []
    started_at = datetime.utcnow().isoformat()

    print(f"[NavySBIR] Fetching listing: {topics_url}")
    topic_links = _get_topic_links(topics_url)

    if not topic_links:
        msg = f"No topic links found on {topics_url}"
        db.log_ingest("navysbir.com", 0, 0, errors=msg, started_at=started_at)
        return {"added": 0, "updated": 0, "errors": [msg]}

    for i, entry in enumerate(topic_links[:max_topics]):
        print(f"[NavySBIR] ({i+1}/{min(len(topic_links), max_topics)}) "
              f"{entry['short_code']} — {entry['title'][:60]}")

        record = _parse_topic_detail(entry["url"])
        if not record:
            errors.append(f"Failed to fetch {entry['url']}")
            continue

        # Fill in list-page title if detail page title is empty
        if not record.get("title"):
            record["title"] = entry["title"]

        try:
            ins, upd = db.upsert_topic(record)
            if ins:
                added += 1
            elif upd:
                updated += 1
            if progress_cb:
                progress_cb(added, updated)
        except Exception as e:
            errors.append(f"{entry['short_code']}: {e}")

        time.sleep(REQUEST_DELAY)

    db.log_ingest(
        "navysbir.com", added, updated,
        errors="; ".join(errors[:5]) if errors else None,
        started_at=started_at,
    )
    print(f"[NavySBIR] Done — {added} added, {updated} updated, {len(errors)} errors")
    return {"added": added, "updated": updated, "errors": errors}
