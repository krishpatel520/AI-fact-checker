"""
tests/agents/test_verifier_agent.py
------------------------------------
Unit tests for the verifier agent.

Tests are isolated — no real Ollama or Serper calls.
External dependencies are mocked using pytest monkeypatch / unittest.mock.

Run:
    python -m pytest tests/agents/test_verifier_agent.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unittest.mock import patch, MagicMock
from backend.agents.verifier_agent import _llm_nli, _heuristic_nli, run_verifier


# ── _llm_nli ──────────────────────────────────────────────────────────────────

class TestLlmNli:
    def test_returns_none_on_connection_error(self):
        """Ollama unavailable → returns None (triggers fallback)."""
        with patch("backend.agents.verifier_agent._requests.post", side_effect=ConnectionError("offline")):
            result = _llm_nli("The earth is round.", "The earth is a sphere.")
        assert result is None

    def test_returns_none_on_invalid_json(self):
        """Malformed Ollama response → returns None."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "not valid json {{"}
        mock_resp.raise_for_status = MagicMock()
        with patch("backend.agents.verifier_agent._requests.post", return_value=mock_resp):
            result = _llm_nli("claim", "evidence")
        assert result is None

    def test_returns_none_on_invalid_verdict(self):
        """Ollama returns an unrecognised verdict field → returns None."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": '{"verdict": "maybe", "confidence": 0.5, "reason": "unsure"}'}
        mock_resp.raise_for_status = MagicMock()
        with patch("backend.agents.verifier_agent._requests.post", return_value=mock_resp):
            result = _llm_nli("claim", "evidence")
        assert result is None

    def test_valid_supported_response(self):
        """Well-formed Ollama 'supported' response is parsed correctly."""
        payload = '{"verdict": "supported", "confidence": 0.92, "reason": "Evidence confirms the claim."}'
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": payload}
        mock_resp.raise_for_status = MagicMock()
        with patch("backend.agents.verifier_agent._requests.post", return_value=mock_resp):
            result = _llm_nli("The sky is blue.", "The sky appears blue due to Rayleigh scattering.")
        assert result is not None
        assert result["verdict"] == "supported"
        assert result["confidence"] == 0.92
        assert "Evidence" in result["reason"]

    def test_valid_refuted_response(self):
        payload = '{"verdict": "refuted", "confidence": 0.88, "reason": "Evidence contradicts the claim."}'
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": payload}
        mock_resp.raise_for_status = MagicMock()
        with patch("backend.agents.verifier_agent._requests.post", return_value=mock_resp):
            result = _llm_nli("Vaccines cause autism.", "Studies show no link between vaccines and autism.")
        assert result["verdict"] == "refuted"


# ── _heuristic_nli ────────────────────────────────────────────────────────────

class TestHeuristicNli:
    def test_returns_dict_with_required_keys(self):
        result = _heuristic_nli("The unemployment rate fell to 3.5%.",
                                "The unemployment rate fell to 3.5 percent in March.")
        assert "verdict"    in result
        assert "confidence" in result
        assert "reason"     in result
        assert "method"     in result
        assert result["method"] == "heuristic"

    def test_verdict_is_valid_value(self):
        result = _heuristic_nli("COVID vaccines are safe.", "Studies confirm vaccine safety.")
        assert result["verdict"] in ("supported", "refuted", "not_enough_info")

    def test_confidence_between_0_and_1(self):
        result = _heuristic_nli("The president signed the bill.", "The president vetoed the legislation.")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_unrelated_texts_give_low_confidence_support(self):
        result = _heuristic_nli("Cats are mammals.", "The stock market rose sharply yesterday.")
        assert result["verdict"] in ("not_enough_info", "supported")


# ── run_verifier (Celery task) ────────────────────────────────────────────────

class TestRunVerifier:
    def _mock_evidence(self):
        return [
            {"title": "Reuters", "content": "GDP grew by 3.2% in Q3.", "url": "https://reuters.com/1"},
            {"title": "AP News", "content": "Economic growth reached 3.2% last quarter.", "url": "https://apnews.com/1"},
        ]

    def test_returns_claim_and_verdict(self):
        claim = "The economy grew by 3.2% last quarter."
        with patch("backend.agents.verifier_agent.retrieve_from_trusted_sources", return_value=self._mock_evidence()), \
             patch("backend.agents.verifier_agent._llm_nli", return_value={
                 "verdict": "supported", "confidence": 0.91, "reason": "Evidence confirms growth."
             }):
            result = run_verifier.run(claim)

        assert result["claim"] == claim
        assert result["verdict"] in ("supported", "refuted", "not_enough_info")
        assert isinstance(result["evidence"], list)

    def test_falls_back_to_heuristic_when_ollama_fails(self):
        claim = "The economy grew by 3.2% last quarter."
        with patch("backend.agents.verifier_agent.retrieve_from_trusted_sources", return_value=self._mock_evidence()), \
             patch("backend.agents.verifier_agent._llm_nli", return_value=None):
            result = run_verifier.run(claim)

        # Should still have results (heuristic fallback ran)
        assert len(result["evidence"]) > 0
        assert result["evidence"][0]["method"] == "heuristic"

    def test_no_evidence_gives_not_enough_info(self):
        claim = "Some obscure claim no one has written about."
        with patch("backend.agents.verifier_agent.retrieve_from_trusted_sources", return_value=[]):
            result = run_verifier.run(claim)

        assert result["verdict"] == "not_enough_info"
        assert result["evidence"] == []

    def test_evidence_items_have_required_fields(self):
        claim = "The earth orbits the sun."
        with patch("backend.agents.verifier_agent.retrieve_from_trusted_sources", return_value=self._mock_evidence()), \
             patch("backend.agents.verifier_agent._llm_nli", return_value={
                 "verdict": "supported", "confidence": 0.95, "reason": "Confirmed."
             }):
            result = run_verifier.run(claim)

        for ev in result["evidence"]:
            assert "title"      in ev
            assert "url"        in ev
            assert "verdict"    in ev
            assert "confidence" in ev
            assert "reason"     in ev
            assert "method"     in ev
