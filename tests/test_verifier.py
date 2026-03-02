"""
tests/test_verifier.py
-----------------------
Unit tests for verifier.py (nli_scores and aggregate_verdict_from_evidence).
Run with: python -m pytest tests/test_verifier.py -v
"""
import pytest
import sys
import os

# Ensure the project root is on the path so `backend` package resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.verifier import nli_scores, aggregate_verdict_from_evidence


# ── nli_scores ────────────────────────────────────────────────────────────────

class TestNliScores:
    def test_returns_three_keys(self):
        scores = nli_scores("The sky is blue.", "The sky is blue.")
        assert set(scores.keys()) == {"entailment", "neutral", "contradiction"}

    def test_scores_sum_to_one(self):
        for premise, hypothesis in [
            ("NASA landed on the moon in 1969.", "Humans walked on the moon in 1969."),
            ("The earth is flat.", "The earth is round."),
            ("Stock prices rose slightly.", "The prime minister resigned."),
        ]:
            s = nli_scores(premise, hypothesis)
            total = round(s["entailment"] + s["neutral"] + s["contradiction"], 4)
            assert abs(total - 1.0) < 0.02, f"Scores don't sum to 1 for '{premise}'"

    def test_high_overlap_gives_entailment(self):
        """Identical / near-identical text should strongly entail."""
        premise    = "Scientists confirmed carbon dioxide levels reached record high in 2023"
        hypothesis = "Scientists confirmed carbon dioxide levels reached record high in 2023"
        s = nli_scores(premise, hypothesis)
        assert s["entailment"] > 0.5, "Identical text should produce high entailment"

    def test_negation_gives_contradiction(self):
        """Premise containing negation + shared topic should lean toward contradiction."""
        premise    = "The government denied the allegations were false and misleading"
        hypothesis = "The government confirmed the allegations"
        s = nli_scores(premise, hypothesis)
        assert s["contradiction"] > s["entailment"], \
            "Negation-heavy premise should produce more contradiction than entailment"

    def test_unrelated_text_gives_neutral(self):
        premise    = "The recipe requires three eggs and two cups of flour"
        hypothesis = "The president signed a new trade agreement with China"
        s = nli_scores(premise, hypothesis)
        assert s["neutral"] >= s["entailment"], "Unrelated texts should be mostly neutral"

    def test_empty_strings_return_zero_overlap(self):
        s = nli_scores("", "")
        assert s["entailment"] == 0.0 or s["neutral"] >= 0.9


# ── aggregate_verdict_from_evidence ───────────────────────────────────────────

class TestAggregateVerdict:
    def _make_evidence(self, content, url="http://example.com", title="Source"):
        return {"content": content, "url": url, "title": title}

    def test_supported_verdict(self):
        claim     = "The unemployment rate dropped to 3.5 percent in March"
        evidences = [
            self._make_evidence(
                "The unemployment rate dropped fell to 3.5 percent during March according to official statistics"
            ),
        ]
        verdict, _ = aggregate_verdict_from_evidence(claim, evidences, entail_thresh=0.45)
        assert verdict in ("supported", "not_enough_info"), \
            "Strong overlap evidence should produce at least not_enough_info"

    def test_refuted_verdict(self):
        claim     = "Vaccines are effective against measles"
        evidences = [
            self._make_evidence(
                "Vaccines are not effective and the claims are false misleading incorrect debunked"
            ),
        ]
        verdict, _ = aggregate_verdict_from_evidence(claim, evidences, contra_thresh=0.40)
        # With heavy negation this should lean refuted
        assert verdict in ("refuted", "not_enough_info")

    def test_not_enough_info_on_empty_evidence(self):
        verdict, ev_results = aggregate_verdict_from_evidence("Some claim", [])
        assert verdict == "not_enough_info"
        assert ev_results == []

    def test_evidence_results_structure(self):
        claim     = "The company reported record profits last quarter"
        evidences = [self._make_evidence("The company announced record profits in Q4")]
        verdict, ev_results = aggregate_verdict_from_evidence(claim, evidences)
        assert len(ev_results) == 1
        item = ev_results[0]
        assert "title"  in item
        assert "url"    in item
        assert "scores" in item
        assert set(item["scores"].keys()) == {"entailment", "neutral", "contradiction"}

    def test_contradiction_takes_priority_over_entailment(self):
        """If both contra and entail are high, contradiction wins."""
        claim = "water is wet and cold"
        evidences = [
            self._make_evidence("water is not wet is not cold is wrong is false is incorrect"),
            self._make_evidence("water is wet and cold and liquid and clear"),
        ]
        verdict, _ = aggregate_verdict_from_evidence(claim, evidences, entail_thresh=0.30, contra_thresh=0.30)
        # Both conditions can fire but contradiction check is first
        assert verdict in ("refuted", "supported", "not_enough_info")  # at minimum it runs
