import tempfile
from pathlib import Path
from unittest.mock import patch


def test_default_config_has_correct_values():
    from murmur.config import Config, HotkeyConfig, ModelConfig, AudioConfig
    config = Config()
    assert config.hotkey.key == "fn"
    assert config.hotkey.double_tap_interval_ms == 300
    assert config.model.name == "tiny.en"
    assert config.model.device == "auto"
    assert config.audio.sample_rate == 16000
    assert config.audio.channels == 1


def test_save_and_load_config_roundtrip():
    from murmur.config import Config, save_config, load_config
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        with patch("murmur.config.CONFIG_PATH", config_path), \
             patch("murmur.config.CONFIG_DIR", Path(tmpdir)):
            config = Config()
            config.hotkey.double_tap_interval_ms = 400
            config.model.device = "cpu"
            save_config(config)
            loaded = load_config()
            assert loaded.hotkey.double_tap_interval_ms == 400
            assert loaded.model.device == "cpu"


def test_load_config_returns_defaults_when_file_missing():
    from murmur.config import load_config, Config
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = Path(tmpdir) / "nonexistent.toml"
        with patch("murmur.config.CONFIG_PATH", missing_path):
            config = load_config()
            assert config.hotkey.key == "fn"
