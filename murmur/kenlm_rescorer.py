"""
KenLM domain language model — lazy-loaded, graceful fallback when model is absent.
Used by vocabulary.py to validate rapidfuzz correction candidates.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MODEL_PATH = Path.home() / ".apple-murmur" / "models" / "domain.klm"
_model = None
_load_attempted = False


def _get_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    try:
        import kenlm
        if _MODEL_PATH.exists():
            _model = kenlm.Model(str(_MODEL_PATH))
            logger.info("KenLM domain model loaded (%s)", _MODEL_PATH)
        else:
            logger.info("KenLM model not found at %s — LM rescoring disabled", _MODEL_PATH)
    except ImportError:
        logger.debug("kenlm not installed — LM rescoring disabled")
    except Exception as exc:
        logger.warning("KenLM load failed: %s", exc)
    return _model


def has_model() -> bool:
    return _get_model() is not None


def score(text: str) -> float:
    """Return log10 probability of text. Higher (less negative) = more likely."""
    model = _get_model()
    if model is None:
        return 0.0
    return model.score(text)
