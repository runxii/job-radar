"""
Stage 1 - Scraper
Fetches LinkedIn job listings via JobSpy for each keyword in config.
Returns a list of raw job dicts (JobSpy DataFrame rows).
"""

import time
import pandas as pd
from jobspy import scrape_jobs
import config


def fetch_jobs(
    queries: list[str] = config.SEARCH_QUERIES,
    location: str = config.SEARCH_LOCATION,
    results_wanted: int = config.RESULTS_WANTED,
    hours_old: int = config.HOURS_OLD,
    delay_seconds: float = 2.0,
) -> list[dict]:
    """
    Scrape LinkedIn for each search query and return combined raw results.
    Deduplication by job id happens in cleaner.py.
    """
    all_frames: list[pd.DataFrame] = []

    for query in queries:
        print(f"[scraper] Searching: '{query}' in {location} ...")
        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=query,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                linkedin_fetch_description=True,
                country_indeed="Ireland",  # ignored for linkedin but harmless
            )
            print(f"[scraper] Got {len(df)} results")
            all_frames.append(df)
        except Exception as exc:
            print(f"[scraper] WARNING: query '{query}' failed - {exc}")

        time.sleep(delay_seconds)  # be polite to LinkedIn

    if not all_frames:
        return []

    combined = pd.concat(all_frames, ignore_index=True)
    return combined.to_dict(orient="records")


if __name__ == "__main__":
    jobs = fetch_jobs()
    print(f"[scraper] Total raw records fetched: {len(jobs)}")
