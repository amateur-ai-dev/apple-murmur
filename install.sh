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
    echo "For Intel Macs or other platforms, use murmur instead:"
    echo "  curl -fsSL https://raw.githubusercontent.com/amateur-ai-dev/murmur/main/install.sh | bash"
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
elif [ -d "$INSTALL_DIR" ]; then
    echo "==> Found existing data dir, preserving config and cloning fresh..."
    [ -f "$INSTALL_DIR/config.toml" ] && cp "$INSTALL_DIR/config.toml" /tmp/apple-murmur-config.toml.bak
    rm -rf "$INSTALL_DIR"
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
    [ -f /tmp/apple-murmur-config.toml.bak ] && mv /tmp/apple-murmur-config.toml.bak "$INSTALL_DIR/config.toml"
else
    echo "==> Cloning apple-murmur..."
    git clone --quiet "$REPO_URL" "$INSTALL_DIR"
fi

# Create venv and install deps
echo "==> Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip3 install --quiet -r "$INSTALL_DIR/requirements.txt"
pip3 install --quiet -e "$INSTALL_DIR"

# Download MLX model
MODEL_DIR="$INSTALL_DIR/models/whisper-tiny-mlx"
if [ ! -d "$MODEL_DIR" ]; then
    echo "==> Downloading whisper-tiny MLX model (~75MB, one-time)..."
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('$MODEL_REPO', local_dir='$MODEL_DIR')
print('Model downloaded.')
"
fi

# Install CLI wrapper
echo "==> Installing murmur CLI (may prompt for sudo password)..."
sudo tee "$BIN_PATH" > /dev/null << 'WRAPPER'
#!/usr/bin/env bash
source "$HOME/.apple-murmur/venv/bin/activate"
python3 -m murmur.cli "$@"
WRAPPER
sudo chmod +x "$BIN_PATH"

# Install Claude Code /voice command
CLAUDE_CMD_DIR="$HOME/.claude/commands"
if [ -d "$HOME/.claude" ]; then
    mkdir -p "$CLAUDE_CMD_DIR"
    cp "$INSTALL_DIR/scripts/claude_voice.md" "$CLAUDE_CMD_DIR/voice.md"
    echo "==> Installed /voice command for Claude Code"
fi

# macOS: Accessibility settings reminder (non-blocking)
echo ""
echo "==> NOTE: murmur needs Accessibility permission to capture the fn key system-wide."
echo "    If not already granted: System Settings -> Privacy & Security -> Accessibility"
echo "    Add your terminal app (Terminal.app or iTerm2) and enable it."
echo "    If already granted, ignore this — murmur will work immediately."

# Verify
echo ""
"$BIN_PATH" status
echo ""
echo "apple-murmur installed successfully!"
echo "Run 'murmur start' to begin, or type /voice in Claude Code."
