import numpy as np
import pytest
from unittest.mock import patch, MagicMock


def test_transcribe_returns_stripped_string():
    from murmur.engine import Engine
    mock_result = {"text": "  hello world  "}
    with patch("murmur.engine.mlx_whisper.transcribe", return_value=mock_result):
        engine = Engine()
        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == "hello world"
        assert isinstance(result, str)


def test_transcribe_passes_correct_model_path():
    from murmur.engine import Engine
    mock_result = {"text": "test"}
    with patch("murmur.engine.mlx_whisper.transcribe", return_value=mock_result) as mock_transcribe:
        engine = Engine(model_name="whisper-tiny-mlx")
        audio = np.zeros(16000, dtype=np.float32)
        engine.transcribe(audio)
        call_args = mock_transcribe.call_args
        # path_or_hf_repo should be passed as positional or keyword arg
        assert call_args is not None
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        assert any("whisper-tiny-mlx" in str(a) for a in all_args)


def test_transcribe_returns_empty_string_on_whitespace_result():
    from murmur.engine import Engine
    with patch("murmur.engine.mlx_whisper.transcribe", return_value={"text": "   "}):
        engine = Engine()
        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == ""


def test_load_is_noop_for_mlx():
    from murmur.engine import Engine
    engine = Engine()
    engine.load()  # should not raise


def test_initial_prompt_contains_key_cli_terms():
    from murmur.engine import _INITIAL_PROMPT
    required = ["git", "docker", "kubectl", "npm", "pip", "brew", "ssh", "curl",
                "terraform", "python", "bash", "sudo", "grep", "awk", "sed"]
    for term in required:
        assert term in _INITIAL_PROMPT, f"Missing CLI term in prompt: {term}"


def test_initial_prompt_contains_indian_names():
    from murmur.engine import _INITIAL_PROMPT
    required = ["Sharma", "Patel", "Reddy", "Nair", "Rahul", "Priya", "Arjun"]
    for term in required:
        assert term in _INITIAL_PROMPT, f"Missing Indian name in prompt: {term}"
