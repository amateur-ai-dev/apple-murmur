import threading
import time
import logging
from pynput import keyboard

logger = logging.getLogger(__name__)

# Maps config key names to pynput Key objects.
# keyboard.Key.fn is not available on all platforms/pynput versions — guard with getattr.
_KEY_MAP = {
    "alt_r":   keyboard.Key.alt_r,    # Right Option — default on macOS
    "alt_l":   keyboard.Key.alt_l,
    "ctrl_r":  keyboard.Key.ctrl_r,
    "ctrl_l":  keyboard.Key.ctrl_l,
    "cmd_r":   keyboard.Key.cmd_r,
    "cmd_l":   keyboard.Key.cmd_l,
    "shift_r": keyboard.Key.shift_r,
    "caps_lock": keyboard.Key.caps_lock,
}
_fn_key = getattr(keyboard.Key, "fn", None)
if _fn_key is not None:
    _KEY_MAP["fn"] = _fn_key


class HotkeyListener:
    def __init__(self, on_double_tap, interval_ms: int = 300, key: str = "alt_r"):
        self.on_double_tap = on_double_tap
        self.interval_s = interval_ms / 1000.0
        self._key = _KEY_MAP.get(key, keyboard.Key.alt_r)
        self._last_press_time: float = 0.0
        self._lock = threading.Lock()
        self._listener = keyboard.Listener(on_press=self._on_press)

    def start(self) -> None:
        self._listener.start()
        logger.info(
            "Hotkey listener started (double-tap %s within %.0fms)",
            self._key,
            self.interval_s * 1000,
        )

    def stop(self) -> None:
        self._listener.stop()

    def _on_press(self, key) -> None:
        try:
            if key != self._key:
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
