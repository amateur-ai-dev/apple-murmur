"""
Audio preprocessing pipeline: noise reduction → volume normalization → VAD silence stripping.
Applied to every recording before it reaches the Whisper engine.
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# webrtcvad requires frame sizes of exactly 10, 20, or 30ms.
# At 16kHz, 30ms = 480 samples — must match AudioCapture._BLOCK_SIZE.
_VAD_FRAME_SAMPLES = 480
_VAD_AGGRESSIVENESS = 2   # 0 (least) – 3 (most aggressive silence removal)
_TARGET_RMS = 0.08        # target RMS after volume normalization


def _normalize_volume(audio: np.ndarray) -> np.ndarray:
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-6:
        return audio
    return (audio * (_TARGET_RMS / rms)).clip(-1.0, 1.0)


def _reduce_noise(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    try:
        import noisereduce as nr
        return nr.reduce_noise(y=audio, sr=sample_rate, stationary=False,
                               prop_decrease=0.75)
    except Exception as exc:
        logger.debug("noisereduce skipped: %s", exc)
        return audio


def _strip_silence_vad(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Remove non-speech frames using WebRTC VAD."""
    try:
        import webrtcvad
    except ImportError:
        return audio

    vad = webrtcvad.Vad(_VAD_AGGRESSIVENESS)
    pcm = (audio * 32767).astype(np.int16)
    voiced = []

    for start in range(0, len(pcm) - _VAD_FRAME_SAMPLES + 1, _VAD_FRAME_SAMPLES):
        frame = pcm[start:start + _VAD_FRAME_SAMPLES]
        try:
            if vad.is_speech(frame.tobytes(), sample_rate):
                voiced.append(audio[start:start + _VAD_FRAME_SAMPLES])
        except Exception:
            voiced.append(audio[start:start + _VAD_FRAME_SAMPLES])

    if not voiced:
        logger.debug("VAD stripped all frames — returning original audio")
        return audio

    return np.concatenate(voiced)


def preprocess(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Full pipeline: noise reduction → normalize volume → strip silence."""
    audio = _reduce_noise(audio, sample_rate)
    audio = _normalize_volume(audio)
    audio = _strip_silence_vad(audio, sample_rate)
    return audio
