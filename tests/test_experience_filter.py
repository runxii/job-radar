import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from experience_filter import (
    title_implies_senior,
    extract_explicit_years,
    annotate_experience,
    filter_by_experience,
)


class TestTitleImpliesSenior:
    @pytest.mark.parametrize(
        "title",
        [
            "Principal Engineer",
            "Lead Software Engineer",
            "Head of Engineering",
            "Engineering Director",
            "Engineering Manager",
            "LEAD developer",
            "VP of Engineering",  # 'VP' not in list - should NOT match (see below)
        ],
    )
    def test_senior_titles(self, title):
        # VP is not in the keyword list, only principal/lead/head/director/manager
        if "VP" in title:
            assert title_implies_senior(title) is False
        else:
            assert title_implies_senior(title) is True

    @pytest.mark.parametrize(
        "title",
        [
            "Software Engineer",
            "Graduate Engineer",
            "Junior Developer",
            "QA Engineer",
            "Technical Support Engineer",
            "",
        ],
    )
    def test_non_senior_titles(self, title):
        assert title_implies_senior(title) is False


class TestExtractExplicitYears:
    @pytest.mark.parametrize(
        "text, expected_years",
        [
            ("3\\+ years of experience required", 3),
            ("minimum 5 years of relevant experience", 5),
            ("at least 4 years experience", 4),
            ("over 7 years of experience", 7),
            ("more than 6 years in software development", 6),
            ("2-4 years of experience", 2),  # range → minimum
            ("10\\+ yoe required", 10),
            ("requires 8 years with Python", 8),
            ("5 years' experience in cloud", 5),
            ("1 year of experience", 1),
            ("2 years relevant professional experience", 2),
            ("7\\+ years of experience in software", 7),
            ("Minimum of 4 years of relevant technical experience", 4),
            ("3 – 5 years’ progressive experience in", 5),
        ],
    )
    def test_explicit_patterns(self, text, expected_years):
        result = extract_explicit_years(text)
        assert result["years"] == expected_years
        assert result["explicit"] is True
        assert result["evidence"] != ""

    @pytest.mark.parametrize(
        "text",
        [
            "No experience required",
            "Fresh graduates welcome",
            "Entry level position",
            "",
            "   ",
        ],
    )
    def test_no_years_found(self, text):
        result = extract_explicit_years(text)
        assert result["years"] == 0
        assert result["explicit"] is False

    def test_picks_minimum_from_multiple_mentions(self):
        text = "5+ years experience preferred, but 2 years of experience minimum"
        result = extract_explicit_years(text)
        assert result["years"] == 2

    def test_ignores_absurd_values(self):
        result = extract_explicit_years("50 years of experience needed")
        assert result["years"] == 0  # >40 is ignored


class TestAnnotateExperience:
    def _job(self, title="Software Engineer", description=""):
        return {"id": "1", "title": title, "description": description}

    def test_senior_title_overrides_description(self):
        job = self._job(
            title="Lead Engineer", description="2 years experience required"
        )
        result = annotate_experience(job)
        assert result["explicit_years_required"] == 10
        assert result["is_explicit_exp_requirement"] is False
        assert result["exp_evidence"] == "Lead Engineer"

    def test_extracts_from_description(self):
        job = self._job(description="We need 3+ years of experience in Python.")
        result = annotate_experience(job)
        assert result["explicit_years_required"] == 3
        assert result["is_explicit_exp_requirement"] is True

    def test_no_requirement_gives_zero(self):
        job = self._job(description="Great place to work. Fresh grads welcome.")
        result = annotate_experience(job)
        assert result["explicit_years_required"] == 0
        assert result["is_explicit_exp_requirement"] is False

    def test_original_dict_not_mutated(self):
        job = {"id": "2", "title": "Dev", "description": "5 years experience"}
        _ = annotate_experience(job)
        assert "explicit_years_required" not in job


class TestFilterByExperience:
    def _job(self, job_id, description=""):
        return {"id": job_id, "title": "Engineer", "description": description}

    def test_splits_correctly(self):
        jobs = [
            self._job("1", "No experience required"),
            self._job("2", "2+ years of experience"),
            self._job("3", "5+ years of experience"),  # should be filtered out
            self._job("4", "10+ years of experience"),  # should be filtered out
        ]
        matched, unmatched = filter_by_experience(jobs, max_years=3)
        matched_ids = {j["id"] for j in matched}
        unmatched_ids = {j["id"] for j in unmatched}
        assert matched_ids == {"1", "2"}
        assert unmatched_ids == {"3", "4"}

    def test_empty_input(self):
        matched, unmatched = filter_by_experience([], max_years=3)
        assert matched == []
        assert unmatched == []

    def test_all_match(self):
        jobs = [self._job(str(i), "entry level") for i in range(5)]
        matched, unmatched = filter_by_experience(jobs, max_years=3)
        assert len(matched) == 5
        assert len(unmatched) == 0

    def test_senior_title_always_unmatched(self):
        jobs = [
            {"id": "X", "title": "Principal Engineer", "description": "entry level"}
        ]
        matched, unmatched = filter_by_experience(jobs, max_years=3)
        assert len(matched) == 0
        assert len(unmatched) == 1
