"""
SBIR Pipeline - SBIR.gov Topics Ingestor
Scrapes topic listings from sbir.gov/topics (server-rendered Drupal HTML).
No public JSON API exists for topics; we use BeautifulSoup on the
paginated listing pages, then fetch each detail page for full content.

Listing URL:  GET https://www.sbir.gov/topics?page=N  (10 results/page)
Detail URL:   GET https://www.sbir.gov/topics/{id}
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import database as db

BASE       = "https://www.sbir.gov"
PAGE_SIZE  = 10          # sbir.gov shows 10 topics per listing page
MAX_PAGES  = 50          # safety cap — 50 pages × 10 = 500 topics
DELAY      = 0.7         # seconds between requests — be polite to the server

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})


# ── Date helpers ───────────────────────────────────────────────────────────────

def _clean_date(text: str) -> str | None:
    if not text:
        return None
    text = text.strip()
    for fmt in ("%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text[:10] if len(text) >= 10 else text


def _find_date(text: str, *labels) -> str | None:
    """Search for 'Label ... Month DD, YYYY' in text (handles newlines)."""
    for label in labels:
        m = re.search(
            rf'{re.escape(label)}[\s\S]{{0,30}}?([A-Z][a-z]+ \d{{1,2}}, \d{{4}})',
            text, re.IGNORECASE
        )
        if m:
            return _clean_date(m.group(1))
    return None


# ── Listing page parser ────────────────────────────────────────────────────────

def _parse_listing(html: str) -> tuple[list[str], int]:
    """
    Returns (topic_ids, total_count).
    topic_ids  — list of numeric ID strings from /topics/{id} links
    total_count — total results declared by 'Showing X-Y of N results'
    """
    soup = BeautifulSoup(html, "lxml")

    ids, seen = [], set()
    for a in soup.find_all("a", href=re.compile(r"/topics/\d+")):
        m = re.search(r"/topics/(\d+)", a["href"])
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            ids.append(m.group(1))

    total = 0
    body_text = soup.get_text()
    count_m = re.search(r"Showing \d+-\d+ of (\d+) results", body_text)
    if count_m:
        total = int(count_m.group(1))

    return ids, total


# ── Section text extractor ─────────────────────────────────────────────────────

def _section_after(soup: BeautifulSoup, heading_re: str) -> str:
    """
    Find the first h2/h3 whose text matches heading_re, then collect all
    following sibling text until the next heading.  Returns clean plain text.
    """
    heading = None
    for tag in soup.find_all(["h2", "h3"]):
        if re.search(heading_re, tag.get_text(strip=True), re.IGNORECASE):
            heading = tag
            break
    if not heading:
        return ""

    chunks = []
    for sib in heading.find_next_siblings():
        if sib.name in ["h2", "h3"]:
            break
        t = sib.get_text(separator="\n", strip=True)
        if t:
            chunks.append(t)
    return "\n\n".join(chunks)


# ── Detail page parser ─────────────────────────────────────────────────────────

def _parse_detail(topic_id: str, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    main = soup.find("main") or soup

    # ── Title (first <h2>) ──────────────────────────────────────────────────
    h2 = main.find("h2")
    title = h2.get_text(strip=True) if h2 else f"Topic {topic_id}"

    # ── Funding Agency (<h3> "Funding Agency" → next <p>) ──────────────────
    agency = ""
    for h3 in main.find_all("h3"):
        if "funding agency" in h3.get_text(strip=True).lower():
            nxt = h3.find_next_sibling()
            if nxt:
                agency = nxt.get_text(strip=True)
            break

    # ── Metadata block (Year, Topic Number, Programme, Phase, Status) ───────
    meta_text = main.get_text(separator="\n")

    year_m      = re.search(r"Year:\s*(\d{4})", meta_text)
    topic_num_m = re.search(r"Topic Number:\s*([^\n]+)", meta_text)
    status_m    = re.search(r"Solicitation Status:\s*([^\n]+)", meta_text)

    year         = year_m.group(1).strip()       if year_m       else ""
    topic_number = topic_num_m.group(1).strip()  if topic_num_m  else ""
    sol_status   = status_m.group(1).strip()     if status_m     else "open"

    # Programme (SBIR / STTR) — look for "Tagged as:" block
    program = ""
    phase   = ""
    # Find "Tagged as:" text then grab the next non-blank lines
    tagged_m = re.search(
        r"Tagged as:\s*\n+\s*([A-Z]+)\s*\n+\s*(Phase [^\n]+)",
        meta_text, re.IGNORECASE
    )
    if tagged_m:
        program = tagged_m.group(1).strip()
        phase   = tagged_m.group(2).strip().replace("Phase ", "")
    else:
        # Fallback: look for badges explicitly
        for badge in main.find_all(["span", "div", "li"],
                                   class_=re.compile(r"badge|tag|label", re.I)):
            t = badge.get_text(strip=True)
            if t in ("SBIR", "STTR"):
                program = t
            elif re.match(r"Phase [IVX\d]+", t, re.I):
                phase = t.replace("Phase ", "")

    # ── Dates from the Release Schedule section ─────────────────────────────
    sched_text = _section_after(soup, r"Release Schedule")
    # Fallback to full page text if section not found
    date_src   = sched_text or meta_text

    close_date   = _find_date(date_src, "Close Date", "Due Date")
    open_date    = _find_date(date_src, "Open Date")
    release_date = _find_date(date_src, "Release Date")

    # ── Full description from the Description section ───────────────────────
    description = _section_after(soup, r"^Description$")

    return {
        "external_id":        f"sbir_gov_topic_{topic_id}",
        "topic_number":       topic_number,
        "title":              title,
        "agency":             agency,
        "branch":             "",
        "phase":              phase,
        "description":        description,
        "source":             "sbir.gov",
        "url":                f"{BASE}/topics/{topic_id}",
        "close_date":         close_date,
        "open_date":          open_date,
        "release_date":       release_date,
        "solicitation_year":  year,
        "solicitation_status": sol_status,
    }


# ── Main ingest function ───────────────────────────────────────────────────────

def ingest(agency: str = "", phase: str = "", year: str = "",
           keyword: str = "", status: str = "open",
           max_records: int = 100, fetch_details: bool = True) -> dict:
    """
    Scrape topics from sbir.gov and upsert them into the local DB.

    Parameters
    ----------
    max_records   : Stop after ingesting this many topics
    fetch_details : If True, make one extra GET per topic for full content
                    (description, dates, agency, topic number).
                    If False, only the topic ID and URL are stored.
    """
    added = updated = 0
    errors: list[str] = []
    started_at = datetime.utcnow().isoformat()

    for page_num in range(MAX_PAGES):
        if added + updated >= max_records:
            break

        list_url = f"{BASE}/topics?page={page_num}"
        try:
            resp = SESSION.get(list_url, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            errors.append(f"Listing page {page_num}: {e}")
            break

        topic_ids, total = _parse_listing(resp.text)

        if not topic_ids:
            break  # no more results on this page

        for topic_id in topic_ids:
            if added + updated >= max_records:
                break
            try:
                if fetch_details:
                    time.sleep(DELAY)
                    det_resp = SESSION.get(f"{BASE}/topics/{topic_id}", timeout=20)
                    det_resp.raise_for_status()
                    record = _parse_detail(topic_id, det_resp.text)
                else:
                    record = {
                        "external_id": f"sbir_gov_topic_{topic_id}",
                        "title":       f"Topic {topic_id}",
                        "url":         f"{BASE}/topics/{topic_id}",
                        "source":      "sbir.gov",
                    }

                ins, upd = db.upsert_topic(record)
                if ins:
                    added += 1
                if upd:
                    updated += 1

            except Exception as e:
                errors.append(f"Topic {topic_id}: {e}")

        if len(topic_ids) < PAGE_SIZE:
            break  # last page reached

        time.sleep(DELAY)

    db.log_ingest(
        "sbir.gov/topics", added, updated,
        errors="; ".join(errors[:5]) if errors else None,
        started_at=started_at,
    )
    return {"added": added, "updated": updated, "errors": errors}
