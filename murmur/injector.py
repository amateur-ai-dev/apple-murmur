import logging
import platform
import time

import pyautogui
import pyperclip

logger = logging.getLogger(__name__)


class Injector:
    def inject(self, text: str) -> None:
        if not text.strip():
            return
        try:
            self._inject_via_clipboard(text)
        except Exception as e:
            logger.warning("Clipboard injection failed (%s), falling back to typewrite", e)
            try:
                self._inject_via_typewrite(text)
            except Exception as e2:
                logger.error("Typewrite injection also failed: %s", e2)

    def _inject_via_clipboard(self, text: str) -> None:
        try:
            previous = pyperclip.paste()
        except Exception:
            previous = ""

        pyperclip.copy(text)
        time.sleep(0.05)  # let clipboard settle

        if platform.system() == "Darwin":
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")

        time.sleep(0.1)  # wait for paste to complete

        # Restore previous clipboard — failure here must NOT trigger typewrite fallback
        try:
            if previous:
                pyperclip.copy(previous)
        except Exception:
            pass

    def _inject_via_typewrite(self, text: str) -> None:
        pyautogui.write(text, interval=0.01)
