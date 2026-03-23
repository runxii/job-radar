"""
Stage 2 - Cleaner
Normalises raw JobSpy records into a consistent schema and removes duplicates.
"""
from __future__ import annotations
from datetime import datetime, timezone

def _str(value, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s and s.lower() not in ("nan", "none") else fallback


def clean_job(raw: dict) -> dict:
    """Map a single raw JobSpy record to the project's canonical schema."""
    job_id = _str(raw.get("id")).removeprefix("li-")

    # JobSpy exposes job_url (LinkedIn post URL) and job_url_direct (apply link)
    post_url = _str(raw.get("job_url"))
    if job_id != "N/A" and post_url == "N/A":
        post_url = f"https://www.linkedin.com/jobs/view/{job_id}"

    return {
        "id":          job_id,
        "title":       _str(raw.get("title")),
        "company":     _str(raw.get("company")),
        "post_url":    post_url,
        "description": _str(raw.get("description"), fallback=""),
        "location":    _str(raw.get("location")),
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
    }


def clean_jobs(raw_jobs: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Clean and deduplicate a list of raw records.
 
    Returns
    -------
    cleaned      : all records after normalisation (including dups for raw storage)
    deduplicated : unique records by id (for downstream processing)
    """
    cleaned = [clean_job(r) for r in raw_jobs]
 
    seen: set[str] = set()
    deduplicated: list[dict] = []
    for job in cleaned:
        if job["id"] not in seen:
            seen.add(job["id"])
            deduplicated.append(job)
 
    print(f"[cleaner] {len(cleaned)} records cleaned, {len(deduplicated)} unique")
    return cleaned, deduplicated
