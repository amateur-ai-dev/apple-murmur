import threading

import numpy as np
import sounddevice as sd

_BLOCK_SIZE = 512  # 32ms per chunk at 16kHz


class AudioCapture:
    def __init__(self, sample_rate: int = 16000, on_silence=None,
                 silence_threshold: float = 0.01, silence_duration_s: float = 1.0):
        self.sample_rate = sample_rate
        self._on_silence = on_silence
        self._silence_threshold = silence_threshold
        self._silence_chunks_needed = int(silence_duration_s * sample_rate / _BLOCK_SIZE)
        self._frames: list = []
        self._stream = None
        self._lock = threading.Lock()
        self._silence_chunks = 0
        self._has_spoken = False
        self._silence_triggered = False

    def start(self) -> None:
        self._frames = []
        self._silence_chunks = 0
        self._has_spoken = False
        self._silence_triggered = False
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=_BLOCK_SIZE,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        with self._lock:
            self._frames.append(indata.copy())

        if self._on_silence and not self._silence_triggered:
            rms = float(np.sqrt(np.mean(indata ** 2)))
            if rms > self._silence_threshold:
                self._has_spoken = True
                self._silence_chunks = 0
            elif self._has_spoken:
                self._silence_chunks += 1
                if self._silence_chunks >= self._silence_chunks_needed:
                    self._silence_triggered = True
                    threading.Thread(target=self._on_silence, daemon=True).start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if self._frames:
                return np.concatenate(self._frames, axis=0).flatten()
        return np.zeros(self.sample_rate, dtype=np.float32)
