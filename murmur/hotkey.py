import threading
import time
import logging
from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    def __init__(self, on_double_tap, interval_ms: int = 300):
        self.on_double_tap = on_double_tap
        self.interval_s = interval_ms / 1000.0
        self._last_press_time: float = 0.0
        self._lock = threading.Lock()
        self._listener = keyboard.Listener(on_press=self._on_press)

    def start(self) -> None:
        self._listener.start()
        logger.info(
            "Hotkey listener started (double-tap fn within %.0fms)",
            self.interval_s * 1000,
        )

    def stop(self) -> None:
        self._listener.stop()

    def _on_press(self, key) -> None:
        try:
            if key != keyboard.Key.fn:
                return
        except AttributeError:
            return
        self._on_press_time(time.time())

    def _on_press_time(self, now: float) -> None:
        with self._lock:
            elapsed = now - self._last_press_time
            if 0 < elapsed <= self.interval_s:
                self._last_press_time = 0.0  # reset — prevents triple-tap re-fire
                threading.Thread(target=self.on_double_tap, daemon=True).start()
            else:
                self._last_press_time = now
