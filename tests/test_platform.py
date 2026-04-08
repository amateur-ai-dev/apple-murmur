import subprocess
from unittest.mock import patch, MagicMock


def _mock_run(bundle_id: str):
    """Return a mock subprocess.run result with the given bundle ID."""
    result = MagicMock()
    result.stdout = f"{bundle_id}\n"
    return result


def test_get_active_bundle_returns_stripped_bundle_id():
    from murmur.platform import get_active_bundle
    with patch("murmur.platform.subprocess.run", return_value=_mock_run("com.googlecode.iterm2")):
        assert get_active_bundle() == "com.googlecode.iterm2"


def test_get_active_bundle_returns_empty_on_timeout():
    from murmur.platform import get_active_bundle
    with patch("murmur.platform.subprocess.run",
               side_effect=subprocess.TimeoutExpired("osascript", 0.5)):
        assert get_active_bundle() == ""


def test_get_active_bundle_returns_empty_on_any_exception():
    from murmur.platform import get_active_bundle
    with patch("murmur.platform.subprocess.run", side_effect=OSError("no osascript")):
        assert get_active_bundle() == ""


def test_is_terminal_true_for_iterm2():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value="com.googlecode.iterm2"):
        assert is_terminal() is True


def test_is_terminal_true_for_terminal_app():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value="com.apple.Terminal"):
        assert is_terminal() is True


def test_is_terminal_false_for_chrome():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value="com.google.Chrome"):
        assert is_terminal() is False


def test_is_terminal_false_for_empty_bundle():
    from murmur.platform import is_terminal
    with patch("murmur.platform.get_active_bundle", return_value=""):
        assert is_terminal() is False


def test_get_profile_returns_terminal_when_in_terminal():
    from murmur.platform import get_profile
    with patch("murmur.platform.is_terminal", return_value=True):
        assert get_profile() == "terminal"


def test_get_profile_returns_default_when_not_in_terminal():
    from murmur.platform import get_profile
    with patch("murmur.platform.is_terminal", return_value=False):
        assert get_profile() == "default"
