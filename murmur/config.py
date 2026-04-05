import toml
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_DIR = Path.home() / ".apple-murmur"
CONFIG_PATH = CONFIG_DIR / "config.toml"


@dataclass
class HotkeyConfig:
    key: str = "fn"
    double_tap_interval_ms: int = 300


@dataclass
class ModelConfig:
    name: str = "tiny.en"
    device: str = "auto"  # auto | mps | cuda | cpu


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class Config:
    hotkey: HotkeyConfig = None
    model: ModelConfig = None
    audio: AudioConfig = None

    def __post_init__(self):
        if self.hotkey is None:
            self.hotkey = HotkeyConfig()
        if self.model is None:
            self.model = ModelConfig()
        if self.audio is None:
            self.audio = AudioConfig()


def load_config() -> Config:
    if not CONFIG_PATH.exists():
        return Config()
    data = toml.load(CONFIG_PATH)
    return Config(
        hotkey=HotkeyConfig(**data.get("hotkey", {})),
        model=ModelConfig(**data.get("model", {})),
        audio=AudioConfig(**data.get("audio", {})),
    )


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "hotkey": asdict(config.hotkey),
        "model": asdict(config.model),
        "audio": asdict(config.audio),
    }
    with open(CONFIG_PATH, "w") as f:
        toml.dump(data, f)
