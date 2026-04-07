"""
Tests for the KenLM lazy-loader.
Each test resets module-level globals (_model, _load_attempted) via monkeypatch
so tests are order-independent.
_MODEL_PATH is replaced with a MagicMock (PosixPath.exists is read-only).
"""
import sys
from unittest.mock import MagicMock, patch
import pytest


def _mock_path(exists: bool):
    p = MagicMock()
    p.exists.return_value = exists
    p.__str__ = lambda self: "/fake/path/domain.klm"
    return p


@pytest.fixture(autouse=True)
def reset_kenlm_state(monkeypatch):
    """Reset kenlm_rescorer module globals before every test."""
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_model", None)
    monkeypatch.setattr(kr, "_load_attempted", False)


# ---------------------------------------------------------------------------
# has_model
# ---------------------------------------------------------------------------

def test_has_model_false_when_model_file_absent(monkeypatch):
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=False))
    assert not kr.has_model()


def test_has_model_false_when_kenlm_not_installed(monkeypatch):
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=True))
    with patch.dict(sys.modules, {"kenlm": None}):
        assert not kr.has_model()


def test_has_model_true_when_model_loads_successfully(monkeypatch):
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=True))
    mock_kenlm = MagicMock()
    mock_kenlm.Model.return_value = MagicMock()
    with patch.dict(sys.modules, {"kenlm": mock_kenlm}):
        assert kr.has_model()


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------

def test_score_returns_zero_when_no_model(monkeypatch):
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=False))
    assert kr.score("hello world") == 0.0


def test_score_delegates_to_kenlm_model(monkeypatch):
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=True))
    mock_model = MagicMock()
    mock_model.score.return_value = -3.14
    mock_kenlm = MagicMock()
    mock_kenlm.Model.return_value = mock_model
    with patch.dict(sys.modules, {"kenlm": mock_kenlm}):
        result = kr.score("the incident was escalated")
    assert result == -3.14
    mock_model.score.assert_called_once_with("the incident was escalated")


# ---------------------------------------------------------------------------
# Load idempotency
# ---------------------------------------------------------------------------

def test_get_model_only_loads_once(monkeypatch):
    """_load_attempted prevents repeated load attempts."""
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=True))
    mock_kenlm = MagicMock()
    with patch.dict(sys.modules, {"kenlm": mock_kenlm}):
        kr._get_model()
        kr._get_model()
    assert mock_kenlm.Model.call_count == 1


def test_get_model_returns_none_on_load_exception(monkeypatch):
    """A crash during kenlm.Model() must not propagate — fall back to None."""
    import murmur.kenlm_rescorer as kr
    monkeypatch.setattr(kr, "_MODEL_PATH", _mock_path(exists=True))
    mock_kenlm = MagicMock()
    mock_kenlm.Model.side_effect = OSError("corrupt model file")
    with patch.dict(sys.modules, {"kenlm": mock_kenlm}):
        model = kr._get_model()
    assert model is None
