import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cleaner import clean_job, clean_jobs


class TestCleanJob:
    def test_basic_mapping(self):
        raw = {
            "id": "123",
            "title": "Software Engineer",
            "company": "ACME",
            "date_posted": "2024-01-01",
            "job_url_direct": "https://apply.example.com",
            "job_url": "https://linkedin.com/jobs/view/123",
            "description": "Great job",
            "location": "Dublin, Ireland",
        }
        result = clean_job(raw)
        assert result["id"] == "123"
        assert result["title"] == "Software Engineer"
        assert result["company"] == "ACME"
        assert result["apply_url"] == "https://apply.example.com"
        assert result["post_url"] == "https://linkedin.com/jobs/view/123"
        assert result["description"] == "Great job"
        assert result["location"] == "Dublin, Ireland"
        assert result["applicants"] == "N/A"

    def test_none_fields_become_na(self):
        raw = {"id": "1", "title": None, "company": None, "date_posted": None,
               "job_url_direct": None, "job_url": None, "description": None, "location": None}
        result = clean_job(raw)
        assert result["title"] == "N/A"
        assert result["company"] == "N/A"
        assert result["location"] == "N/A"

    def test_nan_string_becomes_na(self):
        raw = {"id": "2", "title": "nan", "company": "NaN", "date_posted": "",
               "job_url_direct": "nan", "job_url": None, "description": "", "location": "nan"}
        result = clean_job(raw)
        assert result["title"] == "N/A"
        assert result["company"] == "N/A"
        assert result["apply_url"] == "N/A"

    def test_post_url_constructed_from_id_when_missing(self):
        raw = {"id": "99999", "title": "Dev", "company": "X",
               "date_posted": None, "job_url_direct": None, "job_url": None,
               "description": "", "location": ""}
        result = clean_job(raw)
        assert result["post_url"] == "https://www.linkedin.com/jobs/view/99999"

    def test_description_fallback_is_empty_string(self):
        raw = {"id": "5", "title": "T", "company": "C", "date_posted": None,
               "job_url_direct": None, "job_url": None, "description": None, "location": None}
        result = clean_job(raw)
        assert result["description"] == ""


class TestCleanJobs:
    def _make_raw(self, job_id, title="Dev"):
        return {"id": job_id, "title": title, "company": "Co", "date_posted": "2024-01-01",
                "job_url_direct": None, "job_url": None, "description": "desc", "location": "IE"}

    def test_deduplication_by_id(self):
        raws = [self._make_raw("A"), self._make_raw("A"), self._make_raw("B")]
        cleaned, deduped = clean_jobs(raws)
        assert len(cleaned) == 3       # all normalised
        assert len(deduped) == 2       # duplicates removed

    def test_empty_input(self):
        cleaned, deduped = clean_jobs([])
        assert cleaned == []
        assert deduped == []

    def test_all_unique(self):
        raws = [self._make_raw(str(i)) for i in range(5)]
        cleaned, deduped = clean_jobs(raws)
        assert len(cleaned) == len(deduped) == 5

    def test_first_occurrence_kept_on_dup(self):
        raws = [self._make_raw("X", "First"), self._make_raw("X", "Second")]
        _, deduped = clean_jobs(raws)
        assert deduped[0]["title"] == "First"
