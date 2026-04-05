import pytest
from unittest.mock import patch, MagicMock


def test_inject_copies_text_to_clipboard_and_pastes():
    from murmur.injector import Injector
    with patch("murmur.injector.pyperclip.copy") as mock_copy, \
         patch("murmur.injector.pyperclip.paste", return_value=""), \
         patch("murmur.injector.pyautogui.hotkey") as mock_hotkey, \
         patch("murmur.injector.platform.system", return_value="Darwin"), \
         patch("murmur.injector.time.sleep"):
        injector = Injector()
        injector.inject("hello world")
        mock_copy.assert_any_call("hello world")
        mock_hotkey.assert_called_once_with("command", "v")


def test_inject_uses_ctrl_v_on_linux():
    from murmur.injector import Injector
    with patch("murmur.injector.pyperclip.copy"), \
         patch("murmur.injector.pyperclip.paste", return_value=""), \
         patch("murmur.injector.pyautogui.hotkey") as mock_hotkey, \
         patch("murmur.injector.platform.system", return_value="Linux"), \
         patch("murmur.injector.time.sleep"):
        injector = Injector()
        injector.inject("hello")
        mock_hotkey.assert_called_once_with("ctrl", "v")


def test_inject_skips_empty_text():
    from murmur.injector import Injector
    with patch("murmur.injector.pyperclip.copy") as mock_copy:
        injector = Injector()
        injector.inject("   ")
        mock_copy.assert_not_called()


def test_inject_falls_back_to_typewrite_on_clipboard_error():
    from murmur.injector import Injector
    with patch("murmur.injector.pyperclip.copy", side_effect=Exception("clipboard unavailable")), \
         patch("murmur.injector.pyperclip.paste", side_effect=Exception("no clipboard")), \
         patch("murmur.injector.pyautogui.write") as mock_write, \
         patch("murmur.injector.time.sleep"):
        injector = Injector()
        injector.inject("hello")
        mock_write.assert_called_once_with("hello", interval=0.01)
