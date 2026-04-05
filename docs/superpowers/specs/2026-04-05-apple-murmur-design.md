# apple-murmur — Design Spec
**Date:** 2026-04-05
**Version:** 1.0
**Platform:** Apple Silicon macOS only (M1/M2/M3/M4)

---

## Overview

apple-murmur is the Apple Silicon-native sibling of murmur. Identical UX — double-tap fn anywhere, speak, text injects at cursor — but uses Apple's MLX framework to run Whisper on the Neural Engine instead of PyTorch MPS. Result: near-instant transcription, lower power draw, smaller memory footprint.

This is not a cross-platform tool. It is purpose-built for Apple Silicon and accepts that constraint in exchange for maximum on-device performance.

---

## Architecture

Identical three-layer structure to murmur. Only the engine layer differs.

```
┌──────────────────────────────────────────┐
│              INTERFACE LAYER             │
│   murmur CLI (start/stop/status/update)  │
│   /voice  — Claude Code slash command    │
├──────────────────────────────────────────┤
│              DAEMON LAYER                │
│   Hotkey listener  (pynput, global)      │
│   Audio capture    (sounddevice, 16kHz)  │
│   Text injector    (clipboard + paste)   │
│   State machine    (idle/recording/busy) │
├──────────────────────────────────────────┤
│              ENGINE LAYER                │
│   mlx-whisper (Apple MLX framework)      │
│   Runs on Neural Engine (ANE)            │
│   Whisper tiny model — MLX format        │
└──────────────────────────────────────────┘
```

The engine exposes the same interface as murmur: `transcribe(audio_bytes) -> str`. The daemon layer is byte-for-byte identical to murmur.

---

## Components

### 1. CLI (`murmur/cli.py`)
Identical to murmur. Binary name: `murmur` (same CLI contract for users switching between repos).

Commands: `start`, `stop`, `status`, `update`

### 2. Daemon (`murmur/daemon.py`)
Identical to murmur. Same state machine, same logging, same PID file location (`~/.apple-murmur/`), same SIGTERM handling.

### 3. Hotkey Listener (`murmur/hotkey.py`)
Identical to murmur. fn double-tap at 300ms interval, pynput, Accessibility permission required.

### 4. Audio Capture (`murmur/audio.py`)
Identical to murmur. sounddevice, 16kHz mono.

### 5. Inference Engine (`murmur/engine.py`) — THE ONLY DIFFERENCE
Uses `mlx-whisper` instead of PyTorch:

```python
import mlx_whisper

class Engine:
    def __init__(self):
        self.model_path = "~/.apple-murmur/models/whisper-tiny-mlx"

    def transcribe(self, audio_bytes: bytes) -> str:
        return mlx_whisper.transcribe(audio_bytes, path_or_hf_repo=self.model_path)["text"]
```

- Model runs on Apple Neural Engine via MLX
- Target latency: <150ms for 10s audio (vs ~500ms for murmur on MPS)
- Lower power draw than PyTorch MPS
- Model downloaded from Hugging Face MLX community at install time (`mlx-community/whisper-tiny-mlx`)

### 6. Text Injector (`murmur/injector.py`)
Identical to murmur.

### 7. Config (`murmur/config.py`)
Same format as murmur. Device field is ignored (always ANE via MLX).

```toml
[hotkey]
key = "fn"
double_tap_interval_ms = 300

[model]
name = "whisper-tiny-mlx"

[audio]
sample_rate = 16000
channels = 1
```

---

## Install Flow

```bash
curl -fsSL https://raw.githubusercontent.com/amateur-ai-dev/apple-murmur/main/install.sh | bash
```

Script steps:
1. Check Apple Silicon (`uname -m` must be `arm64`), Python 3.9+
2. Clone repo to `~/.apple-murmur/`
3. Create venv, `pip3 install -r requirements.txt`
4. Download `mlx-community/whisper-tiny-mlx` to `~/.apple-murmur/models/`
5. Install `murmur` CLI to `/usr/local/bin/`
6. Copy `scripts/claude_voice.md` to `~/.claude/commands/voice.md`
7. Open System Settings → Accessibility with prompt
8. Run `murmur status` to verify
9. Print success

No compilation step — pure pip install. Faster than murmur install.

---

## Claude Code Integration

Identical to murmur. `/voice` command boots the daemon.

---

## File Structure

```
apple-murmur/
├── install.sh
├── requirements.txt
├── README.md
├── murmur/
│   ├── __init__.py
│   ├── cli.py           # identical to murmur
│   ├── daemon.py        # identical to murmur
│   ├── hotkey.py        # identical to murmur
│   ├── audio.py         # identical to murmur
│   ├── engine.py        # DIFFERENT — mlx-whisper
│   ├── injector.py      # identical to murmur
│   └── config.py        # identical to murmur
├── scripts/
│   └── claude_voice.md
├── models/              # .gitignored
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-05-apple-murmur-design.md
```

---

## Dependencies

```
mlx-whisper>=0.3.0
sounddevice
pynput
pyperclip
pyautogui
toml
numpy
```

No PyTorch. No transformers. Minimal footprint.

---

## Performance vs murmur

| Metric | murmur (PyTorch MPS) | apple-murmur (MLX ANE) |
|---|---|---|
| 10s audio latency | ~500ms | ~150ms |
| Model load time | ~800ms | ~300ms |
| Memory footprint | ~300MB | ~120MB |
| Power draw | Medium | Low |
| Cross-platform | Yes | No |

---

## Relationship to murmur

apple-murmur is not a fork of murmur — it is a separate repo with:
- 6 of 7 source files identical (cli, daemon, hotkey, audio, injector, config)
- 1 file different (engine.py)

Future consideration: if the shared code diverges significantly, extract a `murmur-core` package that both repos depend on. Not needed in v1.

---

## Non-Goals (v1)

- No Intel Mac support
- No GUI, no menu bar icon
- No VAD
- No multi-language (tiny model only in v1)
- No streaming transcription
- No shared package with murmur (duplication is intentional and simple)
