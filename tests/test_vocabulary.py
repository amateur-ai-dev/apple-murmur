"""
Tests for the IT domain vocabulary corrector.
rapidfuzz is mocked in conftest; tests patch murmur.vocabulary.process.extract
directly to control candidate lists without depending on fuzzy score thresholds.
kenlm_rescorer is patched at the murmur.kenlm_rescorer level (lazy import in correct()).
"""
from unittest.mock import patch, MagicMock


def _correct(text, candidates=None, has_lm=False, lm_score=None):
    """
    Call vocabulary.correct() with controlled rapidfuzz and kenlm responses.

    candidates: list of (word, score) tuples that process.extract returns
    has_lm: whether kenlm_rescorer.has_model() returns True
    lm_score: callable(text) -> float, or a constant float
    """
    from murmur import vocabulary
    if candidates is None:
        candidates = []
    # process.extract returns (match, score, index) triples
    extract_result = [(w, s, 0) for w, s in candidates]

    score_fn = lm_score if callable(lm_score) else (lambda t: lm_score or 0.0)

    with patch.object(vocabulary.process, "extract", return_value=extract_result), \
         patch("murmur.kenlm_rescorer.has_model", return_value=has_lm), \
         patch("murmur.kenlm_rescorer.score", side_effect=score_fn):
        return vocabulary.correct(text)


# ---------------------------------------------------------------------------
# No-op cases
# ---------------------------------------------------------------------------

def test_correct_returns_text_unchanged_when_no_candidates():
    assert _correct("hello world") == "hello world"


def test_correct_skips_tokens_shorter_than_3_chars():
    """Tokens of length < 3 are never looked up."""
    from murmur import vocabulary
    with patch.object(vocabulary.process, "extract", return_value=[]) as mock_extract, \
         patch("murmur.kenlm_rescorer.has_model", return_value=False):
        _correct("hi to go")
    calls = [call[0][0] for call in mock_extract.call_args_list]
    assert "hi" not in calls
    assert "to" not in calls
    assert "go" not in calls


def test_correct_skips_tokens_already_in_vocab():
    """Exact vocab members should not be looked up."""
    from murmur import vocabulary
    with patch.object(vocabulary.process, "extract", return_value=[]) as mock_extract, \
         patch("murmur.kenlm_rescorer.has_model", return_value=False):
        _correct("ITIL SLA MTTR")
    assert mock_extract.call_count == 0


# ---------------------------------------------------------------------------
# Substitution without LM
# ---------------------------------------------------------------------------

def test_correct_substitutes_above_threshold():
    result = _correct("servic now", candidates=[("ServiceNow", 92)])
    assert "ServiceNow" in result


def test_correct_does_not_substitute_below_threshold():
    # Score 80 < _THRESHOLD (88)
    result = _correct("foobar", candidates=[("firewall", 80)])
    assert result == "foobar"


def test_correct_applies_first_candidate_when_no_lm():
    """Without LM, the highest-scored eligible candidate wins."""
    result = _correct("incedent", candidates=[("incident", 95), ("endpoint", 89)])
    assert result == "incident"


# ---------------------------------------------------------------------------
# Single-candidate LM validation (the bug that was fixed)
# ---------------------------------------------------------------------------

def test_correct_lm_single_candidate_applied_when_score_improves():
    """LM should validate even a single candidate — apply if log-prob improves."""
    scores = {"incedent": -10.0, "incident": -8.0}
    result = _correct(
        "incedent",
        candidates=[("incident", 95)],
        has_lm=True,
        lm_score=lambda t: scores.get(t.split()[-1], -10.0),
    )
    assert result == "incident"


def test_correct_lm_single_candidate_rejected_when_score_worsens():
    """LM should reject the candidate if it makes the sentence less likely."""
    scores = {"incedent": -8.0, "incident": -10.0}  # original is better
    result = _correct(
        "incedent",
        candidates=[("incident", 95)],
        has_lm=True,
        lm_score=lambda t: scores.get(t.split()[-1], -10.0),
    )
    assert result == "incedent"


def test_correct_lm_picks_best_among_multiple_candidates():
    """LM should pick the candidate with the highest log-prob gain."""
    scores = {"incedent": -10.0, "incident": -7.0, "endpoint": -9.0}
    result = _correct(
        "incedent",
        candidates=[("incident", 95), ("endpoint", 90)],
        has_lm=True,
        lm_score=lambda t: scores.get(t.split()[-1], -10.0),
    )
    assert result == "incident"
