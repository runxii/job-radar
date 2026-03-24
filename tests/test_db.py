"""
test_db.py - Integration tests for db.py against a real Supabase instance.

Setup before running:
  1. Create a Supabase project at https://supabase.com (free tier is fine)
  2. Run the SQL in db.py docstring inside the Supabase SQL editor
  3. Export credentials:
       export SUPABASE_URL=https://xxxx.supabase.co
       export SUPABASE_KEY=your-anon-key
  4. Run:
       pytest tests/test_db.py -v

These tests write and delete real rows. They are isolated by using
ids prefixed with 'test-' and cleaned up in teardown.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timezone

# Skip entire module if credentials are not set
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"),
    reason="SUPABASE_URL and SUPABASE_KEY not set - skipping integration tests"
)

import db

# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #

TEST_IDS = ["test-001", "test-002", "test-003"]

def _sample_job(job_id: str, score: float = 0.75, status: str = "high_matched") -> dict:
    return {
        "id":          job_id,
        "title":       "Test Software Engineer",
        "company":     "Test Corp",
        "post_url":    f"https://linkedin.com/jobs/view/{job_id}",
        "description": "A test job description.",
        "location":    "Dublin, Ireland",
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
        "match_score": score,
        "status":      status,
    }


@pytest.fixture(autouse=True)
def cleanup():
    """Delete test rows before and after every test."""
    _delete_test_rows()
    yield
    _delete_test_rows()


def _delete_test_rows():
    client = db.get_client()
    for tid in TEST_IDS:
        client.table("jobs").delete().eq("id", tid).execute()


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #

class TestUpsertJobs:
    def test_insert_single_record(self):
        db.upsert_jobs([_sample_job("test-001")])
        ids = db.fetch_known_ids()
        assert "test-001" in ids

    def test_insert_multiple_records(self):
        db.upsert_jobs([_sample_job("test-001"), _sample_job("test-002")])
        ids = db.fetch_known_ids()
        assert "test-001" in ids
        assert "test-002" in ids

    def test_upsert_updates_existing(self):
        db.upsert_jobs([_sample_job("test-001", score=0.5)])
        db.upsert_jobs([_sample_job("test-001", score=0.9)])
        client = db.get_client()
        row = client.table("jobs").select("match_score").eq("id", "test-001").execute()
        assert abs(row.data[0]["match_score"] - 0.9) < 1e-6

    def test_empty_list_is_noop(self):
        db.upsert_jobs([])   # should not raise


class TestFetchKnownIds:
    def test_returns_set(self):
        result = db.fetch_known_ids()
        assert isinstance(result, set)

    def test_contains_inserted_id(self):
        db.upsert_jobs([_sample_job("test-001")])
        ids = db.fetch_known_ids()
        assert "test-001" in ids

    def test_does_not_contain_uninserted_id(self):
        ids = db.fetch_known_ids()
        assert "test-999-nonexistent" not in ids


class TestFetchNextJob:
    def test_returns_highest_score_first(self):
        db.upsert_jobs([
            _sample_job("test-001", score=0.5, status="high_matched"),
            _sample_job("test-002", score=0.9, status="high_matched"),
        ])
        job = db.fetch_next_job()
        assert job is not None
        assert job["id"] == "test-002"

    def test_returns_none_when_no_pending(self):
        db.upsert_jobs([_sample_job("test-001", status="Drop")])
        job = db.fetch_next_job(statuses=["high_matched", "mid_matched"])
        # test-001 has status Drop so should not be returned
        assert job is None or job["id"] != "test-001"

    def test_returns_none_on_empty_table(self):
        # cleanup fixture ensures no test rows exist
        job = db.fetch_next_job(statuses=["nonexistent-status"])
        assert job is None


class TestUpdateStatus:
    def test_updates_to_applied(self):
        db.upsert_jobs([_sample_job("test-001")])
        db.update_status("test-001", "Applied")
        client = db.get_client()
        row = client.table("jobs").select("status").eq("id", "test-001").execute()
        assert row.data[0]["status"] == "Applied"

    # def test_updates_to_skipped(self):
    #     db.upsert_jobs([_sample_job("test-001")])
    #     db.update_status("test-001", "Skipped")
    #     client = db.get_client()
    #     row = client.table("jobs").select("status").eq("id", "test-001").execute()
    #     assert row.data[0]["status"] == "Skipped"

    def test_updates_to_saved(self):
        db.upsert_jobs([_sample_job("test-001")])
        db.update_status("test-001", "Saved")
        client = db.get_client()
        row = client.table("jobs").select("status").eq("id", "test-001").execute()
        assert row.data[0]["status"] == "Saved"


class TestFetchStats:
    def test_returns_dict(self):
        result = db.fetch_stats()
        assert isinstance(result, dict)

    def test_counts_are_correct(self):
        db.upsert_jobs([
            _sample_job("test-001", status="high_matched"),
            _sample_job("test-002", status="high_matched"),
            _sample_job("test-003", status="Drop"),
        ])
        stats = db.fetch_stats()
        # These counts may include rows from real data, so just check >= not ==
        assert stats.get("high_matched", 0) >= 2
        assert stats.get("Drop", 0) >= 1