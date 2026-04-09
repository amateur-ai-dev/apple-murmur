import sys
import numpy as np
from unittest.mock import MagicMock, patch


def _audio(n=4800, amplitude=0.5):
    return np.ones(n, dtype=np.float32) * amplitude


def _speech_vad():
    """A webrtcvad mock whose Vad.is_speech always returns True."""
    mock_vad_instance = MagicMock()
    mock_vad_instance.is_speech.return_value = True
    mock_webrtcvad = MagicMock()
    mock_webrtcvad.Vad.return_value = mock_vad_instance
    return mock_webrtcvad


def _silence_vad():
    """A webrtcvad mock whose Vad.is_speech always returns False."""
    mock_vad_instance = MagicMock()
    mock_vad_instance.is_speech.return_value = False
    mock_webrtcvad = MagicMock()
    mock_webrtcvad.Vad.return_value = mock_vad_instance
    return mock_webrtcvad


# ---------------------------------------------------------------------------
# _normalize_volume
# ---------------------------------------------------------------------------

def test_normalize_volume_scales_to_target_rms():
    from murmur.preprocessor import _normalize_volume, _TARGET_RMS
    result = _normalize_volume(_audio(amplitude=0.1))
    rms = float(np.sqrt(np.mean(result ** 2)))
    assert abs(rms - _TARGET_RMS) < 1e-4


def test_normalize_volume_clips_loud_audio_to_unity():
    from murmur.preprocessor import _normalize_volume
    # Very quiet input → large scale factor → would overflow without clip
    result = _normalize_volume(_audio(amplitude=1e-4))
    assert result.max() <= 1.0
    assert result.min() >= -1.0


def test_normalize_volume_skips_silent_audio():
    from murmur.preprocessor import _normalize_volume
    silent = np.zeros(4800, dtype=np.float32)
    result = _normalize_volume(silent)
    np.testing.assert_array_equal(result, silent)


# ---------------------------------------------------------------------------
# _strip_silence_vad
# ---------------------------------------------------------------------------

def test_strip_silence_vad_keeps_speech_frames():
    from murmur.preprocessor import _strip_silence_vad
    audio = _audio(4800)
    with patch.dict(sys.modules, {"webrtcvad": _speech_vad()}):
        result = _strip_silence_vad(audio, 16000)
    assert len(result) == 4800


def test_strip_silence_vad_returns_original_when_all_silent():
    """When VAD marks every frame as silence, fall back to original audio."""
    from murmur.preprocessor import _strip_silence_vad
    audio = _audio(4800)
    with patch.dict(sys.modules, {"webrtcvad": _silence_vad()}):
        result = _strip_silence_vad(audio, 16000)
    np.testing.assert_array_equal(result, audio)


def test_strip_silence_vad_returns_original_when_webrtcvad_absent():
    """ImportError from webrtcvad must leave audio unchanged."""
    from murmur.preprocessor import _strip_silence_vad
    audio = _audio(4800)
    with patch.dict(sys.modules, {"webrtcvad": None}):
        result = _strip_silence_vad(audio, 16000)
    np.testing.assert_array_equal(result, audio)


# ---------------------------------------------------------------------------
# _reduce_noise
# ---------------------------------------------------------------------------

def test_reduce_noise_returns_original_on_exception():
    """noisereduce failure must not crash — original audio is returned."""
    from murmur.preprocessor import _reduce_noise
    audio = _audio()
    failing_nr = MagicMock()
    failing_nr.reduce_noise.side_effect = RuntimeError("cuda error")
    with patch.dict(sys.modules, {"noisereduce": failing_nr}):
        result = _reduce_noise(audio, 16000)
    np.testing.assert_array_equal(result, audio)


# ---------------------------------------------------------------------------
# preprocess (full pipeline)
# ---------------------------------------------------------------------------

def test_preprocess_returns_float32_ndarray():
    from murmur.preprocessor import preprocess
    from murmur.profiles import DEFAULT_PROFILE
    passthrough_nr = MagicMock()
    passthrough_nr.reduce_noise.side_effect = lambda y, **kwargs: y
    with patch.dict(sys.modules, {"webrtcvad": _speech_vad(), "noisereduce": passthrough_nr}):
        result = preprocess(_audio(), sample_rate=16000, profile=DEFAULT_PROFILE)
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32


def test_preprocess_terminal_profile_skips_vad():
    """TERMINAL_PROFILE.skip_vad=True — VAD must not run."""
    from murmur.preprocessor import preprocess
    from murmur.profiles import TERMINAL_PROFILE
    silence_vad = _silence_vad()  # would strip everything if called
    passthrough_nr = MagicMock()
    passthrough_nr.reduce_noise.side_effect = lambda y, **kwargs: y
    audio = _audio(4800)
    with patch.dict(sys.modules, {"webrtcvad": silence_vad, "noisereduce": passthrough_nr}):
        result = preprocess(audio, sample_rate=16000, profile=TERMINAL_PROFILE)
    assert len(result) == 4800
    silence_vad.Vad.assert_not_called()


def test_preprocess_default_profile_runs_vad():
    """DEFAULT_PROFILE.skip_vad=False — VAD runs as normal."""
    from murmur.preprocessor import preprocess
    from murmur.profiles import DEFAULT_PROFILE
    speech_vad = _speech_vad()
    passthrough_nr = MagicMock()
    passthrough_nr.reduce_noise.side_effect = lambda y, **kwargs: y
    with patch.dict(sys.modules, {"webrtcvad": speech_vad, "noisereduce": passthrough_nr}):
        preprocess(_audio(4800), sample_rate=16000, profile=DEFAULT_PROFILE)
    speech_vad.Vad.assert_called_once()
