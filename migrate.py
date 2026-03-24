"""
migrate_excel.py - One-off script to push existing jobs.xlsx data into Supabase.

Usage:
    SUPABASE_URL=... SUPABASE_KEY=... python migrate_excel.py
"""

import pandas as pd
from datetime import datetime, timezone
import db

EXCEL_PATH = "output/jobs.xlsx"


def dedupe_by_id(records):
    deduped = {}
    for record in records:
        record_id = str(record.get("id", "")).strip()
        if record_id:
            deduped[record_id] = record
    return list(deduped.values())


def migrate():
    # Read matched sheet — has scores and statuses
    matched = pd.read_excel(EXCEL_PATH, sheet_name="matched", dtype={"id": str})
    matched.columns = (
        matched.columns.str.strip()
    )  # Remove any leading/trailing whitespace from column names
    # Read unmatched sheet
    unmatched = pd.read_excel(EXCEL_PATH, sheet_name="unmatched", dtype={"id": str})
    unmatched.columns = (
        unmatched.columns.str.strip()
    )  # Remove any leading/trailing whitespace from column names

    now = datetime.now(timezone.utc).isoformat()

    matched_records = []
    for _, row in matched.iterrows():
        status = str(row.get("status", ""))
        # Remap old labels to new ones
        status_map = {"high_matched": "high_matched", "mid_matched": "mid_matched"}
        status = status_map.get(status, status)
        matched_records.append(
            {
                "id": str(row["id"]),
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "post_url": str(row.get("post_url", "")),
                "description": str(row.get("description", "")),
                "location": str(row.get("location", "")),
                "scraped_at": now,
                "match_score": float(row["match_score"])
                if pd.notna(row.get("match_score"))
                else None,
                "status": status,
            }
        )

    unmatched_records = []
    for _, row in unmatched.iterrows():
        unmatched_records.append(
            {
                "id": str(row["id"]),
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "post_url": str(row.get("post_url", "")),
                "description": str(row.get("description", "")),
                "location": str(row.get("location", "")),
                "scraped_at": now,
                "status": "Drop",
            }
        )

    all_records = matched_records + unmatched_records
    all_records = dedupe_by_id(all_records)

    print(f"Migrating {len(all_records)} unique records...")
    db.upsert_jobs(all_records)

    print("Done.")


if __name__ == "__main__":
    migrate()
