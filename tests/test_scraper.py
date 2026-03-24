import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from unittest.mock import patch
from scraper import fetch_jobs


def _fake_df(n=3, prefix=""):
    return pd.DataFrame(
        [
            {
                "id": f"{prefix}{i}",
                "title": f"Engineer {i}",
                "company": "ACME",
                "date_posted": "2024-01-01",
                "job_url_direct": f"https://apply.example.com/{i}",
                "job_url": f"https://linkedin.com/jobs/view/{i}",
                "description": f"Description {i}",
                "location": "Dublin, Ireland",
            }
            for i in range(n)
        ]
    )


class TestFetchJobs:
    def test_returns_list_of_dicts(self):
        with patch("scraper.scrape_jobs", return_value=_fake_df(2)):
            results = fetch_jobs(queries=["Software Engineer"], delay_seconds=0)
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)

    def test_combines_multiple_queries(self):
        with patch(
            "scraper.scrape_jobs", side_effect=[_fake_df(2, "A"), _fake_df(2, "B")]
        ):
            results = fetch_jobs(queries=["SWE", "QA"], delay_seconds=0)
        assert len(results) == 4

    def test_returns_empty_list_on_all_failures(self):
        with patch("scraper.scrape_jobs", side_effect=Exception("Network error")):
            results = fetch_jobs(queries=["SWE"], delay_seconds=0)
        assert results == []

    def test_partial_failure_still_returns_successes(self):
        side_effects = [Exception("fail"), _fake_df(3)]
        with patch("scraper.scrape_jobs", side_effect=side_effects):
            results = fetch_jobs(queries=["Q1", "Q2"], delay_seconds=0)
        assert len(results) == 3

    def test_result_contains_expected_keys(self):
        with patch("scraper.scrape_jobs", return_value=_fake_df(1)):
            results = fetch_jobs(queries=["SWE"], delay_seconds=0)
        assert "id" in results[0]
        assert "title" in results[0]
        assert "description" in results[0]

    def test_empty_query_list_returns_empty(self):
        with patch("scraper.scrape_jobs") as mock_scrape:
            results = fetch_jobs(queries=[], delay_seconds=0)
        mock_scrape.assert_not_called()
        assert results == []
