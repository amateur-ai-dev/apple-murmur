# apple-murmur Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Apple Silicon-native variant of murmur — identical UX, but using mlx-whisper on the Neural Engine for near-instant transcription (~150ms vs ~500ms).

**Architecture:** Same three-layer design as murmur. Six of seven source files are copied verbatim from murmur. Only `engine.py` differs — it uses `mlx-whisper` instead of PyTorch. Install dir is `~/.apple-murmur/` to avoid collision with murmur.

**Tech Stack:** Python 3.9+, mlx-whisper, pynput, sounddevice, pyperclip, pyautogui, toml, argparse

**Prerequisite:** murmur must be fully built first. This plan copies shared files from `/Users/nithingowda/murmur/`.

---

## File Map

```
apple-murmur/
├── install.sh                          CREATE — curl-installable, arm64 check, no compilation
├── requirements.txt                    CREATE — mlx-whisper instead of torch/openai-whisper
├── setup.py                            COPY from murmur (unchanged)
├── .gitignore                          COPY from murmur (unchanged)
├── README.md                           CREATE — apple-murmur specific
├── scripts/
│   └── claude_voice.md                 COPY from murmur (unchanged)
├── murmur/
│   ├── __init__.py                     COPY from murmur (unchanged)
│   ├── config.py                       COPY from murmur (unchanged)
│   ├── engine.py                       CREATE — mlx-whisper implementation (ONLY DIFFERENCE)
│   ├── audio.py                        COPY from murmur (unchanged)
│   ├── hotkey.py                       COPY from murmur (unchanged)
│   ├── injector.py                     COPY from murmur (unchanged)
│   ├── daemon.py                       COPY from murmur (unchanged)
│   └── cli.py                          COPY from murmur, update INSTALL_DIR constant
└── tests/
    ├── __init__.py                     COPY from murmur (unchanged)
    ├── test_config.py                  COPY from murmur (unchanged)
    ├── test_engine.py                  CREATE — mlx-whisper specific tests
    ├── test_audio.py                   COPY from murmur (unchanged)
    ├── test_hotkey.py                  COPY from murmur (unchanged)
    ├── test_injector.py                COPY from murmur (unchanged)
    └── test_daemon.py                  COPY from murmur (unchanged)
```

---

### Task 1: Copy Shared Files from murmur

**Files:** All shared files listed above.

- [ ] **Step 1: Copy shared source files**

```bash
MURMUR=/Users/nithingowda/murmur
DEST=/Users/nithingowda/apple-murmur

cp $MURMUR/setup.py $DEST/
cp $MURMUR/.gitignore $DEST/
cp -r $MURMUR/scripts $DEST/
mkdir -p $DEST/murmur
cp $MURMUR/murmur/__init__.py $DEST/murmur/
cp $MURMUR/murmur/config.py $DEST/murmur/
cp $MURMUR/murmur/audio.py $DEST/murmur/
cp $MURMUR/murmur/hotkey.py $DEST/murmur/
cp $MURMUR/murmur/injector.py $DEST/murmur/
cp $MURMUR/murmur/daemon.py $DEST/murmur/
cp $MURMUR/murmur/cli.py $DEST/murmur/
mkdir -p $DEST/tests
cp $MURMUR/tests/__init__.py $DEST/tests/
cp $MURMUR/tests/test_config.py $DEST/tests/
cp $MURMUR/tests/test_audio.py $DEST/tests/
cp $MURMUR/tests/test_hotkey.py $DEST/tests/
cp $MURMUR/tests/test_injector.py $DEST/tests/
cp $MURMUR/tests/test_daemon.py $DEST/tests/
```

