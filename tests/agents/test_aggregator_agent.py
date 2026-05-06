"""
tests/agents/test_aggregator_agent.py
---------------------------------------
Unit tests for the aggregator agent's scoring helpers and DB/WS utilities.
All DB and Redis calls are mocked — no running infrastructure needed.

Run:
    python -m pytest tests/agents/test_aggregator_agent.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
from unittest.mock import patch, MagicMock

from backend.agents.aggregator_agent import (
    _doc_status,
    _credibility_score,
    run_aggregator,
)


# ── _doc_status ───────────────────────────────────────────────────────────────

class TestDocStatus:
    def test_empty_results_returns_not_enough_info(self):
        assert _doc_status([]) == "not_enough_info"

    def test_all_supported_returns_clean(self):
        results = [
            {"verdict": "supported"},
            {"verdict": "not_enough_info"},
        ]
        assert _doc_status(results) == "clean_document"

    def test_any_refuted_returns_inaccuracies(self):
        results = [
            {"verdict": "supported"},
            {"verdict": "refuted"},
        ]
        assert _doc_status(results) == "inaccuracies_found"

    def test_all_not_enough_info_returns_clean(self):
        results = [{"verdict": "not_enough_info"}] * 5
        assert _doc_status(results) == "clean_document"


# ── _credibility_score ────────────────────────────────────────────────────────

class TestCredibilityScore:
    def test_empty_returns_50(self):
        assert _credibility_score([]) == 50

    def test_all_supported_returns_high(self):
        results = [{"verdict": "supported"}] * 5
        score = _credibility_score(results)
        assert score > 70, f"All supported should score >70, got {score}"

    def test_all_refuted_returns_low(self):
        results = [{"verdict": "refuted"}] * 5
        score = _credibility_score(results)
        assert score < 30, f"All refuted should score <30, got {score}"

    def test_mixed_returns_around_50(self):
        results = [{"verdict": "supported"}, {"verdict": "refuted"}]
        score = _credibility_score(results)
        assert 30 <= score <= 70

    def test_score_clamped_0_to_100(self):
        results = [{"verdict": "supported"}] * 100
        assert _credibility_score(results) <= 100
        results = [{"verdict": "refuted"}] * 100
        assert _credibility_score(results) >= 0


# ── run_aggregator ────────────────────────────────────────────────────────────

class TestRunAggregator:
    def _build_phase2_results(self, num_claims=2):
        verifier_results = [
            {"claim": f"Claim {i}", "verdict": "supported", "evidence": []}
            for i in range(num_claims)
        ]
        coverage = [{"title": "Reuters", "domain": "reuters.com", "bias": "Center"}]
        return verifier_results + [coverage]

    def test_assembles_correct_payload_structure(self):
        parser_result = {"text": "Article body text.", "title": "Test Article", "publish_date": "2024-01-01"}
        source_info   = {"domain": "bbc.com", "bias": "Center", "factual_reporting": "High",
                         "political_leaning_score": -0.05, "country": "UK", "logo_url": "", "description": ""}
        claims = ["Claim 0", "Claim 1"]

        with patch("backend.agents.aggregator_agent._write_to_db"), \
             patch("backend.agents.aggregator_agent._update_job_status"), \
             patch("backend.agents.aggregator_agent._publish_ws"):
            json_str = run_aggregator.run(
                self._build_phase2_results(num_claims=2),
                url="https://bbc.com/test",
                job_id="test-job-id",
                parser_result=parser_result,
                source_info=source_info,
                claims=claims,
            )

        result = json.loads(json_str)
        assert "status"            in result
        assert "credibility_score" in result
        assert "article_title"     in result
        assert "source_analysis"   in result
        assert "related_coverage"  in result
        assert "results"           in result
        assert result["article_title"] == "Test Article"
        assert len(result["results"]) == 2

    def test_coverage_separated_from_verifier_results(self):
        parser_result = {"text": "", "title": "T", "publish_date": ""}
        source_info   = {"domain": "x.com", "bias": "N/A", "factual_reporting": "N/A",
                         "political_leaning_score": None, "country": None, "logo_url": None, "description": None}
        claims = ["Claim A"]
        phase2 = [{"claim": "Claim A", "verdict": "not_enough_info", "evidence": []}] + \
                 [[{"title": "BBC", "domain": "bbc.com"}]]

        with patch("backend.agents.aggregator_agent._write_to_db"), \
             patch("backend.agents.aggregator_agent._update_job_status"), \
             patch("backend.agents.aggregator_agent._publish_ws"):
            json_str = run_aggregator.run(
                phase2, url="", job_id="x", parser_result=parser_result,
                source_info=source_info, claims=claims,
            )

        result = json.loads(json_str)
        assert len(result["results"]) == 1
        assert isinstance(result["related_coverage"], list)

    def test_calls_write_to_db_when_url_provided(self):
        parser_result = {"text": "", "title": "T", "publish_date": ""}
        source_info   = {"domain": "test.com", "bias": "N/A", "factual_reporting": "N/A",
                         "political_leaning_score": None, "country": None, "logo_url": None, "description": None}

        with patch("backend.agents.aggregator_agent._write_to_db") as mock_db, \
             patch("backend.agents.aggregator_agent._update_job_status"), \
             patch("backend.agents.aggregator_agent._publish_ws"):
            run_aggregator.run(
                [[]], url="https://test.com/article", job_id="j",
                parser_result=parser_result, source_info=source_info, claims=[],
            )
        mock_db.assert_called_once()

    def test_skips_write_to_db_when_no_url(self):
        parser_result = {"text": "", "title": "", "publish_date": ""}
        source_info   = {"domain": "Pasted Text", "bias": "N/A", "factual_reporting": "N/A",
                         "political_leaning_score": None, "country": None, "logo_url": None, "description": None}

        with patch("backend.agents.aggregator_agent._write_to_db") as mock_db, \
             patch("backend.agents.aggregator_agent._update_job_status"), \
             patch("backend.agents.aggregator_agent._publish_ws"):
            run_aggregator.run(
                [[]], url="", job_id="j",
                parser_result=parser_result, source_info=source_info, claims=[],
            )
        mock_db.assert_not_called()

    def test_publishes_ws_event(self):
        parser_result = {"text": "", "title": "", "publish_date": ""}
        source_info   = {"domain": "x", "bias": "N/A", "factual_reporting": "N/A",
                         "political_leaning_score": None, "country": None, "logo_url": None, "description": None}

        with patch("backend.agents.aggregator_agent._write_to_db"), \
             patch("backend.agents.aggregator_agent._update_job_status"), \
             patch("backend.agents.aggregator_agent._publish_ws") as mock_ws:
            run_aggregator.run(
                [[]], url="", job_id="ws-test-id",
                parser_result=parser_result, source_info=source_info, claims=[],
            )
        mock_ws.assert_called_once()
        call_args = mock_ws.call_args[0]
        assert call_args[0] == "ws-test-id"
