import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from unittest.mock import MagicMock, patch
from ai_scorer import _parse_response, _label, score_job, score_jobs


class TestLabel:
    def test_high_matched(self):
        assert _label(0.7) == "high_matcheded"
        assert _label(0.90) == "high_matcheded"
        assert _label(1.00) == "high_matcheded"

    def test_mid_match(self):
        assert _label(0.40) == "mid_matched"
        assert _label(0.50) == "mid_matched"
        assert _label(0.69) == "mid_matched"

    def test_low_match(self):
        assert _label(0.00) == "Drop"
        assert _label(0.39) == "Drop"


class TestParseResponse:
    def test_clean_json(self):
        raw = '{"id": "123", "stack_match": 0.8, "res_match": 0.7, "engi_match": 0.6, "overall_fit": 0.7}'
        result = _parse_response(raw)
        assert result["overall_fit"] == pytest.approx(0.7)
        assert result["stack_match"] == pytest.approx(0.8)

    def test_strips_markdown_fences(self):
        raw = '```json\n{"id": "1", "overall_fit": 0.5}\n```'
        result = _parse_response(raw)
        assert result["overall_fit"] == pytest.approx(0.5)

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response("not json at all")


class TestScoreJob:
    def _make_job(self):
        return {"id": "42", "title": "SWE", "description": "Python, AWS, Docker"}

    def _make_mock_client(self, overall_fit: float):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps({
            "id": "42",
            "stack_match": overall_fit,
            "res_match": overall_fit,
            "engi_match": overall_fit,
            "overall_fit": overall_fit,
        })
        client = MagicMock()
        client.chat.completions.create.return_value = mock_resp
        return client

    def test_ai_apply_label(self):
        client = self._make_mock_client(0.80)
        result = score_job(self._make_job(), "My great CV", client)
        assert result["match_score"] == pytest.approx(0.80)
        assert result["status"] == "high_matcheded"

    def test_human_apply_label(self):
        client = self._make_mock_client(0.55)
        result = score_job(self._make_job(), "My great CV", client)
        assert result["status"] == "mid_matched"

    def test_drop_label(self):
        client = self._make_mock_client(0.20)
        result = score_job(self._make_job(), "My great CV", client)
        assert result["status"] == "Drop"

    def test_skills_required_is_valid_json(self):
        client = self._make_mock_client(0.70)
        result = score_job(self._make_job(), "CV", client)
        skills = json.loads(result["skills_required"])
        assert "stack" in skills
        assert "responsibility" in skills
        assert "engineering" in skills

    def test_original_job_fields_preserved(self):
        client = self._make_mock_client(0.70)
        job = self._make_job()
        result = score_job(job, "CV", client)
        assert result["title"] == "SWE"
        assert result["description"] == "Python, AWS, Docker"


class TestScoreJobs:
    def _make_job(self, job_id):
        return {"id": job_id, "title": "Dev", "description": "Python"}

    def test_failed_job_gets_drop_status(self):
        """If OpenAI raises, the job should be added with status=Drop instead of crashing."""
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API error")

        with patch("ai_scorer.OpenAI", return_value=client), \
             patch("ai_scorer.config.OPENAI_API_KEY", "fake-key"):
            results = score_jobs([self._make_job("1")], "CV", delay_seconds=0)

        assert len(results) == 1
        assert results[0]["status"] == "Drop"
        assert results[0]["match_score"] == 0.0

    def test_processes_all_jobs(self):
        response_json = json.dumps({"id": "x", "stack_match": 0.7,
                                    "res_match": 0.7, "engi_match": 0.7, "overall_fit": 0.7})
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = response_json
        client = MagicMock()
        client.chat.completions.create.return_value = mock_resp

        jobs = [self._make_job(str(i)) for i in range(3)]
        with patch("ai_scorer.OpenAI", return_value=client), \
             patch("ai_scorer.config.OPENAI_API_KEY", "fake-key"):
            results = score_jobs(jobs, "CV", delay_seconds=0)

        assert len(results) == 3
