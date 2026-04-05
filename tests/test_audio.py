import numpy as np
import pytest
from unittest.mock import patch, MagicMock


def test_stop_before_start_returns_silence():
    from murmur.audio import AudioCapture
    capture = AudioCapture()
    result = capture.stop()
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32
    assert len(result) > 0


def test_stop_returns_flat_float32_array():
    from murmur.audio import AudioCapture
    mock_stream = MagicMock()
    with patch("murmur.audio.sd.InputStream", return_value=mock_stream):
        capture = AudioCapture(sample_rate=16000)
        capture.start()
        # Simulate audio callback delivering two chunks
        chunk = np.ones((1600, 1), dtype=np.float32)
        capture._callback(chunk, 1600, None, None)
        capture._callback(chunk, 1600, None, None)
        result = capture.stop()
        assert result.ndim == 1
        assert result.dtype == np.float32
        assert len(result) == 3200


def test_start_creates_input_stream_with_correct_params():
    from murmur.audio import AudioCapture
    mock_stream = MagicMock()
    with patch("murmur.audio.sd.InputStream", return_value=mock_stream) as mock_cls:
        capture = AudioCapture(sample_rate=16000)
        capture.start()
        mock_cls.assert_called_once_with(
            samplerate=16000,
            channels=1,
            dtype="float32",
            callback=capture._callback,
        )
        mock_stream.start.assert_called_once()
