"""
db.py - Supabase client, replaces excel_writer.py
All pipeline stages write here. server.py reads from here.

Table schema (run once in Supabase SQL editor):

    create table jobs (
        id                          text primary key,
        title                       text,
        company                     text,
        post_url                    text,
        description                 text,
        location                    text,
        scraped_at                  timestamptz,
        applied_at                  timestamptz,
        drop_at                  timestamptz,
        explicit_years_required     integer,
        is_explicit_exp_requirement boolean,
        exp_evidence                text,
        match_score                 float,
        status                      text
    );
"""
from __future__ import annotations
from datetime import datetime, timezone
from supabase import create_client, Client
import config

_client: Client | None = None

# remove physical last_operated_at from select
LIST_COLS = "id, title, company, match_score, post_url, status, scraped_at, applied_at, drop_at"


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
# helpers                                                                     #
# --------------------------------------------------------------------------- #

def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # handles "...Z"
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _compute_last_operated_at(row: dict) -> str | None:
    """
    Rule:
    - mix of scraped_at, applied_at, drop_at
    - if applied_at and drop_at are both None, display scraped_at
    - if all 3 are None, return None
    - otherwise use the latest non-null timestamp among the 3
    """
    scraped_at = row.get("scraped_at")
    applied_at = row.get("applied_at")
    drop_at = row.get("drop_at")

    if applied_at is None and drop_at is None:
        return scraped_at  # may also be None

    candidates = [ts for ts in [scraped_at, applied_at, drop_at] if ts is not None]
    if not candidates:
        return None

    latest = max(candidates, key=lambda ts: _parse_ts(ts) or datetime.min.replace(tzinfo=timezone.utc))
    return latest


def _attach_last_operated_at(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["last_operated_at"] = _compute_last_operated_at(row)
    return rows


def _sort_rows_by_last_operated_at(rows: list[dict]) -> list[dict]:
    """
    Sort desc by computed last_operated_at.
    Rows with None keep default relative order and stay at the end.
    If all are None, this becomes effectively 'no order'.
    """
    indexed = list(enumerate(rows))

    def key(item):
        idx, row = item
        ts = _parse_ts(row.get("last_operated_at"))
        if ts is None:
            return (1, idx)  # preserve original order for None rows
        return (0, -ts.timestamp())

    indexed.sort(key=key)
    return [row for _, row in indexed]


# --------------------------------------------------------------------------- #
# Pipeline writes                                                              #
# --------------------------------------------------------------------------- #

def upsert_jobs(records: list[dict]) -> None:
    if not records:
        return
    get_client().table("jobs").upsert(records, on_conflict="id").execute()
    print(f"[db] upserted {len(records)} records")


def fetch_known_ids(ids:list[str]) -> set[str]:
    if not ids:
        return set()

    response = (
        get_client()
        .table("jobs")
        .select("id")
        .in_("id", ids)
        .execute()
    )
    return {str(r["id"]) for r in (response.data or [])}

    # response = get_client().table("jobs").select("id").execute()
    # return {row["id"] for row in response.data}


# --------------------------------------------------------------------------- #
# Server reads                                                                 #
# --------------------------------------------------------------------------- #

def fetch_next_job(statuses: list[str] = ("high_matched", "mid_matched")) -> dict | None:
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


def fetch_jobs_by_status(status: str, limit: int = 200) -> list[dict]:
    """
    Return jobs filtered by status.
    last_operated_at is computed from scraped_at / applied_at / drop_at.
    """
    response = (
        get_client()
        .table("jobs")
        .select(LIST_COLS)
        .eq("status", status)
        .limit(limit)
        .execute()
    )
    rows = response.data or []
    rows = _attach_last_operated_at(rows)
    rows = _sort_rows_by_last_operated_at(rows)
    return rows


def update_status(job_id: str, status: str) -> None:
    now = datetime.now(timezone.utc).isoformat()

    payload = {"status": status}
    if status == "Applied":
        payload["applied_at"] = now
    elif status == "Drop":
        payload["drop_at"] = now

    get_client().table("jobs").update(payload).eq("id", job_id).execute()
    print(f"[db] job {job_id} -> {status}")


def delete_job(job_id: str) -> None:
    get_client().table("jobs").delete().eq("id", job_id).execute()
    print(f"[db] deleted job {job_id}")


def fetch_stats() -> dict[str, int]:
    statuses = ["high_matched", "mid_matched", "Applied", "Saved", "Drop"]
    counts: dict[str, int] = {}

    for status in statuses:
        response = (
            get_client()
            .table("jobs")
            .select("id", count="exact")
            .eq("status", status)
            .execute()
        )
        counts[status] = response.count or 0

    return counts