"""
main.py - Orchestrates all 5 stages end-to-end.

Usage:
    OPENAI_API_KEY=sk-... python main.py
"""

import sys
import config
from scraper import fetch_jobs
from cleaner import clean_jobs
from experience_filter import filter_by_experience
from ai_scorer import score_jobs, load_cv
from db import upsert_jobs, fetch_known_ids


def run():
    print("=" * 50)
    print("JobRadar - starting pipeline")
    print("=" * 50)

    # Stage 1 - Scrape
    raw_jobs = fetch_jobs()
    if not raw_jobs:
        print("[main] No jobs fetched. Exiting.")
        sys.exit(0)

    # Stage 2 - Clean & deduplicate
    cleaned, deduped = clean_jobs(raw_jobs)

    # Stage 3 - Experience filter
    matched_jobs, unmatched_jobs = filter_by_experience(deduped)

    # Persist unmatched with status=Drop so they appear in DB but won't surface in UI
    for j in unmatched_jobs:
        j["status"] = "Drop"
    upsert_jobs(unmatched_jobs)

    # Skip jobs already processed in a previous run
    ids = [str(r["id"]) for r in matched_jobs]
    existing_ids = fetch_known_ids(ids)
    new_jobs = [r for r in matched_jobs if str(r["id"]) not in existing_ids]

    # known_ids = {str(x) for x in fetch_known_ids()}
    # new_jobs = [j for j in matched_jobs if str(j["id"]) not in known_ids]

    if new_jobs:
        print(
            f"[main] {len(new_jobs)} new jobs to process "
            f"(skipping {len(matched_jobs) - len(new_jobs)} already in DB)"
        )
        upsert_jobs(new_jobs)

    if not new_jobs:
        print("[main] Nothing new. Exiting.")
        sys.exit(0)

    if not matched_jobs:
        print("[main] All jobs filtered out by experience requirement. Exiting.")
        sys.exit(0)

    # Stage 4 - AI scoring
    cv = load_cv(config.CV_PATH)
    scored_jobs = score_jobs(new_jobs, cv)

    # Stage 5 - Persist scored jobs
    upsert_jobs(scored_jobs)

    # Summary
    statuses = [j.get("status", "?") for j in scored_jobs]
    print("\n[main] -- Summary --")
    for label in ("high_matched", "mid_matched", "Drop"):
        print(f"  {label}: {statuses.count(label)}")
    print(f"  Total scored: {len(scored_jobs)}")


if __name__ == "__main__":
    run()
