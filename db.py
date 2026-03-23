"""
db.py - Supabase client, replaces excel_writer.py
All pipeline stages write here. server.py reads from here.

Table schema (run once in Supabase SQL editor):

    create table jobs (
        id              text primary key,
        title           text,
        company         text,
        post_url        text,
        description     text,
        location        text,
        scraped_at      timestamptz,
        -- added by experience_filter
        explicit_years_required   integer,
        is_explicit_exp_requirement boolean,
        exp_evidence    text,
        -- added by ai_scorer
        match_score     float,
        skills_required jsonb,
        status          text       -- 'high_matched' | 'mid_matched' | 'Drop' | 'Applied' | 'Skipped' | 'Saved'
    );
"""
from __future__ import annotations
from supabase import create_client, Client
import config

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set as environment variables."
            )
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


# --------------------------------------------------------------------------- #
# Pipeline writes                                                               #
# --------------------------------------------------------------------------- #

def upsert_jobs(records: list[dict]) -> None:
    """Insert or update jobs by id. Safe to call multiple times with same data."""
    if not records:
        return
    get_client().table("jobs").upsert(records, on_conflict="id").execute()
    print(f"[db] upserted {len(records)} records")


def fetch_known_ids() -> set[str]:
    """Return all job ids already in the DB (for skipping on re-runs)."""
    response = get_client().table("jobs").select("id").execute()
    return {row["id"] for row in response.data}


# --------------------------------------------------------------------------- #
# Server reads                                                                 #
# --------------------------------------------------------------------------- #

def fetch_next_job(statuses: list[str] = ("high_matched", "mid_matched")) -> dict | None:
    """
    Return the next unactioned job ordered by match_score desc.
    'Unactioned' means status is still the AI-assigned label, not yet
    touched by the user (Applied / Skipped / Saved).
    """
    response = (
        get_client()
        .table("jobs")
        .select("id, title, company, match_score, post_url, location, status")
        .in_("status", list(statuses))
        .order("match_score", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def fetch_all_jobs(limit: int = 200) -> list[dict]:
    """Return all jobs ordered by match_score desc, for stats / overview."""
    response = (
        get_client()
        .table("jobs")
        .select("id, title, company, match_score, post_url, location, status, scraped_at")
        .order("match_score", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


def update_status(job_id: str, status: str) -> None:
    """Update a single job's user-facing status (Applied / Skipped / Saved)."""
    get_client().table("jobs").update({"status": status}).eq("id", job_id).execute()
    print(f"[db] job {job_id} -> {status}")


def fetch_stats() -> dict:
    """Return count of jobs grouped by status."""
    response = get_client().table("jobs").select("status").execute()
    counts: dict[str, int] = {}
    for row in response.data:
        s = row["status"] or "Unknown"
        counts[s] = counts.get(s, 0) + 1
    return counts