import threading
import pytest
from unittest.mock import patch, MagicMock


def _make_daemon():
    from murmur.daemon import Daemon
    mock_engine = MagicMock()
    mock_audio = MagicMock()
    mock_injector = MagicMock()
    mock_hotkey = MagicMock()
    daemon = Daemon.__new__(Daemon)
    daemon.engine = mock_engine
    daemon.audio = mock_audio
    daemon.injector = mock_injector
    daemon.hotkey = mock_hotkey
    daemon.state = "idle"
    daemon._lock = threading.Lock()  # required — on_double_tap and _transcribe both use it
    return daemon, mock_engine, mock_audio, mock_injector


def test_double_tap_idle_starts_recording():
    daemon, engine, audio, injector = _make_daemon()
    daemon.on_double_tap()
    assert daemon.state == "recording"
    audio.start.assert_called_once()


def test_double_tap_recording_stops_and_transcribes():
    daemon, engine, audio, injector = _make_daemon()
    daemon.state = "recording"
    audio.stop.return_value = __import__("numpy").zeros(16000, dtype="float32")
    engine.transcribe.return_value = "hello world"
    daemon.on_double_tap()
    audio.stop.assert_called_once()
    engine.transcribe.assert_called_once()
    injector.inject.assert_called_once_with("hello world")
    assert daemon.state == "idle"


def test_double_tap_while_transcribing_is_ignored():
    daemon, engine, audio, injector = _make_daemon()
    daemon.state = "transcribing"
    daemon.on_double_tap()
    audio.start.assert_not_called()
    audio.stop.assert_not_called()


def test_transcription_error_resets_state_to_idle():
    daemon, engine, audio, injector = _make_daemon()
    daemon.state = "recording"
    audio.stop.return_value = __import__("numpy").zeros(16000, dtype="float32")
    engine.transcribe.side_effect = RuntimeError("model failed")
    daemon.on_double_tap()
    assert daemon.state == "idle"
    injector.inject.assert_not_called()


def test_cli_start_writes_pid_file(tmp_path):
    import types
    from murmur.cli import cmd_start
    pid_file = tmp_path / "murmur.pid"
    log_file = tmp_path / "murmur.log"
    mock_proc = MagicMock()
    mock_proc.pid = 12345
    with patch("murmur.cli.PID_FILE", pid_file), \
         patch("murmur.cli.LOG_FILE", log_file), \
         patch("murmur.cli.subprocess.Popen", return_value=mock_proc):
        cmd_start(types.SimpleNamespace())
    assert pid_file.read_text().strip() == "12345"


def test_cli_stop_removes_pid_file(tmp_path):
    import types
    from murmur.cli import cmd_stop
    pid_file = tmp_path / "murmur.pid"
    pid_file.write_text("99999")
    with patch("murmur.cli.PID_FILE", pid_file), \
         patch("murmur.cli.os.kill"):
        cmd_stop(types.SimpleNamespace())
    assert not pid_file.exists()
