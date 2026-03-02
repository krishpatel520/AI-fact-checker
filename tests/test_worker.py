"""
tests/test_worker.py
---------------------
Unit tests for private helpers in worker.py.
Run with: python -m pytest tests/test_worker.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the private helpers directly from the module
from backend.worker import _doc_status, _credibility_score


class TestDocStatus:
    def test_empty_results_returns_not_enough_info(self):
        assert _doc_status([]) == "not_enough_info"

    def test_all_supported_returns_clean(self):
        results = [
            {"verdict": "supported"},
            {"verdict": "supported"},
            {"verdict": "not_enough_info"},
        ]
        assert _doc_status(results) == "clean_document"

    def test_one_refuted_returns_inaccuracies(self):
        results = [
            {"verdict": "supported"},
            {"verdict": "refuted"},
        ]
        assert _doc_status(results) == "inaccuracies_found"

    def test_all_not_enough_info_returns_clean(self):
        results = [{"verdict": "not_enough_info"}, {"verdict": "not_enough_info"}]
        assert _doc_status(results) == "clean_document"


class TestCredibilityScore:
    def test_empty_results_returns_50(self):
        assert _credibility_score([]) == 50

    def test_all_supported_returns_high(self):
        results = [{"verdict": "supported"}] * 5
        score = _credibility_score(results)
        assert score >= 80

    def test_all_refuted_returns_low(self):
        results = [{"verdict": "refuted"}] * 5
        score = _credibility_score(results)
        assert score <= 20

    def test_mixed_returns_midrange(self):
        results = [
            {"verdict": "supported"},
            {"verdict": "refuted"},
            {"verdict": "not_enough_info"},
        ]
        score = _credibility_score(results)
        assert 0 <= score <= 100

    def test_score_clamped_between_0_and_100(self):
        for verdicts in [["supported"]*20, ["refuted"]*20, []]:
            score = _credibility_score([{"verdict": v} for v in verdicts])
            assert 0 <= score <= 100
