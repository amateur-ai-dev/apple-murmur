import logging
import signal
import sys
import threading
from pathlib import Path

from murmur.audio import AudioCapture
from murmur.config import load_config
from murmur.engine import Engine
from murmur.hotkey import HotkeyListener
from murmur.injector import Injector
from murmur.normalizer import normalize
from murmur.preprocessor import preprocess

LOG_FILE = Path.home() / ".apple-murmur" / "murmur.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class Daemon:
    def __init__(self):
        config = load_config()
        self.engine = Engine(model_name=config.model.name, device=config.model.device)
        self.audio = AudioCapture(
            sample_rate=config.audio.sample_rate,
        )
        self.injector = Injector()
        self.hotkey = HotkeyListener(
            on_double_tap=self.on_double_tap,
            interval_ms=config.hotkey.double_tap_interval_ms,
            key=config.hotkey.key,
        )
        self.state = "idle"
        self._lock = threading.Lock()

    def start(self) -> None:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Starting murmur daemon")
        self.engine.load()
        self.hotkey.start()
        logger.info("murmur ready — double-tap fn to record")
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        self.hotkey._listener.join()

    def on_double_tap(self) -> None:
        # Capture audio_data outside the lock so _transcribe can re-acquire it in finally.
        # Holding a non-reentrant lock while calling _transcribe would deadlock.
        audio_to_transcribe = None
        with self._lock:
            if self.state == "idle":
                self.state = "recording"
                self.audio.start()
                logger.info("Recording started")
            elif self.state == "recording":
                self.state = "transcribing"
                audio_to_transcribe = self.audio.stop()
                logger.info("Recording stopped (%.1fs)", len(audio_to_transcribe) / 16000)
            # state == "transcribing": ignore double-tap

        if audio_to_transcribe is not None:
            self._transcribe(audio_to_transcribe)

    def _transcribe(self, audio_data) -> None:
        try:
            audio_data = preprocess(audio_data, self.audio.sample_rate)
            text = self.engine.transcribe(audio_data)
            text = normalize(text)
            logger.info("Transcribed: %r", text)
            if text:
                self.injector.inject(text)
        except Exception as e:
            logger.error("Transcription failed: %s", e)
        finally:
            with self._lock:
                self.state = "idle"

    def _handle_sigterm(self, signum, frame) -> None:
        logger.info("SIGTERM received, shutting down")
        self.hotkey.stop()
        sys.exit(0)


if __name__ == "__main__":
    Daemon().start()
