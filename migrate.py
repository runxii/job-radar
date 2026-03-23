"""
migrate_excel.py - One-off script to push existing jobs.xlsx data into Supabase.

Usage:
    SUPABASE_URL=... SUPABASE_KEY=... python migrate_excel.py
"""
import pandas as pd
from datetime import datetime, timezone
import db

EXCEL_PATH = "output/jobs.xlsx"

def migrate():
    # Read matched sheet — has scores and statuses
    matched = pd.read_excel(EXCEL_PATH, sheet_name="matched", dtype={"id": str})
    # Read unmatched sheet
    unmatched = pd.read_excel(EXCEL_PATH, sheet_name="unmatched", dtype={"id": str})

    now = datetime.now(timezone.utc).isoformat()

    matched_records = []
    for _, row in matched.iterrows():
        status = str(row.get("status", ""))
        # Remap old labels to new ones
        status_map = {"AI Apply": "high_matched", "Human Apply": "mid_matched"}
        status = status_map.get(status, status)
        matched_records.append({
            "id":          str(row["id"]),
            "title":       str(row.get("title", "")),
            "company":     str(row.get("company", "")),
            "post_url":    str(row.get("post_url", "")),
            "description": str(row.get("description", "")),
            "location":    str(row.get("location", "")),
            "scraped_at":  now,
            "match_score": float(row["match_score"]) if pd.notna(row.get("match_score")) else None,
            "status":      status,
        })

    unmatched_records = []
    for _, row in unmatched.iterrows():
        unmatched_records.append({
            "id":          str(row["id"]),
            "title":       str(row.get("title", "")),
            "company":     str(row.get("company", "")),
            "post_url":    str(row.get("post_url", "")),
            "description": str(row.get("description", "")),
            "location":    str(row.get("location", "")),
            "scraped_at":  now,
            "status":      "Drop",
        })

    all_records = matched_records + unmatched_records
    print(f"Migrating {len(matched_records)} matched + {len(unmatched_records)} unmatched...")
    db.upsert_jobs(all_records)
    print("Done.")

if __name__ == "__main__":
    migrate()