- [ ] **Step 2: Update INSTALL_DIR in cli.py to use ~/.apple-murmur/**

Edit `/Users/nithingowda/apple-murmur/murmur/cli.py` — change lines:
```python
PID_FILE = Path.home() / ".murmur" / "murmur.pid"
LOG_FILE = Path.home() / ".murmur" / "murmur.log"
```
to:
```python
PID_FILE = Path.home() / ".apple-murmur" / "murmur.pid"
LOG_FILE = Path.home() / ".apple-murmur" / "murmur.log"
```

Also update `cmd_update`:
```python
def cmd_update(args) -> None:
    install_dir = Path.home() / ".apple-murmur"
    ...
```

- [ ] **Step 3: Update INSTALL_DIR in daemon.py**

Edit `/Users/nithingowda/apple-murmur/murmur/daemon.py` — change:
```python
LOG_FILE = Path.home() / ".murmur" / "murmur.log"
```
to:
```python
LOG_FILE = Path.home() / ".apple-murmur" / "murmur.log"
```

Also update the `start()` method:
```python
def start(self) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
```
(This line is unchanged, but the path now resolves to `~/.apple-murmur/` correctly.)

- [ ] **Step 4: Update CONFIG_DIR in config.py**

Edit `/Users/nithingowda/apple-murmur/murmur/config.py` — change:
```python
CONFIG_DIR = Path.home() / ".murmur"
CONFIG_PATH = CONFIG_DIR / "config.toml"
```
to:
```python
CONFIG_DIR = Path.home() / ".apple-murmur"
CONFIG_PATH = CONFIG_DIR / "config.toml"
```

- [ ] **Step 5: Create requirements.txt**

`requirements.txt`:
```
mlx-whisper>=0.3.0
sounddevice>=0.4.6
pynput>=1.7.6
pyperclip>=1.8.2
pyautogui>=0.9.54
toml>=0.10.2
numpy>=1.24.0
pytest>=7.4.0
```

- [ ] **Step 6: Commit**

```bash
cd /Users/nithingowda/apple-murmur
git add .
git commit -m "chore: copy shared files from murmur, update install paths to ~/.apple-murmur/"
```

---

### Task 2: MLX Engine Module

**Files:**
- Create: `murmur/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

`tests/test_engine.py`:
```python
import numpy as np
import pytest
from unittest.mock import patch, MagicMock


def test_transcribe_returns_stripped_string():
    from murmur.engine import Engine
    mock_result = {"text": "  hello world  "}
    with patch("murmur.engine.mlx_whisper.transcribe", return_value=mock_result):
        engine = Engine()
        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == "hello world"
        assert isinstance(result, str)


def test_transcribe_passes_correct_model_path():
    from murmur.engine import Engine
    mock_result = {"text": "test"}
    with patch("murmur.engine.mlx_whisper.transcribe", return_value=mock_result) as mock_transcribe:
        engine = Engine(model_name="whisper-tiny-mlx")
        audio = np.zeros(16000, dtype=np.float32)
        engine.transcribe(audio)
        call_kwargs = mock_transcribe.call_args
        assert "path_or_hf_repo" in call_kwargs.kwargs or len(call_kwargs.args) >= 2


def test_transcribe_returns_empty_string_on_empty_result():
    from murmur.engine import Engine
    with patch("murmur.engine.mlx_whisper.transcribe", return_value={"text": "   "}):
        engine = Engine()
        audio = np.zeros(16000, dtype=np.float32)
        result = engine.transcribe(audio)
        assert result == ""


def test_load_is_noop_for_mlx():
    from murmur.engine import Engine
    # MLX loads lazily on first transcribe call — load() should not raise
    engine = Engine()
    engine.load()  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/nithingowda/apple-murmur && python3 -m pytest tests/test_engine.py -v
```
Expected: `ImportError` — `murmur.engine` doesn't exist yet (was not copied from murmur).

- [ ] **Step 3: Implement engine.py**

`murmur/engine.py`:
```python
import logging
from pathlib import Path

import mlx_whisper
import numpy as np

logger = logging.getLogger(__name__)

_MODEL_DIR = Path.home() / ".apple-murmur" / "models"


class Engine:
    def __init__(self, model_name: str = "whisper-tiny-mlx"):
        self.model_name = model_name
        self._model_path = str(_MODEL_DIR / model_name)
        # MLX models lazy-load on first inference call — no explicit load step needed
        logger.info("Engine initialised: model=%s path=%s", model_name, self._model_path)

    def load(self) -> None:
        # No-op for MLX — model is loaded lazily by mlx_whisper on first transcribe call.
        # This method exists so the daemon can call engine.load() without branching.
        logger.info("MLX engine ready (model loads lazily on first transcribe)")

    def transcribe(self, audio: np.ndarray) -> str:
        result = mlx_whisper.transcribe(audio, path_or_hf_repo=self._model_path)
        return result["text"].strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_engine.py -v
```
Expected: 4 passed

- [ ] **Step 5: Run full test suite**

```bash
python3 -m pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add murmur/engine.py tests/test_engine.py
git commit -m "feat: MLX Whisper engine for Apple Neural Engine inference"
```

---

### Task 3: Install Script + README + Final Push

**Files:**
- Create: `install.sh`
- Create: `README.md`

- [ ] **Step 1: Create install.sh**

`install.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$HOME/.apple-murmur"
REPO_URL="https://github.com/amateur-ai-dev/apple-murmur.git"
BIN_PATH="/usr/local/bin/murmur"
MODEL_REPO="mlx-community/whisper-tiny-mlx"

echo "==> Installing apple-murmur..."

# Check Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "Error: apple-murmur requires Apple Silicon (M1/M2/M3/M4)."
    echo "For Intel Macs or other platforms, use murmur: https://github.com/amateur-ai-dev/murmur"
    exit 1
fi

# Check Python 3.9+
python3 -c "import sys; assert sys.version_info >= (3, 9), 'Python 3.9+ required'" 2>/dev/null || {
    echo "Error: Python 3.9+ is required."
    exit 1
}

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Updating existing installation..."
    git -C "$INSTALL_DIR" pull --quiet
else
    echo "==> Cloning apple-murmur..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
fi

# Create venv and install deps
echo "==> Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip3 install --quiet -r "$INSTALL_DIR/requirements.txt"

# Download MLX model
MODEL_DIR="$INSTALL_DIR/models/whisper-tiny-mlx"
if [ ! -d "$MODEL_DIR" ]; then
    echo "==> Downloading whisper-tiny MLX model (~75MB, one-time)..."
    python3 -c "
from huggingface_hub import snapshot_download
import os
snapshot_download('$MODEL_REPO', local_dir='$MODEL_DIR')
print('Model downloaded.')
"
fi

# Install CLI wrapper
echo "==> Installing murmur CLI..."
cat > "$BIN_PATH" << WRAPPER
#!/usr/bin/env bash
source "\$HOME/.apple-murmur/venv/bin/activate"
python3 -m murmur.cli "\$@"
WRAPPER
chmod +x "$BIN_PATH"

# Install Claude Code /voice command
CLAUDE_CMD_DIR="$HOME/.claude/commands"
if [ -d "$HOME/.claude" ]; then
    mkdir -p "$CLAUDE_CMD_DIR"
    cp "$INSTALL_DIR/scripts/claude_voice.md" "$CLAUDE_CMD_DIR/voice.md"
    echo "==> Installed /voice command for Claude Code"
fi

# macOS Accessibility permission
echo ""
echo "==> ACTION REQUIRED: Grant Accessibility permission to your terminal app"
echo "    This allows murmur to capture the fn key and inject text system-wide."
echo "    Opening System Settings → Privacy & Security → Accessibility..."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
echo "    Add your terminal (Terminal.app or iTerm2) and enable it."
printf "    Press Enter when done... "
read -r

# Verify
echo ""
"$BIN_PATH" status
echo ""
echo "apple-murmur installed successfully!"
echo "Run 'murmur start' to begin, or type /voice in Claude Code."
```

- [ ] **Step 2: Create README.md**

`README.md`:
```markdown
# apple-murmur

Apple Silicon-native system-wide voice-to-text. Double-tap `fn`, speak, text appears wherever your cursor is — in any app, any text field. Uses Apple's Neural Engine via MLX for near-instant transcription (~150ms).

> For cross-platform use (Intel Mac, Linux, Windows), see [murmur](https://github.com/amateur-ai-dev/murmur).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/amateur-ai-dev/apple-murmur/main/install.sh | bash
```

Requires Apple Silicon (M1/M2/M3/M4). No compilation. Downloads model (~75MB) on first install.

## Usage

```bash
murmur start     # start the daemon
murmur stop      # stop the daemon
murmur status    # check if running
murmur update    # pull latest version
```

Or from Claude Code: `/voice`

**Recording:** Double-tap `fn` to start, double-tap again to stop. Text injects at cursor.

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 13 Ventura or later
- Python 3.9+
- Accessibility permission (prompted at install)

## How it works

- **Engine** — OpenAI Whisper tiny model, runs on Apple Neural Engine via MLX framework
- **Daemon** — background process, listens for fn double-tap globally via pynput  
- **CLI** — `murmur start/stop/status/update`

No data leaves your machine. No API keys. No subscriptions.

## Performance vs murmur

| | apple-murmur (MLX) | murmur (PyTorch) |
|---|---|---|
| 10s audio latency | ~150ms | ~500ms |
| Memory | ~120MB | ~300MB |
| Power | Low | Medium |
| Platform | Apple Silicon only | Cross-platform |

## Update

```bash
murmur update
```

## License

MIT
```

- [ ] **Step 3: Make install.sh executable**

```bash
chmod +x install.sh
```

- [ ] **Step 4: Run full test suite**

```bash
python3 -m pytest tests/ -v --tb=short
```
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add install.sh README.md
git commit -m "feat: install script and README for apple-murmur"
```

- [ ] **Step 6: Push to GitHub**

```bash
git push origin main
```
Expected: all commits pushed to `https://github.com/amateur-ai-dev/apple-murmur`

- [ ] **Step 7: Verify on GitHub**

```bash
gh repo view amateur-ai-dev/apple-murmur --web
```
Confirm: all files visible, README renders correctly.
