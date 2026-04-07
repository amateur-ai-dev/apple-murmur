"""
Pre-mock heavy optional dependencies so tests run without installing them.
mlx_whisper is only needed at runtime (when the engine actually transcribes).
All engine tests mock this at the attribute level — this lets those patches apply.
"""
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("mlx_whisper", MagicMock())

# Optional audio/NLP deps — gracefully absent in CI / dev environments
sys.modules.setdefault("webrtcvad", MagicMock())

# noisereduce: reduce_noise must return a numpy array (the input audio), not a MagicMock
_noisereduce_mock = MagicMock()
_noisereduce_mock.reduce_noise.side_effect = lambda y, **kwargs: y
sys.modules.setdefault("noisereduce", _noisereduce_mock)

# rapidfuzz: mock process.extract to return no candidates by default
_rapidfuzz_process = MagicMock()
_rapidfuzz_process.extract.return_value = []
_rapidfuzz_fuzz = MagicMock()
_rapidfuzz_mock = MagicMock()
_rapidfuzz_mock.process = _rapidfuzz_process
_rapidfuzz_mock.fuzz = _rapidfuzz_fuzz
sys.modules.setdefault("rapidfuzz", _rapidfuzz_mock)
sys.modules.setdefault("rapidfuzz.process", _rapidfuzz_process)
sys.modules.setdefault("rapidfuzz.fuzz", _rapidfuzz_fuzz)

# kenlm: mock so kenlm_rescorer skips LM rescoring in tests
sys.modules.setdefault("kenlm", MagicMock())
