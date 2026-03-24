"""
test_db.py - Integration tests for db.py against a real Supabase instance.

Setup before running:
  1. Create a Supabase project at https://supabase.com
  2. Run the SQL in db.py docstring inside the Supabase SQL editor
  3. Export credentials:
       export SUPABASE_URL=https://xxxx.supabase.co
       export SUPABASE_KEY=your-anon-key
  4. Run:
       pytest tests/test_db.py -v

These tests write and delete real rows. They are isolated by using
ids prefixed with 'test-' and cleaned up in teardown.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db


pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"),
    reason="SUPABASE_URL and SUPABASE_KEY not set - skipping integration tests",
)

TEST_TABLE = "job_test"
TEST_IDS = ["test-001", "test-002", "test-003", "test-004", "test-005"]


@pytest.fixture(autouse=True, scope="session")
def use_test_table():
    original = db.TABLE_NAME
    db.TABLE_NAME = TEST_TABLE
    yield
    db.TABLE_NAME = original


def _table():
    return db.get_client().table(db.TABLE_NAME)


def _sample_job(
    job_id: str,
    score: float = 0.75,
    status: str = "high_matched",
    scraped_at: str | None = None,
    applied_at: str | None = None,
    drop_at: str | None = None,
) -> dict:
    return {
        "id": job_id,
        "title": "Test Software Engineer",
        "company": "Test Corp",
        "post_url": f"https://linkedin.com/jobs/view/{job_id}",
        "description": "A test job description.",
        "location": "Dublin, Ireland",
        "scraped_at": scraped_at or datetime.now(timezone.utc).isoformat(),
        "explicit_years_required": None,
        "is_explicit_exp_requirement": None,
        "exp_evidence": None,
        "match_score": score,
        "skills_required": [],
        "status": status,
        "drop_at": drop_at,
        "applied_at": applied_at,
    }


def _delete_test_rows() -> None:
    for tid in TEST_IDS:
        _table().delete().eq("id", tid).execute()


@pytest.fixture(autouse=True)
def cleanup():
    _delete_test_rows()
    yield
    _delete_test_rows()


class TestUpsertJobs:
    def test_insert_single_record(self):
        db.upsert_jobs([_sample_job("test-001")])

        row = _table().select("id").eq("id", "test-001").execute()
        assert row.data
        assert row.data[0]["id"] == "test-001"

    def test_insert_multiple_records(self):
        db.upsert_jobs([_sample_job("test-001"), _sample_job("test-002")])

        ids = db.fetch_known_ids(["test-001", "test-002", "test-999"])
        assert ids == {"test-001", "test-002"}

    def test_upsert_updates_existing_row_by_id(self):
        db.upsert_jobs([_sample_job("test-001", score=0.5)])
        db.upsert_jobs([_sample_job("test-001", score=0.9)])

        row = _table().select("match_score").eq("id", "test-001").execute()
        assert row.data
        assert abs(row.data[0]["match_score"] - 0.9) < 1e-6

    def test_empty_list_is_noop(self):
        db.upsert_jobs([])
        ids = db.fetch_known_ids(TEST_IDS)
        assert ids == set()


class TestFetchKnownIds:
    def test_returns_set(self):
        result = db.fetch_known_ids(["test-001", "test-002"])
        assert isinstance(result, set)

    def test_empty_input_returns_empty_set(self):
        assert db.fetch_known_ids([]) == set()

    def test_returns_only_existing_ids_from_given_batch(self):
        db.upsert_jobs([_sample_job("test-001"), _sample_job("test-003")])

        ids = db.fetch_known_ids(["test-001", "test-002", "test-003"])
        assert ids == {"test-001", "test-003"}

    def test_does_not_return_ids_outside_the_requested_batch(self):
        db.upsert_jobs([_sample_job("test-001"), _sample_job("test-003")])

        ids = db.fetch_known_ids(["test-001"])
        assert ids == {"test-001"}


class TestFetchNextJob:
    def test_returns_highest_score_across_default_pending_statuses(self):
        db.upsert_jobs(
            [
                _sample_job("test-001", score=0.5, status="high_matched"),
                _sample_job("test-002", score=0.9, status="mid_matched"),
                _sample_job("test-003", score=0.99, status="Applied"),
            ]
        )

        job = db.fetch_next_job()
        assert job is not None
        assert job["id"] == "test-002"

    def test_respects_custom_status_filter(self):
        db.upsert_jobs(
            [
                _sample_job("test-001", score=0.7, status="high_matched"),
                _sample_job("test-002", score=0.9, status="Saved"),
            ]
        )

        job = db.fetch_next_job(statuses=["Saved"])
        assert job is not None
        assert job["id"] == "test-002"

    def test_returns_none_when_no_row_matches_requested_statuses(self):
        db.upsert_jobs(
            [
                _sample_job("test-001", status="Drop"),
                _sample_job("test-002", status="Applied"),
            ]
        )

        job = db.fetch_next_job(statuses=["high_matched", "mid_matched"])
        assert job is None


class TestFetchJobsByStatus:
    def test_returns_only_requested_status_rows(self):
        db.upsert_jobs(
            [
                _sample_job("test-001", status="Applied"),
                _sample_job("test-002", status="Drop"),
                _sample_job("test-003", status="Applied"),
            ]
        )

        rows = db.fetch_jobs_by_status("Applied", limit=10)
        ids = {row["id"] for row in rows}
        assert ids == {"test-001", "test-003"}

    def test_attaches_last_operated_at_from_scraped_at_when_no_action_timestamps(self):
        scraped_at = datetime.now(timezone.utc).isoformat()
        db.upsert_jobs([_sample_job("test-001", status="Saved", scraped_at=scraped_at)])

        rows = db.fetch_jobs_by_status("Saved", limit=10)
        assert len(rows) == 1
        assert rows[0]["id"] == "test-001"
        assert rows[0]["last_operated_at"] == scraped_at

    def test_returns_none_for_last_operated_at_when_all_timestamps_are_none(self):
        job = _sample_job(
            "test-001", status="Saved", scraped_at=None, applied_at=None, drop_at=None
        )
        job["scraped_at"] = None
        db.upsert_jobs([job])

        rows = db.fetch_jobs_by_status("Saved", limit=10)
        assert len(rows) == 1
        assert rows[0]["last_operated_at"] is None

    def test_last_operated_at_prefers_latest_non_null_timestamp(self):
        base = datetime.now(timezone.utc)
        scraped_at = (base - timedelta(days=2)).isoformat()
        applied_at = (base - timedelta(days=1)).isoformat()
        drop_at = base.isoformat()

        db.upsert_jobs(
            [
                _sample_job(
                    "test-001",
                    status="Drop",
                    scraped_at=scraped_at,
                    applied_at=applied_at,
                    drop_at=drop_at,
                )
            ]
        )

        rows = db.fetch_jobs_by_status("Drop", limit=10)
        assert len(rows) == 1
        assert rows[0]["last_operated_at"] == drop_at

    def test_sorts_by_computed_last_operated_at_desc(self):
        base = datetime.now(timezone.utc)

        db.upsert_jobs(
            [
                _sample_job(
                    "test-001",
                    status="Saved",
                    scraped_at=(base - timedelta(hours=3)).isoformat(),
                ),
                _sample_job(
                    "test-002",
                    status="Saved",
                    scraped_at=(base - timedelta(hours=1)).isoformat(),
                ),
                _sample_job(
                    "test-003",
                    status="Saved",
                    scraped_at=(base - timedelta(hours=2)).isoformat(),
                ),
            ]
        )

        rows = db.fetch_jobs_by_status("Saved", limit=10)
        ids = [row["id"] for row in rows]
        assert ids == ["test-002", "test-003", "test-001"]

    def test_none_last_operated_at_rows_stay_at_the_end(self):
        base = datetime.now(timezone.utc)

        job_with_none = _sample_job("test-001", status="Saved", scraped_at=None)
        job_with_none["scraped_at"] = None

        db.upsert_jobs(
            [
                job_with_none,
                _sample_job(
                    "test-002",
                    status="Saved",
                    scraped_at=base.isoformat(),
                ),
            ]
        )

        rows = db.fetch_jobs_by_status("Saved", limit=10)
        ids = [row["id"] for row in rows]
        assert ids == ["test-002", "test-001"]


class TestUpdateStatus:
    def test_updates_to_applied_and_sets_applied_at(self):
        db.upsert_jobs([_sample_job("test-001")])

        before = _table().select("applied_at, drop_at").eq("id", "test-001").execute()
        assert before.data
        assert before.data[0]["applied_at"] is None
        assert before.data[0]["drop_at"] is None

        db.update_status("test-001", "Applied")

        row = (
            _table()
            .select("status, applied_at, drop_at")
            .eq("id", "test-001")
            .execute()
        )
        assert row.data
        record = row.data[0]
        assert record["status"] == "Applied"
        assert record["applied_at"] is not None
        assert record["drop_at"] is None

    def test_updates_to_drop_and_sets_drop_at(self):
        db.upsert_jobs([_sample_job("test-001")])

        db.update_status("test-001", "Drop")

        row = (
            _table()
            .select("status, applied_at, drop_at")
            .eq("id", "test-001")
            .execute()
        )
        assert row.data
        record = row.data[0]
        assert record["status"] == "Drop"
        assert record["drop_at"] is not None

    def test_updates_to_saved_without_setting_action_timestamps(self):
        db.upsert_jobs([_sample_job("test-001")])

        db.update_status("test-001", "Saved")

        row = (
            _table()
            .select("status, applied_at, drop_at")
            .eq("id", "test-001")
            .execute()
        )
        assert row.data
        record = row.data[0]
        assert record["status"] == "Saved"
        assert record["applied_at"] is None
        assert record["drop_at"] is None

    def test_update_status_does_not_clear_existing_applied_at_when_switching_to_saved(
        self,
    ):
        db.upsert_jobs([_sample_job("test-001")])

        db.update_status("test-001", "Applied")
        first = _table().select("applied_at").eq("id", "test-001").execute()
        applied_at = first.data[0]["applied_at"]
        assert applied_at is not None

        db.update_status("test-001", "Saved")
        second = _table().select("status, applied_at").eq("id", "test-001").execute()
        assert second.data[0]["status"] == "Saved"
        assert second.data[0]["applied_at"] == applied_at


class TestDeleteJob:
    def test_delete_job_removes_row(self):
        db.upsert_jobs([_sample_job("test-001")])
        assert db.fetch_known_ids(["test-001"]) == {"test-001"}

        db.delete_job("test-001")

        assert db.fetch_known_ids(["test-001"]) == set()


class TestFetchStats:
    def test_returns_fixed_status_keys(self):
        stats = db.fetch_stats()
        assert set(stats.keys()) == {
            "high_matched",
            "mid_matched",
            "Applied",
            "Saved",
            "Drop",
        }

    def test_counts_exact_rows_in_isolated_test_table(self):
        db.upsert_jobs(
            [
                _sample_job("test-001", status="high_matched"),
                _sample_job("test-002", status="high_matched"),
                _sample_job("test-003", status="Applied"),
                _sample_job("test-004", status="Saved"),
                _sample_job("test-005", status="Drop"),
            ]
        )

        stats = db.fetch_stats()
        assert stats["high_matched"] == 2
        assert stats["mid_matched"] == 0
        assert stats["Applied"] == 1
        assert stats["Saved"] == 1
        assert stats["Drop"] == 1
