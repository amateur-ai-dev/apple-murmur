import threading

import numpy as np
import sounddevice as sd


class AudioCapture:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._frames: list = []
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> None:
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        with self._lock:
            self._frames.append(indata.copy())

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if self._frames:
                return np.concatenate(self._frames, axis=0).flatten()
        # Return one second of silence if nothing was recorded
        return np.zeros(self.sample_rate, dtype=np.float32)
